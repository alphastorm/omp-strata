import contextlib
import copy
from datetime import datetime
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json, read_json, sha256_file
from scripts import publish_run
from scripts.verify_release import verify

REPO = Path(__file__).resolve().parents[2]
REFERENCES = (
    "win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8",
    "win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8",
    "win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6",
)
ROOT_PATH = "D:\\qualification-fixture"
MANUAL_GATES = {"G00", "G01", "G02", "G03", "G04", "G05", "G06", "G22", "G23", "G25"}


def timestamp(run_id):
    value = next(part for part in run_id.split("-") if len(part) == 16 and part.endswith("Z"))
    return datetime.strptime(value, "%Y%m%dT%H%M%SZ").isoformat() + "Z"


class PulledRun:
    """Rebuild the contracted pull exclusively from scrubbed repository artifacts.

    The oldest run predates requalify and did not export its install record. Its
    synthetic record takes the exact runtime/file digests from the manifest; no
    unpublished host facts or operator credentials are needed by these fixtures.
    """
    def __init__(self, root, reference=REFERENCES[0]):
        self.root, self.reference = root, reference
        source = REPO / "releases" / reference
        self.profile = root / "profiles" / (reference + ".json")
        self.profile.parent.mkdir(parents=True)
        shutil.copyfile(REPO / "profiles" / self.profile.name, self.profile)
        self.release = root / "releases" / reference
        self.release.mkdir(parents=True)
        self.pulled = root / "pulled"
        self.pulled.mkdir()
        (root / "eval").mkdir()
        shutil.copyfile(REPO / "eval/tasks.json", root / "eval/tasks.json")
        ledger, self.manifest = read_json(source / "qualification.json"), read_json(source / "manifest.json")
        self.receipts = {}
        for gate in ledger["gates"]:
            if gate["id"] in publish_run.GATE_STEPS:
                self.receipts[gate["id"]] = read_json(source / gate["receipts"][-1]["path"])
            gate.update(status="not_run", receipts=[], receipt_paths=[], note=None)
        ledger["execution_performed"] = False
        atomic_write_json(self.release / "qualification.json", ledger)
        draft = copy.deepcopy(self.manifest)
        draft["qualification"]["ledger_sha256"] = sha256_file(self.release / "qualification.json")
        draft["install"] = {"generated_files": [], "runtime_identity_sha256": None}
        atomic_write_json(self.release / "manifest.json", draft)
        self.draft = draft
        self.commit = self.receipts["G10"]["implementation_commit"]
        self.host = reference.split("-")[1] + "-win-a"
        self.host_had_strata = "second-root" in self.receipts["G26"]["run_id"]
        self.original_evidence = {}
        for receipt in self.receipts.values():
            for ref in receipt["evidence"]:
                self.original_evidence[ref["path_or_ref"]] = (source / ref["path_or_ref"]).read_bytes()
        self.quickstart = read_json(source / self.receipts["G26"]["evidence"][0]["path_or_ref"])
        self.rows = copy.deepcopy(self.quickstart.get("runner_steps", []))
        by_step = {row["step"]: row for row in self.rows}
        for gid, receipt in self.receipts.items():
            if gid in ("G24", "G26"):
                continue
            for ref in receipt["evidence"]:
                raw = self.original_evidence[ref["path_or_ref"]]
                result = json.loads(raw)
                if gid == "G12" and "all_protocol_pass" in result:
                    # Legacy G12 also cites the G11 aggregate, already rebuilt.
                    continue
                if gid == "G11":
                    runs = list(result["runs"].values()) if isinstance(result["runs"], dict) else result["runs"]
                    for run in runs:
                        self.put_result(run["run_id"], publish_run.encoded(run))
                    step, run_id = "tracer", [r["run_id"] for r in runs]
                else:
                    step, run_id = result["gate"].lower(), result["run_id"]
                    self.put_result(run_id, raw)
                if step not in by_step:
                    row = dict(step=step, run_id=run_id, rc=0,
                               pass_observed=(result.get("all_protocol_pass") and result.get("all_task_pass"))
                               if gid == "G11" else result.get("pass_observed"),
                               started_utc=result.get("utc", receipt["timestamp_utc"]), seconds=0)
                    self.rows.append(row)
                    by_step[step] = row
        evaluation = read_json(source / self.receipts["G24"]["evidence"][0]["path_or_ref"])
        self.batches = {}
        for step, key in (("pilot", "pilot_non_scored"), ("eval", "scored_batch")):
            batch = copy.deepcopy(evaluation[key])
            directory = self.pulled / "eval" / ("fixture-" + step)
            directory.mkdir(parents=True)
            summary = batch["summary"]
            # Earlier public exports omit pilot batch metadata; it is a subset
            # of the summary written by evaluate.py, not a fabricated result.
            metadata = batch.get("batch", {key: value for key, value in summary.items()
                                          if key in ("pilot", "scored", "profile", "profile_sha256", "manifest_sha256",
                                                     "harness_drift", "scheduled_attempts", "order", "isolation_boundary", "between_phases_hook")})
            atomic_write_json(directory / "summary.json", summary)
            atomic_write_json(directory / "batch.json", metadata)
            self.write_attempts(directory, batch["attempts"])
            self.batches[step] = directory
            if step not in by_step:
                row = dict(step=step, run_id=None, rc=0 if step == "pilot" else 1,
                           pass_observed=step == "pilot", seconds=0,
                           started_utc=timestamp(self.receipts["G24"]["run_id"]))
                self.rows.append(row)
                by_step[step] = row
            by_step[step]["out"] = ROOT_PATH + "\\eval\\" + directory.name
        for step, name in (("fetch", "fetch"), ("install", "install"), ("start", "start"),
                           ("quickstart", "launch_omp_example"), ("quickstart-tests", "quickstart_tests"), ("stop", "stop")):
            if step in by_step:
                continue
            details = self.quickstart["steps"].get(name, {})
            if step == "fetch" and not isinstance(details.get("wall_s"), (int, float)):
                continue
            # The old hand-run quickstart did not time its independent tests.
            row = dict(step=step, run_id=None, rc=details.get("exit", 0),
                       pass_observed=True if step == "quickstart" else None,
                       seconds=details.get("wall_s", 0), started_utc=timestamp(self.receipts["G26"]["run_id"]))
            if step == "stop":
                row["seconds"] = 0
            self.rows.append(row)
            by_step[step] = row
        install = self.quickstart.get("install_record")
        if install is None:
            files = self.manifest["install"]["generated_files"]
            install = dict(profile_id=reference, profile_fingerprint=ledger["profile_fingerprint"],
                           runtime_identity_sha256=self.manifest["install"]["runtime_identity_sha256"],
                           identity=dict(files={item["path_label"]: {"sha256": item["sha256"]} for item in files[:-2]},
                                         config_file_sha256=files[-2]["sha256"], shared_settings_sha256=files[-1]["sha256"]))
        self.install = self.pulled / "state/install-record.json"
        self.install.parent.mkdir(parents=True)
        self.install.write_bytes(self.inject_root(publish_run.encoded(install)))
        self.summary = self.pulled / "evidence/requalify-fixture/summary.json"
        self.summary.parent.mkdir(parents=True)
        self.save_rows()

    @staticmethod
    def inject_root(data):
        # Preserve all other bytes so ordinary gate evidence has exact golden hashes.
        return data.replace(b"<root>", json.dumps(ROOT_PATH)[1:-1].encode())

    def put_result(self, run_id, data):
        path = self.pulled / "evidence" / run_id / "result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.inject_root(data))

    @staticmethod
    def write_attempts(directory, attempts):
        # Public exports flattened the immutable verifier verdict. Reconstruct
        # the raw evaluator shape from that outcome without inventing a score.
        attempts = [dict(item, verifier=item.get("verifier", {"passed": item.get("verifier_pass")})) for item in attempts]
        (directory / "attempts.jsonl").write_text("".join(json.dumps(item) + "\n" for item in attempts), encoding="utf-8")

    def save_rows(self):
        atomic_write_json(self.summary, self.rows)

    def row(self, step):
        return next(row for row in self.rows if row["step"] == step)

    def plan(self, **changes):
        kwargs = dict(pulled=self.pulled, profile_path=self.profile, host_label=self.host, root_path=ROOT_PATH,
                      implementation_commit=self.commit, release_dir=self.release,
                      host_had_strata=self.host_had_strata, denylist=())
        kwargs.update(changes)
        return publish_run.build_plan(**kwargs)

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}


