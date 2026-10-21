"""Stock engine component tarballs: inspection against the pin and manifest, and staging into the native engine folder.
Synthetic archives only; no host or network."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from omp_strata import engine_component as ec
from omp_strata.common import IntegrityError

VERSION = "0.1.46"
NAME = ec.archive_name(VERSION, "windows-x86_64", "cuda", "cuda13")
BUILD = {"version": VERSION, "source": "f-021-rel", "commit": "a7bdbfdabc9a", "archs": [75, 86, 89, 120],
         "ptx": True, "cuda": "13.0", "portable": True}
PAYLOAD = {"strata.exe": b"engine", "strata_kq.dll": b"kq", "cublas64_13.dll": b"cublas"}


def manifest_for(files: dict[str, bytes], **override) -> dict:
    data = {"schema_version": 2, "id": "strata-engine", "name": "strata-engine", "version": VERSION,
            "platform": "windows-x86_64", "backend": "cuda", "variant": "cuda13", "archs": ["sm_86", "sm_120"],
            "min_driver": {"nvidia": "580.65"}, "build_id": "a7bdbfdabc9a+cuda13.0", "entrypoint": "strata.exe",
            "files": [{"path": n, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in files.items()],
            "signature": {"alg": "ed25519", "key_id": "k", "value": "unverified"}}
    data.update(override)
    return data


def write_archive(path: Path, members: dict[str, bytes], *, links: tuple[str, ...] = ()) -> dict:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for name in links:
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = "strata.exe"
            tar.addfile(info)
    raw = path.read_bytes()
    return {"url": f"https://github.com/Niko1221/Strata/releases/download/v0.2.1/{path.name}", "file": path.name,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "sha256_source": "test"}


def members(build=BUILD, payload=PAYLOAD, **manifest_override) -> dict[str, bytes]:
    files = {**payload, "BUILD.json": json.dumps(build).encode()}
    return {**files, ec.MANIFEST: json.dumps(manifest_for(files, **manifest_override)).encode()}


class ArchiveCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.archive = self.dir / NAME

    def build(self, contents, **kw) -> dict:
        return write_archive(self.archive, contents, **kw)


class ComponentArchive(ArchiveCase):
    def test_inspection_derives_the_profile_pin_from_the_manifest_and_build(self):
        contents = members()
        artifact = self.build(contents)
        found = ec.inspect_archive(self.archive, artifact)
        self.assertEqual(found["engine_version"], VERSION)
        self.assertEqual(found["pin"], {"format": "tar.gz", "platform": "windows-x86_64", "backend": "cuda",
                                        "variant": "cuda13",
                                        "manifest_sha256": hashlib.sha256(contents[ec.MANIFEST]).hexdigest(),
                                        "build_id": "a7bdbfdabc9a+cuda13.0", "build_source": "f-021-rel",
                                        "build_commit": "a7bdbfdabc9a"})
        self.assertEqual(found["min_driver"], {"nvidia": "580.65"})

    def test_archive_bytes_must_match_the_artifact_pin(self):
        artifact = self.build(members())
        with self.assertRaises(IntegrityError):
            ec.inspect_archive(self.archive, {**artifact, "sha256": "0" * 64})

    def test_members_must_be_exactly_the_manifest_files(self):
        unlisted = members()
        unlisted["extra.dll"] = b"not in the manifest"
        listed_missing = members()
        del listed_missing["strata_kq.dll"]
        for contents in (unlisted, listed_missing):
            with self.subTest(names=sorted(contents)), self.assertRaises(IntegrityError):
                ec.inspect_archive(self.archive, self.build(contents))

    def test_member_bytes_must_match_the_manifest(self):
        contents = members()
        contents["strata.exe"] = b"tampered"  # same manifest, different bytes
        with self.assertRaises(IntegrityError):
            ec.inspect_archive(self.archive, self.build(contents))

    def test_links_nested_paths_and_case_folded_duplicates_are_refused(self):
        cases = {"link": dict(contents=members(), links=("evil.dll",)),
                 "nested": dict(contents={**members(), "sub/strata.exe": b"x"}),
                 "traversal": dict(contents={**members(), "../strata.exe": b"x"}),
                 "case": dict(contents={**members(), "STRATA.EXE": b"x"})}
        for label, case in cases.items():
            with self.subTest(label), self.assertRaises(IntegrityError):
                ec.inspect_archive(self.archive, self.build(case["contents"], links=case.get("links", ())))

    def test_build_and_manifest_identity_outside_the_lane_are_refused(self):
        cases = {"local build": members(build={**BUILD, "source": "local"}),
                 "build version": members(build={**BUILD, "version": "0.1.45"}),
                 "variant": members(variant="cuda12"),
                 "control runtime": members(min_runtime="0.1.46"),
                 "entrypoint": members(entrypoint="strata-vision.exe")}
        for label, contents in cases.items():
            with self.subTest(label), self.assertRaises(IntegrityError):
                ec.inspect_archive(self.archive, self.build(contents))

    def test_artifact_file_name_must_name_the_component_version(self):
        artifact = self.build(members())
        with self.assertRaises(IntegrityError):
            ec.inspect_archive(self.archive, {**artifact, "file": ec.archive_name("0.1.45", "windows-x86_64",
                                                                                  "cuda", "cuda13")})


class Staging(ArchiveCase):
    def setUp(self):
        super().setUp()
        self.artifact = self.build(members())
        self.pin = ec.inspect_archive(self.archive, self.artifact)["pin"]
        self.engine = self.dir / "root/runtime/strata/engine"

    def stage(self, pin=None):
        return ec.stage(self.archive, self.engine, self.artifact, pin or self.pin, engine_version=VERSION)

    def test_stage_writes_exactly_the_component_files_and_reuses_them(self):
        build = self.stage()
        self.assertEqual(build["source"], "f-021-rel")
        self.assertEqual(sorted(p.name for p in self.engine.iterdir()), sorted(members()))
        self.assertEqual((self.engine / "strata.exe").read_bytes(), b"engine")
        self.assertEqual(self.stage(), build)
        self.assertEqual(sorted(p.name for p in self.engine.parent.iterdir()), ["engine"])

    def test_a_pin_the_archive_does_not_match_stages_nothing(self):
        for key, value in (("manifest_sha256", "0" * 64), ("build_commit", "0123456"), ("build_id", "other")):
            with self.subTest(key), self.assertRaises(IntegrityError):
                self.stage({**self.pin, key: value})
            self.assertFalse(self.engine.exists())
        self.assertEqual(list(self.engine.parent.iterdir()) if self.engine.parent.exists() else [], [])

    def test_foreign_or_changed_engine_folder_content_is_refused_not_repaired(self):
        self.stage()
        (self.engine / "strata.exe").write_bytes(b"changed")
        with self.assertRaises(IntegrityError):
            self.stage()
        self.assertEqual((self.engine / "strata.exe").read_bytes(), b"changed")
        other = self.dir / "other/engine"
        other.mkdir(parents=True)
        (other / "strata.exe").write_bytes(b"an older single-zip engine")
        with self.assertRaises(IntegrityError):
            ec.stage(self.archive, other, self.artifact, self.pin, engine_version=VERSION)


if __name__ == "__main__":
    unittest.main()
