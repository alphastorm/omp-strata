import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata.layout import Layout
from omp_strata.profile import Profile

from scripts import realhost_gates as gates

# Stock OMP's default compaction threshold for each profile window (the window OMP is given is 1,024 smaller).
THRESHOLDS = {131_072: 110_541, 262_144: 221_952, 524_288: 444_775}


def window(profile_window: int) -> int:
    return gates.omp_window({"omp": {"context_window": profile_window}})


class ContextScaledFixtures(unittest.TestCase):
    """g17's near-limit prompt and g18l's long session follow the profile's window: a fixed 131K-sized g18l session
    peaked at 162K tokens on a 262K profile and never reached OMP's threshold, so the gate could not pass."""

    def test_threshold_follows_stock_omp(self):
        for profile_window, threshold in THRESHOLDS.items():
            self.assertEqual(gates.omp_compaction_threshold(window(profile_window), omp_version="18.8.6"), threshold)
        self.assertEqual(gates.omp_compaction_threshold(31_744, omp_version="18.8.6"), 31_744 - 16_384)

    def test_g18l_session_passes_the_threshold(self):
        for profile_window, threshold in THRESHOLDS.items():
            docs = gates.g18l_doc_count(window(profile_window), omp_version="18.8.6")
            self.assertGreater(docs * gates.G18L_DOC_TOKENS, threshold, profile_window)
        self.assertEqual(gates.g18l_doc_count(window(131_072), omp_version="18.8.6"), 20)

    def test_g17_near_limit_prompt_stays_just_under_the_threshold(self):
        for profile_window, threshold in THRESHOLDS.items():
            tokens = gates.g17_near_limit_tokens(window(profile_window), omp_version="18.8.6")
            self.assertLess(tokens, threshold, profile_window)
            self.assertGreater(tokens, 0.9 * threshold, profile_window)


class G17OverCapContract(unittest.TestCase):
    def test_one_token_over_the_room_is_refused_before_and_shortened_from_the_020_beta_engine(self):
        # v0.2.0-beta's server made fit_max_tokens the default (the v0.2.1 PRO and 5090 runs answered 200); a prompt that
        # alone leaves no room is still refused, which g17's OMP overflow step checks on every version.
        for version, shortens in (("0.1.44.1", False), ("0.1.45", False), ("0.1.45.3", True), ("0.1.46", True)):
            with self.subTest(version=version):
                self.assertEqual(shortens, gates.g17_shortens_over_cap(version))


def multi_profile() -> Profile:
    cards = [dict(gpu_index=2, gpu_model="NVIDIA GeForce RTX 4090", arch="89",
                  pci_bus_id="00000000:01:00.0", min_gpu_vram_mib=24000, display_attached=False),
             dict(gpu_index=0, gpu_model="NVIDIA GeForce RTX 3090", arch="86",
                  pci_bus_id="00000000:02:00.0", min_gpu_vram_mib=24000, display_attached=True)]
    return Profile(Path("two-gpu.json"), {"profile_id": "two-gpu-fixture", "host": {"gpus": cards,
                   "min_driver_major": 580}, "omp": {"version": "18.8.9", "context_window": 131072},
                   "strata": {"model_name": "fixture-model", "expected_engine_flags": []},
                   "server": {"listen_host": "127.0.0.1", "port": 18090}})


def observations(profile, *, owned=1, used=20000):
    return [{**{key: card[key] for key in ("gpu_index", "gpu_model", "arch", "pci_bus_id")},
             "memory_total_mib": 24576, "memory_used_mib": used, "driver_version": "580.1",
             "display_active": card["display_attached"], "owned_count": owned,
             "foreign_compute_count": 0, "graphics_client_count": int(card["display_attached"]),
             "problems": [] if owned else ["owned engine not observed on card"]}
            for card in profile.gpu_requirements]


def stage_order(profile):
    return dict(configured=list(profile.gpu_indices), staged=list(reversed(profile.gpu_indices)),
                event="reordered", complete=True)


def sampled_result(profile, *, peaks=(21000, 20000), total=40000):
    return {"gate": "G17", "pass_observed": False, "profile_fingerprint": profile.fingerprint,
            "runtime_identity_sha256": "a" * 64, "resource_samples": 2,
            "resources": {"gpus": [dict(gpu_index=card["gpu_index"], pci_bus_id=card["pci_bus_id"],
                                        peak_gpu_used_mib=peak, samples=2, unavailable_samples=0)
                                   for card, peak in zip(profile.gpu_requirements, peaks)],
                          "gpu_used_mib_sum_peak": total, "min_available_ram_bytes": 64000 * 1024**2 + 1,
                          "complete": True, "missing": []}}


