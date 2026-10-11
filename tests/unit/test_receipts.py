import copy
from pathlib import Path
import tempfile
import unittest

from omp_strata.common import atomic_write_json, read_json, sha256_file
from omp_strata.profile import Profile
from omp_strata.receipts import (gate_inventory, make_receipt, update_ledger, validate_receipt,
                                 validate_gpu_qualification, write_receipt)


def two_gpu_profile_data(data):
    data = copy.deepcopy(data)
    host = data["host"]
    for key in ("gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached"):
        host.pop(key, None)
    host["gpus"] = [
        dict(gpu_index=3, gpu_model="NVIDIA GeForce RTX 4090", arch="89",
             pci_bus_id="00000000:01:00.0", min_gpu_vram_mib=24000, display_attached=False),
        dict(gpu_index=1, gpu_model="NVIDIA GeForce RTX 3090", arch="86",
             pci_bus_id="00000000:02:00.0", min_gpu_vram_mib=24000, display_attached=True),
    ]
    setup = data["strata"]["setup_args"]
    setup.pop("gpu", None)
    setup.update(gpus=[3, 1], layer_split="auto", low_ram="off")
    return data


def gpu_qualification_fixture(profile, gate):
    cards, metrics = [], []

    def metric(name, value, unit="MiB"):
        metrics.append(dict(name=name, value=value, unit=unit, boundary="host", method="resource_sampler"))

    for required in profile.gpu_requirements:
        card = {key: required[key] for key in
                ("gpu_index", "gpu_model", "arch", "pci_bus_id", "display_attached")}
        prefix = f"gpu.{card['gpu_index']}"
        if gate == "G10":
            card.update(memory_total_mib=24576, driver_version="999.00", memory_used_mib=18000,
                        owned_count=1, foreign_compute_count=0,
                        graphics_client_count=int(card["display_attached"]), exclusive=True)
            metric(prefix + ".memory_total_mib", card["memory_total_mib"])
        elif gate == "G20":
            for name, used, owned in (("before_stop", 18000, 1), ("after_stop", 600, 0),
                                      ("after_restart", 18000, 1)):
                card[name] = dict(memory_used_mib=used, owned_count=owned, foreign_compute_count=0)
            card.update(released=True, restarted_owned=True)
            metric(prefix + ".memory_used_mib_after_stop", 600)
        else:
            card.update(peak_used_mib=18000, samples=10, unavailable_samples=0)
            metric(prefix + ".peak_used_mib", card["peak_used_mib"])
        cards.append(card)
    record = dict(schema_version=1, record_type="gpu_qualification", gate=gate,
                  profile_id=profile.id, profile_fingerprint=profile.fingerprint,
                  runtime_identity_sha256="d" * 64, cards=cards,
                  stage_order=dict(configured=[3, 1], staged=[1, 3], event="reordered", complete=True),
                  complete=True, missing=[])
    if gate == "G21":
        record.update(stage_order=None, gpu_used_mib_sum_peak=30000, min_available_ram_mib=12345.25)
        metric("gpu.sum.peak_used_mib", 30000)
        metric("min_available_ram_serving", record["min_available_ram_mib"] * 1024**2, "bytes")
    return record, metrics


