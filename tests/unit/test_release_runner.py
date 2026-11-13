"""Host-free runner protocol tests: loopback HTTP, disposable files and injected native effects."""
import base64
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import release_runner as rr

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/release_runner"
RUN = "01AAAAAAAAAAAAAAAAAAAAAAAA"
CLAIM = "01BBBBBBBBBBBBBBBBBBBBBBBB"
COMMIT = "c" * 40
NOW = 1800000000


def validate(value, schema, root=None):
    """Check the vocabulary present in the pinned schemas; unknown keywords fail the test."""
    root = root or schema
    known = {"$schema", "$defs", "$ref", "title", "default", "description", "discriminator",
             "type", "const", "enum", "properties", "required", "additionalProperties",
             "patternProperties", "propertyNames", "items", "minItems", "maxItems",
             "minLength", "maxLength", "maxProperties", "minimum", "maximum", "pattern",
             "format", "oneOf", "anyOf", "allOf", "if", "then", "not"}
    assert not set(schema) - known, set(schema) - known
    if "$ref" in schema:
        return validate(value, root["$defs"][schema["$ref"].split("/")[-1]], root)
    for sub in schema.get("allOf", []):
        validate(value, sub, root)
    if "if" in schema:
        try:
            validate(value, schema["if"], root)
        except (AssertionError, ValueError, TypeError):
            pass
        else:
            validate(value, schema["then"], root)
    if "not" in schema:
        try:
            validate(value, schema["not"], root)
        except (AssertionError, ValueError, TypeError):
            pass
        else:
            raise AssertionError("negated schema matched")
    for alternative, count in (("oneOf", 1), ("anyOf", None)):
        if alternative in schema:
            successes = 0
            for sub in schema[alternative]:
                try:
                    validate(value, sub, root)
                    successes += 1
                except (AssertionError, ValueError, TypeError):
                    pass
            assert successes == count if count else successes > 0, (alternative, value)
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool,
             "null": type(None)}
    if "type" in schema:
        assert type(value) is kinds[schema["type"]], (schema["type"], value)
    if "const" in schema:
        assert type(value) is type(schema["const"]) and value == schema["const"]
    if "enum" in schema:
        assert value in schema["enum"]
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= set(value), (schema.get("required"), value)
        assert len(value) <= schema.get("maxProperties", len(value))
        for key, item in value.items():
            if "propertyNames" in schema:
                validate(key, schema["propertyNames"], root)
            found = False
            if key in schema.get("properties", {}):
                validate(item, schema["properties"][key], root)
                found = True
            for pattern, sub in schema.get("patternProperties", {}).items():
                if re.search(pattern, key):
                    validate(item, sub, root)
                    found = True
            if not found:
                extra = schema.get("additionalProperties", True)
                assert extra is not False, key
                if isinstance(extra, dict):
                    validate(item, extra, root)
    if isinstance(value, list):
        assert schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value))
        for item in value:
            validate(item, schema.get("items", {}), root)
    if isinstance(value, str):
        assert schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value))
        if "pattern" in schema:
            assert re.search(schema["pattern"], value), (schema["pattern"], value)
        if schema.get("format") == "date-time":
            rr.timestamp(value)
    if type(value) is int:
        assert schema.get("minimum", value) <= value <= schema.get("maximum", value)


def schema(name):
    return rr.document(FIXTURES / (name + ".schema.json"))


