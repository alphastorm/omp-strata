"""Host-free runner protocol tests: loopback HTTP, disposable files and injected native effects."""
import base64
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import release_runner as rr

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/release_runner"
# Byte pins of the control plane's wire schemas at rr.WIRE_COMMIT, as copied into FIXTURES.
WIRE_SCHEMA_SHA256 = {
    "release-admission": "f3a5a92c767ee0f1676ce878b10cd7bbf795f6dddb43bc8c77263b1f2a69ef7a",
    "release-runner-action": "5fbb74f369424dc33d321190c2b4623facf9b5c6fdf34f119016ad431f8b2f4e",
    "release-runner-poll": "bc9eeb9b96a59e62a92bcbcd89b9f60fd359799a1b1ef1c44ac456200a7a6480",
    "release-runner-report": "489bd3fe8405dece8fe83f6179208c0c1ec749eb885b4daf8e6724b85c7f59f9",
}
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
        self.on_usage = self.on_release = None
        self.conflict = None  # bytes: the next report is answered 409 with this body
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
                        if parent.conflict is not None:
                            self.send_response(409)
                            self.end_headers()
                            self.wfile.write(parent.conflict)
                            return
                        action = parent.action
                        reply = {"run": {"id": action["run_id"], "state": "active",
                                         "claim_generation": action["claim_generation"],
                                         "stage_attempt": action["stage_attempt"], "stage": action["action"],
                                         "lease_expires_at": rr.utc(NOW + 600)}}
                        if parent.stale_response:
                            reply["run"]["claim_generation"] += 1
                        if parent.advance_incumbent:
                            reply["run"]["stage"] = "settle"
                        elif (body["stage"] == "incumbent_stop" and body["status"] == "succeeded"
                              and body["facts"]["stopped"]):
                            reply["run"]["stage"] = "qualify"  # as the control plane: the stop is latched confirmed
                    elif self.path.endswith("/usage"):
                        assert set(body) == {"schema_version", "claim_id", "started_at", "ended_at",
                                             "gpu_seconds", "outcome", "restoration", "evidence_paths"}
                        assert body["schema_version"] == "carrythrough.fleet-usage.v1"
                        assert body["claim_id"] == parent.action["claim"]["claim_id"]
                        if parent.on_usage:
                            parent.on_usage()
                        assert rr.timestamp(body["ended_at"]) >= rr.timestamp(body["started_at"])
                        if body["gpu_seconds"] == 0:
                            assert body["outcome"] == "aborted" and body["started_at"] == body["ended_at"]
                        reply = {"state": "cleanup_required" if body["restoration"]["verified"]
                                 else "restoration_failed"}
                    elif self.path.endswith("/release"):
                        assert set(body) in (set(), {"no_mutation_verified", "evidence_sha256"})
                        if parent.on_release:
                            parent.on_release()
                        reply = {"claim": {"claim_id": parent.action["claim"]["claim_id"]}, "state": "released",
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
                         "launch_id": "incumbent-before"}
        self.healthy, self.listening = True, True
        self.candidate_live = False  # a runtime this run did not start is live in the candidate root
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
        # As the lifecycle reports it: a stopped incumbent has no running launch and is not healthy.
        identity = {key: value for key, value in self.identity.items() if key != "launch_id" or self.listening}
        identity["healthy"] = self.healthy and self.listening
        return identity, self.listening

    def stop_candidate(self, work, profile, root):
        self.effects.append("stop_candidate")
        return True

    def candidate_idle(self, profile, root):
        self.effects.append("candidate_idle")
        return not self.candidate_live

    def export(self, *args):
        self.effects.append("export")

    def verify(self, *args):
        return False