# Historical receipts were hand-authored with different labels and units. These
# aliases normalize *test expectations*, never production output or old receipts.
METRIC_NAMES = {
    "ram_total": "ram_total_bytes", "ram_available_serving": "ram_available_bytes",
    "commit_limit": "commit_limit_bytes", "commit_available_serving": "commit_available_bytes",
    "disk_free": "disk_free_bytes", "gpu_memory_used": "gpu_memory_used_serving",
    "protocol_pass": "protocol_passes", "task_pass": "task_passes",
    "idle_after_generating_client_drop": "generating_cancel_to_idle",
    "server_idle_after_client_loss": "generating_cancel_to_idle",
    "server_idle_after_queued_and_generating_drop": "queued_drop_then_active_drop_to_idle",
    "replay_prefill_tokens_after_restart": "idle_kill_prompt_tokens",
    "replay_prefill_ms_after_restart": "idle_kill_prompt_ms",
    "client_restart_wall": "client_restart_recall", "client_restart_turn_wall": "client_restart_recall",
    "client_and_server_restart_turn_wall": "combined_restart_recall",
    "after_full_restart_turn_wall": "combined_restart_recall", "server_ready": "server_restart_ready",
    "after_full_restart_prefill_ms": "combined_restart_prefill", "boundary_cold_prefill": "cold_prefill",
    "boundary_cold_prefill_wall": "cold_prefill", "boundary_cold_prefill_rate": "cold_prefill_rate",
    "near_limit_peak_prompt": "near_limit_peak_prompt_tokens", "near_limit_max_prompt_plus_cap": "max_wire_prompt_plus_cap",
    "near_limit_cold_prefill_ms": "near_limit_cold_prefill", "g18_compactions": "reduced_compactions",
    "g18_tokens_before": "reduced_compaction_tokens_before", "g18l_compactions": "production_compactions",
    "g18l_tokens_before": "production_compaction_tokens_before", "production_tokens_after": "production_compaction_tokens_after",
    "reduced_threshold_compactions": "reduced_compactions", "long_session_compaction_tokens_before": "production_compaction_tokens_before",
    "long_session_peak_prompt": "peak_engine_prompt_tokens", "common_prefix_reused": "shared_prefix_reused",
    "interleaved_continuation_cached_tokens": "shared_prefix_reused", "gpu_after_stop": "gpu_memory_after_stop",
    "engine_peak_private": "engine_peak_private_commit", "current_ready_s": "current_ready",
    "launch_omp_example_wall": "quickstart_example_wall",
}