class Server:
    def __init__(self):
        self.action = None
        self.requests, self.errors = [], []
        self.unreachable, self.stale_response = False, False
        self.advance_incumbent = False
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = rr.parse(self.rfile.read(int(self.headers["Content-Length"])))
                parent.requests.append((self.path, body))
                try:
                    if self.path.endswith("/next-action"):
                        validate(body, schema("release-runner-poll"))
                        reply = copy.deepcopy(parent.action or {"action": None, "retry_after_seconds": 30})
                        if reply["action"] is not None:
                            validate(reply, schema("release-runner-action"))
                            if reply["claim"]:
                                validate(rr.parse(base64.b64decode(reply["admission_receipt_b64"])),
                                         schema("release-admission"))
                    elif self.path.endswith("/reports"):
                        validate(body, schema("release-runner-report"))
                        assert body["facts"] is None or body["stage"] == body["facts"]["stage"]
                        action = parent.action
                        reply = {"run": {"id": action["run_id"], "state": "active",
                                         "claim_generation": action["claim_generation"],
                                         "stage_attempt": action["stage_attempt"], "stage": action["action"],
                                         "lease_expires_at": rr.utc(NOW + 600)}}
                        if parent.stale_response:
                            reply["run"]["claim_generation"] += 1
                        if parent.advance_incumbent:
                            reply["run"]["stage"] = "settle"
                    elif self.path.endswith("/usage"):
                        assert set(body) == {"schema_version", "claim_id", "started_at", "ended_at",
                                             "gpu_seconds", "outcome", "restoration", "evidence_paths"}
                        assert body["schema_version"] == "carrythrough.fleet-usage.v1"
                        assert body["claim_id"] == CLAIM
                        assert rr.timestamp(body["ended_at"]) >= rr.timestamp(body["started_at"])
                        if body["gpu_seconds"] == 0:
                            assert body["outcome"] == "aborted" and body["started_at"] == body["ended_at"]
                        reply = {"state": "cleanup_required" if body["restoration"]["verified"]
                                 else "restoration_failed"}
                    elif self.path.endswith("/release"):
                        assert set(body) in (set(), {"no_mutation_verified", "evidence_sha256"})
                        reply = {"claim": {"claim_id": CLAIM}, "state": "released",
                                 "restoration_verified": True}
                    else:
                        raise AssertionError(self.path)
                    self.send_response(503 if parent.unreachable else 200)
                    self.end_headers()
                    self.wfile.write(json.dumps(reply).encode())
                except Exception as exc:
                    parent.errors.append(exc)
                    self.send_response(400)
                    self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class FakeNative:
    def __init__(self, folder):
        self.folder = folder
        self.effects = []
        self.identity = {"profile_id": "incumbent", "profile_fingerprint": "1" * 64,
                         "runtime_identity_sha256": "2" * 64, "config_file_sha256": "3" * 64,
                         "run_generation": "incumbent-before"}
        self.healthy, self.listening = True, True
        self.profile = {"profile_id": "candidate", "strata": {"tag": "v0.2.14"}, "model": {"fixed": True}}
        self.assets = {}

    def worktree(self, path, commit):
        path.mkdir(parents=True, exist_ok=True)
        rr.atomic_write_json(path / "profiles/candidate.json", self.profile)
        ledger = {"gates": []}
        release = path / "releases/candidate"
        rr.atomic_write_json(release / "qualification.json", ledger)
        rr.atomic_write_json(release / "manifest.json",
                             {"qualification": {"ledger": "qualification.json",
                                                "ledger_sha256": rr.sha256_file(release / "qualification.json")}})

    def prepare(self, path, spec):
        rr.atomic_write_json(path / "releases/campaigns/tuple.json", {"status": "pending"})
        return {"predecessor_id": "incumbent", "predecessor_manifest_sha256": "4" * 64,
                "campaign_path": "releases/campaigns/tuple.json"}

    def asset(self, source, asset):
        return self.assets[asset["name"]]

    def campaign_status(self, work, spec, status, **kwargs):
        self.effects.append("ledger:" + status)
        rr.atomic_write_json(work / "releases/campaigns/tuple.json", {"status": status})

    def fetch(self, work, profile, root, *, heartbeat):
        root.mkdir(parents=True, exist_ok=True)
        self.effects.append("fetch")

    def incumbent(self):
        return copy.deepcopy(self.identity), self.healthy, self.listening

    def stop_candidate(self, work, profile, root):
        self.effects.append("stop_candidate")
        return True

    def export(self, *args):
        self.effects.append("export")

    def verify(self, *args):
        return False


class FakeController:
    def __init__(self, native):
        self.native, self.effects = native, []
        self.reserved, self.fail_return = False, False
        self.return_generation = "incumbent-after"
        self.mutate_identity = None
        self.before_use = None

    def call(self, verb):
        self.effects.append(verb)
        if verb == "use":
            if self.before_use:
                self.before_use()
            self.reserved, self.native.listening = True, False
        elif verb == "return":
            if self.fail_return:
                raise rr.Refused("controller_unavailable")
            self.reserved, self.native.listening = False, True
            self.native.identity["run_generation"] = self.return_generation
            if self.mutate_identity:
                self.native.identity[self.mutate_identity] = "f" * 64
        return {"schema_version": 1, "host": "lab-host", "generation": 1,
                "reserved": self.reserved, "admission_open": not self.reserved,
                "phase": "Ready for you" if self.reserved else "Fleet", "blockers": [], "jobs": {},
                "service": {"generation": 1},
                "resources": {"ready": True, "blockers": [], "unexplained_compute": [],
                              "observed_generation": 1, "observed_utc": NOW,
                              "gpus": [{"uuid": "test-card", "model": "test-model", "used_mib": 0}]}}


