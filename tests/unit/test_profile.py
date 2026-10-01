"""G01: reject unusable or silently expanded candidate configurations."""
import copy
from pathlib import Path
import unittest

from omp_strata.common import read_json
from omp_strata.profile import load, validate

from tests.candidate import PROFILE


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.data = read_json(PROFILE)

    def test_committed_profile_and_canonical_fingerprint(self):
        profile = load(PROFILE)
        self.assertEqual([], validate(self.data))
        from omp_strata.profile import Profile
        reordered = dict(reversed(list(self.data.items())))
        self.assertEqual(profile.fingerprint, Profile(PROFILE, reordered).fingerprint)
        changed = copy.deepcopy(self.data)
        changed["omp"]["max_tokens"] -= 1
        self.assertNotEqual(profile.fingerprint, Profile(PROFILE, changed).fingerprint)

    def test_missing_component_pins(self):
        cases = [("strata", "commit"), ("omp", "source_commit"), ("model", "revision"),
                 ("model", "mtp_source", "revision"), ("omp", "artifacts"),
                 ("model", "files"), ("strata", "artifacts", "engine_archive"),
                 ("strata", "artifacts", "llama_cpp_archive")]
        for keys in cases:
            with self.subTest(keys=keys):
                data = copy.deepcopy(self.data)
                parent = data
                for key in keys[:-1]:
                    parent = parent[key]
                del parent[keys[-1]]
                self.assertTrue(validate(data))
        for key in ("sha256", "bytes", "url", "sha256_source"):
            with self.subTest(artifact_pin=key):
                data = copy.deepcopy(self.data)
                del data["omp"]["artifacts"]["linux-x64"][key]
                self.assertTrue(validate(data))

    def test_artifact_urls_are_immutable_https(self):
        for url in ("http://example.com/pinned", "https://example.com/releases/latest/binary",
                    "https://example.com/resolve/main/model"):
            with self.subTest(url=url):
                self.data["omp"]["artifacts"]["linux-x64"]["url"] = url
                self.assertTrue(validate(self.data))

    def test_sentinels_cannot_reach_launch(self):
        for value in ("RESOLVE_" + "MODEL", "TO" + "DO", "<" + "placeholder>"):
            with self.subTest(value=value):
                self.data["strata"]["model_name"] = value
                self.assertTrue(validate(self.data))

    def test_budgets_route_key_policy_and_setup(self):
        changes = [("strata", "setup_args", "context", 100000),
                   ("omp", "context_window", 8192),
                   ("omp", "max_tokens", self.data["omp"]["context_window"] // 2 + 1),
                   ("server", "listen_host", "0.0.0.0"),
                   ("server", "api_key_env", ""),
                   ("strata", "setup_args", "low_ram", "auto"),
                   ("strata", "setup_args", "vision", "yes"),
                   ("strata", "setup_args", "experimental_speed_projection", "on")]
        for *keys, value in changes:
            with self.subTest(keys=keys):
                data = copy.deepcopy(self.data)
                parent = data
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                self.assertTrue(validate(data))

    def test_unsupported_capabilities_and_tuning(self):
        for capability in ("vision", "remote_client", "durable_engine_state", "multi_tenant"):
            with self.subTest(capability=capability):
                data = copy.deepcopy(self.data)
                data["capabilities"][capability] = True
                self.assertTrue(validate(data))
        for flag in ("--pcie-frac", "--pool-workers", "--spec-min-p-tuned", "--adapt-every"):
            with self.subTest(flag=flag):
                data = copy.deepcopy(self.data)
                data["strata"]["expected_engine_flags"].extend([flag, "1"])
                self.assertTrue(validate(data))
        self.data["strata"]["forbidden_engine_flags"].append("--max-context")
        self.assertTrue(validate(self.data))

    def test_python_lock_null_is_draft_only(self):
        for status in ("draft", "candidate", "qualified"):
            for digest in (None, "a" * 64, "a" * 63):
                with self.subTest(status=status, digest=digest):
                    data = copy.deepcopy(self.data)
                    data["status"] = status
                    data["strata"]["python_lock"]["sha256"] = digest
                    problems = validate(data)
                    expected_valid = digest == "a" * 64 or (digest is None and status == "draft")
                    self.assertEqual(expected_valid, not problems, problems)