class GpuQualificationTests(unittest.TestCase):
    def setUp(self):
        data = dict(profile_id="two-card-fixture", host=dict(min_driver_major=580),
                    strata=dict(setup_args={}))
        self.profile = Profile(Path("two-card-fixture.json"), two_gpu_profile_data(data))

    def validate(self, record, metrics, gate=None, require_complete=True):
        return validate_gpu_qualification(
            record, self.profile, gate=gate or record["gate"], runtime_identity_sha256="d" * 64,
            metrics=metrics, require_complete=require_complete)

    def test_complete_gate_records_and_optional_metrics(self):
        for gate in ("G10", "G20", "G21"):
            with self.subTest(gate=gate):
                record, metrics = gpu_qualification_fixture(self.profile, gate)
                self.assertEqual([], self.validate(record, metrics))
                if gate == "G10":
                    metrics.append(dict(name="gpu.3.memory_used_mib", value=18000, unit="MiB",
                                        boundary="host", method="resource_sampler"))
                    self.assertEqual([], self.validate(record, metrics))
                elif gate == "G20":
                    self.assertEqual([], self.validate(record, []))

    def test_record_schema_bindings_and_scrubbed_field_allowlist(self):
        original, metrics = gpu_qualification_fixture(self.profile, "G10")
        for key, value in (("schema_version", True), ("record_type", "other"), ("gate", "G21"),
                           ("profile_id", "other"), ("profile_fingerprint", "f" * 64),
                           ("runtime_identity_sha256", "e" * 64), ("runtime_identity_sha256", None),
                           ("raw_log", "unexpected"), ("complete", 1), ("missing", ["lost_card"])):
            with self.subTest(key=key, value=value):
                record = copy.deepcopy(original)
                record[key] = value
                self.assertTrue(self.validate(record, metrics, gate="G10"))

    def test_complete_unique_ordered_card_identity(self):
        original, metrics = gpu_qualification_fixture(self.profile, "G10")
        for cards in (original["cards"][:1], original["cards"] * 2,
                      original["cards"][::-1], [original["cards"][0]] * 2):
            with self.subTest(cards=cards):
                record = copy.deepcopy(original)
                record["cards"] = cards
                self.assertTrue(self.validate(record, metrics))
        for key, value in (("gpu_index", True), ("gpu_model", "NVIDIA GeForce RTX 3080"),
                           ("arch", "86"), ("pci_bus_id", "00000000:03:00.0"),
                           ("display_attached", True), ("serial", "unexpected")):
            with self.subTest(key=key):
                record = copy.deepcopy(original)
                record["cards"][0][key] = value
                self.assertTrue(self.validate(record, metrics))

    def test_startup_stage_order_is_complete_and_consistent(self):
        record, metrics = gpu_qualification_fixture(self.profile, "G10")
        for event in ("kept_1576", "kept_configured"):
            record["stage_order"].update(staged=[3, 1], event=event)
            self.assertEqual([], self.validate(record, metrics))
        for changes in (dict(configured=[1, 3]), dict(staged=[3, 3]), dict(staged=[1, 3]),
                        dict(complete=False), dict(staged=None, event="unavailable", complete=False)):
            with self.subTest(changes=changes):
                changed = copy.deepcopy(record)
                changed["stage_order"].update(changes)
                self.assertTrue(self.validate(changed, metrics))

    def test_g10_requires_each_cards_capacity_and_exclusive_owned_activity(self):
        original, metrics = gpu_qualification_fixture(self.profile, "G10")
        for key, value in (("memory_total_mib", 23000), ("memory_used_mib", 25000),
                           ("owned_count", 0), ("foreign_compute_count", 1),
                           ("graphics_client_count", 1), ("exclusive", False),
                           ("driver_version", None), ("driver_version", "579.00"),
                           ("driver_version", "unavailable"), ("memory_used_mib", None),
                           ("owned_count", True)):
            with self.subTest(key=key):
                record = copy.deepcopy(original)
                record["cards"][0][key] = value
                self.assertTrue(self.validate(record, metrics))

    def test_g20_release_and_restart_snapshots_cannot_be_overridden_by_flags(self):
        original, metrics = gpu_qualification_fixture(self.profile, "G20")
        for name, key, value in (("before_stop", "owned_count", 0),
                                  ("after_stop", "owned_count", 1),
                                  ("after_stop", "memory_used_mib", 1500),
                                  ("after_stop", "memory_used_mib", None),
                                  ("after_restart", "owned_count", 0),
                                  ("after_restart", "foreign_compute_count", 1)):
            with self.subTest(name=name, key=key):
                record = copy.deepcopy(original)
                record["cards"][1][name][key] = value
                self.assertTrue(self.validate(record, metrics))
        for key in ("released", "restarted_owned"):
            record = copy.deepcopy(original)
            record["cards"][1][key] = False
            self.assertTrue(self.validate(record, metrics))

    def test_g21_missing_sampling_is_not_complete(self):
        original, metrics = gpu_qualification_fixture(self.profile, "G21")
        for key, value in (("samples", 0), ("unavailable_samples", 1), ("peak_used_mib", None)):
            with self.subTest(key=key):
                record = copy.deepcopy(original)
                record["cards"][1][key] = value
                self.assertTrue(self.validate(record, metrics))
        for key, value in (("gpu_used_mib_sum_peak", 40000), ("min_available_ram_mib", None),
                           ("min_available_ram_mib", float("nan")), ("stage_order", {})):
            record = copy.deepcopy(original)
            record[key] = value
            self.assertTrue(self.validate(record, metrics))

    def test_metrics_require_complete_matching_values_and_units(self):
        for gate in ("G10", "G21"):
            record, original = gpu_qualification_fixture(self.profile, gate)
            for metrics in (original[1:], original + original[:1]):
                self.assertTrue(self.validate(record, metrics))
            for key, value in (("value", 1), ("unit", "bytes"), ("name", "gpu.9.peak_used_mib")):
                with self.subTest(gate=gate, key=key):
                    metrics = copy.deepcopy(original)
                    metrics[0][key] = value
                    self.assertTrue(self.validate(record, metrics))
        metrics = copy.deepcopy(original)
        metrics[-1]["value"] += 1
        self.assertTrue(self.validate(record, metrics))

    def test_incomplete_records_preserve_unavailable_metrics_without_passing(self):
        record, metrics = gpu_qualification_fixture(self.profile, "G21")
        record.update(complete=False, missing=["gpu_sample_unavailable"], gpu_used_mib_sum_peak=None)
        record["cards"][1].update(peak_used_mib=None, samples=0, unavailable_samples=10)
        for metric in metrics[1:3]:
            metric.update(value=None, method="unavailable")
        self.assertEqual([], self.validate(record, metrics, require_complete=False))
        self.assertTrue(self.validate(record, metrics))
        metrics[1]["method"] = "resource_sampler"
        self.assertTrue(self.validate(record, metrics, require_complete=False))