class StockCompactionCases(unittest.TestCase):
    def test_source_backed_cases(self):
        path = Path(__file__).resolve().parents[1] / "fixtures/omp-compaction-thresholds.json"
        fixture = json.loads(path.read_text())
        self.assertEqual(fixture["sources"][0]["commit"], "fa5ff4a3a977a28b93d025f4cf50f046e019f18c")
        for case in fixture["cases"]:
            with self.subTest(case=case):
                kwargs = {key: value for key, value in case.items() if key != "expected"}
                self.assertEqual(gates.omp_compaction_threshold(**kwargs), case["expected"])

    def test_new_lane_derived_workloads_and_invalid_versions(self):
        for size in THRESHOLDS:
            threshold = gates.omp_compaction_threshold(window(size), omp_version="18.8.9")
            self.assertLess(gates.g17_near_limit_tokens(window(size), omp_version="18.8.9"), threshold)
            self.assertGreater(gates.g18l_doc_count(window(size), omp_version="18.8.9") * gates.G18L_DOC_TOKENS,
                               threshold)
        with self.assertRaises(ValueError):
            gates.omp_compaction_threshold(130048, omp_version="latest")
        with self.assertRaises(ValueError):
            gates.omp_compaction_threshold(130048, omp_version="18.8.6", model_entry="f12000")

    def test_g18_uses_exact_model_entry_only_on_new_lane(self):
        # Stop at the first real client invocation: inspect the actual gate's settings without a GPU or client.
        for version in ("18.8.6", "18.8.9"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as root:
                profile = multi_profile()
                profile.data["omp"]["version"] = version
                layout = Layout(Path(root), profile)
                with patch.object(gates.hostrun, "git_fixture", return_value=Path(root)), \
                     patch.object(gates.hostrun, "run_omp", side_effect=RuntimeError("stop fixture")) as run:
                    with self.assertRaisesRegex(RuntimeError, "stop fixture"):
                        gates.g18(layout, "fixture-key", Path(root))
                settings = run.call_args.kwargs["overrides"]["compaction"]
                if version == "18.8.9":
                    self.assertNotIn("thresholdTokens", settings)
                    self.assertEqual(settings["modelThresholds"], {"strata-local/fixture-model": "f12000"})
                else:
                    self.assertEqual(settings["thresholdTokens"], 12000)
                    self.assertNotIn("modelThresholds", settings)


class IndexedSamplerTests(unittest.TestCase):
    def sample(self, sampler, text, *, returncode=0):
        with patch.object(gates.subprocess, "run", return_value=SimpleNamespace(stdout=text, returncode=returncode)), \
             patch.object(gates.procs, "memory", return_value={"available": 50000000000}):
            sampler._sample_once()

    def test_reordered_rows_and_simultaneous_sum_not_sum_of_peaks(self):
        sampler = gates.Sampler(multi_profile())
        self.sample(sampler, "0, 00000000:02:00.0, 5\n2, 00000000:01:00.0, 100\n")
        self.sample(sampler, "2, 00000000:01:00.0, 10\n0, 00000000:02:00.0, 200\n")
        peak, samples = sampler.snapshot()
        self.assertEqual(samples, 2)
        self.assertEqual([row["peak_gpu_used_mib"] for row in peak["gpus"]], [100, 200])
        self.assertEqual(peak["gpu_used_mib_sum_peak"], 210)
        self.assertTrue(peak["complete"])
        peak["gpus"][0]["peak_gpu_used_mib"] = 999
        self.assertEqual(sampler.peak["gpus"][0]["peak_gpu_used_mib"], 100)

    def test_missing_wrong_bus_duplicates_and_failed_query_are_unavailable(self):
        sampler = gates.Sampler(multi_profile())
        self.sample(sampler, "0, 00000000:02:00.0, 5\n2, 00000000:03:00.0, 100\n")
        self.sample(sampler, "0, 00000000:02:00.0, 6\n0, 00000000:02:00.0, 7\n")
        self.sample(sampler, "2, 00000000:01:00.0, 100\n", returncode=1)
        peak = sampler.peak
        self.assertFalse(peak["complete"])
        self.assertIsNone(peak["gpu_used_mib_sum_peak"])
        self.assertIsNone(peak["gpus"][0]["peak_gpu_used_mib"])
        self.assertEqual(peak["gpus"][0]["unavailable_samples"], 3)
        self.assertEqual(peak["gpus"][1]["samples"], 1)
        self.assertEqual(peak["gpus"][1]["unavailable_samples"], 2)

    def test_bus_identity_normalizes_four_and_eight_digit_domains_and_case(self):
        profile = multi_profile()
        profile.data["host"]["gpus"][0]["pci_bus_id"] = "00000000:0a:00.0"
        profile.data["host"]["gpus"][1]["pci_bus_id"] = "00000000:0b:00.0"
        sampler = gates.Sampler(profile)
        self.sample(sampler, "0, 0000:0B:00.0, 5\n2, 00000000:0A:00.0, 100\n")
        self.sample(sampler, "2, 0000:0A:00.0, 10\n0, 00000000:0B:00.0, 200\n")
        peak = sampler.peak
        self.assertTrue(peak["complete"])
        self.assertEqual(peak["gpu_used_mib_sum_peak"], 210)
        self.assertEqual([row["samples"] for row in peak["gpus"]], [2, 2])
        self.assertEqual([row["unavailable_samples"] for row in peak["gpus"]], [0, 0])

    def test_incomplete_shutdown_and_ram_are_reported(self):
        sampler = gates.Sampler(multi_profile())
        self.sample(sampler, "0, 00000000:02:00.0, 5\n2, 00000000:01:00.0, 100\n")
        sampler._stop.set()
        with patch.object(sampler._t, "is_alive", return_value=True):
            self.assertIn("sampler_shutdown", sampler.peak["missing"])
        with patch.object(gates.subprocess, "run", side_effect=OSError), \
             patch.object(gates.procs, "memory", return_value={"available": None}):
            sampler._sample_once()
        self.assertIn("available_ram", sampler.peak["missing"])

    def test_single_card_shape_uses_selected_index(self):
        profile = multi_profile()
        card = profile.data["host"].pop("gpus")[0]
        profile.data["host"].update({key: value for key, value in card.items() if key not in ("arch", "pci_bus_id")})
        sampler = gates.Sampler(profile)
        self.sample(sampler, "0, 00000000:02:00.0, 999\n2, 00000000:01:00.0, 123\n")
        self.assertEqual(sampler.peak, {"gpu_used_mib": 123, "min_available_ram_bytes": 50000000000})

    def test_context_manager_joins_before_final_snapshot(self):
        sampled = threading.Event()

        def memory():
            sampled.set()
            return {"available": 12345}

        with patch.object(gates.subprocess, "run", return_value=SimpleNamespace(returncode=0,
                stdout="0, 00000000:02:00.0, 5\n2, 00000000:01:00.0, 100\n")), \
             patch.object(gates.procs, "memory", side_effect=memory):
            with gates.Sampler(multi_profile(), period=0.01) as sampler:
                self.assertTrue(sampled.wait(2))
            self.assertFalse(sampler._t.is_alive())
            self.assertTrue(sampler.peak["complete"])


class MultiCardGateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.profile = multi_profile()
        self.layout = Layout(self.root, self.profile)
        self.layout.state.mkdir()
        self.layout.install_record.write_text(json.dumps({"runtime_identity_sha256": "a" * 64}))
        self.status = dict(state="healthy", gpu_stage_order=stage_order(self.profile))
        self.enterContext(patch.object(gates.lifecycle, "status", return_value=self.status))
        self.enterContext(patch.object(gates, "server_tree", return_value=[]))

    def test_g10_complete_record_and_each_missing_condition(self):
        rows = observations(self.profile)
        with patch.object(gates.lifecycle, "card_observations", return_value=rows):
            record = gates.g10_gpu_record(self.layout, {123})
        self.assertTrue(record["complete"])
        self.assertEqual([row["gpu_index"] for row in record["cards"]], [2, 0])
        self.assertEqual(record["runtime_identity_sha256"], "a" * 64)
        for change in (dict(memory_used_mib=None), dict(owned_count=0), dict(foreign_compute_count=1),
                       dict(graphics_client_count=1), dict(pci_bus_id="00000000:03:00.0"), dict(problems=["missing"])):
            with self.subTest(change=change):
                bad = copy.deepcopy(rows)
                bad[0].update(change)
                with patch.object(gates.lifecycle, "card_observations", return_value=bad):
                    self.assertFalse(gates.g10_gpu_record(self.layout, {123})["complete"])
        self.status["gpu_stage_order"]["complete"] = False
        with patch.object(gates.lifecycle, "card_observations", return_value=rows):
            self.assertFalse(gates.g10_gpu_record(self.layout, {123})["complete"])

    def test_g20_record_requires_release_restart_and_complete_observations(self):
        before, stopped = observations(self.profile), observations(self.profile, owned=0, used=400)
        record = gates.g20_gpu_record(self.layout, before, stopped, before)
        self.assertTrue(record["complete"])
        self.assertTrue(all(row["released"] and row["restarted_owned"] for row in record["cards"]))
        for change in (dict(memory_used_mib=1500), dict(memory_used_mib=None), dict(owned_count=1),
                       dict(foreign_compute_count=1)):
            bad = copy.deepcopy(stopped)
            bad[1].update(change)
            self.assertFalse(gates.g20_gpu_record(self.layout, before, bad, before)["complete"])
        self.assertFalse(gates.g20_gpu_record(self.layout, before, stopped, stopped)["complete"])

    def test_g10_gate_binds_all_card_record_and_pass(self):
        memory = {key: 1024**3 for key in ("total", "available", "commit_limit", "commit_available")}
        proc = SimpleNamespace(pid=123, exe="strata.exe")
        for owned, expected in ((1, True), (0, False)):
            with self.subTest(owned=owned), \
                 patch.object(gates.lifecycle, "doctor", return_value={"ok": True}), \
                 patch.object(gates.lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}), \
                 patch.object(gates, "server_tree", return_value=[proc]), \
                 patch.object(gates.subprocess, "run", return_value=SimpleNamespace(stdout="TCP 127.0.0.1:18090 0.0.0.0:0 LISTENING 123")), \
                 patch.object(gates.procs, "memory", return_value=memory), \
                 patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile, owned=owned)):
                result = gates.g10(self.layout, "fixture-key", self.root, False)
            self.assertEqual(result["pass_observed"], expected)
            self.assertNotIn("gpu", result)
            self.assertEqual(len(result["gpu_qualification"]["cards"]), 2)

    def test_g20_pass_observed_includes_gpu_facts(self):
        state = dict(stock_strata_appdata_absent=True, user_omp_dir_untouched_since_root_created=True)
        smoke = SimpleNamespace(exit_code=0, final_text=lambda: "nonce")
        for stop_used, expected in ((400, True), (2000, False)):
            with self.subTest(stop_used=stop_used), \
                 patch.object(gates, "host_state", return_value=state), \
                 patch.object(gates.lifecycle, "status", side_effect=[self.status, {"state": "stopped"}, self.status, self.status]), \
                 patch.object(gates.lifecycle, "stop", side_effect=[{"stopped": True}, {"state": "stopped"}]), \
                 patch.object(gates.lifecycle, "start", side_effect=[{"ready_s": 1, "engine_found": True}, gates.lifecycle.LifecycleError("owned")]), \
                 patch.object(gates.lifecycle, "port_in_use", return_value=False), \
                 patch.object(gates.lifecycle, "card_observations", side_effect=[observations(self.profile), observations(self.profile, owned=0, used=stop_used), observations(self.profile)]), \
                 patch.object(gates, "nonce_fixture", return_value=(self.root, "nonce")), \
                 patch.object(gates.hostrun, "run_omp", return_value=smoke):
                result = gates.g20(self.layout, "fixture-key", self.root, ["fixture-tool"])
            self.assertEqual(result["pass_observed"], expected)
            self.assertEqual(result["gpu_qualification"]["complete"], expected)
            self.assertNotIn("gpu_after_stop", result)

    def test_g21_aggregates_only_matching_runtime_and_keeps_failed_samples(self):
        first = sampled_result(self.profile)
        second = sampled_result(self.profile, peaks=(20000, 22000), total=41000)
        unrelated = sampled_result(self.profile, peaks=(24000, 24000), total=48000)
        unrelated["runtime_identity_sha256"] = "b" * 64
        with patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile)):
            record = gates.g21_gpu_record(self.layout, [first, second, unrelated])
        self.assertTrue(record["complete"])
        self.assertEqual([card["peak_used_mib"] for card in record["cards"]], [21000, 22000])
        self.assertEqual([card["samples"] for card in record["cards"]], [4, 4])
        self.assertEqual(record["gpu_used_mib_sum_peak"], 41000)
        self.assertEqual(record["min_available_ram_mib"] * 1024**2, 64000 * 1024**2 + 1)
        self.assertIsNone(record["stage_order"])

    def test_g21_missing_samples_and_scalar_evidence_never_fill_cards(self):
        missing = sampled_result(self.profile)
        missing["resources"]["gpus"][1].update(samples=1, unavailable_samples=1)
        missing["resources"]["complete"] = False
        scalar = sampled_result(self.profile)
        scalar["resources"] = {"gpu_used_mib": 99999, "min_available_ram_bytes": 1}
        for rows in ([missing], [scalar], []):
            with self.subTest(rows=rows), patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile)):
                record = gates.g21_gpu_record(self.layout, rows)
            self.assertFalse(record["complete"])
            self.assertTrue(record["missing"])
        with patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile)):
            record = gates.g21_gpu_record(self.layout, [scalar])
        self.assertIsNone(record["cards"][0]["peak_used_mib"])
        self.assertIsNone(record["gpu_used_mib_sum_peak"])

    def test_g21_gate_retains_failure_and_induced_engine_events(self):
        evidence = self.root / "evidence" / "g17-fixture"
        evidence.mkdir(parents=True)
        evidence.joinpath("result.json").write_text(json.dumps(sampled_result(self.profile)))
        self.layout.logs.mkdir()
        self.layout.logs.joinpath("server-fixture.log").write_text("the engine stopped unexpectedly\n(error, cancel=False)\n")
        with patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile)), \
             patch.object(gates, "tree_memory", return_value=[]):
            result = gates.g21(self.layout, "fixture-key", self.root)
        self.assertIsNone(result["pass_observed"])
        self.assertTrue(result["gpu_qualification"]["complete"])
        self.assertFalse(result["gate_results"][0]["pass_observed"])
        self.assertEqual(result["engine_events"]["stopped_mid_request"], 1)
        self.assertEqual(result["engine_events"]["requests_ended_error"], 1)

    def test_g21_malformed_results_prevent_complete_resource_evidence(self):
        evidence = self.root / "evidence"
        good = evidence / "g17-fixture" / "result.json"
        good.parent.mkdir(parents=True)
        good.write_text(json.dumps(sampled_result(self.profile)))
        bad = evidence / "unexported-attempt" / "result.json"
        bad.parent.mkdir()
        for content in (b"{", b"\xff", b"[]", b"null"):
            with self.subTest(content=content):
                bad.write_bytes(content)
                with patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile)), \
                     patch.object(gates, "tree_memory", return_value=[]):
                    result = gates.g21(self.layout, "fixture-key", self.root)
                record = result["gpu_qualification"]
                self.assertFalse(record["complete"])
                self.assertEqual(record["missing"], ["result_unavailable"])
                self.assertEqual(record["gpu_used_mib_sum_peak"], 40000)
                self.assertNotIn(bad.parent.name, json.dumps(result))

    def test_g21_unreadable_result_prevents_complete_resource_evidence(self):
        evidence = self.root / "evidence"
        good = evidence / "g17-fixture" / "result.json"
        good.parent.mkdir(parents=True)
        good.write_text(json.dumps(sampled_result(self.profile)))
        unreadable = evidence / "unexported-attempt" / "result.json"
        unreadable.parent.mkdir()
        unreadable.write_text("{}")
        read_text = Path.read_text

        def read_result(path, *args, **kwargs):
            if path == unreadable:
                raise PermissionError("unreadable fixture")
            return read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", autospec=True, side_effect=read_result), \
             patch.object(gates.lifecycle, "card_observations", return_value=observations(self.profile)), \
             patch.object(gates, "tree_memory", return_value=[]):
            result = gates.g21(self.layout, "fixture-key", self.root)
        self.assertFalse(result["gpu_qualification"]["complete"])
        self.assertEqual(result["gpu_qualification"]["missing"], ["result_unavailable"])
        self.assertNotIn(unreadable.parent.name, json.dumps(result))

    def test_single_card_g21_still_skips_malformed_json_and_raises_unreadable(self):
        card = self.profile.data["host"].pop("gpus")[0]
        self.profile.data["host"].update({key: value for key, value in card.items() if key not in ("arch", "pci_bus_id")})
        bad = self.root / "evidence" / "malformed-fixture" / "result.json"
        bad.parent.mkdir(parents=True)
        bad.write_text("{")
        with patch.object(gates, "tree_memory", return_value=[]):
            result = gates.g21(self.layout, "fixture-key", self.root)
        self.assertEqual(result["gate_results"], [])
        self.assertNotIn("gpu_qualification", result)
        with patch.object(Path, "read_text", side_effect=PermissionError("unreadable fixture")):
            with self.assertRaises(PermissionError):
                gates.g21(self.layout, "fixture-key", self.root)


if __name__ == "__main__":
    unittest.main()