class FakeController:
    def __init__(self, native):
        self.native, self.effects = native, []
        self.reserved, self.fail_return = False, False
        self.return_launch = "incumbent-after"
        self.mutate_identity = None
        self.before_use = None
        self.receipt_not_ready = False

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
            self.native.identity["launch_id"] = self.return_launch
            if self.mutate_identity:
                self.native.identity[self.mutate_identity] = "f" * 64
        return {"schema_version": 1, "host": "lab-host", "generation": 1,
                "reserved": self.reserved, "admission_open": not self.reserved,
                "phase": "Ready for you" if self.reserved else "Fleet", "blockers": [], "jobs": {},
                "service": {"generation": 1},
                "resources": {"ready": not (self.reserved and self.receipt_not_ready), "blockers": [],
                              "unexplained_compute": [],
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


class LifecycleIncumbent:
    """The runner's real incumbent reader over lifecycle-shaped records, with `lifecycle.status` itself deciding the
    printed state. Only the process census, runtime health checks and port probe are faked. FakeNative's identity and
    FakeController's `use`/`return` drive the records."""
    PROFILE = rr.ROOT / "profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6.json"

    def __init__(self, native, folder):
        self.native, self.root = native, folder / "incumbent-root"
        self.layout = rr.Layout(self.root, rr.load(self.PROFILE))
        self.reader = rr.Native(rr.ROOT, {"incumbent_profile": str(self.PROFILE), "incumbent_root": str(self.root)})
        self.reset()

    def reset(self):
        self.drop, self.problems, self.relaunch = None, [], None

    def __call__(self):
        identity, live = self.native.identity, self.native.listening
        install = {"profile_id": identity["profile_id"], "profile_fingerprint": identity["profile_fingerprint"],
                   "runtime_identity_sha256": identity["runtime_identity_sha256"],
                   "identity": {"config_file_sha256": identity["config_file_sha256"]}}
        if self.drop:
            install["identity"].pop(self.drop, None)
            install.pop(self.drop, None)
        rr.atomic_write_json(self.layout.install_record, install)
        # As lifecycle `start` writes it; a stop keeps the ended launch's identifier in the record.
        rr.atomic_write_json(self.layout.run_record, {
            "schema_version": 1, "launch_id": identity["launch_id"], "state": "running" if live else "stopped",
            "runtime_identity_sha256": identity["runtime_identity_sha256"]})

        def status(*args, **kwargs):
            if self.relaunch:  # the incumbent restarted while status ran
                rr.atomic_write_json(self.layout.run_record,
                                     {**rr.document(self.layout.run_record), "launch_id": self.relaunch})
            census = {"server": SimpleNamespace(pid=1)} if live else {}
            with patch.object(rr.lifecycle, "running", return_value=census), \
                    patch.object(rr.lifecycle, "read_key", return_value="test-key"), \
                    patch.object(rr.lifecycle, "runtime_checks", return_value={"problems": list(self.problems)}), \
                    patch.object(rr.lifecycle.procs, "descendants", return_value=[]):
                return json.dumps(rr.lifecycle.status(self.layout)).encode()
        with patch.object(self.reader, "tool", side_effect=status), \
                patch.object(rr.lifecycle, "port_in_use", return_value=live):
            return self.reader.incumbent()


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

    def assign(self, stage, *, claim=True, claim_id=CLAIM, attempt=1):
        self.generation += 1
        limits = {"stage_seconds": {stage: 100 for stage in (*rr.STAGES, "admission", "publish", "outcome")},
                  "run_seconds_max": 20000, "free_disk_bytes_min": 1, "checkpoint_bytes_min": 1,
                  "candidate_root_bytes_max": 100000000, "provider_calls_max": 0,
                  "retries": {"per_stage_max": 1, "host_attempts_max": 1, "backoff_seconds": 1,
                              "publication_lookups_max": 1}}
        profile_sha = rr.sha256_file(self.runner.profile()) if self.runner.state else "d" * 64
        receipt = {"schema_version": "carrythrough.release-admission.v1", "run_id": RUN, "attempt": attempt,
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
                   "claim": {"claim_id": claim_id, "fencing_generation": 1,
                             "idempotency_key": "rq:" + RUN + ":" + str(attempt)},
                   "admitted_at": rr.utc(NOW - 10)}
        raw = rr.canonical_json(receipt)
        claim_doc = {"schema_version": "carrythrough.fleet-claim.v1", "claim_id": claim_id,
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

    def pass_qualification(self):
        native_id = self.runner.state["native_refs"]["native_run_id"]
        evidence = self.runner.root() / "evidence" / ("requalify-" + native_id)
        rr.atomic_write_json(evidence / "summary.json", [{"step": "start", "rc": 0, "pass_observed": True}])
        rr.atomic_write_json(evidence / "result.json",
                             {"run_id": native_id, "rc": 0, "failed": False, "completed": True,
                              "error": None, "finished_utc": rr.utc(NOW)})

    def passing_run_through_verify(self):
        self.native.verify = lambda *args: True
        self.stop_incumbent()
        self.drive("qualify")
        self.pass_qualification()
        for stage in ("qualify", "candidate_stop", "restore", "settle", "verify"):
            self.drive(stage)
        self.assertTrue(self.reports("verify")[-1]["facts"]["verify_ok"])

    def test_prepare_exits_report_their_wire_class_with_null_facts(self):
        self.assertEqual({"native_refused", "source_unavailable", "candidate_superseded"},
                         set(rr.PREPARE_OUTCOMES.values()))
        for index, (code, failure) in enumerate(sorted(rr.PREPARE_OUTCOMES.items())):
            with self.subTest(code=code):
                calls = []
                def refuse(path, spec, code=code):
                    calls.append(code)
                    raise rr.NativeRefusal(code)
                self.native.prepare = refuse
                run = "01" + "CDEFGHJKMN"[index] * 24
                self.assign("prepare", claim=False)["run_id"] = run
                self.runner.poll()
                self.make_runner().poll()  # after a restart the same attempt replays the stored report
                sent = [body for path, body in self.server.requests if path.endswith(run + "/reports")]
                self.assertEqual([("failed", failure, None)] * 2,
                                 [(body["status"], body["failure_class"], body["facts"]) for body in sent])
                attempts = rr.CAMPAIGN_LOCK_ATTEMPTS if code == "native_campaign_locked" else 1
                self.assertEqual([code] * attempts, calls)
                self.assertEqual(code, rr.document(self.runner.path)["native_outcome"]["code"])
                action = self.assign("prepare", claim=False)
                action.update(run_id=run, stage_attempt=2)
                self.runner = self.make_runner()
                self.runner.poll()  # a new attempt runs the native tools again
                self.assertEqual([code] * attempts * 2, calls)
        self.assertFalse(self.hold_exists())

    def locked_prepare(self, refusals):
        """Prepare whose campaign lock stays held for `refusals` native attempts (None: never released)."""
        calls, prepare = [], self.native.prepare
        def locked(path, spec):
            calls.append(path)
            if refusals is None or len(calls) <= refusals:
                raise rr.NativeRefusal("native_campaign_locked")
            return prepare(path, spec)
        self.native.prepare = locked
        self.drive("prepare", claim=False)
        return len(calls), [(body["status"], body["failure_class"]) for body in self.reports("prepare")]

    def test_a_campaign_lock_released_within_the_bound_lets_the_stage_succeed_with_one_report(self):
        self.assertEqual((3, [("succeeded", None)]), self.locked_prepare(2))

    def test_a_campaign_lock_never_released_is_one_definitive_refusal(self):
        self.assertEqual((3, [("failed", "native_refused")]), self.locked_prepare(None))
        self.assertEqual("native_campaign_locked", rr.document(self.runner.path)["native_outcome"]["code"])

    def test_unmapped_prepare_exits_send_no_prepare_class(self):
        for index, error in enumerate((rr.Refused("worktree_commit_mismatch"),
                                       rr.NativeRefusal("native_ledger_refused"), OSError("local cache"))):
            with self.subTest(error=str(error)):
                def fail(path, spec, error=error):
                    raise error
                self.native.prepare = fail
                self.assign("prepare", claim=False)["run_id"] = "01" + "CDE"[index] * 24
                with self.assertRaises(type(error)):
                    self.runner.poll()
        self.assertEqual([], self.reports("prepare"))

    def test_ledger_reports_no_qualified_fact_the_native_campaign_refused(self):
        self.passing_run_through_verify()
        original = self.native.campaign_status
        def ledger(work, spec, status, **kwargs):
            if status == "qualified":
                raise rr.NativeRefusal("native_ledger_refused")
            original(work, spec, status, **kwargs)
        self.native.campaign_status = ledger
        self.drive("ledger")
        report = self.reports("ledger")[-1]
        path = self.runner.work() / report["facts"]["campaign_path"]
        self.assertEqual(("failed", "verification_failed"), (report["status"], report["failure_class"]))
        self.assertEqual({"status": "blocked"}, rr.document(path))
        self.assertEqual(rr.sha256_file(path), report["facts"]["campaign_sha256"])
        self.assertNotIn("ledger:qualified", self.native.effects)

    def test_ledger_does_not_qualify_evidence_changed_after_verify(self):
        self.passing_run_through_verify()
        manifest = self.runner.work() / "releases/candidate/manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        self.drive("ledger")
        report = self.reports("ledger")[-1]
        self.assertEqual(("failed", "verification_failed"), (report["status"], report["failure_class"]))
        self.assertNotIn("ledger:qualified", self.native.effects)
        self.assertEqual("ledger:blocked", self.native.effects[-1])

    def test_foreign_files_or_fence_in_a_fresh_candidate_root_refuse_before_any_root_effect(self):
        self.stop_incumbent()
        root = Path(self.config["candidates"]) / (RUN + "-h1-a1")
        (root / "state").mkdir(parents=True)
        (root / "state/foreign.json").write_text("{}")
        self.assign("qualify")
        with self.assertRaisesRegex(rr.Refused, "candidate_root_occupied"):
            self.runner.poll()
        fence = root / "state/requalify-run.json"
        fence.write_bytes(b'{"run_id": null}')
        with self.assertRaisesRegex(rr.Refused, "native_fence_mismatch"):
            self.runner.poll()
        self.runner.cleanup()
        self.assertEqual(b'{"run_id": null}', fence.read_bytes())
        self.assertNotIn("candidate_root", self.runner.state["native_refs"])
        self.assertEqual([], [e for e in self.native.effects if e.startswith("ledger:") or e == "fetch"])
        self.assertNotIn("stop_candidate", self.native.effects)
        self.assertEqual((0, 0), (self.launcher.launches, self.launcher.stops))

    def test_unnamed_fence_after_launch_is_foreign_never_stopped_or_removed(self):
        self.stop_incumbent()
        self.drive("qualify")
        fence = self.runner.root() / "state/requalify-run.json"
        fence.write_bytes(b'{"run_id": null}')
        self.launcher.alive = False
        self.runner = self.make_runner()
        self.assign("qualify")
        with self.assertRaisesRegex(rr.Refused, "native_fence_mismatch"):
            self.runner.poll()
        self.runner.cleanup()
        self.assertEqual(b'{"run_id": null}', fence.read_bytes())
        self.assertNotIn("stop_candidate", self.native.effects)
        self.assertEqual((1, 0), (self.launcher.launches, self.launcher.stops))
        self.assertNotIn("return", self.controller.effects)
        self.assertFalse(self.runner.state["restoration"]["verified"])
        self.assertTrue(self.hold_exists())

    def test_unreadable_hold_keeps_custody_and_routes_to_the_restoration_check(self):
        self.stop_incumbent()
        hold = self.folder / "holds/lab-host.lock"
        hold.write_bytes(b"{")
        self.runner = self.make_runner()
        for stage in ("qualify", "candidate_stop", "restore", "settle"):
            self.drive(stage)
            report = self.reports(stage)[-1]
            self.assertEqual(("failed", "host_interrupted", None),
                             (report["status"], report["failure_class"], report["facts"]))
        self.runner.cleanup()
        self.assertEqual(b"{", hold.read_bytes())
        self.assertEqual("host_lock_unreadable", rr.document(self.runner.path)["custody_refused"])
        self.assertEqual((0, 0), (self.launcher.launches, self.launcher.stops))
        self.assertNotIn("return", self.controller.effects)
        self.assertFalse(any(p.endswith(("/usage", "/release")) for p, _ in self.server.requests))

    def test_settlement_does_not_release_a_claim_whose_hold_became_unreadable(self):
        self.stop_incumbent()
        self.drive("candidate_stop")
        self.drive("restore")
        hold = self.folder / "holds/lab-host.lock"
        self.server.on_usage = lambda: hold.write_bytes(b"[]")
        self.drive("settle")
        report = self.reports("settle")[-1]
        self.assertEqual(("failed", "host_interrupted"), (report["status"], report["failure_class"]))
        self.assertFalse(any(p.endswith("/release") for p, _ in self.server.requests))
        self.assertEqual(b"[]", hold.read_bytes())
        self.assertFalse(self.runner.state["settled"])

    def test_local_hold_stays_when_its_removal_fails_after_an_accepted_release(self):
        self.stop_incumbent()
        self.drive("candidate_stop")
        self.drive("restore")
        hold = self.folder / "holds/lab-host.lock"
        self.server.on_release = lambda: hold.write_bytes(b"123")
        self.drive("settle")
        self.assertEqual("succeeded", self.reports("settle")[-1]["status"])
        self.assertEqual(b"123", hold.read_bytes())
        self.assertEqual("host_lock_unreadable", rr.document(self.runner.path)["hold_release_refused"])
        self.assertTrue(self.runner.state["settled"])

    def test_readmitted_claim_is_a_fresh_custody_generation(self):
        self.stop_incumbent()
        self.drive("qualify")
        first = self.runner.state["native_refs"]["native_run_id"]
        rr.atomic_write_json(self.runner.root() / "state/run.json", {"launch_id": "candidate-first"})
        self.launcher.alive = False
        self.drive("qualify")
        self.assertEqual(("runner_lost", "candidate-first"), (self.reports("qualify")[-1]["failure_class"],
                                                              self.reports("qualify")[-1]["facts"]["launch_id"]))
        for stage in ("candidate_stop", "restore", "settle"):
            self.drive(stage)
        self.assertFalse(self.hold_exists())
        second = "01DDDDDDDDDDDDDDDDDDDDDDDD"
        self.assign("host_preflight", claim_id=second, attempt=1)
        with self.assertRaisesRegex(rr.Refused, "admission_attempt_reused"):
            self.runner.poll()
        statuses = self.controller.effects.count("status")
        for stage in ("host_preflight", "incumbent_stop", "qualify"):
            self.assign(stage, claim_id=second, attempt=2)
            self.runner.poll()
        # This attempt's root has no lifecycle launch yet; the earlier attempt's stays contradicting evidence.
        self.assertIsNone(self.reports("qualify")[-1]["facts"]["launch_id"])
        self.assertEqual(["candidate-first"], self.runner.state["native_refs"]["candidate_launch_ids"])
        self.assertGreater(self.controller.effects.count("status"), statuses)
        self.assertEqual(2, self.controller.effects.count("use"))
        self.assertEqual((RUN + "-h1-a1", RUN + "-h2-a1"), (first, self.runner.state["native_refs"]["native_run_id"]))
        self.assertEqual(2, self.launcher.launches)
        self.assertEqual(second, rr.document(self.folder / "holds/lab-host.lock")["claim_id"])
        self.assertEqual(["ledger:queued", "ledger:running", "ledger:failed", "ledger:queued", "ledger:running"],
                         [effect for effect in self.native.effects if effect.startswith("ledger:")])
        self.pass_qualification()
        self.controller.return_launch = "incumbent-after-second"
        self.native.verify = lambda *args: True
        for stage in ("qualify", "candidate_stop", "restore", "settle", "verify"):
            self.assign(stage, claim_id=second, attempt=2)
            self.runner.poll()
        usages = [body for path, body in self.server.requests if path.endswith("/usage")]
        self.assertEqual([CLAIM, second], [usage["claim_id"] for usage in usages])
        self.assertTrue(self.reports("restore")[-1]["facts"]["verified"])
        # The settled first claim's runner_lost report does not fail the second claim's verification.
        self.assertTrue(self.reports("verify")[-1]["facts"]["verify_ok"])

    def test_reused_or_lower_admission_attempt_refuses_without_changing_custody(self):
        self.prepare()
        self.assign("host_preflight", attempt=2)
        self.runner.poll()
        self.assign("settle", attempt=2)
        self.runner.poll()
        self.assertTrue(self.runner.state["settled"])
        self.assertFalse(self.hold_exists())
        second = "01DDDDDDDDDDDDDDDDDDDDDDDD"
        persisted, in_memory = self.runner.path.read_bytes(), copy.deepcopy(self.runner.state)
        effects, requests = list(self.controller.effects), len(self.server.requests)
        for attempt in (1, 2):  # lower, then equal to the settled claim's host attempt
            with self.subTest(attempt=attempt):
                self.assign("host_preflight", claim_id=second, attempt=attempt)
                with self.assertRaisesRegex(rr.Refused, "admission_attempt_reused"):
                    self.runner.poll()
                self.assertEqual(persisted, self.runner.path.read_bytes())
                self.assertEqual(in_memory, self.runner.state)
                self.assertFalse(self.hold_exists())
                self.assertFalse((self.folder / "state/claims" / (second + ".json")).exists())
        self.assertEqual(effects, self.controller.effects)
        self.assertEqual([], [p for p, _ in self.server.requests[requests:] if not p.endswith("/next-action")])
        self.assign("host_preflight", claim_id=second, attempt=3)
        self.runner.poll()
        self.assertEqual(second, rr.document(self.folder / "holds/lab-host.lock")["claim_id"])
        self.assertEqual([CLAIM], [prior["claim_id"] for prior in self.runner.state["prior_claims"]])

    def test_main_cleans_up_after_a_native_value_error_escapes_a_stage(self):
        self.prepare()
        self.drive("host_preflight")
        self.assign("incumbent_stop")
        # After `use`, check_reservation raises ExperimentError (a ValueError, not a runner Refused).
        self.controller.receipt_not_ready = True
        config = {**self.config, "tooling": str(rr.ROOT), "control_plane_origin": self.server.origin,
                  "controller": {"executable": "controller-tool"}}
        path = self.folder / "binding.json"
        rr.atomic_write_json(path, config)
        with patch.object(rr, "Runner", return_value=self.runner):
            with self.assertRaisesRegex(rr.experiment_loop.ExperimentError, "controller_reservation_not_ready"):
                rr.main(["--config", str(path), "--token-file", str(self.token), "--once"])
        # Preflight status; use and its invalid receipt; then cleanup's return and verification status.
        self.assertEqual(["status", "use", "status", "return", "status"], self.controller.effects)
        # Returned under a new launch, but the control plane never accepted the stop: not verified, hold kept.
        self.assertFalse(rr.document(self.runner.path)["restoration"]["verified"])
        self.assertTrue(self.hold_exists())
        self.assertFalse(any(p.endswith(("/usage", "/release")) for p, _ in self.server.requests))

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
        self.drive("host_preflight")
        def before_use():
            state = rr.document(self.runner.path)
            progress = self.reports("incumbent_stop")[-1]
            self.assertEqual(state["incumbent_before_stop"], progress["facts"]["identity"])
            self.assertEqual(("incumbent-before", True), (progress["facts"]["identity"]["launch_id"],
                                                          progress["facts"]["identity"]["healthy"]))
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
        self.drive("host_preflight")  # the reference itself is the wrong incumbent
        self.assign("incumbent_stop")
        with self.assertRaisesRegex(rr.Refused, "incumbent_mismatch"):
            self.runner.poll()
        self.assertNotIn("use", self.controller.effects)
        self.assertFalse(self.runner.state["mutated"])
        self.assertEqual("progress", self.reports("incumbent_stop")[-1]["status"])

    def test_stop_without_a_preflight_reference_or_after_an_incumbent_restart_is_refused(self):
        self.prepare()
        self.assign("incumbent_stop")
        with self.assertRaisesRegex(rr.Refused, "incumbent_mismatch"):
            self.runner.poll()
        self.drive("host_preflight")
        self.native.identity["launch_id"] = "incumbent-restarted"  # same install, another launch than preflight saw
        self.assign("incumbent_stop")
        with self.assertRaisesRegex(rr.Refused, "incumbent_mismatch"):
            self.runner.poll()
        self.assertEqual("incumbent-restarted", self.reports("incumbent_stop")[-1]["facts"]["identity"]["launch_id"])
        self.assertNotIn("use", self.controller.effects)
        self.assertFalse(self.runner.state["mutated"])

    def test_restore_identities_for_the_three_reference_cases(self):
        leaves = {"profile_id": "incumbent", "profile_fingerprint": "1" * 64,
                  "runtime_identity_sha256": "2" * 64, "config_file_sha256": "3" * 64}
        reference = {**leaves, "launch_id": "incumbent-before", "healthy": True}
        for case, launch, verified in (("never stopped", None, True), ("never stopped, relaunched", None, False),
                                       ("stopped, new launch", "incumbent-after", True),
                                       ("stopped, same launch", "incumbent-before", False)):
            with self.subTest(case=case):
                self.runner.state = {}
                self.native.identity.update(launch_id="incumbent-before")
                self.prepare()
                self.drive("host_preflight")
                self.assertEqual(reference, self.reports("host_preflight")[-1]["facts"]["incumbent"])
                if launch is None:
                    if case.endswith("relaunched"):
                        self.native.identity["launch_id"] = "incumbent-relaunched"
                    returns = self.controller.effects.count("return")
                    self.drive("restore")
                    self.assertEqual(returns, self.controller.effects.count("return"))
                else:
                    self.controller.return_launch = launch
                    self.drive("incumbent_stop")
                    self.assertEqual(reference, self.reports("incumbent_stop")[-1]["facts"]["identity"])
                    self.runner.state["candidate_stopped"] = True
                    self.drive("restore")
                facts = self.reports("restore")[-1]["facts"]
                expected = {**leaves, "launch_id": self.native.identity["launch_id"], "healthy": True}
                self.assertEqual((expected, verified), (facts["identity"], facts["verified"]))

    def test_a_stop_the_control_plane_never_accepted_does_not_verify_a_new_launch(self):
        self.prepare()
        self.drive("host_preflight")
        def lose_acknowledgement():
            self.server.unreachable = True
        self.controller.before_use = lose_acknowledgement
        self.assign("incumbent_stop")
        with self.assertRaises(rr.Unreachable):
            self.runner.poll()  # the stopped report is lost; local cleanup returns the incumbent
        restoration = self.runner.state["restoration"]
        self.assertEqual(("incumbent-after", True, False), (restoration["identity"]["launch_id"],
                                                            restoration["identity"]["healthy"],
                                                            restoration["verified"]))
        self.assertNotIn("stop_confirmed", self.runner.state)
        self.assertTrue(self.hold_exists())

    def test_named_restore_cases_from_lifecycle_record_shapes(self):
        reader = LifecycleIncumbent(self.native, self.folder)
        self.native.incumbent = reader
        leaves = {"profile_id": "incumbent", "profile_fingerprint": reader.layout.profile.fingerprint,
                  "runtime_identity_sha256": "2" * 64, "config_file_sha256": "3" * 64}
        def sent(launch, healthy=True, **changes):
            identity = {**leaves, **changes, "launch_id": launch, "healthy": healthy}
            return {key: value for key, value in identity.items() if value is not None}
        for case, stop, launch, knob, verified, identity in (
                ("never_stopped_same_launch", None, None, None, True, sent("incumbent-before")),
                ("stopped_new_launch", "confirmed", "incumbent-after", None, True, sent("incumbent-after")),
                ("unobserved_candidate_proves_nothing", "confirmed", "incumbent-after", "candidates", True,
                 sent("incumbent-after")),
                ("stopped_same_launch", "confirmed", "incumbent-before", None, False, sent("incumbent-before")),
                ("unconfirmed_stop_new_launch", "unconfirmed", "incumbent-after", None, False, sent("incumbent-after")),
                ("candidate_launch", "confirmed", "candidate-one", "candidates", False, sent("candidate-one")),
                ("missing_launch", "confirmed", "incumbent-after", "relaunch", False, sent(None)),
                ("unhealthy", "confirmed", "incumbent-after", "problems", False, sent("incumbent-after", False)),
                ("different_profile", "confirmed", "incumbent-after", "profile", False,
                 sent(None, False, profile_fingerprint="f" * 64)),
                ("missing_stable_leaf", "confirmed", "incumbent-after", "drop", False,
                 sent("incumbent-after", config_file_sha256=None))):
            with self.subTest(case=case):
                self.runner.state = {}
                self.native.identity = {**leaves, "launch_id": "incumbent-before"}
                self.native.listening, self.server.unreachable = True, False
                self.controller.before_use, self.controller.mutate_identity = None, None
                self.controller.return_launch = launch
                reader.reset()
                self.prepare()
                self.drive("host_preflight")
                self.assertEqual(sent("incumbent-before"), self.reports("host_preflight")[-1]["facts"]["incumbent"])
                if stop == "unconfirmed":
                    self.controller.before_use = lambda: setattr(self.server, "unreachable", True)
                    self.assign("incumbent_stop")
                    with self.assertRaises(rr.Unreachable):
                        self.runner.poll()  # the stopped report is lost; local cleanup returns and checks
                    self.server.unreachable = False
                elif stop == "confirmed":
                    self.drive("incumbent_stop")
                    self.runner.state["candidate_stopped"] = True
                    if knob == "candidates":
                        self.runner.state["native_refs"]["candidate_launch_ids"] = ["candidate-one"]
                    reader.drop = "config_file_sha256" if knob == "drop" else None
                    reader.problems = ["test health problem"] if knob == "problems" else []
                    reader.relaunch = "incumbent-relaunched" if knob == "relaunch" else None
                    self.controller.mutate_identity = "profile_fingerprint" if knob == "profile" else None
                self.drive("restore")
                facts = self.reports("restore")[-1]["facts"]
                self.assertEqual((identity, verified), (facts["identity"], facts["verified"]))

    def not_idle_result(self):
        """The launch refused this attempt's root before any step: the requalify result for a root not idle."""
        native_id = self.runner.state["native_refs"]["native_run_id"]
        evidence = self.runner.root() / "evidence" / ("requalify-" + native_id)
        row = {"step": "status-before-launch", "rc": 0, "pass_observed": None}
        rr.atomic_write_json(evidence / "summary.json", [row])
        rr.atomic_write_json(evidence / "result.json",
                             {"schema_version": 1, "run_id": native_id, "rc": 2, "failed": True, "completed": False,
                              "steps": [row], "error": "live_runtime", "finished_utc": rr.utc(NOW)})
        self.launcher.alive = False

    def test_a_root_not_idle_is_named_never_retried_into_and_nothing_in_it_is_stopped(self):
        self.stop_incumbent()
        self.drive("qualify")
        rr.atomic_write_json(self.runner.root() / "state/run.json", {"launch_id": "not-this-runs", "state": "running"})
        self.native.candidate_live = True
        self.not_idle_result()
        for _ in range(2):
            self.drive("qualify")
            report = self.reports("qualify")[-1]
            self.assertEqual(("failed", "host_interrupted", None),
                             (report["status"], report["failure_class"], report["facts"]))
        self.assertEqual("candidate_root_not_idle", self.runner.state["native_refs"]["root_refusal"])
        self.assertEqual(1, self.launcher.launches)
        self.drive("candidate_stop")
        self.assertFalse(self.reports("candidate_stop")[-1]["facts"]["stopped"])
        self.drive("restore")
        self.assertFalse(self.reports("restore")[-1]["facts"]["verified"])
        self.assertNotIn("stop_candidate", self.native.effects)  # observed read-only, still live: no return
        self.assertIn("candidate_idle", self.native.effects)
        self.assertNotIn("return", self.controller.effects)
        self.assertNotIn("not-this-runs", self.runner.state["native_refs"].get("candidate_launch_ids", []))
        self.assertTrue(self.hold_exists())

    def test_a_root_still_not_idle_after_readmission_is_reported_again_and_the_bound_ends_the_run(self):
        # The fake control plane admits the run on this host twice (host-attempt bound 2), then admits no more.
        self.prepare()
        for attempt, claim in ((1, CLAIM), (2, "01DDDDDDDDDDDDDDDDDDDDDDDD")):
            self.controller.return_launch = "incumbent-after-" + str(attempt)
            for stage in ("host_preflight", "incumbent_stop", "qualify"):
                self.assign(stage, claim_id=claim, attempt=attempt)
                self.runner.poll()
            self.assertNotIn("root_refusal", self.runner.state["native_refs"])  # this root is observed afresh
            self.not_idle_result()
            for stage in ("qualify", "candidate_stop", "restore", "settle"):
                self.assign(stage, claim_id=claim, attempt=attempt)
                self.runner.poll()
            self.assertEqual("candidate_root_not_idle", self.runner.state["native_refs"]["root_refusal"])
        finished = [(r["status"], r["failure_class"], r["facts"]) for r in self.reports("qualify")
                    if r["status"] != "progress"]
        self.assertEqual([("failed", "host_interrupted", None)] * 2, finished)
        self.assertEqual("candidate_root_not_idle", self.runner.state["prior_claims"][0]["native_refs"]["root_refusal"])
        self.assertEqual((RUN + "-h1-a1", RUN + "-h2-a1"),
                         (self.runner.state["prior_claims"][0]["native_refs"]["native_run_id"],
                          self.runner.state["native_refs"]["native_run_id"]))
        self.assertEqual(2, self.launcher.launches)
        self.assertEqual([True, True], [r["facts"]["verified"] for r in self.reports("restore")])
        self.assertNotIn("stop_candidate", self.native.effects)
        self.assertFalse(self.hold_exists())

    def interrupted(self, rows, summary=True):
        """A launch ended by a signal (requalify's terminal rc 130); returns the qualify report's facts."""
        self.stop_incumbent()
        self.drive("qualify")
        native_id = self.runner.state["native_refs"]["native_run_id"]
        evidence = self.runner.root() / "evidence" / ("requalify-" + native_id)
        rr.atomic_write_json(evidence / "result.json",
                             {"schema_version": 1, "run_id": native_id, "rc": 130, "failed": True, "completed": False,
                              "steps": rows, "error": None, "finished_utc": rr.utc(NOW)})
        if summary:
            rr.atomic_write_json(evidence / "summary.json", rows)
        self.launcher.alive = False
        self.drive("qualify")
        report = self.reports("qualify")[-1]
        self.assertEqual(("failed", "host_interrupted"), (report["status"], report["failure_class"]))
        self.assertEqual("finished", report["facts"]["phase"])
        self.assertEqual(rr.sha256_file(evidence / "summary.json") if summary else None,
                         report["facts"]["summary_sha256"])
        return report["facts"]

    def test_an_interrupt_before_the_first_step_is_not_a_candidate_failure(self):
        facts = self.interrupted([])  # beside a summary without rows
        self.assertEqual(([], {}), (facts["steps"], facts["gates"]))

    def test_an_interrupt_before_the_first_step_without_a_summary_is_not_a_candidate_failure(self):
        facts = self.interrupted([], summary=False)
        self.assertEqual(([], {}), (facts["steps"], facts["gates"]))

    def test_an_interrupt_after_a_failed_gate_keeps_that_gates_evidence(self):
        facts = self.interrupted([{"step": "status-before-launch", "rc": 0, "pass_observed": None},
                                  {"step": "eval", "rc": 1, "pass_observed": False},
                                  {"step": "g20", "rc": 130, "pass_observed": None}])
        # The interrupted step decided nothing: its gate is incomplete, not failed.
        self.assertEqual({"G24": "fail", "G20": "blocked"}, facts["gates"])
        self.assertEqual(["status-before-launch", "eval", "g20"], facts["steps"])

    def test_an_interrupt_after_a_passed_gate_keeps_that_gates_evidence(self):
        facts = self.interrupted([{"step": "status-before-launch", "rc": 0, "pass_observed": None},
                                  {"step": "eval", "rc": 0, "pass_observed": True},
                                  {"step": "g20", "rc": 130, "pass_observed": None}])
        self.assertEqual({"G24": "pass", "G20": "blocked"}, facts["gates"])

    def test_the_status_row_before_launch_is_a_reported_step_that_decides_no_gate(self):
        self.stop_incumbent()
        self.drive("qualify")
        self.pass_qualification()
        native_id = self.runner.state["native_refs"]["native_run_id"]
        summary = self.runner.root() / "evidence" / ("requalify-" + native_id) / "summary.json"
        # Exit 1: status observed `failed`, an idle state a launch may enter.
        rr.atomic_write_json(summary, [{"step": "status-before-launch", "rc": 1, "pass_observed": None},
                                       *rr.document(summary)])
        self.drive("qualify")
        report = self.reports("qualify")[-1]
        self.assertEqual("succeeded", report["status"])
        self.assertEqual(["status-before-launch", "start"], report["facts"]["steps"])
        self.assertNotIn("fail", report["facts"]["gates"].values())

    def test_only_this_claims_persistent_hold_is_adopted(self):
        self.stop_incumbent()
        hold = self.folder / "holds/lab-host.lock"
        self.assertIs(True, rr.document(hold)["persistent_hold"])
        worker = json.dumps({"pid": 1, "utc": rr.utc(NOW), "claim_id": CLAIM}).encode()  # same claim, not persistent
        hold.write_bytes(worker)
        self.runner = self.make_runner()
        self.drive("qualify")
        report = self.reports("qualify")[-1]
        self.assertEqual(("failed", "host_interrupted", None),
                         (report["status"], report["failure_class"], report["facts"]))
        self.assertEqual(worker, hold.read_bytes())
        self.assertEqual("host_lock_claim_mismatch", rr.document(self.runner.path)["custody_refused"])
        self.assertEqual(0, self.launcher.launches)

    def test_preflight_observes_the_incumbent_before_the_controller_and_reports_absence_as_absence(self):
        self.prepare()
        self.native.listening = False  # a stopped incumbent: no running launch, not healthy
        def unavailable(verb):
            raise rr.ControllerUnavailable("test-unavailable")
        self.controller.call = unavailable
        self.drive("host_preflight")
        self.assertEqual("controller_unavailable", self.reports("host_preflight")[-1]["failure_class"])
        self.assertEqual({"profile_id": "incumbent", "profile_fingerprint": "1" * 64,
                          "runtime_identity_sha256": "2" * 64, "config_file_sha256": "3" * 64, "healthy": False},
                         rr.document(self.runner.path)["incumbent_reference"])

    def test_qualify_reports_the_latest_observed_candidate_launch_or_null(self):
        self.stop_incumbent()
        self.drive("qualify")
        self.assertEqual({None}, {r["facts"]["launch_id"] for r in self.reports("qualify")})
        run = self.runner.root() / "state/run.json"
        for launch in ("candidate-one", "candidate-two"):
            rr.atomic_write_json(run, {"launch_id": launch, "state": "ready"})
            self.drive("qualify")
            self.assertEqual(launch, self.reports("qualify")[-1]["facts"]["launch_id"])
        self.assertEqual(RUN + "-h1-a1", self.reports("qualify")[-1]["facts"]["evidence_name"].removeprefix("requalify-"))
        self.assertEqual(["candidate-one", "candidate-two"], self.runner.state["native_refs"]["candidate_launch_ids"])

    def run_main_once(self):
        config = {**self.config, "tooling": str(rr.ROOT), "control_plane_origin": self.server.origin,
                  "controller": {"executable": "controller-tool"}}
        path = self.folder / "binding.json"
        rr.atomic_write_json(path, config)
        with patch.object(rr, "Runner", return_value=self.runner):
            return rr.main(["--config", str(path), "--token-file", str(self.token), "--once"])

    def test_conflict_codes_decide_retry_resynchronization_or_refusal(self):
        self.stop_incumbent()
        self.drive("qualify")
        for body in (b'{"code": "lock_timeout", "detail": "another command holds this row"}',
                     b'{"code": "fence_lost", "detail": "release report fence changed"}'):
            with self.subTest(body=body):
                self.assign("qualify")
                self.server.conflict = body
                self.assertEqual(0, self.run_main_once())  # retried later: nothing stopped, hold kept
                self.assertEqual((0, True), (self.launcher.stops, self.hold_exists()))
                self.assertNotIn("return", self.controller.effects)
        for body in (b'{"code": "refused", "detail": "release report is in the future"}',
                     b'{"detail": "release report fence changed; resynchronize current run"}',
                     b'{"code": "something_new"}', b"not json"):
            with self.subTest(body=body):
                self.runner.state.pop("restoration", None)
                self.runner.state["candidate_stopped"] = False
                self.launcher.alive, self.native.listening = True, False
                self.assign("qualify")
                self.server.conflict = body
                with self.assertRaises(rr.Refused) as raised, \
                        patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    self.run_main_once()
                self.assertIs(rr.Refused, type(raised.exception))
                self.assertIn("conflict refused", stderr.getvalue())
                # Refused: cleanup ran before the exit for inspection; the hold stays.
                self.assertFalse(self.launcher.alive)
                self.assertTrue(self.runner.state["restoration"]["verified"])
                self.assertTrue(self.hold_exists())
        self.assertFalse(any(p.endswith(("/usage", "/release")) for p, _ in self.server.requests))

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
        for changed, launch, healthy, expected in (
                (None, "incumbent-after", True, True), ("profile_id", "incumbent-after", True, False),
                ("profile_fingerprint", "incumbent-after", True, False),
                ("runtime_identity_sha256", "incumbent-after", True, False),
                ("config_file_sha256", "incumbent-after", True, False),
                (None, "incumbent-before", True, False), (None, "candidate-launch", True, False),
                (None, "incumbent-after", False, False)):
            with self.subTest(changed=changed, launch=launch, healthy=healthy):
                self.runner.state = {}
                self.native.identity.update(profile_id="incumbent", profile_fingerprint="1" * 64,
                                            runtime_identity_sha256="2" * 64, config_file_sha256="3" * 64,
                                            launch_id="incumbent-before")
                self.native.healthy = True
                self.controller.mutate_identity = changed
                self.controller.return_launch = launch
                self.stop_incumbent()
                self.native.healthy = healthy
                self.runner.state["candidate_stopped"] = True
                self.runner.state["native_refs"]["candidate_launch_ids"] = ["candidate-launch"]
                self.drive("restore")
                facts = self.reports("restore")[-1]["facts"]
                self.assertEqual(expected, facts["verified"])
                # Reported as observed: the returned launch and health, never the reference's.
                self.assertEqual((launch, healthy), (facts["identity"]["launch_id"], facts["identity"]["healthy"]))
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
        self.controller.return_launch = "unobserved-launch"
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
    def test_native_execution_cannot_borrow_another_checkouts_identity(self):
        with self.assertRaisesRegex(rr.Refused, "executing_tooling_checkout_mismatch"):
            rr.Native(rr.ROOT / "other-checkout", {})
        calls = []
        def changed(argv, cwd, **kwargs):
            calls.append(argv)
            if argv[:2] == ["git", "diff"]:
                raise rr.Refused("native_command_failed")
            self.fail("native tool reached after modified tracked code")
        native = rr.Native(rr.ROOT, {}, run=changed)
        with self.assertRaises(rr.Refused):
            native.tool(rr.ROOT, "omp_strata", ["status"])
        self.assertEqual(1, len(calls))
        native.run = lambda argv, cwd, **kwargs: b"untracked.py" if argv[1] == "ls-files" else b""
        with self.assertRaisesRegex(rr.Refused, "unrecorded_native_tooling"):
            native.tool(rr.ROOT, "omp_strata", ["status"])

    def test_native_prepare_names_campaign_source_and_draft_refusals(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        work = Path(temp.name).resolve()
        spec = {"candidate_id": "candidate",
                "engine": {"tag": "v0.2.14", "commit_sha": "e" * 40,
                           "assets": [{"name": "engine.zip", "size": 1, "digest": "sha256:" + "1" * 64}]},
                "client": {"tag": "v18.20.0", "commit_sha": "f" * 40,
                           "assets": [{"name": "omp.exe", "size": 2, "digest": "sha256:" + "2" * 64}]}}
        record = {"hosts": [{"profile_id": "candidate", "predecessor": {
                      "profile_id": "predecessor", "manifest": "releases/predecessor/manifest.json"}}],
                  "peeled_commit": "e" * 40, "assets": [{"name": "engine.zip", "bytes": 1, "sha256": "1" * 64}],
                  "omp_release": {"peeled_commit": "f" * 40,
                                  "assets": [{"name": "omp.exe", "bytes": 2, "sha256": "2" * 64}]}}
        superseded, moved, foreign = copy.deepcopy(record), copy.deepcopy(record), copy.deepcopy(record)
        superseded["hosts"][0]["superseded_by"] = "v0.2.15+omp18.20.0"
        moved["omp_release"]["peeled_commit"] = "0" * 40
        foreign["hosts"][0]["profile_id"] = "another-candidate"
        native = rr.Native(rr.ROOT, {"strata_source": str(work)})
        incomplete = rr.upstream_watch.Incomplete
        offline = patch.object(rr.upstream_watch.urllib.request, "urlopen", side_effect=AssertionError("network"))
        offline.start()
        self.addCleanup(offline.stop)
        for step, effect, code in (
                ("open", incomplete("OMP v18.20.0 differs from the frozen client in v0.2.13+omp18.20.0.json"),
                 "native_source_refused"),
                ("open", ValueError("v0.2.14.json already records the same release tuple as "
                                    "v0.2.14+omp18.20.0.json; refused"), "native_campaign_refused"),
                ("open", ValueError("v0.2.14+omp18.20.0.json does not hold the campaign its name identifies"),
                 "native_campaign_refused"),
                ("open", {"state": "skipped", "tag": "v0.2.14", "reason": "prerelease"}, "native_source_refused"),
                ("open", foreign, "candidate_not_in_native_campaign"),
                ("open", superseded, "native_campaign_superseded"),
                ("open", moved, "source_changed"),
                ("asset", rr.Refused("asset_digest_mismatch"), "native_asset_refused"),
                ("asset", rr.SourceUnavailable("asset_source_unavailable"), "native_source_unavailable"),
                ("draft", incomplete("OMP v18.20.0 differs from the frozen client in v0.2.14+omp18.20.0.json"),
                 "native_source_refused"),
                ("draft", ValueError("drafting conflict"), "native_draft_refused")):
            with self.subTest(step=step, code=code):
                component = {"engine_component": {}} if step == "asset" else {}
                rr.atomic_write_json(work / "profiles/predecessor.json", {"strata": component, "host": {}})
                raising = isinstance(effect, Exception)
                opened = ({"side_effect": effect} if step == "open" and raising
                          else {"return_value": effect if step == "open" else record})
                with patch.object(rr.campaign, "open_campaign", **opened), \
                        patch.object(rr.upstream_watch, "select_strata_assets",
                                     return_value={"engine": {"name": "engine.zip"}}), \
                        patch.object(native, "asset", side_effect=effect if step == "asset" else None), \
                        patch.object(rr.upstream_watch, "draft", side_effect=effect if step == "draft" else None) as draft:
                    with self.assertRaises(rr.NativeRefusal) as raised:
                        native.prepare(work, spec)
                self.assertEqual(code, raised.exception.code)
                self.assertIn(code, rr.PREPARE_OUTCOMES)
                self.assertEqual(step == "draft", draft.called)
        rr.atomic_write_json(work / "profiles/predecessor.json", {"strata": {}, "host": {}})
        limited = rr.urllib.error.HTTPError("https://api.github.com/", 403, "limit",
                                            {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "0"}, None)
        for failure in (OSError("unreachable"), limited):
            with self.subTest(transport=type(failure).__name__):
                # The real campaign intake: the metadata request itself fails, so this is not a source refusal.
                with patch.object(rr.upstream_watch, "urllib_transport", side_effect=failure), \
                        patch.object(rr.upstream_watch, "draft") as draft:
                    with self.assertRaises(rr.NativeRefusal) as raised:
                        native.prepare(work, spec)
                self.assertEqual("native_source_unavailable", raised.exception.code)
                self.assertFalse(draft.called)
        self.assertFalse((work / "releases/campaigns").exists())

    def test_asset_download_names_transport_failure_but_not_local_cache_errors(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        native = rr.Native(rr.ROOT, {"cache": temp.name})
        source = {"repository_url": "https://github.com/example/project.git", "tag": "v0.2.14"}
        asset = {"name": "engine.zip", "size": 1, "digest": "sha256:" + "1" * 64}
        for failure in (rr.urllib.error.URLError("unreachable"), TimeoutError("timed out"),
                        rr.urllib.error.HTTPError("https://github.com/", 503, "unavailable", {}, None)):
            with self.subTest(failure=type(failure).__name__), \
                    patch.object(rr.urllib.request, "urlopen", side_effect=failure):
                with self.assertRaises(rr.SourceUnavailable):
                    native.asset(source, asset)
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, size):
                return b""
        with patch.object(rr.urllib.request, "urlopen", return_value=Response()), \
                patch.object(Path, "open", side_effect=PermissionError("cache not writable")):
            with self.assertRaises(PermissionError):  # a local cache error, not SourceUnavailable
                native.asset(source, asset)

    def test_incumbent_identity_reports_only_what_the_lifecycle_establishes(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        profile = rr.ROOT / "profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6.json"
        root = Path(temp.name).resolve() / "incumbent"
        layout = rr.Layout(root, rr.load(profile))
        native = rr.Native(rr.ROOT, {"incumbent_profile": str(profile), "incumbent_root": str(root)})
        install = {"profile_id": "incumbent", "profile_fingerprint": "1" * 64, "runtime_identity_sha256": "2" * 64,
                   "identity": {"config_file_sha256": "3" * 64}}
        leaves = {"profile_id": "incumbent", "profile_fingerprint": "1" * 64,
                  "runtime_identity_sha256": "2" * 64, "config_file_sha256": "3" * 64}
        rows = (("not_installed", None, {"healthy": False}), ("mismatched", install, {**leaves, "healthy": False}),
                ("stopped", install, {**leaves, "healthy": False}), ("failed", install, {**leaves, "healthy": False}),
                ("starting", install, {**leaves, "launch_id": "launch-a", "healthy": False}),
                ("degraded", install, {**leaves, "launch_id": "launch-a", "healthy": False}),
                ("healthy", install, {**leaves, "launch_id": "launch-a", "healthy": True}))
        with patch.object(rr.lifecycle, "port_in_use", return_value=False):
            for state, record, expected in rows:
                with self.subTest(state=state):
                    for path in (layout.install_record, layout.run_record):
                        path.unlink(missing_ok=True)
                    if record is not None:
                        rr.atomic_write_json(layout.install_record, record)
                    rr.atomic_write_json(layout.run_record, {"launch_id": "launch-a"})  # past or present
                    with patch.object(native, "tool", return_value=json.dumps({"state": state}).encode()):
                        self.assertEqual((expected, False), native.incumbent())
            def relaunch(*args, **kwargs):
                rr.atomic_write_json(layout.run_record, {"launch_id": "launch-b"})
                return b'{"state": "healthy"}'
            with patch.object(native, "tool", side_effect=relaunch):  # restarted during the status call
                self.assertEqual({**leaves, "healthy": True}, native.incumbent()[0])
            partial = {**install, "identity": {}}
            rr.atomic_write_json(layout.install_record, partial)
            with patch.object(native, "tool", return_value=b'{"state": "healthy"}'):
                self.assertEqual({**{k: v for k, v in leaves.items() if k != "config_file_sha256"},
                                  "launch_id": "launch-b", "healthy": True}, native.incumbent()[0])
            def reinstall(*args, **kwargs):
                rr.atomic_write_json(layout.install_record, install)
                return b'{"state": "healthy"}'
            with patch.object(native, "tool", side_effect=reinstall):
                with self.assertRaisesRegex(rr.Refused, "incumbent_install_changed_during_observation"):
                    native.incumbent()

    def test_conflict_body_code_decides_and_anything_else_refuses(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        token = Path(temp.name) / "token"
        token.write_text("test-only-bearer")
        class Opener:
            body = b""
            def open(self, request, timeout):
                raise rr.urllib.error.HTTPError(request.full_url, 409, "Conflict", {}, io.BytesIO(self.body))
        opener = Opener()
        http = rr.HTTP("http://127.0.0.1:9", token, opener=opener)
        path = "/api/project-loops/release-runs/" + RUN + "/reports"
        for body, expected in ((b'{"code": "fence_lost", "detail": "x"}', rr.StaleFence),
                               (b'{"code": "lock_timeout", "detail": "x"}', rr.ControlPlaneBusy),
                               (b'{"code": "refused", "detail": "x"}', rr.Refused),
                               (b'{"detail": "release report fence changed; resynchronize current run"}', rr.Refused),
                               (b'{"code": "unknown_code"}', rr.Refused), (b'["code", "fence_lost"]', rr.Refused),
                               (b"<html>", rr.Refused)):
            with self.subTest(body=body), patch("sys.stderr", new_callable=io.StringIO) as stderr:
                opener.body = body
                with self.assertRaises(Exception) as raised:
                    http.post(path, {})
                self.assertIs(expected, type(raised.exception))
                self.assertEqual(expected is rr.Refused, "conflict refused" in stderr.getvalue())

    def test_status_observations_are_read_whatever_their_documented_exit(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        profile = LifecycleIncumbent.PROFILE
        root = Path(temp.name).resolve() / "incumbent"
        layout = rr.Layout(root, rr.load(profile))
        def run(argv, cwd, **kwargs):
            # The real `omp_strata.py status` and exit-code handling; the tooling-drift checks have their own tests.
            return b"" if argv[0] == "git" else rr.command(argv, cwd, **kwargs)
        native = rr.Native(rr.ROOT, {"incumbent_profile": str(profile), "incumbent_root": str(root)}, run=run)
        install = {"profile_id": "incumbent", "profile_fingerprint": layout.profile.fingerprint,
                   "runtime_identity_sha256": "2" * 64, "identity": {"config_file_sha256": "3" * 64}}
        leaves = {"profile_id": "incumbent", "profile_fingerprint": layout.profile.fingerprint,
                  "runtime_identity_sha256": "2" * 64, "config_file_sha256": "3" * 64}
        rows = (("not_installed", None, None, {"healthy": False}),  # exit 0
                ("stopped", install, {"launch_id": "launch-a", "state": "stopped"}, {**leaves, "healthy": False}),
                ("failed", install, {"launch_id": "launch-a", "state": "exited", "exit_code": 3},  # exit 1
                 {**leaves, "healthy": False}),
                ("mismatched", {**install, "profile_fingerprint": "f" * 64}, {"launch_id": "launch-a"},  # exit 1
                 {**leaves, "profile_fingerprint": "f" * 64, "healthy": False}))
        with patch.object(rr.lifecycle, "port_in_use", return_value=False):
            for state, record, run_record, expected in rows:
                with self.subTest(state=state):
                    for path, value in ((layout.install_record, record), (layout.run_record, run_record)):
                        path.unlink(missing_ok=True)
                        if value is not None:
                            rr.atomic_write_json(path, value)
                    self.assertEqual((expected, False), native.incumbent())
        for output in (b"", b'{"state": "unknown"}', b"[]"):  # status crashed (exit 1, no JSON) or named no state
            with self.subTest(output=output), patch.object(native, "tool", return_value=output):
                with self.assertRaisesRegex(rr.Refused, "native_status_unreadable"):
                    native.status(rr.ROOT, profile, root)
        exits = [sys.executable, "-c", "import sys; print('{}'); sys.exit(int(sys.argv[1]))"]
        self.assertEqual(b"{}\n", rr.command([*exits, "1"], rr.ROOT, accept=(0, 1)).replace(b"\r", b""))
        for code in ("1", "2"):
            with self.subTest(exit=code), self.assertRaisesRegex(rr.Refused, "native_command_failed"):
                rr.command([*exits, code], rr.ROOT, accept=(0,) if code == "1" else (0, 1))

    def test_a_missing_campaign_and_the_campaign_lock_are_named_native_refusals(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        work = Path(temp.name).resolve()
        native = rr.Native(rr.ROOT, {"strata_source": str(work)})
        spec = {"candidate_id": "candidate", "engine": {"tag": "v0.2.14"}, "client": {"tag": "v18.20.0"}}
        with self.assertRaises(rr.NativeRefusal) as raised:  # set_host: no such campaign, now a ValueError
            native.campaign_status(work, spec, "queued")
        self.assertEqual("native_ledger_refused", raised.exception.code)
        lock = rr.lifecycle.FileLock
        with lock(work / "local/campaigns.lock"), \
                patch.object(rr.campaign.lifecycle, "FileLock", lambda path, timeout: lock(path, timeout=0.2)), \
                patch.object(rr.campaign, "discover_release", return_value={"tag": "v0.2.14", "prerelease": False}):
            for step, call in (("ledger", lambda: native.campaign_status(work, spec, "queued")),
                               ("prepare", lambda: native.prepare(work, spec))):
                with self.subTest(step=step):
                    with self.assertRaises(rr.NativeRefusal) as raised:
                        call()
                    self.assertEqual("native_campaign_locked", raised.exception.code)
        self.assertEqual("native_refused", rr.PREPARE_OUTCOMES["native_campaign_locked"])
        self.assertFalse((work / "releases").exists())

    def test_the_campaign_lock_file_is_not_checkout_dirt(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        repo = Path(temp.name).resolve() / "checkout"
        (repo / "scripts").mkdir(parents=True)
        shutil.copyfile(rr.ROOT / ".gitignore", repo / ".gitignore")
        (repo / "scripts/noop.py").write_text("print('ok')\n")
        def git(*args):
            return subprocess.run(["git", "-C", str(repo), "-c", "user.name=fixture", "-c", "user.email=fixture",
                                   "-c", "commit.gpgsign=false", *args], check=True, capture_output=True).stdout
        git("init", "-q")
        git("add", ".")
        git("commit", "-q", "-m", "fixture")
        head = git("rev-parse", "HEAD").decode().strip()
        with rr.campaign.campaign_lock(repo):  # the native campaign writers' own lock file
            pass
        self.assertTrue((repo / "local/campaigns.lock").is_file())
        self.assertEqual(head, rr.tooling_identity(repo, head))
        native = rr.Native(rr.ROOT, {})
        self.assertEqual(b"ok\n", native.tool(repo, "noop", []).replace(b"\r", b""))
        (repo / "scripts/stray.py").write_text("")
        with self.assertRaisesRegex(rr.Refused, "unrecorded_native_tooling"):
            native.tool(repo, "noop", [])
        with self.assertRaisesRegex(rr.Refused, "dirty_or_unrecorded_tooling"):
            rr.tooling_identity(repo, head)

    def test_a_candidate_root_is_observed_idle_read_only(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        profile = LifecycleIncumbent.PROFILE
        root = Path(temp.name).resolve() / "candidate"
        layout = rr.Layout(root, rr.load(profile))
        native = rr.Native(rr.ROOT, {})
        rr.atomic_write_json(layout.run_record, {"launch_id": "not-this-runs", "state": "exited"})
        before = layout.run_record.read_bytes()
        for port, expected in ((False, True), (True, False)):
            with self.subTest(port_in_use=port), patch.object(rr.lifecycle, "port_in_use", return_value=port):
                self.assertIs(expected, native.candidate_idle(profile, root))
        self.assertEqual(before, layout.run_record.read_bytes())  # observed, not written
        layout.run_record.write_text("{")
        with patch.object(rr.lifecycle, "port_in_use", return_value=False):
            self.assertIs(False, native.candidate_idle(profile, root))  # an unreadable record proves nothing

    def test_native_ledger_refusal_is_named(self):
        native = rr.Native(rr.ROOT, {})
        spec = {"candidate_id": "candidate", "engine": {"tag": "v0.2.14"}, "client": {"tag": "v18.20.0"}}
        for message in ("result's OMP client differs from the campaign's frozen client snapshot",
                        "v0.2.14.json already records the same release tuple as v0.2.14+omp18.20.0.json; refused"):
            with self.subTest(message=message), patch.object(rr.campaign, "set_host", side_effect=ValueError(message)):
                with self.assertRaisesRegex(rr.NativeRefusal, "native_ledger_refused"):
                    native.campaign_status(Path("unused"), spec, "qualified", result="r", restored_state="s")

    def test_shared_invariant_vector_and_material_change(self):
        vector = rr.document(FIXTURES / "release-invariant.json")
        self.assertEqual(vector["invariant_sha256"], rr.invariant_digest(vector["profile"]))
        changed = copy.deepcopy(vector["profile"])
        changed["strata"]["setup_args"]["context"] += 1
        self.assertNotEqual(vector["invariant_sha256"], rr.invariant_digest(changed))
        self.assertEqual("carrythrough " + rr.WIRE_COMMIT, (FIXTURES / "COMMIT").read_text().splitlines()[0])

    def test_wire_schema_fixtures_are_the_pinned_control_plane_bytes(self):
        self.assertEqual(WIRE_SCHEMA_SHA256, {name: rr.sha256_file(FIXTURES / (name + ".schema.json"))
                                              for name in WIRE_SCHEMA_SHA256})

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
