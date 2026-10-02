"""Generated support claims must follow bound evidence, not optimistic manifest labels."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import io
from pathlib import Path
import re
import tempfile
import unittest

from omp_strata.common import atomic_write_json, read_json, sha256_file
from omp_strata.profile import load, load_route
from omp_strata.ompcfg import CHAT_ROLES
from omp_strata.receipts import gate_inventory, make_receipt
from scripts import render_compatibility as matrix

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "profiles/win11-rtx5090-coder-iq1m-131k.json"


class MatrixTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def candidate(self, pid, status="draft", outcomes=None):
        data = read_json(BASE)
        data.update(profile_id=pid, status=status)
        profile_path = self.root / "profiles" / f"{pid}.json"
        atomic_write_json(profile_path, data)
        profile = load(profile_path)
        release = self.root / "releases" / pid
        gates = []
        for gid, spec in gate_inventory().items():
            outcome = (outcomes or {}).get(gid, "not_run")
            gate = dict(id=gid, key=spec["key"], required=spec["required"],
                        execution_boundary=spec["execution_boundary"], status=outcome,
                        receipts=[], receipt_paths=[])
            if outcome != "not_run":
                receipt = make_receipt(gate_id=gid, status=outcome, execution_boundary=spec["execution_boundary"],
                                       implementation_commit="a" * 40, profile_id=pid,
                                       identity_fingerprint=profile.fingerprint, expected="Fixture scenario passes",
                                       observed="Fixture result", run_id=gid.lower() + "-fixture",
                                       timestamp_utc="2026-10-01T00:00:00Z",
                                       reason="Fixture capability disabled or scenario prevented"
                                       if outcome in ("not_applicable", "blocked", "fail") else None,
                                       evidence=[dict(kind="test_report", path_or_ref="fixture.json", sha256=None,
                                                      scrubbed=True)])
                path = release / "receipts" / f"{gid}.json"
                atomic_write_json(path, receipt)
                relative = path.relative_to(release).as_posix()
                gate["receipts"] = [dict(path=relative, sha256=sha256_file(path))]
                gate["receipt_paths"] = [relative]
            gates.append(gate)
        ledger_path = release / "qualification.json"
        atomic_write_json(ledger_path, dict(profile_id=pid, profile_fingerprint=profile.fingerprint, gates=gates))
        manifest = dict(schema_version=1, candidate_id=pid, status=status, publication_authorized=False,
                        profile=dict(path=f"../../profiles/{pid}.json", fingerprint=profile.fingerprint),
                        install=dict(runtime_identity_sha256=None, generated_files=[]),
                        capabilities=copy.deepcopy(data["capabilities"]),
                        claims=dict(comparative_claims=False, engine_only_comparison=False),
                        qualification=dict(ledger="qualification.json", ledger_sha256=sha256_file(ledger_path)),
                        blockers=[])
        atomic_write_json(release / "manifest.json", manifest)
        return release

    def rows(self):
        server_table = matrix.render(self.root).split("## Client routes", 1)[0]
        lines = [line for line in server_table.splitlines() if line.startswith("| ")]
        names = [v.strip() for v in lines[0].strip("|").split("|")]
        return [dict(zip(names, [v.strip() for v in line.strip("|").split("|")])) for line in lines[2:]]

    def test_draft_and_failed_gate_are_not_qualified(self):
        self.candidate("draft-fixture", outcomes={"G04": "fail", "G10": "blocked", "G22": "not_applicable"})
        row, = self.rows()
        self.assertEqual(("draft", "no", "fail", "blocked", "not_run", "not_applicable"),
                         tuple(row[k] for k in ("Manifest status", "Qualified", "G04", "G10", "G11", "G22")))
        self.assertEqual("131072", row["Configured context"])
        self.assertEqual("off", row["Low-RAM mode"])
        self.assertEqual("coder / IQ1_M", row["Model variant / quantization"])

    def test_qualified_claim_requires_bound_receipts(self):
        outcomes = {gid: "pass" if spec["required"] == "always" else "not_applicable"
                    for gid, spec in gate_inventory().items()}
        release = self.candidate("qualified-fixture", "qualified", outcomes)
        self.assertEqual("yes", self.rows()[0]["Qualified"])
        receipt = release / "receipts/G10.json"
        receipt.write_bytes(receipt.read_bytes() + b"\n")
        self.assertEqual("no", self.rows()[0]["Qualified"])
        self.assertEqual("pass", self.rows()[0]["G10"])

    def test_qualified_label_without_real_proofs_is_not_qualified(self):
        self.candidate("unproven-fixture", "qualified")
        self.assertEqual("no", self.rows()[0]["Qualified"])

    def test_ordering_and_render_bytes_are_deterministic(self):
        self.candidate("zulu-fixture")
        self.candidate("alpha-fixture")
        expected = matrix.render(self.root)
        self.assertEqual(["alpha-fixture", "zulu-fixture"], [row["Profile id"] for row in self.rows()])
        self.assertEqual(expected, matrix.render(self.root))

    def test_missing_ledger_is_not_reported_as_not_run(self):
        release = self.candidate("missing-fixture")
        (release / "qualification.json").unlink()
        row, = self.rows()
        self.assertEqual(("no", "missing"), (row["Qualified"], row["G10"]))

    def test_stale_check_never_overwrites_and_render_repairs_it(self):
        self.candidate("stale-fixture")
        args = ["--root", str(self.root)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(1, matrix.main(args + ["--check"]))
            self.assertEqual(0, matrix.main(args))
            self.assertEqual(0, matrix.main(args + ["--check"]))
            dest = self.root / "docs/COMPATIBILITY.md"
            dest.write_text("stale\n", encoding="utf-8")
            self.assertEqual(1, matrix.main(args + ["--check"]))
            self.assertEqual(b"stale\n", dest.read_bytes())
            self.assertEqual(0, matrix.main(args))
            self.assertEqual(0, matrix.main(args + ["--check"]))


class ClientRouteMatrixTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        atomic_write_json(self.root / "profiles" / BASE.name, read_json(BASE))
        self.server = load(BASE)

    def route(self, pid, labels):
        path = self.root / "routes" / f"{pid}.json"
        data = dict(schema_version=1, kind="client-route", profile_id=pid, status="draft",
                    members=[dict(label=label, server_profile=self.server.id,
                                  server_fingerprint=self.server.fingerprint, local_port=19000 + i)
                             for i, label in enumerate(labels)],
                    roles={role: labels[0] for role in CHAT_ROLES}, agents={})
        atomic_write_json(path, data)
        route = load_route(path, profiles_dir=self.root / "profiles")
        spec = gate_inventory()["G23"]
        ledger = dict(profile_id=pid, profile_fingerprint=route.fingerprint,
                      gates=[dict(id="G23", key=spec["key"], required="always",
                                  execution_boundary=spec["execution_boundary"], status="not_run",
                                  receipts=[], receipt_paths=[])])
        release = self.root / "releases" / pid
        atomic_write_json(release / "qualification.json", ledger)
        manifest = dict(schema_version=1, kind="client-route", candidate_id=pid, status="draft",
                        publication_authorized=False,
                        profile=dict(path=f"../../routes/{pid}.json", fingerprint=route.fingerprint),
                        install=dict(runtime_identity_sha256=None, generated_files=[]),
                        capabilities={key: key == "remote_client" for key in self.server.data["capabilities"]},
                        claims=dict(comparative_claims=False, engine_only_comparison=False),
                        qualification=dict(ledger="qualification.json",
                                           ledger_sha256=sha256_file(release / "qualification.json")), blockers=[])
        atomic_write_json(release / "manifest.json", manifest)
        return release

    def rows(self):
        text = matrix.render(self.root).split("## Client routes", 1)[1]
        lines = [line for line in text.splitlines() if line.startswith("| ")]
        names = [v.strip() for v in lines[0].strip("|").split("|")]
        return [dict(zip(names, [v.strip() for v in line.strip("|").split("|")])) for line in lines[2:]]

    def test_draft_routes_show_shape_members_and_their_own_gate_evidence(self):
        fleet = self.route("zulu-fleet", ["rtx4090-win-a", "rtx3090-win-a"])
        self.route("alpha-client", ["rtx4090-win-a"])
        ledger_path = fleet / "qualification.json"
        ledger = read_json(ledger_path)
        ledger["gates"].append(dict(id="G04", status="fail"))
        atomic_write_json(ledger_path, ledger)
        rows = self.rows()
        self.assertEqual(["alpha-client", "zulu-fleet"], [row["Route id"] for row in rows])
        self.assertEqual(["client-route / single host", "client-route / fleet"],
                         [row["Kind / shape"] for row in rows])
        self.assertEqual(["1", "2"], [row["Members"] for row in rows])
        self.assertEqual(["draft", "draft"], [row["Manifest status"] for row in rows])
        self.assertEqual(["no", "no"], [row["Qualified"] for row in rows])
        self.assertEqual(["not_run", "not_run"], [row["G23"] for row in rows])
        self.assertEqual(["missing", "fail"], [row["G04"] for row in rows])
        self.assertEqual("rtx3090-win-a → " + self.server.id + "; rtx4090-win-a → " + self.server.id,
                         rows[1]["Member → server profile"])
        ledger_path.unlink()
        self.assertEqual("missing", self.rows()[1]["G23"])

    def test_route_change_invalidates_generated_file_and_bad_pins_refuse_render(self):
        release = self.route("client-fixture", ["rtx4090-win-a"])
        args = ["--root", str(self.root)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(0, matrix.main(args))
            self.assertEqual(0, matrix.main(args + ["--check"]))
            manifest_path = release / "manifest.json"
            manifest = read_json(manifest_path)
            manifest["status"] = "candidate"
            atomic_write_json(manifest_path, manifest)
            self.assertEqual(1, matrix.main(args + ["--check"]))
            self.assertEqual(0, matrix.main(args))
            self.assertEqual(0, matrix.main(args + ["--check"]))
        path = self.root / "routes/client-fixture.json"
        data = read_json(path)
        data["members"][0]["server_fingerprint"] = "0" * 64
        atomic_write_json(path, data)
        with self.assertRaisesRegex(ValueError, "route member server fingerprint mismatch"):
            matrix.render(self.root)


class TroubleshootingDriftTests(unittest.TestCase):
    def test_every_quoted_symptom_exists_in_its_referenced_source(self):
        text = (ROOT / "docs/TROUBLESHOOTING.md").read_text(encoding="utf-8")
        entries = re.findall(r"^### `([^`]+)`\n<!-- symptom-source: ([^>]+) -->", text, re.M)
        quoted = re.findall(r"`([^`]+)`", text)
        self.assertEqual([symptom for symptom, _ in entries], quoted,
                         "Every quoted diagnostic needs a source annotation")
        self.assertTrue(entries, "The symptom guide must not silently become empty")
        for symptom, source in entries:
            with self.subTest(symptom=symptom):
                path = ROOT / source
                self.assertIn(source.split("/")[0], ("omp_strata", "scripts", "docs"))
                self.assertNotEqual(path.name, "TROUBLESHOOTING.md")
                self.assertIn(symptom, path.read_text(encoding="utf-8"),
                              "Diagnostic changed; update the symptom and recovery advice together")


if __name__ == "__main__":
    unittest.main()
