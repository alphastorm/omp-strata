import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from omp_strata.common import atomic_write_json, read_json, sha256_file
from omp_strata.profile import load
from omp_strata.receipts import make_receipt, update_ledger, write_receipt
from scripts.verify_release import rebind, verify
from tests.candidate import CANDIDATE, REPO


class VerifyReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "manifest.json"
        self.ledger_path = self.root / "qualification.json"
        atomic_write_json(self.root / "profile.json", read_json(REPO / "profiles" / (CANDIDATE + ".json")))
        self.profile = load(self.root / "profile.json")
        self.manifest = read_json(REPO / "releases" / CANDIDATE / "manifest.json")
        self.manifest["profile"]["path"] = "profile.json"
        self.manifest["profile"]["fingerprint"] = self.profile.fingerprint
        self.ledger = read_json(REPO / "docs/handoff/2026-09-30/acceptance_matrix.json")
        self.ledger.update(profile_id=self.profile.id, profile_fingerprint=self.profile.fingerprint)
        for gate in self.ledger["gates"]:
            gate["receipts"] = []
        self.save()

    def save(self):
        atomic_write_json(self.ledger_path, self.ledger)
        self.manifest["qualification"]["ledger_sha256"] = sha256_file(self.ledger_path)
        atomic_write_json(self.path, self.manifest)

    def add_receipt(self, gid="G01", status="pass"):
        gate = next(g for g in self.ledger["gates"] if g["id"] == gid)
        rec = make_receipt(gate_id=gid, status=status, execution_boundary=gate["execution_boundary"],
                           implementation_commit="a" * 40, profile_id=self.profile.id,
                           identity_fingerprint=self.profile.fingerprint, expected="Scenario completes",
                           observed="Independent verifier confirms result",
                           reason="Capability disabled" if status == "not_applicable" else None,
                           evidence=[dict(kind="test_report", path_or_ref="report.json", sha256=None, scrubbed=True)])
        path = write_receipt(self.root / "receipts", rec)
        update_ledger(self.ledger_path, path)
        self.ledger = read_json(self.ledger_path)
        self.save()
        return path

    def add_comparison(self, plan_profile=None):
        from omp_strata.comparison import canonical, plan_digest
        from tests.unit.test_comparison import comparison_fixture

        plan, windows, summary = comparison_fixture(plan_profile or self.profile)
        evidence = []

        def publish(kind, name, data):
            path = self.root / name
            path.write_bytes(canonical(data) + b"\n")
            evidence.append(dict(kind=kind, path_or_ref=name, sha256=sha256_file(path), scrubbed=True))
            return evidence[-1]["sha256"]

        plan_hash = publish("comparison_plan", "plan.json", plan)
        for window in windows:
            publish("window_aggregate", f"window-{window['window']}.json", window)
        summary_hash = publish("paired_summary", "summary.json", summary)
        verifier = dict(schema_version=1, record_type="verifier_aggregate",
                        comparison_id=plan["comparison_id"], plan_sha256=plan_digest(plan), attempts=[])
        for pair in summary["pairs"]:
            for arm in ("strata", "ninfer"):
                verifier["attempts"].append(dict(
                    arm=arm, task_id=pair["task_id"], attempt_number=pair["attempt_number"],
                    attempt_sha256=pair[arm + "_sha256"],
                    verified_pass=pair["outcome"] in ("both_pass", arm + "_only")))
        publish("verifier_aggregate", "verifier.json", verifier)
        rec = make_receipt(
            gate_id="G25", status="pass", execution_boundary="evaluation",
            implementation_commit="a" * 40, profile_id=self.profile.id,
            identity_fingerprint=self.profile.fingerprint, expected="All paired outcomes retained",
            observed="36 outcomes across six exclusive evaluation windows", evidence=evidence,
            limitations=["Engine, model, quantization and protocol differ."],
            comparison=dict(comparison_id=plan["comparison_id"], comparison_class="same_host_product_route",
                            plan_sha256=plan_hash, paired_summary_sha256=summary_hash,
                            omp_binary_sha256=plan["omp"]["sha256"],
                            ninfer_manifest_sha256=plan["ninfer"]["manifest_sha256"],
                            attempts_per_arm=18, paired_attempts=18, engine_only=False))
        path = write_receipt(self.root / "receipts", rec)
        update_ledger(self.ledger_path, path)
        self.ledger = read_json(self.ledger_path)
        self.save()
        return path

    def replace_comparison_receipt(self, path, data):
        atomic_write_json(path, data)
        gate = next(g for g in self.ledger["gates"] if g["id"] == "G25")
        gate["receipts"][0]["sha256"] = sha256_file(path)
        self.save()

    def rehash_comparison_evidence(self, receipt_path, name):
        data = read_json(receipt_path)
        ref = next(ref for ref in data["evidence"] if ref["path_or_ref"] == name)
        ref["sha256"] = sha256_file(self.root / name)
        key = {"comparison_plan": "plan_sha256", "paired_summary": "paired_summary_sha256"}.get(ref["kind"])
        if key:
            data["comparison"][key] = ref["sha256"]
        self.replace_comparison_receipt(receipt_path, data)

    def test_g25_complete_release_export_and_cli(self):
        self.add_comparison()
        for gate in list(self.ledger["gates"]):
            if gate["id"] != "G25":
                self.add_receipt(gate["id"], "pass" if gate["required"] == "always" else "not_applicable")
        self.manifest["claims"]["comparative_claims"] = True
        self.manifest["status"] = "qualified"
        self.manifest["blockers"] = []
        self.save()
        self.assertEqual([], verify(self.path, require_ready=True)["errors"])
        result = subprocess.run([sys.executable, str(REPO / "scripts/verify_release.py"),
                                 "--manifest", str(self.path), "--require-ready", "--json"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stdout)

    def test_g25_wrong_receipt_pins_and_engine_only_are_refused(self):
        path = self.add_comparison()
        original = read_json(path)
        for field, value, expected in (("omp_binary_sha256", "f" * 64, "OMP binary pin"),
                                       ("ninfer_manifest_sha256", "f" * 64, "NInfer manifest pin"),
                                       ("engine_only", True, "engine_only")):
            with self.subTest(field=field):
                data = copy.deepcopy(original)
                data["comparison"][field] = value
                self.replace_comparison_receipt(path, data)
                self.assertTrue(any(expected in e for e in verify(self.path)["errors"]))

    def test_g25_evidence_traversal_hashless_missing_and_changed_bytes(self):
        path = self.add_comparison()
        original = read_json(path)
        for field, value, expected in (("path_or_ref", "../plan.json", "traversal"),
                                       ("path_or_ref", "absent.json", "evidence missing"),
                                       ("sha256", None, "invalid type")):
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(original)
                data["evidence"][0][field] = value
                self.replace_comparison_receipt(path, data)
                self.assertTrue(any(expected in e for e in verify(self.path)["errors"]))
        self.replace_comparison_receipt(path, original)
        with (self.root / "plan.json").open("a") as out:
            out.write("\n")
        self.assertIn("G25: evidence sha256 mismatch", verify(self.path)["errors"])

    def test_g25_symlink_cannot_escape_release(self):
        self.add_comparison()
        with tempfile.TemporaryDirectory() as outside:
            source = self.root / "plan.json"
            target = Path(outside) / "plan.json"
            target.write_bytes(source.read_bytes())
            source.unlink()
            try:
                source.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Creating symlinks is unavailable on this platform")
            self.assertIn("G25: evidence escapes release directory", verify(self.path)["errors"])

    def test_g25_self_consistent_export_cannot_qualify_a_stale_profile(self):
        data = copy.deepcopy(self.profile.data)
        data["omp"]["max_tokens"] -= 1
        stale_path = self.root / "stale-profile.json"
        atomic_write_json(stale_path, data)
        self.add_comparison(load(stale_path))
        self.assertIn("G25: plan Strata profile fingerprint or id mismatch", verify(self.path)["errors"])

    def test_g25_rehashed_incomplete_exports_are_refused(self):
        path = self.add_comparison()
        for name, mutate in (
                ("summary.json", lambda data: data["pairs"].pop()),
                ("summary.json", lambda data: data["windows"].pop()),
                ("summary.json", lambda data: data.update(ordered_records_sha256="f" * 64)),
                ("summary.json", lambda data: data["host"].update(driver="changed-driver")),
                ("verifier.json", lambda data: data["attempts"].pop()),
                ("verifier.json", lambda data: data["attempts"][0].update(verified_pass=False)),
                ("window-1.json", lambda data: data.update(exclusive_gpu=False))):
            with self.subTest(name=name):
                target = self.root / name
                original = target.read_bytes()
                data = read_json(target)
                mutate(data)
                atomic_write_json(target, data)
                self.rehash_comparison_evidence(path, name)
                self.assertTrue(verify(self.path)["errors"])
                target.write_bytes(original)
                self.rehash_comparison_evidence(path, name)

    def test_consistent_draft_cli_and_ready_refusal(self):
        command = [sys.executable, str(REPO / "scripts/verify_release.py"), "--manifest", str(self.path), "--json"]
        draft = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, draft.returncode, draft.stdout)
        ready = subprocess.run(command + ["--require-ready"], capture_output=True, text=True, timeout=15)
        self.assertEqual(1, ready.returncode)
        self.assertIn("G10: required gate is not_run", ready.stdout)
        self.assertIn("G24: required gate is not_run", ready.stdout)
        self.assertIn("G26: required gate is not_run", ready.stdout)

    def test_qualified_requires_all_applicable_gates(self):
        for gate in list(self.ledger["gates"]):
            self.add_receipt(gate["id"], "pass" if gate["required"] == "always" else "not_applicable")
        self.manifest["status"] = "qualified"
        self.manifest["blockers"] = []
        self.save()
        self.assertEqual([], verify(self.path, require_ready=True)["errors"])
        self.manifest["claims"]["comparative_claims"] = True
        self.save()
        self.assertTrue(any("G25" in e for e in verify(self.path, require_ready=True)["errors"]))

    def test_comparative_not_run_refused_by_ready_cli(self):
        self.manifest["claims"]["comparative_claims"] = True
        self.save()
        command = [sys.executable, str(REPO / "scripts/verify_release.py"),
                   "--manifest", str(self.path), "--require-ready", "--json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(1, result.returncode)
        self.assertIn("G25: required gate is not_run", result.stdout)

    def test_profile_missing_invalid_and_fingerprint_drift(self):
        path = self.root / "profile.json"
        original = path.read_bytes()
        path.unlink()
        self.assertTrue(verify(self.path)["errors"])
        path.write_text("{}")
        self.assertTrue(verify(self.path)["errors"])
        path.write_bytes(original)
        data = read_json(path)
        data["omp"]["max_tokens"] -= 1
        atomic_write_json(path, data)
        self.assertIn("profile fingerprint mismatch", verify(self.path)["errors"])

    def test_ledger_hash_drift_and_inventory_cannot_weaken_requirements(self):
        self.ledger_path.write_text(self.ledger_path.read_text() + "\n")
        self.assertIn("ledger sha256 mismatch", verify(self.path)["errors"])
        self.ledger["gates"] = [g for g in self.ledger["gates"] if g["id"] != "G10"]
        self.save()
        self.assertTrue(any("inventory" in e for e in verify(self.path)["errors"]))

    def test_rebind_refreshes_hashes_but_never_rewrites_stale_receipts(self):
        path = self.add_receipt()
        original = path.read_bytes()
        data = read_json(self.root / "profile.json")
        data["omp"]["max_tokens"] -= 1
        atomic_write_json(self.root / "profile.json", data)
        rebind(self.path)
        bound = read_json(self.path)
        profile = load(self.root / "profile.json")
        self.assertEqual(profile.fingerprint, bound["profile"]["fingerprint"])
        self.assertEqual(profile.fingerprint, read_json(self.ledger_path)["profile_fingerprint"])
        self.assertEqual(sha256_file(self.ledger_path), bound["qualification"]["ledger_sha256"])
        self.assertEqual(original, path.read_bytes())
        self.assertTrue(any("receipt fingerprint mismatch" in e for e in verify(self.path)["errors"]))
        manifest_bytes = self.path.read_bytes()
        ledger_bytes = self.ledger_path.read_bytes()
        rebind(self.path)
        self.assertEqual(manifest_bytes, self.path.read_bytes())
        self.assertEqual(ledger_bytes, self.ledger_path.read_bytes())

    def test_receipt_missing_hash_identity_boundary_and_schema_failures(self):
        path = self.add_receipt()
        original = path.read_bytes()
        path.unlink()
        self.assertTrue(any("missing" in e for e in verify(self.path)["errors"]))
        path.write_bytes(original + b"\n")
        self.assertTrue(any("receipt sha256" in e for e in verify(self.path)["errors"]))
        path.write_bytes(original)
        rec = read_json(path)
        gate = next(g for g in self.ledger["gates"] if g["id"] == "G01")
        for key, value, expected in (("identity_fingerprint", "f" * 64, "fingerprint"),
                                     ("execution_boundary", "source", "boundary"),
                                     ("evidence", [], "too few items")):
            with self.subTest(key=key):
                changed = copy.deepcopy(rec)
                changed[key] = value
                atomic_write_json(path, changed)
                gate["receipts"][0]["sha256"] = sha256_file(path)
                self.save()
                self.assertTrue(any(expected in e for e in verify(self.path)["errors"]))

    def test_gate_status_and_duplicate_run_ids_are_not_trusted(self):
        first = self.add_receipt()
        second = self.add_receipt("G02")
        data = read_json(second)
        data["run_id"] = read_json(first)["run_id"]
        atomic_write_json(second, data)
        gate = next(g for g in self.ledger["gates"] if g["id"] == "G02")
        gate["receipts"][0]["sha256"] = sha256_file(second)
        gate["status"] = "fail"
        self.save()
        errors = verify(self.path)["errors"]
        self.assertTrue(any("duplicate run_id" in e for e in errors))
        self.assertTrue(any("newest receipt" in e for e in errors))

    def test_capabilities_publication_and_unbacked_pass(self):
        for capability in ("vision", "remote_client", "durable_engine_state", "multi_tenant"):
            with self.subTest(capability=capability):
                self.manifest["capabilities"][capability] = True
                self.save()
                self.assertTrue(verify(self.path)["errors"])
                self.manifest["capabilities"][capability] = False
        self.manifest["publication_authorized"] = True
        self.save()
        self.assertTrue(verify(self.path)["errors"])
        self.manifest["publication_authorized"] = False
        self.ledger["gates"][0]["status"] = "pass"
        self.save()
        self.assertTrue(any("no receipt" in e for e in verify(self.path)["errors"]))