class PublishRunTests(unittest.TestCase):
    def fixture(self, reference=REFERENCES[0]):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        return PulledRun(Path(directory), reference)

    def test_reference_golden_publication(self):
        for reference in REFERENCES:
            with self.subTest(reference=reference):
                fixture = self.fixture(reference)
                plan = fixture.plan()
                before_manual = {g["id"]: copy.deepcopy(g) for g in read_json(fixture.release / "qualification.json")["gates"]
                                 if g["id"] in MANUAL_GATES}
                publish_run.publish(plan)
                self.assertEqual([], verify(fixture.release / "manifest.json")["errors"])
                actual = {r["gate_id"]: r for r in plan["receipts"]}
                self.assertEqual(set(fixture.receipts), set(actual))
                for gid, expected in fixture.receipts.items():
                    got = actual[gid]
                    self.assertEqual(expected["status"], got["status"], gid)
                    self.assertEqual(expected["gate_id"], got["gate_id"])
                    # The 4090 author named the G18 receipt after the reduced
                    # probe. The canonical mapping uses the production probe.
                    run_id = expected["run_id"]
                    if gid == "G18" and "rtx4090" in reference:
                        run_id = fixture.row("g18l")["run_id"]
                    self.assertEqual(run_id, got["run_id"], gid)
                    if gid not in ("G24", "G26") and not (gid == "G11" and reference == REFERENCES[2]):
                        old_refs = {r["path_or_ref"]: r["sha256"] for r in expected["evidence"]}
                        if gid == "G12" and reference == REFERENCES[2]:
                            old_refs = {path: digest for path, digest in old_refs.items() if "/g11-" not in path}
                        new_refs = {r["path_or_ref"]: r["sha256"] for r in got["evidence"]}
                        self.assertEqual(old_refs, new_refs, gid)
                    for ref in got["evidence"]:
                        self.assertEqual(ref["sha256"], sha256_file(fixture.release / ref["path_or_ref"]))
                    if gid == "G11":
                        aggregate = read_json(fixture.release / got["evidence"][0]["path_or_ref"])
                        self.assertEqual(fixture.row("tracer")["run_id"], [run["run_id"] for run in aggregate["runs"]])
                    if gid == "G24":
                        exported = read_json(fixture.release / got["evidence"][0]["path_or_ref"])
                        self.assertTrue(exported["pilot_non_scored"]["summary"]["pilot"])
                        self.assertTrue(exported["scored_batch"]["summary"]["scored"])
                        attempts = exported["scored_batch"]["attempts"]
                        self.assertEqual(18, len(attempts))
                        self.assertEqual(18 - exported["scored_batch"]["summary"]["completion_count"],
                                         sum(not attempt["verified_pass"] for attempt in attempts))
                    metrics = {m["name"]: m for m in got["metrics"]}
                    for old in expected["metrics"]:
                        name = METRIC_NAMES.get(old["name"], old["name"])
                        self.assertIn(name, metrics, (gid, name))
                        new = metrics[name]
                        # These exports have first-start readiness only in the
                        # hand-written G26 wrapper, not in a contracted input.
                        if reference in REFERENCES[1:] and gid == "G26" and name == "first_start_ready":
                            self.assertIsNone(new["value"])
                            self.assertEqual("unavailable", new["method"])
                            continue
                        if reference == REFERENCES[2] and gid == "G24" and old["unit"] == "s":
                            self.assertEqual(old["value"], round(new["value"] / 1000, 1), name)
                        elif reference == REFERENCES[2] and gid == "G24" and name == "completion_rate":
                            self.assertEqual(old["value"], round(new["value"], 4))
                        else:
                            self.assertEqual(old["value"], new["value"], (gid, name))
                manifest = read_json(fixture.release / "manifest.json")
                self.assertEqual(fixture.manifest["install"], manifest["install"])
                self.assertEqual(sha256_file(fixture.release / "qualification.json"), manifest["qualification"]["ledger_sha256"])
                for name in ("status", "blockers", "publication_authorized"):
                    self.assertEqual(fixture.draft.get(name), manifest.get(name))
                ledger = read_json(fixture.release / "qualification.json")
                self.assertEqual(before_manual, {g["id"]: g for g in ledger["gates"] if g["id"] in MANUAL_GATES})
                for path in fixture.release.rglob("*.json"):
                    self.assertNotIn(ROOT_PATH.casefold(), path.read_text().casefold())
                    self.assertNotIn(json.dumps(ROOT_PATH)[1:-1].casefold(), path.read_text().casefold())

    def test_rc_and_observation_failures_are_retained_and_combined(self):
        fixture = self.fixture()
        fixture.row("g10")["pass_observed"] = False
        fixture.row("g14q").update(rc=1, pass_observed=True)
        fixture.row("g18").update(rc=0, pass_observed=None)
        # A probe that crashed before allocating an id is still a failed receipt.
        fixture.row("g16").update(rc=1, run_id=None, pass_observed=None)
        fixture.save_rows()
        plan = fixture.plan()
        publish_run.publish(plan)
        receipts = {r["gate_id"]: r for r in plan["receipts"]}
        for gid in ("G10", "G14", "G16", "G18"):
            self.assertEqual("fail", receipts[gid]["status"])
        self.assertEqual(2, len(receipts["G14"]["evidence"]))
        self.assertEqual(2, len(receipts["G18"]["evidence"]))
        self.assertEqual("pass", receipts["G15"]["status"])
        self.assertEqual([], verify(fixture.release / "manifest.json")["errors"])

    def test_measurement_gate_requires_complete_measurements_and_successful_rc(self):
        fixture = self.fixture()
        self.assertIsNone(fixture.row("g21")["pass_observed"])
        plan = fixture.plan()
        self.assertEqual("pass", next(r for r in plan["receipts"] if r["gate_id"] == "G21")["status"])
        path = fixture.pulled / "evidence" / fixture.row("g21")["run_id"] / "result.json"
        result = read_json(path)
        errors = result["engine_events"].pop("requests_ended_error")
        atomic_write_json(path, result)
        plan = fixture.plan()
        self.assertEqual("fail", next(r for r in plan["receipts"] if r["gate_id"] == "G21")["status"])
        result["engine_events"]["requests_ended_error"] = errors
        atomic_write_json(path, result)
        fixture.row("g21")["rc"] = 1
        fixture.save_rows()
        self.assertEqual("fail", next(r for r in fixture.plan()["receipts"] if r["gate_id"] == "G21")["status"])

    def test_evaluation_reports_failed_tasks_but_refuses_missing_verification(self):
        fixture = self.fixture()
        self.assertEqual(1, fixture.row("eval")["rc"])
        self.assertFalse(fixture.row("eval")["pass_observed"])
        plan = fixture.plan()
        self.assertEqual("pass", next(r for r in plan["receipts"] if r["gate_id"] == "G24")["status"])
        directory = fixture.batches["eval"]
        original = [json.loads(line) for line in (directory / "attempts.jsonl").read_text().splitlines()]
        mutations = [original[:-1]] + [copy.deepcopy(original) for _ in range(3)]
        mutations[1][0].pop("verifier_pass")
        mutations[2][0]["not_started"] = True
        mutations[3][0]["verifier"] = {}
        for attempts in mutations:
            fixture.write_attempts(directory, attempts)
            receipt = next(r for r in fixture.plan()["receipts"] if r["gate_id"] == "G24")
            self.assertEqual("fail", receipt["status"])

    def test_scrubs_root_variants_and_extra_terms_without_mutating_input(self):
        fixture = self.fixture()
        row = fixture.row("g10")
        path = fixture.pulled / "evidence" / row["run_id"] / "result.json"
        result = read_json(path)
        result["publication_scrub_probe"] = [ROOT_PATH, ROOT_PATH[0].lower() + ROOT_PATH[1:], ROOT_PATH.replace("\\", "/"),
                                             json.dumps(ROOT_PATH)[1:-1], "PRIVATE-FIXTURE-LABEL"]
        atomic_write_json(path, result)
        source = path.read_bytes()
        plan = fixture.plan(private=["private-fixture-label"])
        published = json.loads(plan["evidence"]["evidence/" + row["run_id"] + ".json"])
        self.assertEqual(["<root>"] * 4 + ["<redacted>"], published["publication_scrub_probe"])
        self.assertEqual(source, path.read_bytes())

    def test_hygiene_refusal_is_all_or_nothing_and_never_echoes_private_inputs(self):
        fixture = self.fixture()
        path = fixture.pulled / "evidence" / fixture.row("g10")["run_id"] / "result.json"
        original = path.read_bytes()
        # JSON escaping defeats literal replacement, but the decoded final scan
        # must still refuse the leftover explicitly private term.
        changed = original.rstrip()[:-1] + b', "private_probe": "\\u0070rivate-fixture-label"}\n'
        path.write_bytes(changed)
        before = fixture.snapshot()
        with self.assertRaises(publish_run.PublicationError):
            fixture.plan(private=["private-fixture-label"])
        self.assertEqual(before, fixture.snapshot())
        result = json.loads(original)
        result["unlisted_private_probe"] = "denylist-fixture-label"
        atomic_write_json(path, result)
        before = fixture.snapshot()
        with self.assertRaises(publish_run.PublicationError):
            fixture.plan(denylist=["denylist-fixture-label"])
        self.assertEqual(before, fixture.snapshot())
        output, error = io.StringIO(), io.StringIO()
        with patch.object(publish_run, "REPO", fixture.root), patch.object(publish_run, "private_denylist", return_value=["denylist-fixture-label"]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            rc = publish_run.main(self.cli_args(fixture))
        self.assertEqual(1, rc)
        self.assertNotIn("denylist-fixture-label", output.getvalue() + error.getvalue())
        self.assertNotIn(ROOT_PATH, output.getvalue() + error.getvalue())
        self.assertEqual(before, fixture.snapshot())
        result = json.loads(original)
        result["private_network_probe"] = ".".join(("192", "168", "1", "19"))
        atomic_write_json(path, result)
        before = fixture.snapshot()
        with self.assertRaises(publish_run.PublicationError):
            fixture.plan()
        self.assertEqual(before, fixture.snapshot())

    @staticmethod
    def cli_args(fixture):
        return ["--pulled", str(fixture.pulled), "--profile", str(fixture.profile), "--host-label", fixture.host,
                "--root-path", ROOT_PATH, "--implementation-commit", fixture.commit]

    def test_cli_dry_run_writes_nothing_then_publication_is_append_only(self):
        fixture = self.fixture()
        before = fixture.snapshot()
        output = io.StringIO()
        with patch.object(publish_run, "REPO", fixture.root), patch.object(publish_run, "private_denylist", return_value=[]), contextlib.redirect_stdout(output):
            self.assertEqual(0, publish_run.main(self.cli_args(fixture) + ["--dry-run", "--host-had-strata"]))
            self.assertEqual(before, fixture.snapshot())
            self.assertEqual(0, publish_run.main(self.cli_args(fixture) + ["--host-had-strata"]))
        ledger = read_json(fixture.release / "qualification.json")
        receipt = next(g for g in ledger["gates"] if g["id"] == "G26")["receipt_paths"][0]
        self.assertIn("g26-second-root-", receipt)
        after = fixture.snapshot()
        with self.assertRaises(publish_run.PublicationError):
            fixture.plan(host_had_strata=True)
        self.assertEqual(after, fixture.snapshot())

    def test_foreign_profile_or_install_identity_cannot_publish(self):
        fixture = self.fixture()
        path = fixture.pulled / "evidence" / fixture.row("g10")["run_id"] / "result.json"
        result = read_json(path)
        result["profile_fingerprint"] = "0" * 64
        atomic_write_json(path, result)
        before = fixture.snapshot()
        with self.assertRaises(publish_run.PublicationError):
            fixture.plan()
        self.assertEqual(before, fixture.snapshot())


if __name__ == "__main__":
    unittest.main()