class FakeLauncher:
    def __init__(self):
        self.alive, self.launches, self.stops = False, 0, 0

    def live(self, root, run_id):
        return ["test-process"] if self.alive else []

    def launch(self, work, profile, root, run_id):
        self.launches += 1
        self.alive = True
        rr.atomic_write_json(root / "state/requalify-run.json", {"run_id": run_id})
        return {"pid": 42}

    def stop(self, root, run_id):
        self.stops += 1
        self.alive = False
        return True


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.server = Server()
        self.addCleanup(self.server.close)
        self.native = FakeNative(self.folder)
        self.controller = FakeController(self.native)
        self.launcher = FakeLauncher()
        self.token = self.folder / "token"
        self.token.write_text("test-only-bearer")
        self.config = {"state_directory": str(self.folder / "state"), "tooling": str(self.folder / "tooling"),
                       "tooling_commit": COMMIT, "runner": "lab-runner", "resource_id": "lab-resource",
                       "host": "lab-host", "native_host": "lab-host", "public_host_label": "lab-host",
                       "incumbent_kind": "strata", "controller_kind": "fleet", "restoration_ref": "incumbent",
                       "incumbent_root": str(self.folder / "incumbent"),
                       "candidates": str(self.folder / "candidates"), "checkpoint_directory": str(self.folder),
                       "gpu_uuids": ["test-card"]}
        self.spec = {"schema_version": "carrythrough.release-candidate.v1", "adapter": "omp-strata.v1",
                     "candidate_id": "candidate",
                     "recipe": {"recipe_id": "recipe", "kind": "server", "profile_family": "candidate",
                                "resource_id": "lab-resource", "model": {"fixed": "true"},
                                "invariant_sha256": [rr.invariant_digest(self.native.profile)]},
                     "host": {**{key: self.config[key] for key in ("resource_id", "host", "native_host", "runner",
                                                                  "restoration_ref")},
                              "gpu_count": 1, "gpu_models": ["test-model"]}}
        for role in ("engine", "client"):
            path = self.folder / (role + ".exe")
            path.write_bytes(b"MZ" + role.encode())
            self.native.assets[path.name] = path
            self.spec[role] = {"repository_url": "https://github.com/example/project.git",
                               "tag": "v0.2.14" if role == "engine" else "v18.20.0", "release_id": 1,
                               "commit_sha": "e" * 40, "identity_sha256": "a" * 64,
                               "observation_event_id": RUN,
                               "assets": [{"name": path.name, "size": path.stat().st_size,
                                           "digest": "sha256:" + rr.sha256_file(path)}]}
        self.generation = 0
        self.runner = self.make_runner()
        # Effects are injected; a regression that escapes them must fail rather than launch.
        self.process_guard = patch.object(rr.subprocess, "run", side_effect=AssertionError("real process"))
        self.process_guard.start()
        self.addCleanup(self.process_guard.stop)
        self.popen_guard = patch.object(rr.subprocess, "Popen", side_effect=AssertionError("real process"))
        self.popen_guard.start()
        self.addCleanup(self.popen_guard.stop)
        self.addCleanup(lambda: self.assertEqual([], self.server.errors))

    def make_runner(self, **kwargs):
        return rr.Runner(self.config, rr.HTTP(self.server.origin, self.token), self.native, self.controller,
                         self.launcher, clock=lambda: NOW, identity=lambda root, commit: commit,
                         hold_directory=self.folder / "holds", **kwargs)

    def assign(self, stage, *, claim=True):
        self.generation += 1
        limits = {"stage_seconds": {stage: 100 for stage in (*rr.STAGES, "admission", "publish", "outcome")},
                  "run_seconds_max": 20000, "free_disk_bytes_min": 1, "checkpoint_bytes_min": 1,
                  "candidate_root_bytes_max": 100000000, "provider_calls_max": 0,
                  "retries": {"per_stage_max": 1, "host_attempts_max": 1, "backoff_seconds": 1,
                              "publication_lookups_max": 1}}
        profile_sha = rr.sha256_file(self.runner.profile()) if self.runner.state else "d" * 64
        receipt = {"schema_version": "carrythrough.release-admission.v1", "run_id": RUN, "attempt": 1,
                   "project": "project", "policy": {"generation": 1, "sha256": "a" * 64,
                                                  "envelope_sha256": "b" * 64},
                   "candidate": {"candidate_id": "candidate", "candidate_sha256": rr.candidate_digest(self.spec),
                                 "profile_sha256": profile_sha, "recipe_id": "recipe", "adapter": "omp-strata.v1",
                                 "recipe_invariant_sha256": self.spec["recipe"]["invariant_sha256"][0]},
                   "sources": [{"role": role, **self.spec[role]} for role in ("engine", "client")],
                   "runtime": {"tooling_repository": "alphastorm/omp-strata",
                               "tooling_commit": COMMIT, "runner": "lab-runner"},
                   "host": self.spec["host"],
                   "limits": {**limits, "reserved_gpu_seconds": 20000,
                              "rolling_24h": {"max_admissions_per_host": 2, "max_gpu_seconds_per_host": 50000,
                                              "spent_gpu_seconds": 0, "admissions": 0}},
                   "claim": {"claim_id": CLAIM, "fencing_generation": 1, "idempotency_key": "rq:" + RUN + ":1"},
                   "admitted_at": rr.utc(NOW - 10)}
        raw = rr.canonical_json(receipt)
        claim_doc = {"schema_version": "carrythrough.fleet-claim.v1", "claim_id": CLAIM,
                     "project_key": "project", "policy_generation": 1, "policy_sha256": "a" * 64,
                     "resource_id": "lab-resource", "host": "lab-host", "variant_id": "candidate",
                     "trial_manifest_sha256": rr.digest(raw), "repetitions": 1, "max_seconds": 20000,
                     "owner": "lab-runner", "restoration_ref": "incumbent",
                     "acquired_at": rr.utc(NOW - 10), "expires_at": rr.utc(NOW + 20000)}
        self.server.action = {"schema_version": "carrythrough.release-runner-action.v1", "action": stage,
                              "reattach": self.generation > 1, "run_id": RUN, "stage_attempt": 1,
                              "claim_generation": self.generation, "claim_token": "f" * 64,
                              "lease_expires_at": rr.utc(NOW + 600), "stage_deadline_at": rr.utc(NOW + 100),
                              "spec": copy.deepcopy(self.spec), "profile_sha256": profile_sha if claim else None,
                              "claim": claim_doc if claim else None,
                              "admission_receipt_b64": rr.encoded(raw) if claim else None,
                              "limits": limits, "native_refs": {}}
        return self.server.action

    def drive(self, stage, *, claim=True):
        self.assign(stage, claim=claim)
        self.runner.poll()

    def prepare(self):
        self.drive("prepare", claim=False)
        self.drive("source_check", claim=False)

    def stop_incumbent(self):
        self.prepare()
        self.drive("host_preflight")
        self.drive("incumbent_stop")

    def hold_exists(self):
        return (self.folder / "holds/lab-host.lock").exists()

    def reports(self, stage):
        return [body for path, body in self.server.requests if path.endswith("/reports") and body["stage"] == stage]

    def test_complete_protocol_stages_and_custody_order(self):
        self.stop_incumbent()
        self.drive("qualify")
        root = self.runner.root()
        native_id = self.runner.state["native_refs"]["native_run_id"]
        evidence = root / "evidence" / ("requalify-" + native_id)
        rr.atomic_write_json(evidence / "summary.json", [{"step": "start", "rc": 1, "pass_observed": False}])
        rr.atomic_write_json(evidence / "result.json",
                             {"run_id": native_id, "rc": 1, "failed": True, "completed": False,
                              "error": "test-failure", "finished_utc": rr.utc(NOW)})
        self.drive("qualify")
        self.drive("candidate_stop")
        self.drive("restore")
        self.assertTrue(self.hold_exists())
        self.drive("settle")
        self.assertFalse(self.hold_exists())
        self.drive("verify")
        self.drive("ledger")
        self.assertEqual(set(rr.STAGES), {b["stage"] for p, b in self.server.requests if p.endswith("/reports")})
        paths = [p for p, b in self.server.requests]
        release_at = next(i for i, p in enumerate(paths) if p.endswith("/release"))
        verify_at = next(i for i, (p, b) in enumerate(self.server.requests)
                         if p.endswith("/reports") and b["stage"] == "verify")
        self.assertLess(release_at, verify_at)
        self.assertEqual("test-failure", self.runner.state["native_refs"]["result_error"])

    def test_restart_during_qualify_reattaches_without_launch(self):
        self.stop_incumbent()
        self.drive("qualify")
        self.runner = self.make_runner()
        self.drive("qualify")
        self.assertEqual(1, self.launcher.launches)
        self.assertEqual("running", self.reports("qualify")[-1]["facts"]["phase"])
        self.assertTrue(self.hold_exists())

    def test_launch_intent_crash_without_native_fence_does_not_retry(self):
        self.stop_incumbent()
        self.drive("qualify")
        (self.runner.root() / "state/requalify-run.json").unlink()
        self.launcher.alive = False
        self.runner = self.make_runner()
        self.drive("qualify")
        self.assertEqual("runner_lost", self.reports("qualify")[-1]["failure_class"])
        self.assertEqual(1, self.launcher.launches)

    def test_stop_identity_is_durable_and_acknowledged_before_controller_use(self):
        self.prepare()
        def before_use():
            state = rr.document(self.runner.path)
            progress = self.reports("incumbent_stop")[-1]
            self.assertEqual(state["incumbent_identity"], progress["facts"]["identity"])
            self.assertFalse(progress["facts"]["stopped"])
            self.assertNotIn("pending_report", state)
        self.controller.before_use = before_use
        self.drive("incumbent_stop")
        self.runner = self.make_runner()
        self.drive("incumbent_stop")
        self.assertEqual(1, self.controller.effects.count("use"))

    def test_dead_fenced_run_without_result_reports_unknown_progress(self):
        self.stop_incumbent()
        self.drive("qualify")
        self.launcher.alive = False
        self.runner = self.make_runner()
        self.drive("qualify")
        report = self.reports("qualify")[-1]
        self.assertEqual(("failed", "runner_lost", None),
                         (report["status"], report["failure_class"], report["facts"]["summary_sha256"]))
        self.assertNotEqual("finished", report["facts"]["phase"])
        self.assertEqual(1, self.launcher.launches)
        self.assertTrue(self.hold_exists())

    def test_nonterminal_result_is_progress_when_live_and_lost_when_dead(self):
        self.stop_incumbent()
        self.drive("qualify")
        native_id = self.runner.state["native_refs"]["native_run_id"]
        path = self.runner.root() / "evidence" / ("requalify-" + native_id) / "result.json"
        rr.atomic_write_json(path, {"run_id": native_id, "rc": None, "completed": False,
                                   "failed": False, "steps": [], "finished_utc": None})
        self.runner = self.make_runner()
        self.drive("qualify")
        self.assertEqual("progress", self.reports("qualify")[-1]["status"])
        self.launcher.alive = False
        self.runner = self.make_runner()
        self.drive("qualify")
        report = self.reports("qualify")[-1]
        self.assertEqual(("failed", "runner_lost", None),
                         (report["status"], report["failure_class"], report["facts"]["summary_sha256"]))
        self.assertEqual(1, self.launcher.launches)
        self.assertTrue(self.hold_exists())

    def test_new_run_without_prior_custody_can_prepare(self):
        self.prepare()
        self.assign("prepare", claim=False)["run_id"] = "01CCCCCCCCCCCCCCCCCCCCCCCC"
        self.runner.poll()
        self.assertEqual("01CCCCCCCCCCCCCCCCCCCCCCCC", self.runner.state["run_id"])
        self.assertFalse(self.hold_exists())

    def test_control_plane_outage_cleans_up_and_keeps_hold(self):
        self.stop_incumbent()
        self.drive("qualify")
        self.server.unreachable = True
        with self.assertRaises(rr.Unreachable):
            self.runner.poll()
        self.assertIn("stop_candidate", self.native.effects)
        self.assertIn("return", self.controller.effects)
        self.assertFalse(self.launcher.alive)
        self.assertTrue(self.hold_exists())
        self.assertTrue(self.runner.state["restoration"]["verified"])
        self.assertFalse(any(p.endswith("/release") for p, _ in self.server.requests))

    def test_incumbent_mismatch_reports_before_refusing_mutation(self):
        self.prepare()
        self.native.identity["profile_id"] = "other-incumbent"
        self.assign("incumbent_stop")
        with self.assertRaisesRegex(rr.Refused, "incumbent_mismatch"):
            self.runner.poll()
        self.assertNotIn("use", self.controller.effects)
        self.assertFalse(self.runner.state["mutated"])
        self.assertEqual("progress", self.reports("incumbent_stop")[-1]["status"])

    def test_stale_report_response_and_action_prevent_mutation(self):
        self.prepare()
        self.assign("incumbent_stop")
        self.server.stale_response = True
        with self.assertRaises(rr.StaleFence):
            self.runner.poll()
        self.assertNotIn("use", self.controller.effects)
        self.server.stale_response = False
        self.server.action["claim_generation"] -= 1
        with self.assertRaises(rr.StaleFence):
            self.runner.poll()
        self.assertNotIn("use", self.controller.effects)

    def test_acknowledged_cleanup_route_prevents_original_stage_effect(self):
        self.prepare()
        self.assign("incumbent_stop")
        self.server.advance_incumbent = True
        with self.assertRaises(rr.StaleFence):
            self.runner.poll()
        self.assertNotIn("use", self.controller.effects)
        self.assertFalse(self.runner.state["mutated"])

    def test_expired_action_keeps_hold_and_does_not_launch(self):
        self.stop_incumbent()
        action = self.assign("qualify")
        action["lease_expires_at"] = rr.utc(NOW - 1)
        with self.assertRaises(rr.StaleFence):
            self.runner.poll()
        self.assertTrue(self.hold_exists())
        self.assertEqual(0, self.launcher.launches)

    def test_unstarted_settlement_requires_explicit_proof(self):
        self.prepare()
        self.drive("host_preflight")
        self.drive("settle")
        usage = next(body for path, body in self.server.requests if path.endswith("/usage"))
        release = next(body for path, body in self.server.requests if path.endswith("/release"))
        self.assertEqual(("aborted", 0, usage["started_at"]),
                         (usage["outcome"], usage["gpu_seconds"], usage["ended_at"]))
        self.assertTrue(release["no_mutation_verified"])
        self.assertEqual(usage["restoration"]["evidence_sha256"], release["evidence_sha256"])
        self.assertFalse(self.hold_exists())
        self.assertNotIn("return", self.controller.effects)

    def test_restoration_identity_and_launch_lineage(self):
        for changed, launch, expected in (
                (None, "incumbent-after", True), ("profile_id", "incumbent-after", False),
                ("profile_fingerprint", "incumbent-after", False),
                ("runtime_identity_sha256", "incumbent-after", False),
                ("config_file_sha256", "incumbent-after", False),
                (None, "incumbent-before", False), (None, "candidate-launch", False)):
            with self.subTest(changed=changed, launch=launch):
                self.runner.state = {}
                self.native.identity.update(profile_id="incumbent", profile_fingerprint="1" * 64,
                                            runtime_identity_sha256="2" * 64, config_file_sha256="3" * 64,
                                            run_generation="incumbent-before")
                self.controller.mutate_identity = changed
                self.controller.return_generation = launch
                self.stop_incumbent()
                self.runner.state["candidate_stopped"] = True
                self.runner.state["native_refs"]["candidate_launch_ids"] = ["candidate-launch"]
                self.drive("restore")
                self.assertEqual(expected, self.reports("restore")[-1]["facts"]["verified"])
                self.assertNotIn("run_generation", self.reports("restore")[-1]["facts"]["identity"])
                self.assertTrue(self.hold_exists())

    def test_restoration_failure_settlement_keeps_hold(self):
        self.stop_incumbent()
        self.drive("candidate_stop")
        self.controller.fail_return = True
        self.drive("restore")
        self.drive("settle")
        self.assertFalse(self.reports("restore")[-1]["facts"]["verified"])
        self.assertEqual("restoration_failed", self.reports("restore")[-1]["failure_class"])
        self.assertTrue(self.hold_exists())
        self.assertFalse(any(p.endswith("/release") for p, _ in self.server.requests))

    def test_foreign_claim_bindings_refuse_before_controller(self):
        self.prepare()
        for field in ("host", "resource_id", "variant_id", "trial_manifest_sha256", "restoration_ref"):
            with self.subTest(field=field):
                action = self.assign("host_preflight")
                action["claim"][field] = "wrong"
                with self.assertRaisesRegex(rr.Refused, "claim_binding_mismatch"):
                    self.runner.poll()
        self.assertEqual([], self.controller.effects)
        self.assertFalse(self.hold_exists())

    def test_foreign_action_binding_or_admission_refuses(self):
        self.prepare()
        for field in ("host", "native_host", "resource_id", "runner"):
            with self.subTest(field=field):
                action = self.assign("host_preflight")
                action["spec"]["host"][field] = "other"
                with self.assertRaisesRegex(rr.Refused, "action_binding_mismatch"):
                    self.runner.poll()
        action = self.assign("host_preflight")
        receipt = rr.parse(base64.b64decode(action["admission_receipt_b64"]))
        receipt["candidate"]["candidate_id"] = "other-candidate"
        raw = rr.canonical_json(receipt)
        action["admission_receipt_b64"] = rr.encoded(raw)
        action["claim"]["trial_manifest_sha256"] = rr.digest(raw)
        with self.assertRaisesRegex(rr.Refused, "admission_binding_mismatch"):
            self.runner.poll()
        self.assertEqual([], self.controller.effects)
        self.assertFalse(self.hold_exists())

    def test_replaced_native_profile_refuses_launch(self):
        self.stop_incumbent()
        self.assign("qualify")
        self.runner.profile().write_text('{"profile_id":"changed"}')
        with self.assertRaisesRegex(rr.Refused, "candidate_profile_changed"):
            self.runner.poll()
        self.assertEqual(0, self.launcher.launches)
        self.assertTrue(self.hold_exists())

    def test_candidate_stop_failure_prevents_controller_return(self):
        self.stop_incumbent()
        self.drive("qualify")
        self.native.stop_candidate = lambda *args: False
        self.drive("candidate_stop")
        self.drive("restore")
        self.assertNotIn("return", self.controller.effects)
        self.assertFalse(self.reports("restore")[-1]["facts"]["verified"])
        self.assertTrue(self.hold_exists())

    def test_candidate_profile_after_return_fails_despite_unobserved_launch(self):
        self.stop_incumbent()
        self.drive("candidate_stop")
        self.controller.mutate_identity = "profile_id"
        self.controller.return_generation = "unobserved-launch"
        self.drive("restore")
        self.assertFalse(self.reports("restore")[-1]["facts"]["verified"])
        self.assertTrue(self.hold_exists())

    def test_missing_facts_reports_only_allowed_interruption_failures(self):
        self.prepare()
        action = self.assign("host_preflight")
        self.runner.accept(action)
        for failure in ("runner_lost", "host_interrupted", "controller_unavailable"):
            self.runner.report(action, None, "failed", failure)
            self.assertIsNone(self.reports("host_preflight")[-1]["facts"])
        for status, failure in (("progress", "runner_lost"), ("succeeded", "runner_lost"),
                                ("failed", "candidate_failed"), ("failed", None)):
            with self.assertRaisesRegex(rr.Refused, "absent_stage_facts_refused"):
                self.runner.report(action, None, status, failure)
        self.assertEqual(3, len(self.reports("host_preflight")))

    def test_controller_loss_reports_absent_facts_and_retains_hold(self):
        self.prepare()
        def unavailable(verb):
            raise rr.ControllerUnavailable("test-unavailable")
        self.controller.call = unavailable
        self.drive("host_preflight")
        report = self.reports("host_preflight")[-1]
        self.assertEqual(("failed", "controller_unavailable", None),
                         (report["status"], report["failure_class"], report["facts"]))
        self.assertTrue(self.hold_exists())

    def test_unsupported_incumbent_and_controller_refuse_before_poll(self):
        for field in ("incumbent_kind", "controller_kind"):
            original = self.config[field]
            self.config[field] = "unsupported"
            with self.assertRaisesRegex(rr.Refused, "unsupported"):
                self.runner.poll()
            self.config[field] = original
        self.assertEqual([], self.server.requests)
        self.assertEqual([], self.controller.effects)

    def test_dirty_or_unrecorded_tooling_refuses_to_poll(self):
        for commit, head, status in ((None, COMMIT, b""), (COMMIT, "d" * 40, b""),
                                     (COMMIT, COMMIT, b"?? local.py"), (COMMIT, COMMIT, b" M script.py")):
            with self.subTest(commit=commit, status=status):
                def probe(root, expected):
                    values = iter((head.encode(), status))
                    return rr.tooling_identity(root, commit, run=lambda *a: next(values))
                self.runner.identity = probe
                with self.assertRaises(rr.Refused):
                    self.runner.poll()
        self.assertEqual([], self.server.requests)

    def test_single_instance_lock_does_not_remove_persistent_hold(self):
        self.prepare()
        self.drive("host_preflight")
        with self.runner.lock():
            with self.assertRaises(rr.lifecycle.LifecycleError):
                with self.make_runner().lock():
                    self.fail("second native host lock acquired")
        self.assertTrue(self.hold_exists())

    def test_schema_action_census_and_named_publication_refusal(self):
        self.assertEqual(set(rr.STAGES), set(schema("release-runner-action")["properties"]["action"]["enum"]))
        self.prepare()
        action = self.assign("verify")
        for stage in ("publish", "publish_lookup", "unrecognized"):
            with self.subTest(stage=stage):
                with self.assertRaisesRegex(rr.Refused, "unsupported_action:" + stage):
                    self.runner.accept({**action, "action": stage})