def receipt(**changes):
    values = dict(gate_id="G01", status="pass", execution_boundary="host_free",
                  expected="Invalid identities are rejected", observed="Changed hash rejected",
                  implementation_commit="a" * 40, profile_id="synthetic-profile",
                  identity_fingerprint="b" * 64,
                  evidence=[dict(kind="test_report", path_or_ref="report.json", sha256="c" * 64, scrubbed=True)])
    values.update(changes)
    return make_receipt(**values)


class ReceiptTests(unittest.TestCase):
    def comparison_receipt(self):
        kinds = ["comparison_plan", "paired_summary", *(["window_aggregate"] * 6), "verifier_aggregate"]
        return receipt(
            gate_id="G25", execution_boundary="evaluation",
            comparison=dict(comparison_id="comparison-a", comparison_class="same_host_product_route",
                            plan_sha256="c" * 64, paired_summary_sha256="c" * 64,
                            omp_binary_sha256="d" * 64, ninfer_manifest_sha256="e" * 64,
                            attempts_per_arm=18, paired_attempts=18, engine_only=False),
            evidence=[dict(kind=kind, path_or_ref=f"comparison/{index}.json",
                           sha256="c" * 64, scrubbed=True) for index, kind in enumerate(kinds)],
            limitations=["Engine, model, quantization and protocol differ."])

    def test_g25_requires_evaluation_and_complete_comparison(self):
        original = self.comparison_receipt()
        self.assertEqual([], validate_receipt(original))
        for field, value in (("execution_boundary", "host_free"), ("execution_boundary", "source"),
                             ("implementation_commit", None), ("profile_id", None),
                             ("identity_fingerprint", None), ("limitations", [])):
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(original)
                data[field] = value
                self.assertTrue(validate_receipt(data))
        for field in original["comparison"]:
            with self.subTest(missing=field):
                data = copy.deepcopy(original)
                del data["comparison"][field]
                self.assertTrue(validate_receipt(data))
        for field, value in (("attempts_per_arm", 17), ("paired_attempts", 17), ("engine_only", True)):
            with self.subTest(field=field):
                data = copy.deepcopy(original)
                data["comparison"][field] = value
                self.assertTrue(validate_receipt(data))

    def test_g25_evidence_must_be_complete_hashed_scrubbed_and_relative(self):
        original = self.comparison_receipt()
        for index in (0, 1, 2, 8):
            with self.subTest(missing_evidence=index):
                data = copy.deepcopy(original)
                data["evidence"].pop(index)
                self.assertTrue(validate_receipt(data))
        for field, value in (("sha256", None), ("sha256", "f" * 64), ("scrubbed", False),
                             ("path_or_ref", "../plan.json"), ("path_or_ref", "/plan.json"),
                             ("path_or_ref", "C:\\plan.json"), ("path_or_ref", "comparison/../plan.json")):
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(original)
                data["evidence"][0][field] = value
                self.assertTrue(validate_receipt(data))
        data = copy.deepcopy(original)
        data["evidence"][3] = copy.deepcopy(data["evidence"][2])
        self.assertTrue(validate_receipt(data))

    def test_g25_historical_not_applicable_needs_no_comparison(self):
        self.assertEqual([], validate_receipt(receipt(
            gate_id="G25", status="not_applicable", execution_boundary="evaluation",
            reason="No comparative claims")))

    def test_pass_and_unavailable_metrics(self):
        data = receipt(metrics=[dict(name="cache", value=None, unit="tokens", boundary="engine", method="unavailable")])
        self.assertEqual([], validate_receipt(data))
        data["metrics"][0]["method"] = "server_reported"
        self.assertTrue(validate_receipt(data))

    def test_pass_requires_evidence_and_exact_identities(self):
        for changes in ({"evidence": []}, {"implementation_commit": None},
                        {"implementation_commit": "a" * 39}, {"identity_fingerprint": None},
                        {"identity_fingerprint": "g" * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                receipt(**changes)
        for boundary, gate in (("real_host", "G10"), ("evaluation", "G24")):
            with self.subTest(boundary=boundary), self.assertRaises(ValueError):
                receipt(gate_id=gate, execution_boundary=boundary, profile_id=None)

    def test_mock_cannot_pass_hardware_or_evaluation(self):
        for gate in ("G11", "G24"):
            for boundary in ("source", "host_free"):
                with self.subTest(gate=gate, boundary=boundary), self.assertRaises(ValueError):
                    receipt(gate_id=gate, execution_boundary=boundary)

    def test_blocked_and_not_applicable_require_nonblank_reasons(self):
        for status in ("blocked", "not_applicable"):
            for reason in (None, "", "  "):
                with self.subTest(status=status, reason=reason), self.assertRaises(ValueError):
                    receipt(status=status, reason=reason)
            self.assertEqual([], validate_receipt(receipt(status=status, reason="Unavailable hardware")))

    def test_timestamp_type_and_unknown_fields(self):
        for value in ("2026-09-30T12:00:00+00:00", "2026-02-30T00:00:00Z", "yesterday"):
            with self.subTest(timestamp=value), self.assertRaises(ValueError):
                receipt(timestamp_utc=value)
        data = receipt()
        data["schema_version"] = True
        self.assertTrue(validate_receipt(data))
        data = receipt()
        data["evidence"][0]["secret"] = "unexpected"
        self.assertTrue(validate_receipt(data))
        data = receipt()
        data["metrics"] = [dict(name="wall", value=float("nan"), unit="ms", boundary="request", method="calculated")]
        self.assertTrue(validate_receipt(data))

    def test_append_only_history_newest_timestamp_wins_and_runs_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = dict(profile_id="synthetic-profile", profile_fingerprint="b" * 64,
                          gates=[dict(copy.deepcopy(g), receipts=[]) for g in gate_inventory().values()])
            path = root / "qualification.json"
            atomic_write_json(path, ledger)
            first = write_receipt(root, receipt(run_id="first", timestamp_utc="2026-09-30T10:00:00Z"))
            update_ledger(path, first)
            later = write_receipt(root, receipt(run_id="later", status="fail", timestamp_utc="2026-09-30T11:00:00Z"))
            update_ledger(path, later)
            old = write_receipt(root, receipt(run_id="older", timestamp_utc="2026-09-30T09:00:00Z"))
            update_ledger(path, old)
            gate = next(g for g in read_json(path)["gates"] if g["id"] == "G01")
            self.assertEqual("fail", gate["status"])
            self.assertEqual(["first.json", "later.json", "older.json"], gate["receipt_paths"])
            self.assertEqual(sha256_file(first), gate["receipts"][0]["sha256"])
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "duplicate run_id"):
                update_ledger(path, first)
            self.assertEqual(before, path.read_bytes())
            with self.assertRaises(FileExistsError):
                write_receipt(root, read_json(first))
            first.write_text("{}")
            next_receipt = write_receipt(root, receipt(run_id="newest"))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                update_ledger(path, next_receipt)
            self.assertEqual(before, path.read_bytes())

    def test_receipt_filename_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_receipt(Path(tmp), receipt(run_id="../escape"))