class PureTests(unittest.TestCase):
    def test_shared_invariant_vector_and_material_change(self):
        vector = rr.document(FIXTURES / "release-invariant.json")
        self.assertEqual(vector["invariant_sha256"], rr.invariant_digest(vector["profile"]))
        changed = copy.deepcopy(vector["profile"])
        changed["strata"]["setup_args"]["context"] += 1
        self.assertNotEqual(vector["invariant_sha256"], rr.invariant_digest(changed))
        self.assertEqual("carrythrough " + rr.WIRE_COMMIT, (FIXTURES / "COMMIT").read_text().splitlines()[0])

    def test_schema_validator_rejects_invalid_documents(self):
        valid = {"schema_version": "carrythrough.release-runner-poll.v1", "runner": "test-runner",
                 "adapter": "omp-strata.v1", "tooling_commit": COMMIT, "tooling_dirty": False,
                 "resources": [{"resource_id": "test-resource", "available": True, "free_disk_bytes": 1}]}
        validate(valid, schema("release-runner-poll"))
        for update in ({"tooling_dirty": True}, {"tooling_commit": "short"}, {"extra": True},
                       {"resources": []}, {"runner": ""}):
            with self.assertRaises(AssertionError):
                validate({**valid, **update}, schema("release-runner-poll"))

    def test_hash_closure_bounds_and_missing_or_mismatched_files(self):
        with tempfile.TemporaryDirectory() as folder:
            release = Path(folder).resolve()
            evidence = release / "evidence/data.bin"
            rr.atomic_write_bytes(evidence, b"opaque evidence")
            receipt = release / "receipts/gate.json"
            rr.atomic_write_json(receipt, {"evidence": [{"path_or_ref": "evidence/data.bin",
                                                       "sha256": rr.sha256_file(evidence)}]})
            ledger = release / "qualification.json"
            rr.atomic_write_json(ledger, {"gates": [{"receipts": [{"path": "receipts/gate.json",
                                                                 "sha256": rr.sha256_file(receipt)}]}]})
            rr.atomic_write_json(release / "manifest.json", {"qualification": {
                "ledger": "qualification.json", "ledger_sha256": rr.sha256_file(ledger)}})
            _, files = rr.evidence_bundle(release)
            self.assertEqual({"qualification.json", "receipts/gate.json", "evidence/data.bin"}, set(files))
            evidence.write_bytes(b"changed")
            with self.assertRaisesRegex(rr.Refused, "hash_mismatch"):
                rr.evidence_bundle(release)
            evidence.unlink()
            with self.assertRaises(FileNotFoundError):
                rr.evidence_bundle(release)
            evidence.write_bytes(b"x" * (rr.FILE_MAX + 1))
            with self.assertRaisesRegex(rr.Refused, "too_large"):
                rr.evidence_bundle(release)

    def test_controller_has_fixed_verbs_without_shell(self):
        calls = []
        controller = rr.Controller("controller-tool", "test-host",
                                   run=lambda argv, cwd, **kw: calls.append(argv) or b'{"schema_version":1}')
        for verb in ("status", "use", "return"):
            controller.call(verb)
        self.assertEqual([["controller-tool", verb, "test-host"] for verb in ("status", "use", "return")], calls)
        with self.assertRaises(rr.Refused):
            controller.call("start")

    def test_transport_refuses_publication_routes_and_token_in_origin(self):
        transport = rr.HTTP("https://control-plane.invalid", Path("not-read"))
        for path in ("/repos/example/project/pulls", "/api/project-loops/publish",
                     "/api/project-loops/release-runs/../reports"):
            with self.assertRaisesRegex(rr.Refused, "route_refused"):
                transport.post(path, {})
        with self.assertRaisesRegex(rr.Refused, "origin_required"):
            authority = "test-userinfo" + chr(64) + "control-plane.invalid"
            rr.HTTP("https://" + authority, Path("not-read"))

    def test_export_replay_compares_bytes_and_refuses_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            release = Path(folder).resolve() / "release"
            release.mkdir()
            (release / "manifest.json").write_bytes(b"before")
            def build(stage):
                self.assertEqual(b"before", (stage / "manifest.json").read_bytes())
                (stage / "manifest.json").write_bytes(b"after")
            rr.export_once(release, build)
            rr.export_once(release, build)
            self.assertEqual(b"after", (release / "manifest.json").read_bytes())
            (release / "manifest.json").write_bytes(b"foreign")
            with self.assertRaisesRegex(rr.Refused, "local_export_conflict"):
                rr.export_once(release, build)
            self.assertEqual(b"foreign", (release / "manifest.json").read_bytes())
