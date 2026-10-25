import copy
import contextlib
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import itertools
import json
from pathlib import Path, PureWindowsPath
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json, sha256_file
from scripts import eval_taskset, experiment_loop as loop
from scripts.publish_run import PublicationError, Scrubber

BASELINE = "win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1"
CANDIDATE = "win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1"
NEXT = "win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1"
PRO_BASELINE = "win11-rtxpro6000-coder-iq1m-131k-strata0.1.44.1-omp18.10.1"
PRO_CANDIDATE = "win11-rtxpro6000-coder-iq1m-262k-strata0.1.44.1-omp18.10.1"


def admitted():
    return dict(reachable=True, gpu_idle=True, ram_above_floor=True, disk_above_floor=True,
                no_competing_tenant=True, predecessor_matches=True, doctor_ok=True)


class FakeAdapter:
    def __init__(self):
        self.lock_id = "rtx5090-win-a"
        self.scrubber = Scrubber("D:/private-root", private=["fixture-host", "192.0.2.55"])
        self.events = []
        self.observation = admitted()
        self.fail_at = None
        self.restore_serving = True
        self.result = {"status": "complete", "samples": [], "queue": {"both_complete": True}}

    def event(self, name):
        self.events.append(name)
        if name == self.fail_at:
            raise loop.ExperimentError("probe_failed")

    def precondition(self, manifest, timeout):
        self.event("precondition")
        return self.observation.copy()

    def quiesce(self, manifest, timeout):
        self.event("quiesce")
        return {"mode": "loop_quiesced_warm", "profile_fingerprint": manifest["baseline"]["profile_fingerprint"]}

    def install(self, manifest, timeout):
        self.event("install")

    def start(self, arm, timeout):
        self.event("start:" + arm)

    def stop(self, arm, timeout):
        self.event("stop:" + arm)

    def settle(self, timeout):
        self.event("settle")
        return {"status": "ready", "observations": []}

    def guard(self, arm, timeout):
        self.event("guard:" + arm)

    def probe(self, arm, workload, timeout):
        self.event("probe:" + arm)
        return copy.deepcopy(self.result)

    def restore(self, manifest, *, custody):
        self.restored_profile = manifest["restoration_target"]["profile_id"]
        self.event("restore")
        return {"status": "restored" if self.restore_serving else "failed", "serving": self.restore_serving,
                "profile_id": self.restored_profile,
                "gate": {"gate": "G10", "pass_observed": self.restore_serving}}


class ModelProcessSuspended(BaseException):
    """A scheduler cut, not a Python exception delivered to the modelled process."""


class LifecycleModelHost(loop.HostAdapter):
    """In-memory kernel: real start/serve/stop/restore code, no processes or host I/O.

    Lock-held transitions are atomic. A detached wrapper may run at every cut in the
    parent timeout -> cancel -> restore -> release chain. Publication and readiness
    faults are independent axes, not reimplementations of lifecycle policy.
    """

    def __init__(self, manifest, *, publication="ok", foreign=False, windows=False):
        self.manifest = manifest
        self.publication = publication
        self.foreign = foreign
        self.windows = windows
        self.owned_runs = {}
        self.launch_requests = {}
        self.owned_commands = {}
        self.records = {}
        self.processes = {}
        self.spawned = []
        self.locks = set()
        self.requests = {}
        self.released = False
        self.stopped = False
        self.restored = False
        self.serial = 100
        self.layouts = {arm: loop.Layout(Path("/model") / arm, loop.load(
            loop.ROOT / "profiles" / (manifest[arm]["profile_id"] + ".json")))
            for arm in ("baseline", "candidate", "restoration_target")}
        self.arm = "candidate"
        self.custody = contextlib.ExitStack()
        self.stack = contextlib.ExitStack()
        self.trace = []
        self.lock_resume = None

    def __enter__(self):
        host = self

        class Lock:
            def __init__(self, path, *, timeout=0):
                self.path = path
                self.timeout = timeout

            def __enter__(self):
                if self.path in host.locks and self.timeout and host.lock_resume:
                    resume, host.lock_resume = host.lock_resume, None
                    resume()
                if self.path in host.locks:
                    raise loop.lifecycle.LifecycleError("model root lock busy")
                host.locks.add(self.path)
                return self

            def __exit__(self, *_args):
                host.locks.remove(self.path)

        def info(pid):
            if pid == loop.os.getpid():
                return SimpleNamespace(pid=pid, exe="wrapper", as_dict=lambda: {
                    "pid": pid, "exe": "wrapper", "created": "wrapper-generation"})
            return self.processes.get(pid)

        def matches(record):
            proc = self.processes.get((record or {}).get("pid"))
            return proc if proc and proc.as_dict() == record else None

        def terminate(proc, _timeout):
            self.processes.pop(proc.pid, None)
            return True

        for module in (loop, loop.lifecycle):
            self.stack.enter_context(patch.object(module, "read_json", side_effect=self.read))
            self.stack.enter_context(patch.object(module, "atomic_write_json", side_effect=self.write))
        replacements = {
            "FileLock": Lock, "verify_install_fast": lambda _layout: {"runtime_identity_sha256": "a" * 64},
            "read_key": lambda _layout: "model-key", "port_in_use": lambda *_args: False,
            "gpu_facts": lambda *_args: {}, "gpu_busy": lambda *_args: None,
            "_launch_detached": self.dispatch, "status": lambda _layout: {"state": "healthy"},
        }
        for name, value in replacements.items():
            self.stack.enter_context(patch.object(loop.lifecycle, name, value))
        for name, value in {
            "info": info, "matches": matches, "terminate": terminate, "descendants": lambda _pid: [],
            "memory": lambda: {"available": 0},
        }.items():
            self.stack.enter_context(patch.object(loop.procs, name, value))
        self.stack.enter_context(patch.object(loop.lifecycle.subprocess, "Popen", self.spawn))
        self.stack.enter_context(patch.object(loop.lifecycle.subprocess, "run", side_effect=self.kill_tree))
        self.stack.enter_context(patch.object(loop.lifecycle, "WINDOWS", self.windows))
        self.stack.enter_context(patch.object(loop.lifecycle.os, "killpg",
                                             lambda pid, _signal: self.processes.pop(pid, None), create=True))
        self.stack.enter_context(patch.object(Path, "exists", lambda path: path in host.records))
        self.stack.enter_context(patch.object(Path, "mkdir", lambda *_args, **_kwargs: None))
        self.stack.enter_context(patch.object(Path, "open", lambda *_args, **_kwargs: io.StringIO()))
        self.stack.enter_context(patch("builtins.open", lambda *_args, **_kwargs: io.BytesIO()))
        self.stack.enter_context(patch.object(loop.lifecycle.time, "sleep", lambda _seconds: None))
        return self

    def __exit__(self, *_args):
        self.custody.close()
        self.stack.close()

    def read(self, path):
        return copy.deepcopy(self.records[path])

    def write(self, path, data):
        if path.name == "run.json":
            assert path.with_name("lifecycle.lock") in self.locks or any(
                layout.run_record == path and layout.lock_file in self.locks for layout in self.layouts.values())
        if (path == self.layouts["candidate"].run_record
                and data.get("server") and data.get("state") == "starting" and self.publication == "fail"):
            self.publication = "failed"
            raise OSError("model identity publication failed")
        self.records[path] = copy.deepcopy(data)

    def dispatch(self, argv, **_kwargs):
        launch_id = argv[argv.index("--launch-id") + 1]
        self.requests[self.arm] = launch_id
        if self.arm == "candidate":
            raise ModelProcessSuspended
        self.resume_wrapper(self.arm)

    def spawn(self, *_args, **_kwargs):
        self.serial += 1
        pid = self.serial
        arm = self.arm
        record = self.read(self.layouts[arm].run_record)
        identity = {"pid": pid, "exe": "server", "created": str(pid)}
        proc = SimpleNamespace(pid=pid, exe="server", as_dict=lambda: identity.copy())
        self.processes[pid] = proc
        self.spawned.append((pid, arm, record["launch_id"]))

        def wait(timeout=None):
            if pid in self.processes:
                raise ModelProcessSuspended
            return -1

        return SimpleNamespace(pid=pid, wait=wait, poll=lambda: None if pid in self.processes else -1,
                               kill=lambda: self.processes.pop(pid, None))

    def kill_tree(self, argv, **_kwargs):
        assert argv[0] == "taskkill"
        self.processes.pop(int(argv[argv.index("/PID") + 1]), None)
        return SimpleNamespace(returncode=0)

    def command(self, arm, _script, args, _timeout, **kwargs):
        self.arm = arm
        if args[0] == "g10":
            return {"gate": "G10", "pass_observed": True, "run_id": "g10-20261024T000000Z-abcdef",
                    "profile_fingerprint": self.layouts[arm].profile.fingerprint,
                    "runtime_identity_sha256": "a" * 64}
        with patch.dict(loop.os.environ, kwargs["env"]), \
                patch.object(loop.lifecycle, "runtime_checks", return_value={"ready": True}):
            try:
                return loop.lifecycle.start(self.layouts[arm], tool_argv=["model"], log=lambda _line: None)
            except ModelProcessSuspended:
                if arm != "candidate":
                    raise AssertionError("incumbent start did not finish")
                # The parent command remains suspended until the scheduler's timeout event.
                for event in self.before_timeout:
                    self.event(event)
                if self.foreign:
                    path = self.layouts[arm].run_record
                    self.records[path] = {**self.records[path], "launch_id": "foreign",
                                          "experiment_launch_id": "foreign"}
                raise loop.ExperimentError("max_wall_time") from None

    def resume_wrapper(self, arm="candidate"):
        self.arm = arm
        try:
            loop.lifecycle.serve(self.layouts[arm], log_path=Path("/model/log"),
                                 launch_id=self.requests[arm])
        except (ModelProcessSuspended, loop.lifecycle.LifecycleError, OSError):
            pass

    def event(self, event):
        self.trace.append(event)
        if event == "wrapper":
            self.resume_wrapper()
        elif event == "cancel":
            before = copy.deepcopy(self.records.get(self.layouts["candidate"].run_record))
            self.stop("candidate", 120)
            self.stopped = True
            if self.foreign:
                assert self.records[self.layouts["candidate"].run_record] == before, "foreign request cancelled"
        elif event == "restore":
            self.restored = self.restore(self.manifest, custody=self.custody)["serving"]
        elif event == "release":
            self.released = self.restored
            self.custody.close()

    def violations(self):
        bad = []
        candidate = self.read(self.layouts["candidate"].run_record)
        for pid, arm, token in self.spawned:
            if pid not in self.processes:
                continue
            if self.released and arm != "restoration_target":
                bad.append("M1 live candidate after release")
            record = self.read(self.layouts[arm].run_record)
            if record.get("launch_id") != token or record.get("server") != self.processes[pid].as_dict():
                bad.append("M2 child not published under exact token")
            if self.stopped and arm == "candidate":
                bad.append("M2 arm stopped with live child")
        if self.released and candidate.get("state") == "launching" and not self.foreign:
            bad.append("M1 released with executable pending request")
        return bad


class LifecycleInterleavingModelTests(unittest.TestCase):
    def extended_schedules(self, manifest):
        """R1: locks remain held across cuts; direct parents and descendants have separate lifetimes."""
        examples = []
        explored = 0
        for stage, foreign in itertools.product(("direct_cleanup", "capture", "cancel"), (False, True)):
            explored += 1
            with LifecycleModelHost(manifest) as host:
                layout = host.layouts["candidate"]
                host.before_timeout = []

                def resume():
                    host.locks.remove(layout.lock_file)
                    if foreign:
                        host.records[layout.run_record].update(launch_id="foreign", experiment_launch_id="foreign")
                    else:
                        host.resume_wrapper()

                def contended_dispatch(argv, **_kwargs):
                    host.requests["candidate"] = argv[argv.index("--launch-id") + 1]
                    host.locks.add(layout.lock_file)
                    host.lock_resume = resume
                    raise RuntimeError("dispatch failed while wrapper holds root lock")

                if stage == "direct_cleanup":
                    with patch.object(loop.lifecycle, "_launch_detached", contended_dispatch):
                        try:
                            loop.lifecycle.start(layout, tool_argv=["model"], log=lambda _line: None)
                        except RuntimeError:
                            pass
                else:
                    original_dispatch = host.dispatch

                    def dispatch(argv, **kwargs):
                        if host.arm == "candidate" and stage == "capture":
                            host.requests["candidate"] = argv[argv.index("--launch-id") + 1]
                            host.locks.add(layout.lock_file)
                            host.lock_resume = resume
                            raise ModelProcessSuspended
                        return original_dispatch(argv, **kwargs)

                    with patch.object(loop.lifecycle, "_launch_detached", dispatch):
                        try:
                            host.start("candidate", 1)
                        except (RuntimeError, loop.ExperimentError):
                            pass
                    if stage == "cancel":
                        host.locks.add(layout.lock_file)
                        host.lock_resume = resume
                    try:
                        host.stop("candidate", 120)
                    except RuntimeError:
                        pass
                bad = []
                if layout.lock_file in host.locks:
                    # The wrapper resumes after the caller wrongly gave up cleanup.
                    resume()
                    bad.append("M3 cleanup abandoned on ordinary wrapper lock contention")
                if not foreign and host.processes:
                    bad.append("M3 matching server survived cleanup")
                if foreign and host.records[layout.run_record]["launch_id"] != "foreign":
                    bad.append("M3 replacement was not preserved")
                if bad:
                    examples.append({"schedule": ["start", "wrapper_lock", stage, "wrapper_resume"],
                                     "foreign": foreign, "violations": bad})
        for parent_exit, kill_failure, wrapper_live in itertools.product((False, True), (False, True), (False, True)):
            explored += 1
            with LifecycleModelHost(manifest, publication="fail", windows=True) as host:
                host.before_timeout = []
                try:
                    host.start("candidate", 1)
                except loop.ExperimentError:
                    pass
                layout = host.layouts["candidate"]
                token = host.requests["candidate"]
                original_spawn = host.spawn
                descendant = 900
                host.processes[descendant] = SimpleNamespace(
                    pid=descendant, exe="engine", as_dict=lambda: {
                        "pid": descendant, "exe": "engine", "created": "orphan"})

                def spawn(*args, **kwargs):
                    child = original_spawn(*args, **kwargs)
                    if parent_exit:
                        host.processes.pop(child.pid)
                    return child

                def kill(argv, **kwargs):
                    # A failed tree kill can still coincide with the direct parent's exit.
                    host.processes.pop(int(argv[argv.index("/PID") + 1]), None)
                    if kill_failure:
                        if kwargs.get("check"):
                            raise loop.subprocess.CalledProcessError(1, argv)
                        return SimpleNamespace(returncode=1)
                    host.processes.pop(descendant, None)
                    return SimpleNamespace(returncode=0)

                with patch.object(loop.lifecycle.subprocess, "Popen", spawn), \
                        patch.object(loop.lifecycle.subprocess, "run", kill):
                    try:
                        host.resume_wrapper()
                    except loop.subprocess.CalledProcessError:
                        pass
                if wrapper_live:
                    identity = host.records[layout.run_record].get("wrapper") or {
                        "pid": loop.os.getpid(), "exe": "wrapper", "created": "wrapper-generation"}
                    host.processes[identity["pid"]] = SimpleNamespace(
                        pid=identity["pid"], exe=identity["exe"], as_dict=lambda: identity.copy())
                try:
                    host.stop("candidate", 120)
                    stopped = True
                except loop.lifecycle.LifecycleError:
                    stopped = False
                bad = []
                if descendant in host.processes and stopped:
                    bad.append("M2 surviving descendant counted stopped")
                before = copy.deepcopy(host.records[layout.run_record])
                host.arm = "candidate"
                # Ordinary start must not erase unresolved child custody.
                host.processes.pop(loop.os.getpid(), None)
                with patch.object(loop.lifecycle, "_launch_detached", side_effect=ModelProcessSuspended):
                    try:
                        loop.lifecycle.start(layout, tool_argv=["model"], log=lambda _line: None)
                    except (ModelProcessSuspended, loop.lifecycle.LifecycleError):
                        pass
                if descendant in host.processes and host.records[layout.run_record] != before:
                    bad.append("M1 new start erased unknown descendant custody")
                if bad:
                    examples.append({"schedule": ["start", "spawn_tree", "parent_exit" if parent_exit else "parent_live",
                                                  "publication_failure", "kill_failure" if kill_failure else "kill_success",
                                                  "stop", "replacement_start"], "wrapper_live": wrapper_live,
                                     "token": "owned" if token else "missing", "violations": bad})
        for failure in ("taskkill_nonzero", "taskkill_timeout", "wait_timeout"):
            explored += 1
            with LifecycleModelHost(manifest, windows=True) as host:
                host.before_timeout = []
                alive = [True]
                child = SimpleNamespace(pid=800, returncode=None, poll=lambda: None if alive[0] else 0)

                def wait(timeout=None):
                    raise loop.subprocess.TimeoutExpired("model command", timeout)

                child.wait = wait

                def kill(argv, **kwargs):
                    if failure == "taskkill_timeout":
                        raise loop.subprocess.TimeoutExpired("taskkill", 30)
                    if failure == "taskkill_nonzero" and kwargs.get("check"):
                        raise loop.subprocess.CalledProcessError(1, argv)
                    return SimpleNamespace(returncode=1 if failure == "taskkill_nonzero" else 0)

                actual_command = host.command

                def command(arm, script, args, timeout, **kwargs):
                    if arm != "candidate":
                        return actual_command(arm, script, args, timeout, **kwargs)
                    with patch.object(loop.subprocess, "Popen", return_value=child), \
                            patch.object(loop.subprocess, "run", kill), \
                            patch.object(loop.time, "monotonic", side_effect=[0, 2]):
                        return loop.HostAdapter.command(host, arm, script, args, 1, **kwargs)

                host.command = command
                try:
                    host.start("candidate", 1)
                except (loop.ExperimentError, loop.subprocess.SubprocessError):
                    pass
                host.event("restore")
                host.event("release")
                if host.released or not host.owned_commands:
                    examples.append({"schedule": ["start_command_before_publication", failure, "restore", "release",
                                                  "late_command_resume"],
                                     "violations": ["M1 unresolved command tree forgotten before custody release"]})
        return explored, examples

    def test_exhaustive_custody_interleavings(self):
        """Finite exhaustive model, not hardware qualification; prints concrete failing schedules."""
        manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Lifecycle model.")
        chain = ("timeout", "cancel", "restore", "release")
        schedules = [events for events in itertools.permutations((*chain, "wrapper"))
                     if tuple(event for event in events if event != "wrapper") == chain]
        counterexamples = []
        explored = 0
        for publication, foreign, windows, schedule in itertools.product(
                ("ok", "fail"), (False, True), (False, True), schedules):
            # A foreign request can replace an identity-less request, never an already-live owned child.
            if foreign and schedule[0] == "wrapper":
                continue
            explored += 1
            with LifecycleModelHost(manifest, publication=publication, foreign=foreign, windows=windows) as host:
                boundary = schedule.index("timeout")
                host.before_timeout = schedule[:boundary]
                try:
                    host.start("candidate", 120)
                except loop.ExperimentError:
                    pass
                bad = host.violations()
                for event in schedule[boundary + 1:]:
                    host.event(event)
                    bad += host.violations()
                if not host.released:
                    bad.append("M1 cleaned trial retained custody")
                if bad:
                    counterexamples.append({"publication": publication, "foreign": foreign, "windows": windows,
                                            "schedule": ["start", *schedule], "violations": sorted(set(bad))})
        for fault, replaced in itertools.product(("readiness", "nested_props"), (False, True)):
            explored += 1
            with LifecycleModelHost(manifest) as host:
                layout = host.layouts["candidate"]

                def dispatch(argv, **_kwargs):
                    host.requests["candidate"] = argv[argv.index("--launch-id") + 1]
                    host.resume_wrapper()

                def readiness(_layout, _key):
                    if replaced:
                        host.processes.clear()  # foreign controller stopped our generation before replacing it
                        host.records[layout.run_record].update(launch_id="foreign", state="launching")
                    if fault == "readiness":
                        raise RuntimeError("model readiness exception")
                    return original_checks(_layout, _key)

                def response(url, **_kwargs):
                    data = layout.profile.data
                    if url.endswith("/health"):
                        return 200, {"api_key": True, "model": data["strata"]["model_name"],
                                     "max_context": data["strata"]["setup_args"]["context"]}
                    if url.endswith("/props"):
                        return 200, {"default_generation_settings": ["malformed"]}
                    return 401, {}

                original_checks = loop.lifecycle.runtime_checks
                with patch.object(loop.lifecycle, "_launch_detached", dispatch), \
                        patch.object(loop.lifecycle, "runtime_checks", readiness), \
                        patch.object(loop.lifecycle, "http_json", response):
                    try:
                        loop.lifecycle.start(layout, tool_argv=["model"], log=lambda _line: None)
                    except (RuntimeError, AttributeError):
                        pass
                bad = []
                if host.processes:
                    bad.append("M3 readiness exception leaked exact generation")
                if replaced and host.records[layout.run_record]["state"] != "launching":
                    bad.append("M3 cleanup cancelled foreign request")
                if bad:
                    counterexamples.append({"schedule": ["start", "wrapper", fault, "exception"],
                                            "replaced": replaced, "violations": bad})
        for fault in ("child_failed", "max_wall_time", "interrupt", "error_result", "complete"):
            explored += 1
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                adapter = FakeAdapter()
                snapshots = []
                directory = root / "receipts" / loop.experiment_key(manifest)

                def probe(arm, workload, timeout):
                    measured = json.loads((directory / "measurements.json").read_text())
                    snapshots.append((arm, copy.deepcopy(measured)))
                    if arm == "candidate":
                        if fault == "interrupt":
                            raise KeyboardInterrupt
                        if fault in ("child_failed", "max_wall_time"):
                            raise loop.ExperimentError(fault)
                        if fault == "error_result":
                            return {"status": "error"}
                    return {"status": "complete"}

                adapter.probe = probe
                loop.run(manifest, adapter, releases=root / "receipts", lock_directory=root / "locks")
                measured = json.loads((directory / "measurements.json").read_text())
                bad = []
                for index, (arm, snapshot) in enumerate(snapshots, 1):
                    attempts = snapshot.get("probe_attempts", [])
                    if len(attempts) != index or attempts[-1].get("arm") != arm:
                        bad.append("M4 probe effect preceded attempt record")
                    if snapshot.get("planned_repetitions") != {"baseline": 2, "candidate": 2}:
                        bad.append("M5 frozen attempt denominator missing or changed")
                if len(measured.get("probe_attempts", [])) != len(snapshots):
                    bad.append("M5 interrupted attempt disappeared")
                if fault != "complete":
                    resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Model resume.",
                                               retry_of=directory.name, resume_candidate=True)
                    try:
                        loop.validate(resume, releases=root / "receipts")
                    except loop.ExperimentError:
                        pass
                    else:
                        bad.append("M4 attempted candidate admitted baseline-only resume")
                if bad:
                    counterexamples.append({"schedule": ["baseline", "candidate_probe", fault, "restore", "resume"],
                                            "violations": sorted(set(bad))})
        extra_count, extra_examples = self.extended_schedules(manifest)
        explored += extra_count
        counterexamples += extra_examples
        print(json.dumps({"lifecycle_model": {"schedules": explored, "counterexamples": len(counterexamples),
                                             "traces": counterexamples}}, sort_keys=True))
        self.assertEqual(counterexamples, [])


class ExperimentLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.releases = self.root / "experiments"
        self.locks = self.root / "locks"
        self.manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Compare qualified context variants.")
        self.adapter = FakeAdapter()

    def run_trial(self):
        return loop.run(self.manifest, self.adapter, releases=self.releases, lock_directory=self.locks)

    def read(self, directory, name):
        return json.loads((directory / (name + ".json")).read_text())

    def test_healthy_admission_runs_both_arms_and_restores(self):
        directory = self.run_trial()
        measurements = self.read(directory, "measurements")
        self.assertEqual(measurements["status"], "complete")
        for arm in ("baseline", "candidate"):
            self.assertEqual([r["repetition"] for r in measurements[arm]], [1, 2])
            self.assertEqual(self.adapter.events.count("probe:" + arm), 2)
        self.assertLess(self.adapter.events.index("stop:baseline"), self.adapter.events.index("start:candidate"))
        self.assertEqual(self.adapter.events[-1], "restore")
        self.assertTrue(self.read(directory, "restoration")["gate"]["pass_observed"])
        self.assertFalse(list(self.locks.glob("*.lock")))
        self.assertEqual(set(p.name for p in directory.iterdir()),
                         {"manifest.json", "measurements.json", "failures.json", "restoration.json"})

    def test_opt_in_warm_handoff_runs_under_claim_and_is_receipted(self):
        original = self.adapter.quiesce
        def quiesce(manifest, timeout):
            self.assertTrue((self.locks / (self.adapter.lock_id + ".lock")).is_file())
            return original(manifest, timeout)
        self.adapter.quiesce = quiesce
        directory = loop.run(self.manifest, self.adapter, releases=self.releases,
                             lock_directory=self.locks, quiesce_incumbent=True)
        self.assertEqual(self.adapter.events[0], "quiesce")
        self.assertEqual(self.read(directory, "measurements")["incumbent_handoff"]["mode"], "loop_quiesced_warm")
        self.assertTrue(self.read(directory, "restoration")["serving"])
        self.assertFalse((self.locks / (self.adapter.lock_id + ".lock")).exists())

    def test_quiesce_failure_is_already_a_mutation_and_always_restores(self):
        self.adapter.fail_at = "quiesce"
        directory = loop.run(self.manifest, self.adapter, releases=self.releases,
                             lock_directory=self.locks, quiesce_incumbent=True)
        self.assertEqual(self.adapter.events, ["quiesce", "restore"])
        self.assertEqual(self.read(directory, "measurements")["status"], "failed")
        self.assertTrue(self.read(directory, "restoration")["serving"])

    def test_per_arm_disk_floor_keeps_qualified_baseline_on_its_own_drive(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.disk_floor = 206
        adapter.disk_floors = {"baseline": 91, "candidate": 206}
        record = self.root / "incumbent.json"
        record.write_text(json.dumps({"profile_fingerprint": self.manifest["baseline"]["profile_fingerprint"]}))
        adapter.layouts = {arm: SimpleNamespace(root=self.root / arm, install_record=record,
            profile=SimpleNamespace(data={"host": {"min_available_ram_gib_at_start": 8,
                                                    "min_free_disk_gib": floor}}))
                           for arm, floor in adapter.disk_floors.items()}
        adapter.layouts["restoration_target"] = adapter.layouts["baseline"]
        adapter.disk_floors["restoration_target"] = adapter.disk_floors["baseline"]
        with patch.object(loop.lifecycle, "doctor", return_value={"ok": True, "checks": []}), \
                patch.object(loop.lifecycle, "gpu_facts", return_value={"available": True}), \
                patch.object(loop.lifecycle, "gpu_busy", return_value=None), \
                patch.object(loop.lifecycle, "port_in_use", return_value=False), \
                patch.object(loop.procs, "memory", return_value={"available": 100 * (1 << 30)}), \
                patch.object(shutil, "disk_usage", side_effect=lambda root: SimpleNamespace(
                    free=(153 if root.name == "baseline" else 1000) * (1 << 30))):
            for layout in adapter.layouts.values():
                layout.profile.data["server"] = {"port": 18090}
            observed = adapter.precondition(self.manifest, 120)
        self.assertTrue(observed["disk_above_floor"])
        self.assertEqual(91, observed["disk_by_arm"]["baseline"]["floor_gib"])
        self.assertEqual(206, observed["disk_by_arm"]["candidate"]["floor_gib"])

    def test_failed_restoration_retains_the_physical_claim_for_reconciliation(self):
        self.adapter.restore_serving = False
        directory = self.run_trial()
        self.assertEqual(self.read(directory, "measurements")["status"], "restoration_failed")
        self.assertTrue((self.locks / (self.adapter.lock_id + ".lock")).is_file())

    def test_taskset_scheduler_cannot_steal_a_dead_failed_restoration_hold(self):
        from scripts import eval_taskset
        self.adapter.restore_serving = False
        self.run_trial()
        path = self.locks / (self.adapter.lock_id + ".lock")
        before = path.read_bytes()
        with patch.object(eval_taskset.os, "kill", side_effect=ProcessLookupError):
            self.assertFalse(eval_taskset.take_pid_file(path))
        self.assertEqual(before, path.read_bytes())
        self.assertIs(json.loads(before)["persistent_hold"], True)

    def test_dedupe_refuses_replay_even_with_different_workload_or_repetitions(self):
        self.run_trial()
        self.manifest["repetitions"] = 3
        self.manifest["workload"]["depths"] = [0]
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.validate(self.manifest, releases=self.releases)
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            self.run_trial()
        self.assertEqual(self.adapter.events.count("install"), 1)

    def test_all_preconditions_are_fail_closed_without_any_lifecycle_mutation(self):
        for name in admitted():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                adapter = FakeAdapter()
                adapter.observation[name] = False
                directory = loop.run(self.manifest, adapter, releases=Path(tmp) / "releases", lock_directory=self.locks)
                self.assertEqual(adapter.events, ["precondition"])
                self.assertEqual(self.read(directory, "measurements")["status"], "blocked")
                self.assertEqual(self.read(directory, "restoration")["status"], "not_required")
                self.assertIn(name, self.read(directory, "failures")[0]["reason"])
        with self.assertRaises(loop.ExperimentError):
            loop.check_preconditions({})

    def test_live_lock_owner_is_not_stolen_or_unlinked(self):
        self.locks.mkdir()
        path = self.locks / (self.adapter.lock_id + ".lock")
        path.write_text('{"pid": 12345}')
        directory = self.run_trial()
        self.assertEqual(self.adapter.events, [])
        self.assertEqual(path.read_text(), '{"pid": 12345}')
        self.assertEqual(self.read(directory, "failures")[0]["reason"], "host_lock_owned")

    def test_restore_runs_on_install_start_probe_stop_failure(self):
        for failure in ("install", "start:baseline", "probe:baseline", "stop:baseline", "start:candidate", "probe:candidate"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                adapter = FakeAdapter()
                adapter.fail_at = failure
                directory = loop.run(self.manifest, adapter, releases=Path(tmp), lock_directory=self.locks)
                self.assertEqual(adapter.events[-1], "restore")
                self.assertTrue(self.read(directory, "restoration")["serving"])
                self.assertTrue(self.read(directory, "failures"))
                self.assertEqual(self.read(directory, "measurements")["status"], "failed")

    def test_wall_limit_stops_dispatch_but_does_not_skip_restoration(self):
        now = [0]
        original = self.adapter.install
        def install(manifest, timeout):
            original(manifest, timeout)
            now[0] = manifest["stop_conditions"]["max_wall_time_s"]
        self.adapter.install = install
        directory = loop.run(self.manifest, self.adapter, releases=self.releases,
                             lock_directory=self.locks, clock=lambda: now[0])
        self.assertEqual(self.adapter.events, ["precondition", "install", "restore"])
        self.assertEqual(self.read(directory, "failures")[0]["reason"], "max_wall_time")
        self.assertTrue(self.read(directory, "restoration")["serving"])

    def test_failure_budget_preserves_results_and_stops_exactly_at_limit(self):
        self.manifest["stop_conditions"]["max_failures"] = 2
        self.adapter.result["status"] = "error"
        directory = self.run_trial()
        data = self.read(directory, "measurements")
        self.assertEqual(len(data["baseline"]), 2)
        self.assertEqual(data["candidate"], [])
        self.assertEqual(self.adapter.events.count("probe:baseline"), 2)
        self.assertEqual(self.adapter.events[-1], "restore")

    def test_restoration_failure_is_not_reported_as_success(self):
        self.adapter.restore_serving = False
        directory = self.run_trial()
        self.assertEqual(self.read(directory, "measurements")["status"], "restoration_failed")
        self.assertFalse(self.read(directory, "restoration")["serving"])
        self.assertEqual(loop.report(directory)["recommendation"], "hold")

    def test_report_refuses_context_model_quant_and_protocol_confounding(self):
        directory = self.run_trial()
        self.assertFalse(loop.report(directory)["engine_only_comparison"])
        with self.assertRaisesRegex(loop.ExperimentError, "engine_only_claim_refused"):
            loop.report(directory, engine_only=True)
        for key, value in (("model", {"repository": "other/model"}), ("quantization", "Q2_0"),
                           ("protocol", "openai-responses")):
            changed = copy.deepcopy(self.manifest)
            changed["candidate"] = copy.deepcopy(changed["baseline"])
            changed["candidate"]["engine"] = "0.1.44.2"
            changed["candidate"][key] = value
            atomic_write_json(directory / "manifest.json", changed)
            with self.subTest(key=key), self.assertRaisesRegex(loop.ExperimentError, "engine_only_claim_refused"):
                loop.report(directory, engine_only=True)

    def test_throughput_alone_never_adopts(self):
        self.adapter.result["samples"] = [{"metrics": [{"name": "decode_tokens_s", "value": 1000000}]}]
        directory = self.run_trial()
        self.assertEqual(loop.report(directory)["recommendation"], "hold")

    def test_scrub_applies_before_publication(self):
        self.adapter.observation["fixture"] = "fixture-host at 192.0.2.55 under D:/private-root/evidence"
        self.adapter.result["raw_log"] = "unpublished raw text without a private identifier"
        directory = self.run_trial()
        text = (directory / "measurements.json").read_text()
        for private in ("fixture-host", "192.0.2.55", "D:/private-root"):
            self.assertNotIn(private, text)
        self.assertIn("<redacted>", text)
        self.assertIn("<root>", text)
        self.assertNotIn("raw_log", text)
        self.assertNotIn("unpublished raw text", text)
        unsafe = self.root / "unsafe.json"
        with self.assertRaises(PublicationError):
            loop.public_write(unsafe, {"unreviewed": "unreviewed-fixture"},
                              Scrubber("D:/private-root", denylist=["unreviewed-fixture"]))
        self.assertFalse(unsafe.exists())

    def test_frozen_profile_and_harness_drift_refuse(self):
        self.manifest["candidate"]["config"]["setup_args"]["context"] = 524288
        with self.assertRaisesRegex(loop.ExperimentError, "frozen_profile_drift"):
            loop.validate(self.manifest, releases=self.releases)
        self.manifest = loop.new_manifest(BASELINE, CANDIDATE, rationale="fixture")
        self.manifest["harness_files"]["scripts/perf_probe.py"] = "0" * 64
        with self.assertRaisesRegex(loop.ExperimentError, "frozen_harness_drift"):
            loop.validate(self.manifest, releases=self.releases)

    def test_manifest_limits_and_safety_flags_are_enforced(self):
        cases = [("repetitions", 0), ("repetitions", 21), ("repetitions", True)]
        for key, value in cases:
            with self.subTest(value=value):
                manifest = copy.deepcopy(self.manifest)
                manifest[key] = value
                with self.assertRaises(loop.ExperimentError):
                    loop.validate(manifest, releases=self.releases)
        for key in ("abort_on_gpu_busy", "abort_on_competing_tenant", "abort_on_disk_floor"):
            manifest = copy.deepcopy(self.manifest)
            manifest["stop_conditions"][key] = False
            with self.assertRaises(loop.ExperimentError):
                loop.validate(manifest, releases=self.releases)
        self.manifest["workload"]["depths"] = [131072 - 512 - 8]
        with self.assertRaisesRegex(loop.ExperimentError, "workload_exceeds_common_context"):
            loop.validate(self.manifest, releases=self.releases)

    def test_unknown_fields_and_restoration_mismatch_refuse(self):
        self.manifest["shell"] = "not executable authority"
        with self.assertRaisesRegex(loop.ExperimentError, "invalid_manifest_schema"):
            loop.validate(self.manifest, releases=self.releases)
        del self.manifest["shell"]
        self.manifest["restoration_target"] = self.manifest["candidate"]
        with self.assertRaisesRegex(loop.ExperimentError, "restoration_must_match_predecessor"):
            loop.validate(self.manifest, releases=self.releases)

    def test_next_queues_one_frozen_distinct_trial_without_execution(self):
        directory = self.run_trial()
        events = self.adapter.events.copy()
        queue = loop.propose_next(directory, NEXT, releases=self.releases)
        self.assertFalse(queue["automatic_execution"])
        self.assertEqual(len(queue["trials"]), 1)
        queued = queue["trials"][0]
        self.assertEqual(loop.validate(queued["manifest"], releases=self.releases), queued["key"])
        self.assertNotEqual(queued["key"], loop.identity_key(self.manifest))
        self.assertEqual(events, self.adapter.events)
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.propose_next(directory, CANDIDATE, releases=self.releases)

    def test_record_blocked_is_not_a_mock_measurement_or_authorization(self):
        observation = admitted()
        observation.update(timestamp_utc="2026-10-16T00:00:00Z", wall_time_s=2.0)
        with self.assertRaisesRegex(loop.ExperimentError, "observation_does_not_establish_blocker"):
            loop.record_blocked(self.manifest, observation, releases=self.releases)
        self.assertFalse(self.releases.exists())
        observation["gpu_idle"] = False
        with patch.object(loop, "HostAdapter", side_effect=AssertionError("adapter")), \
                patch.object(loop, "host_lock", side_effect=AssertionError("host_lock")), \
                patch.object(loop, "lifecycle", None):
            directory = loop.record_blocked(self.manifest, observation, releases=self.releases)
        measurements = self.read(directory, "measurements")
        self.assertEqual((measurements["baseline"], measurements["candidate"]), ([], []))
        self.assertEqual((measurements["started_utc"], measurements["wall_time_s"]), ("2026-10-16T00:00:00Z", 2.0))
        self.assertEqual(measurements["status"], "blocked")
        self.assertEqual(self.read(directory, "failures"), [{"reason": "precondition:gpu_idle"}])
        restoration = self.read(directory, "restoration")
        self.assertEqual(restoration["status"], "not_required")
        self.assertIsNone(restoration["serving"])

    def blocked_observation(self, **changes):
        observation = admitted()
        observation.update(gpu_idle=False, timestamp_utc="2026-10-16T00:00:00Z", wall_time_s=2.0)
        observation.update(changes)
        return observation

    def assert_blocked_refused(self, observation, reason="invalid_observation"):
        key = loop.identity_key(self.manifest)
        with self.assertRaises(loop.ExperimentError) as caught:
            loop.record_blocked(self.manifest, observation, releases=self.releases)
        self.assertEqual(str(caught.exception), reason)
        # Refusal happens before the identity is reserved: no directory and no public bytes.
        self.assertFalse((self.releases / key).exists())
        self.assertEqual(list(self.releases.rglob("*")) if self.releases.exists() else [], [])

    def test_record_blocked_refuses_malformed_observations_before_creating_a_directory(self):
        cases = [None, [], "gpu_idle=false", self.blocked_observation(timestamp_utc=None)]
        for name in loop.ADMISSION_FLAGS:
            missing = self.blocked_observation()
            del missing[name]
            cases += [missing, self.blocked_observation(**{name: "false"}),
                      self.blocked_observation(**{name: 0}), self.blocked_observation(**{name: None})]
        for timestamp in ("2026-10-16T00:00:00", "2026-10-16T02:00:00+02:00", "not a time", "",
                          "2026-13-01T00:00:00Z", 1760572800):
            cases.append(self.blocked_observation(timestamp_utc=timestamp))
        for duration in (-0.001, True, False, float("nan"), float("inf"), float("-inf"), "2.0", None):
            cases.append(self.blocked_observation(wall_time_s=duration))
        missing = self.blocked_observation()
        del missing["wall_time_s"]
        cases.append(missing)
        for observation in cases:
            with self.subTest(observation=observation):
                self.assert_blocked_refused(observation)
        # An absent flag is invalid input, never evidence of a measured blocker; all-true still refuses.
        self.assert_blocked_refused(self.blocked_observation(gpu_idle=True), "observation_does_not_establish_blocker")
        observation = self.blocked_observation(timestamp_utc="2026-10-16T00:00:00+00:00", wall_time_s=0)
        directory = loop.record_blocked(self.manifest, observation, releases=self.releases)
        self.assertEqual(self.read(directory, "measurements")["wall_time_s"], 0)

    def test_record_blocked_scrubber_refusal_leaves_identity_unconsumed(self):
        key = loop.identity_key(self.manifest)
        with patch.object(loop, "private_denylist", return_value=["denied-fixture"]):
            with self.assertRaises(PublicationError) as caught:
                loop.record_blocked(self.manifest, self.blocked_observation(note="denied-fixture"),
                                    releases=self.releases)
            self.assertNotIn("denied-fixture", str(caught.exception))
            self.assertFalse((self.releases / key).exists())
            self.assertEqual(list(self.releases.rglob("*")) if self.releases.exists() else [], [])
            directory = loop.record_blocked(self.manifest, self.blocked_observation(note="corrected"),
                                            releases=self.releases)
        self.assertEqual(directory.name, key)
        self.assertEqual({p.name for p in directory.iterdir()},
                         {"manifest.json", "measurements.json", "failures.json", "restoration.json"})

    def test_record_blocked_never_overwrites_or_removes_an_existing_receipt(self):
        first = loop.record_blocked(self.manifest, self.blocked_observation(), releases=self.releases)
        original = {p.name: p.read_bytes() for p in first.iterdir()}
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.record_blocked(self.manifest, self.blocked_observation(gpu_idle=True, doctor_ok=False),
                                releases=self.releases)
        self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()}, original)
        shutil.rmtree(first)
        # Another writer wins the exclusive creation after validation; its directory stays untouched.
        real = loop.Scrubber

        class RacingScrubber(real):
            def scrub(inner, data):
                if not first.exists():
                    first.mkdir(parents=True)
                    (first / "measurements.json").write_bytes(b'{"writer": "other"}')
                return real.scrub(inner, data)

        with patch.object(loop, "Scrubber", RacingScrubber), \
                self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.record_blocked(self.manifest, self.blocked_observation(), releases=self.releases)
        self.assertEqual([p.name for p in first.iterdir()], ["measurements.json"])
        self.assertEqual((first / "measurements.json").read_bytes(), b'{"writer": "other"}')

    def test_blocked_retry_preserves_original_and_has_one_append_only_attempt(self):
        self.adapter.observation["gpu_idle"] = False
        prior = self.run_trial()
        original = (prior / "measurements.json").read_bytes()
        retry = loop.new_manifest(BASELINE, CANDIDATE, rationale="Owner released the GPU.",
                                  retry_of=prior.name)
        key = loop.validate(retry, releases=self.releases)
        self.assertNotEqual(key, prior.name)
        self.adapter.observation["gpu_idle"] = True
        directory = loop.run(retry, self.adapter, releases=self.releases, lock_directory=self.locks)
        self.assertEqual(self.read(directory, "measurements")["status"], "complete")
        self.assertEqual((prior / "measurements.json").read_bytes(), original)
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.validate(retry, releases=self.releases)

    def test_retry_refuses_completed_or_mismatched_trial(self):
        prior = self.run_trial()
        retry = loop.new_manifest(BASELINE, CANDIDATE, rationale="fixture", retry_of=prior.name)
        with self.assertRaisesRegex(loop.ExperimentError, "matching_blocked_or_restored_failed"):
            loop.validate(retry, releases=self.releases)
        retry["retry_of"] = "f" * 64
        with self.assertRaisesRegex(loop.ExperimentError, "retry_receipt_missing"):
            loop.validate(retry, releases=self.releases)

    def test_candidate_resume_preserves_measured_baseline_provenance(self):
        self.adapter.fail_at = "start:candidate"
        prior = self.run_trial()
        adapter = FakeAdapter()
        manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Retry the unstarted arm.",
                                     retry_of=prior.name, resume_candidate=True)
        directory = loop.run(manifest, adapter, releases=self.releases, lock_directory=self.locks)
        measured = self.read(directory, "measurements")
        self.assertEqual(measured["status"], "complete")
        self.assertEqual(measured["baseline_source_experiment"], prior.name)
        self.assertEqual([r["source_experiment"] for r in measured["baseline"]], [prior.name] * 2)
        self.assertNotIn("start:baseline", adapter.events)
        self.assertEqual(adapter.events.count("probe:candidate"), 2)
        self.assertTrue(self.read(directory, "restoration")["serving"])
        manifest["repetitions"] = 3
        with self.assertRaisesRegex(loop.ExperimentError, "complete_baseline"):
            loop.validate(manifest, releases=self.releases)

    # Synthetic receipts only: these exercise retry admission, never real-host restoration or performance.
    def restored_failure(self):
        self.adapter.fail_at = "start:candidate"
        return self.run_trial()

    def receipt_copy(self, prior, name=None, edit=None):
        """Copy a synthetic receipt into fresh releases and optionally rewrite one of its files."""
        releases = Path(tempfile.mkdtemp(dir=self.root))
        shutil.copytree(prior, releases / (name or prior.name))
        if edit:
            edit(releases / (name or prior.name))
        return releases

    def assert_refused_before_mutation(self, manifest, releases, reason):
        before = sorted(p.name for p in releases.iterdir())
        adapter = FakeAdapter()
        with self.assertRaisesRegex(loop.ExperimentError, reason) as caught:
            loop.run(manifest, adapter, releases=releases, lock_directory=self.locks)
        self.assertEqual(adapter.events, [])
        self.assertEqual(sorted(p.name for p in releases.iterdir()), before)
        return str(caught.exception)

    def test_retry_refuses_matching_receipt_copied_under_another_key(self):
        self.adapter.observation["gpu_idle"] = False
        prior = self.run_trial()
        alias = "e" * 64
        releases = self.receipt_copy(prior, alias)
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=alias)
        self.assert_refused_before_mutation(retry, releases, "retry_receipt_key_mismatch")

    def test_restored_failure_retry_remains_eligible_and_keeps_receipt_bytes(self):
        prior = self.restored_failure()
        original = {p.name: p.read_bytes() for p in prior.iterdir()}
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=prior.name)
        directory = loop.run(retry, FakeAdapter(), releases=self.releases, lock_directory=self.locks)
        self.assertEqual(self.read(directory, "measurements")["status"], "complete")
        self.assertEqual({p.name: p.read_bytes() for p in prior.iterdir()}, original)

    def test_malformed_retry_receipts_refuse_with_closed_public_safe_reason(self):
        prior = self.restored_failure()
        marker = "private-receipt-marker"

        def write(name, text):
            return lambda d: (d / (name + ".json")).write_text(text)

        def rewrite(name, change):
            def edit(d):
                data = json.loads((d / (name + ".json")).read_text())
                change(data)
                (d / (name + ".json")).write_text(json.dumps(data))
            return edit

        cases = {
            "missing_measurements": lambda d: (d / "measurements.json").unlink(),
            "missing_restoration": lambda d: (d / "restoration.json").unlink(),
            "malformed_json": write("measurements", '{"status": "' + marker),
            "duplicate_key": write("restoration", '{"status": "restored", "status": "' + marker + '"}'),
            "non_object_measurements": write("measurements", json.dumps([marker])),
            "non_object_restoration": write("restoration", json.dumps(marker)),
            "manifest_schema": rewrite("manifest", lambda m: m.update(shell=marker)),
            "manifest_missing_field": rewrite("manifest", lambda m: m.pop("harness_files")),
            "missing_status": rewrite("measurements", lambda m: m.pop("status")),
            "non_string_status": rewrite("measurements", lambda m: m.update(status=[marker])),
            "missing_arm": rewrite("measurements", lambda m: m.pop("candidate")),
            "non_list_arm": rewrite("measurements", lambda m: m.update(baseline={"1": marker})),
            "non_object_row": rewrite("measurements", lambda m: m.update(baseline=[marker])),
            "row_missing_result": rewrite("measurements", lambda m: m["baseline"][0].pop("result")),
            "row_string_result": rewrite("measurements", lambda m: m["baseline"][0].update(result=marker)),
            "row_string_repetition": rewrite("measurements", lambda m: m["baseline"][0].update(repetition="1")),
            "row_boolean_repetition": rewrite("measurements", lambda m: m["baseline"][0].update(repetition=True)),
            "missing_restoration_status": rewrite("restoration", lambda m: m.pop("status")),
            "missing_serving": rewrite("restoration", lambda m: m.pop("serving")),
            "non_boolean_serving": rewrite("restoration", lambda m: m.update(serving=marker)),
        }
        for case, edit in cases.items():
            for resume in (False, True):
                with self.subTest(case=case, resume=resume):
                    releases = self.receipt_copy(prior, edit=edit)
                    retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                              retry_of=prior.name, resume_candidate=resume)
                    reason = self.assert_refused_before_mutation(retry, releases, "^retry_receipt_")
                    self.assertNotIn(marker, reason)
                    self.assertNotIn(str(self.root), reason)
                    self.assertNotIn("json", reason)

    def test_missing_fields_are_never_synthesized_into_restoration(self):
        prior = self.restored_failure()
        releases = self.receipt_copy(prior, edit=lambda d: (d / "restoration.json").write_text(
            json.dumps({"status": "restored", "serving": None})))
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=prior.name)
        self.assert_refused_before_mutation(retry, releases, "matching_blocked_or_restored_failed")

    def test_running_and_restoration_failed_trials_remain_ineligible(self):
        prior = self.restored_failure()
        for status in ("running", "complete", "restoration_failed"):
            with self.subTest(status=status):
                def edit(d, status=status):
                    data = json.loads((d / "measurements.json").read_text())
                    data["status"] = status
                    (d / "measurements.json").write_text(json.dumps(data))
                releases = self.receipt_copy(prior, edit=edit)
                retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                          retry_of=prior.name)
                self.assert_refused_before_mutation(retry, releases, "matching_blocked_or_restored_failed")

    def test_candidate_resume_refuses_baseline_measured_by_another_harness(self):
        prior = self.restored_failure()
        path = prior / "manifest.json"
        data = json.loads(path.read_text())
        data["harness_files"]["scripts/perf_probe.py"] = "0" * 64
        path.write_text(json.dumps(data))
        original = {p.name: p.read_bytes() for p in prior.iterdir()}
        resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                   retry_of=prior.name, resume_candidate=True)
        self.assert_refused_before_mutation(resume, self.releases, "complete_baseline")
        # The explicit full retry may use newly frozen tooling; it re-measures both arms.
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=prior.name)
        adapter = FakeAdapter()
        directory = loop.run(retry, adapter, releases=self.releases, lock_directory=self.locks)
        self.assertEqual(adapter.events.count("probe:baseline"), 2)
        self.assertNotIn("baseline_source_experiment", self.read(directory, "measurements"))
        self.assertEqual({p.name: p.read_bytes() for p in prior.iterdir()}, original)

    def test_candidate_resume_refuses_incomplete_or_misnumbered_baseline(self):
        prior = self.restored_failure()
        row = json.loads((prior / "measurements.json").read_text())["baseline"][0]

        def rows(*numbers, status="complete"):
            return [dict(copy.deepcopy(row), repetition=n, result=dict(row["result"], status=status))
                    for n in numbers]

        cases = {"duplicate": rows(1, 1), "missing": rows(1), "reordered": rows(2, 1),
                 "out_of_range": rows(1, 3), "zero_based": rows(0, 1), "extra": rows(1, 2, 3),
                 "incomplete": rows(1, 2, status="error"),
                 "result_without_status": [dict(r, result={}) for r in rows(1, 2)]}
        for case, baseline in cases.items():
            with self.subTest(case=case):
                def edit(d, baseline=baseline):
                    data = json.loads((d / "measurements.json").read_text())
                    data["baseline"] = baseline
                    (d / "measurements.json").write_text(json.dumps(data))
                releases = self.receipt_copy(prior, edit=edit)
                resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                           retry_of=prior.name, resume_candidate=True)
                self.assert_refused_before_mutation(resume, releases, "complete_baseline")

        def candidate_row(d):
            data = json.loads((d / "measurements.json").read_text())
            data["candidate"] = rows(1)
            (d / "measurements.json").write_text(json.dumps(data))
        resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                   retry_of=prior.name, resume_candidate=True)
        self.assert_refused_before_mutation(resume, self.receipt_copy(prior, edit=candidate_row), "complete_baseline")
        for change in ({"repetitions": 3}, {"workload": dict(resume["workload"], depths=[0])}):
            with self.subTest(change=sorted(change)):
                changed = dict(copy.deepcopy(resume), **change)
                self.assert_refused_before_mutation(changed, self.receipt_copy(prior), "complete_baseline")

    def test_ram_settle_is_bounded_and_never_lowers_the_floor(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.ram_floor = 36
        now = [0]
        def sleep(seconds):
            now[0] += seconds
        with patch.object(loop.procs, "memory", return_value={"available": 35 * (1 << 30)}):
            result = adapter.settle(900, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(result["status"], "below_floor")
        self.assertEqual(now[0], 90)
        self.assertEqual(result["ram_floor_gib"], 36)
        now[0] = 0
        with patch.object(loop.procs, "memory", side_effect=[{"available": 35 * (1 << 30)},
                                                            {"available": 36 * (1 << 30)}]):
            result = adapter.settle(20, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(now[0], 5)

    def test_pro_host_profile_is_frozen_and_mismatched_gpu_refuses(self):
        manifest = loop.new_manifest(PRO_BASELINE, PRO_CANDIDATE, rationale="Same Coder context comparison.",
                                     host_profile="rtxpro6000-win-a")
        loop.validate(manifest, releases=self.releases)
        self.assertEqual(manifest["baseline"]["config"]["host"]["min_gpu_vram_mib"], 97000)
        manifest["host_role"] = "rtx5090-win-a"
        with self.assertRaisesRegex(loop.ExperimentError, "host_profile_mismatch"):
            loop.validate(manifest, releases=self.releases)

    def test_display_clients_are_tolerated_but_foreign_compute_is_not(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.disk_floor = 1
        adapter.disk_floors = {"baseline": 1}
        layout = SimpleNamespace(root=self.root, profile=SimpleNamespace(data={"host": {"display_attached": True}}))
        adapter.layouts = {"baseline": layout}
        gpu = {"available": True, "processes": [{"pid": 10, "type": "C"}, {"pid": 20, "type": "G"}]}
        with patch.object(loop.lifecycle, "status", return_value={"state": "healthy"}), \
             patch.object(loop.lifecycle, "running", return_value={"server": SimpleNamespace(pid=10)}), \
             patch.object(loop.lifecycle, "gpu_facts", return_value=gpu):
            adapter.guard("baseline", 10)
            gpu["processes"][1]["type"] = "C"
            with self.assertRaisesRegex(loop.ExperimentError, "competing_tenant"):
                adapter.guard("baseline", 10)

    def test_host_adapter_refuses_non_windows_without_lifecycle_calls(self):
        with patch.object(loop.sys, "platform", "darwin"), self.assertRaisesRegex(loop.ExperimentError, "native_windows"):
            loop.HostAdapter(self.manifest, {})

    def test_host_adapter_allows_the_native_tooling_archive_in_either_arm(self):
        roots = {arm: self.root.resolve() / arm for arm in ("baseline", "candidate")}
        bindings = {"host_lock_id": "fixture-host", "roots": {arm: str(root) for arm, root in roots.items()}}
        source = loop.ROOT
        for arm, root in roots.items():
            with self.subTest(arm=arm):
                tooling = root / "tooling"
                (tooling / "profiles").mkdir(parents=True)
                for profile in (BASELINE, CANDIDATE):
                    shutil.copyfile(source / "profiles" / (profile + ".json"),
                                    tooling / "profiles" / (profile + ".json"))
                with patch.object(loop.sys, "platform", "win32"), patch.object(loop, "ROOT", tooling):
                    adapter = loop.HostAdapter(self.manifest, bindings)
                self.assertEqual(adapter.layouts["baseline"].root, roots["baseline"])
                self.assertEqual(adapter.layouts["candidate"].root, roots["candidate"])
                self.assertIs(adapter.layouts["restoration_target"], adapter.layouts["baseline"])

    def test_host_adapter_still_refuses_repository_roots_and_other_harness_ancestors(self):
        root = self.root.resolve() / "candidate"
        bindings = {"host_lock_id": "fixture-host", "roots": {
            "baseline": str(self.root.resolve() / "baseline"), "candidate": str(root)}}
        for tooling in (root, root / "source", root / "staging" / "tooling", root / "tooling" / "checkout"):
            with self.subTest(tooling=tooling), patch.object(loop.sys, "platform", "win32"), \
                    patch.object(loop, "ROOT", tooling), patch.object(loop, "load") as load_profile, \
                    self.assertRaisesRegex(loop.ExperimentError, "unsafe_integration_root"):
                loop.HostAdapter(self.manifest, bindings)
            load_profile.assert_not_called()

    def test_host_adapter_still_refuses_home_and_volume_roots_with_native_tooling(self):
        home = Path.home().resolve()
        for root in (home, *home.parents):
            bindings = {"host_lock_id": "fixture-host", "roots": {
                "baseline": str(self.root.resolve() / "baseline"), "candidate": str(root)}}
            with self.subTest(root=root), patch.object(loop.sys, "platform", "win32"), \
                    patch.object(loop, "ROOT", root / "tooling"), patch.object(loop, "load") as load_profile, \
                    self.assertRaisesRegex(loop.ExperimentError, "unsafe_integration_root"):
                loop.HostAdapter(self.manifest, bindings)
            load_profile.assert_not_called()

    def test_host_adapter_refuses_every_root_nested_inside_the_harness_before_loading(self):
        tooling = self.root.resolve() / "checkout"
        for arm in ("baseline", "candidate", "restoration_target"):
            for nested in (tooling / "profiles", tooling / "scratch" / "candidate",
                           tooling / "unused" / ".." / "profiles"):
                bindings = {"host_lock_id": "fixture-host", "roots": {
                    name: str(nested if name == arm else self.root.resolve() / name)
                    for name in ("baseline", "candidate", "restoration_target")}}
                with self.subTest(arm=arm, root=nested), patch.object(loop.sys, "platform", "win32"), \
                        patch.object(loop, "ROOT", tooling), \
                        patch.object(loop, "load", side_effect=AssertionError("profile load before root refusal")) as load_profile, \
                        self.assertRaisesRegex(loop.ExperimentError, "unsafe_integration_root"):
                    loop.HostAdapter(self.manifest, bindings, claim={"fixture": True})
                load_profile.assert_not_called()

    def test_host_adapter_still_refuses_symlinked_integration_roots(self):
        root = self.root.resolve() / "candidate"
        root.mkdir()
        link = self.root.resolve() / "candidate-link"
        link.symlink_to(root, target_is_directory=True)
        bindings = {"host_lock_id": "fixture-host", "roots": {
            "baseline": str(self.root.resolve() / "baseline"), "candidate": str(link)}}
        with patch.object(loop.sys, "platform", "win32"), patch.object(loop, "ROOT", root / "tooling"), \
                patch.object(loop, "load") as load_profile, \
                self.assertRaisesRegex(loop.ExperimentError, "root_reparse_point"):
            loop.HostAdapter(self.manifest, bindings)
        load_profile.assert_not_called()

    def test_host_adapter_refuses_volume_roots_outside_the_home_drive_before_loading(self):
        class WindowsPath(PureWindowsPath):
            @classmethod
            def home(cls):
                return cls("C:/fixture-home")

            def absolute(self):
                return self

            def resolve(self):
                return self

            def is_symlink(self):
                return False

            def is_junction(self):
                return False

        for arm in ("baseline", "candidate", "restoration_target"):
            for volume in ("D:/", "//fixture/share/"):
                root = WindowsPath(volume)
                bindings = {"host_lock_id": "fixture-host", "roots": {
                    name: str(root if name == arm else WindowsPath("E:/") / name)
                    for name in ("baseline", "candidate", "restoration_target")}}
                with self.subTest(arm=arm, volume=volume), \
                        patch.object(loop.sys, "platform", "win32"), patch.object(loop, "Path", WindowsPath), \
                        patch.object(loop, "ROOT", root / "tooling"), \
                        patch.object(loop, "load", side_effect=AssertionError("profile load before root refusal")) as load_profile, \
                        self.assertRaisesRegex(loop.ExperimentError, "unsafe_integration_root"):
                    loop.HostAdapter(self.manifest, bindings, claim={"fixture": True})
                load_profile.assert_not_called()

    def test_host_adapter_refuses_unsafe_roots_spelled_with_dot_segments(self):
        home = Path.home().resolve()
        for root in (home / "unused" / "..", home / "unused" / ".." / "..", Path("/") / "unused" / ".."):
            bindings = {"host_lock_id": "fixture-host", "roots": {
                "baseline": str(self.root.resolve() / "baseline"), "candidate": str(root)}}
            with self.subTest(root=root), patch.object(loop.sys, "platform", "win32"), \
                    patch.object(loop, "ROOT", home / "tooling"), \
                    patch.object(loop, "load", side_effect=AssertionError("profile load before root refusal")) as load_profile, \
                    self.assertRaisesRegex(loop.ExperimentError, "unsafe_integration_root"):
                loop.HostAdapter(self.manifest, bindings)
            load_profile.assert_not_called()

    def test_lifecycle_start_records_the_call_marker_under_its_lock_before_launch(self):
        layout = loop.Layout(self.root, loop.load(loop.ROOT / "profiles" / (BASELINE + ".json")))
        write_json = loop.lifecycle.atomic_write_json

        def record(path, data):
            with self.assertRaises(loop.lifecycle.LifecycleError):
                with loop.lifecycle.FileLock(layout.lock_file):
                    pass
            write_json(path, data)

        def launch(argv, **_kwargs):
            with loop.lifecycle.FileLock(layout.lock_file):
                current = json.loads(layout.run_record.read_text())
                self.assertEqual(argv[argv.index("--launch-id") + 1], current["launch_id"])
            raise RuntimeError("fixture_launch_boundary")

        with patch.dict(loop.os.environ, {"OMP_STRATA_EXPERIMENT_LAUNCH": "fixture-launch"}), \
                patch.object(loop.lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
                patch.object(loop.lifecycle, "read_key", return_value="fixture"), \
                patch.object(loop.lifecycle, "running", return_value={}), \
                patch.object(loop.lifecycle, "port_in_use", return_value=False), \
                patch.object(loop.lifecycle, "gpu_facts", return_value={}), \
                patch.object(loop.lifecycle, "gpu_busy", return_value=None), \
                patch.object(loop.lifecycle.procs, "memory", return_value={"available": 0}), \
                patch.object(loop.lifecycle, "atomic_write_json", side_effect=record), \
                patch.object(loop.lifecycle, "_launch_detached", side_effect=launch), \
                self.assertRaisesRegex(RuntimeError, "fixture_launch_boundary"):
            loop.lifecycle.start(layout, tool_argv=["fixture"], log=lambda _line: None)
        current = json.loads(layout.run_record.read_text())
        self.assertEqual(current.get("experiment_launch_id"), "fixture-launch")


class FleetClaimTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.evidence = self.root / "private-trials"
        self.locks = self.root / "locks"
        self.manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Claim fixture.")
        self.manifest["restoration_target"] = loop.freeze_arm(NEXT)
        self.raw = json.dumps(self.manifest, indent=2).encode()
        now = datetime.now(timezone.utc)
        self.claim = {
            "schema_version": "carrythrough.fleet-claim.v1", "claim_id": "fixture-claim",
            "project_key": "fleet-lab", "policy_generation": 6, "policy_sha256": "a" * 64,
            "resource_id": "fixture-host:rtx5090", "host": "fixture-host",
            "variant_id": CANDIDATE, "trial_manifest_sha256": loop.sha256(self.raw),
            "repetitions": 2, "max_seconds": 3600,
            "acquired_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(), "owner": "fixture-owner",
            "restoration_ref": NEXT,
        }
        self.bindings = {"host": "fixture-host", "resource_id": "fixture-host:rtx5090",
                         "host_role": "rtx5090-win-a", "host_lock_id": "rtx5090-win-a"}
        self.adapter = FakeAdapter()

    def run_claim(self, **kwargs):
        return loop.run(self.manifest, self.adapter, claim=self.claim, bindings=self.bindings,
                        manifest_bytes=self.raw, releases=self.evidence, lock_directory=self.locks, **kwargs)

    def usage(self, directory):
        return json.loads((directory.parent / "usage.json").read_text())

    def test_valid_claim_restores_claim_incumbent_and_writes_bound_usage(self):
        directory = self.run_claim()
        usage = self.usage(directory)
        self.assertEqual(usage["schema_version"], "carrythrough.fleet-usage.v1")
        self.assertEqual(usage["claim_id"], self.claim["claim_id"])
        self.assertEqual(usage["outcome"], "passed")
        self.assertTrue(usage["restoration"]["verified"])
        self.assertEqual(usage["restoration"]["incumbent_ref"], NEXT)
        self.assertEqual(self.adapter.restored_profile, NEXT)
        self.assertEqual(usage["restoration"]["evidence_sha256"], sha256_file(directory / "restoration.json"))
        self.assertEqual(sha256_file(directory / "manifest.json"), self.claim["trial_manifest_sha256"])
        self.assertGreaterEqual(usage["gpu_seconds"], 0)
        self.assertLessEqual(usage["started_at"], usage["ended_at"])
        self.assertEqual(directory.parent.name, self.claim["claim_id"])
        for path in usage["evidence_paths"]:
            self.assertTrue((directory.parent / path).is_file())
        self.assertFalse(list(self.locks.glob("*.lock")))
        self.assertTrue((self.locks / "claims" / "fixture-claim.json").is_file())

    def test_every_claim_field_is_required_and_malformed_values_refuse_before_adapter(self):
        invalid = [None, [], {}, {**self.claim, "unknown": True}]
        for field in self.claim:
            missing = self.claim.copy()
            del missing[field]
            invalid.append(missing)
            invalid.append({**self.claim, field: None})
        for field in ("claim_id", "project_key", "resource_id", "host", "variant_id", "owner", "restoration_ref"):
            for bad in ("", " ", "../escape", "line\nbreak", 123):
                invalid.append({**self.claim, field: bad})
        for field in ("policy_sha256", "trial_manifest_sha256"):
            for bad in ("a" * 63, "G" * 64, True):
                invalid.append({**self.claim, field: bad})
        for field in ("policy_generation", "repetitions", "max_seconds"):
            for bad in (0, -1, True, "3", 1.5, float("inf")):
                invalid.append({**self.claim, field: bad})
        for field in ("acquired_at", "expires_at"):
            for bad in ("2026-10-23", "2026-10-23T01:00:00", "not-a-date"):
                invalid.append({**self.claim, field: bad})
        valid = self.claim
        for claim in invalid:
            with self.subTest(claim=claim):
                self.claim = claim
                with self.assertRaises(loop.ExperimentError):
                    self.run_claim()
                self.assertEqual(self.adapter.events, [])
                self.assertFalse(self.evidence.exists())
        self.claim = valid

    def test_expired_future_mismatched_or_over_budget_claims_refuse_before_adapter(self):
        for changes in (
            {"expires_at": "2020-01-01T00:00:00Z"},
            {"acquired_at": "2099-01-01T00:00:00Z"},
            {"host": "other-host"}, {"resource_id": "fixture-host:rtxpro6000"},
            {"variant_id": BASELINE}, {"repetitions": 1}, {"max_seconds": 3599},
            {"trial_manifest_sha256": "f" * 64}, {"restoration_ref": BASELINE},
        ):
            with self.subTest(changes=changes):
                original = self.claim
                self.claim = {**original, **changes}
                with self.assertRaises(loop.ExperimentError):
                    self.run_claim()
                self.claim = original
                self.assertEqual(self.adapter.events, [])
                self.assertFalse(self.evidence.exists())

    def test_manifest_hash_is_exact_bytes_not_canonical_json(self):
        self.claim["trial_manifest_sha256"] = loop.sha256(loop.canonical(self.manifest))
        with self.assertRaisesRegex(loop.ExperimentError, "manifest"):
            self.run_claim()
        self.assertEqual(self.adapter.events, [])

    def test_modified_manifest_object_cannot_reuse_authorized_file_hash(self):
        self.manifest["rationale"] = "Not the authorized bytes."
        with self.assertRaisesRegex(loop.ExperimentError, "manifest"):
            self.run_claim()
        self.assertEqual(self.adapter.events, [])

    def test_restoration_failure_or_exception_writes_failed_usage_and_retains_mutex(self):
        for failure in ("not-serving", "restore"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                self.evidence = Path(tmp) / "trials"
                self.locks = Path(tmp) / "locks"
                self.adapter = FakeAdapter()
                self.adapter.restore_serving = False
                self.adapter.fail_at = failure
                directory = self.run_claim()
                usage = self.usage(directory)
                self.assertEqual(usage["outcome"], "failed")
                self.assertFalse(usage["restoration"]["verified"])
                lock = self.locks / (self.adapter.lock_id + ".lock")
                original = lock.read_bytes()
                with self.assertRaisesRegex(loop.ExperimentError, "host_lock_owned"):
                    with loop.host_lock(self.adapter.lock_id, self.locks):
                        self.fail("failed restoration lock must never be stolen")
                self.assertEqual(lock.read_bytes(), original)

    def test_claim_is_consumed_once_even_with_a_different_evidence_directory(self):
        self.run_claim()
        self.evidence = self.root / "second-trials"
        self.adapter.events.clear()
        directory = self.run_claim()
        self.assertEqual(self.adapter.events, [])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")

    def test_wall_cap_aborts_trial_but_preserves_restoration_budget_and_usage(self):
        now = [0]
        original = self.adapter.install
        def install(manifest, timeout):
            original(manifest, timeout)
            now[0] = 3600
        original_restore = self.adapter.restore
        def restore(manifest, *, custody):
            now[0] += 30
            return original_restore(manifest, custody=custody)
        self.adapter.install, self.adapter.restore = install, restore
        directory = self.run_claim(clock=lambda: now[0])
        self.assertEqual(self.adapter.events, ["precondition", "install", "restore"])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")
        self.assertEqual(self.usage(directory)["gpu_seconds"], 3630)
        self.assertTrue(self.usage(directory)["restoration"]["verified"])

    def test_unattended_without_claim_refuses_before_adapter(self):
        self.manifest["restoration_target"] = self.manifest["baseline"]
        with self.assertRaisesRegex(loop.ExperimentError, "claim_required"):
            loop.run(self.manifest, self.adapter, unattended=True, releases=self.evidence)
        self.assertEqual(self.adapter.events, [])
        with patch.object(loop, "HostAdapter", side_effect=AssertionError("adapter")):
            result = loop.main(["run", "--unattended", "--manifest", "absent.json",
                                "--bindings", "absent-bindings.json"])
        self.assertEqual(result, 1)

    def test_claim_evidence_cannot_enter_release_ledgers(self):
        self.evidence = loop.RELEASES
        with self.assertRaisesRegex(loop.ExperimentError, "private"):
            self.run_claim()
        self.assertEqual(self.adapter.events, [])

    def test_cli_consumes_claim_and_rejects_expiry_before_constructing_adapter(self):
        manifest, claim, bindings = (self.root / (name + ".json") for name in ("manifest", "claim", "bindings"))
        manifest.write_bytes(self.raw)
        atomic_write_json(claim, self.claim)
        atomic_write_json(bindings, self.bindings)
        argv = ["run", "--manifest", str(manifest), "--claim", str(claim),
                "--bindings", str(bindings), "--evidence-dir", str(self.evidence)]
        real_run = loop.run
        def run(*args, **kwargs):
            return real_run(*args, **kwargs, lock_directory=self.locks)
        with patch.object(loop, "HostAdapter", return_value=self.adapter), \
                patch.object(loop, "run", side_effect=run), redirect_stdout(io.StringIO()):
            self.assertEqual(loop.main(argv), 0)
        self.assertEqual(self.adapter.restored_profile, NEXT)
        self.claim["expires_at"] = "2020-01-01T00:00:00Z"
        atomic_write_json(claim, self.claim)
        with patch.object(loop, "HostAdapter", side_effect=AssertionError("adapter")), redirect_stdout(io.StringIO()):
            self.assertEqual(loop.main(argv), 1)

    def test_claim_expiry_limits_dispatch_but_not_cleanup(self):
        now = [0]
        self.claim["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
        original = self.adapter.install
        def install(manifest, timeout):
            self.assertLessEqual(timeout, 10)
            original(manifest, timeout)
            now[0] = 11
        self.adapter.install = install
        directory = self.run_claim(clock=lambda: now[0])
        self.assertEqual(self.adapter.events, ["precondition", "install", "restore"])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")
        self.assertTrue(self.usage(directory)["restoration"]["verified"])

    def test_serving_without_matching_incumbent_and_g10_never_unlocks(self):
        for changes in ({"profile_id": BASELINE}, {"gate": {"gate": "G10", "pass_observed": False}},
                        {"gate": {"gate": "G11", "pass_observed": True}}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                self.evidence, self.locks = Path(tmp) / "trials", Path(tmp) / "locks"
                self.adapter = FakeAdapter()
                original = self.adapter.restore
                self.adapter.restore = lambda manifest, **kwargs: {**original(manifest, **kwargs), **changes}
                directory = self.run_claim()
                self.assertEqual(self.usage(directory)["outcome"], "failed")
                self.assertFalse(self.usage(directory)["restoration"]["verified"])
                self.assertTrue(list(self.locks.glob("*.lock")))

    def test_preconditions_refuse_without_mutation_or_fabricated_restoration(self):
        self.adapter.observation["no_competing_tenant"] = False
        directory = self.run_claim()
        self.assertEqual(self.adapter.events, ["precondition"])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")
        self.assertEqual(self.usage(directory)["gpu_seconds"], 0)
        self.assertFalse(self.usage(directory)["restoration"]["verified"])

    def test_adapter_never_adopts_a_competing_start_after_its_own_child_fails_or_returns(self):
        for fails in (True, False):
            with self.subTest(child_failed=fails):
                adapter = object.__new__(loop.HostAdapter)
                adapter.owned_runs = {}
                adapter.launch_requests = {}
                adapter.owned_commands = {}
                root = self.root / ("failed-start" if fails else "returned-start")
                root.mkdir()
                layout = SimpleNamespace(root=root, run_record=root / "run.json", lock_file=root / "state.lock",
                                         profile=SimpleNamespace(fingerprint="fixture-profile"))
                adapter.layouts = {"candidate": layout}

                def command(*_args, **_kwargs):
                    atomic_write_json(layout.run_record, {
                        "requested_utc": "2026-10-24T00:00:00Z",
                        "profile_fingerprint": "fixture-profile",
                        "experiment_launch_id": "unrelated-start",
                        "wrapper": {"pid": 101, "created": "fixture"},
                        "server": {"pid": 102, "created": "fixture"}})
                    if fails:
                        raise loop.ExperimentError("child_failed")
                    return {"state": "healthy"}

                adapter.command = command
                with patch.object(loop.lifecycle, "running", return_value={}), \
                        patch.object(loop.lifecycle, "stop") as stop:
                    with self.assertRaisesRegex(loop.ExperimentError,
                                                "child_failed" if fails else "start_generation_unverified"):
                        adapter.start("candidate", 120)
                    self.assertNotIn("candidate", adapter.owned_runs)
                    self.assertEqual(adapter.stop("candidate", 120)["state"], "not_owned")
                    stop.assert_not_called()

    def test_adapter_retains_its_exact_partially_started_generation_on_child_failure(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.owned_runs = {}
        adapter.launch_requests = {}
        adapter.owned_commands = {}
        layout = SimpleNamespace(root=self.root, run_record=self.root / "run.json",
                                 lock_file=self.root / "state.lock",
                                 profile=SimpleNamespace(fingerprint="fixture-profile"))
        adapter.layouts = {"candidate": layout}

        def command(*_args, **kwargs):
            atomic_write_json(layout.run_record, {
                "requested_utc": "2026-10-24T00:00:00Z",
                "profile_fingerprint": "fixture-profile",
                "launch_id": "fixture-token",
                "experiment_launch_id": kwargs.get("env", {}).get("OMP_STRATA_EXPERIMENT_LAUNCH"),
                "wrapper": {"pid": 101, "created": "fixture"}, "server": {"pid": 102, "created": "fixture"}})
            raise loop.ExperimentError("child_failed")

        adapter.command = command
        with patch.object(loop.lifecycle, "running", return_value={}), \
                self.assertRaisesRegex(loop.ExperimentError, "child_failed"):
            adapter.start("candidate", 120)
        self.assertEqual(adapter.owned_runs["candidate"]["server"], {"pid": 102, "created": "fixture"})
        self.assertEqual(set(adapter.owned_runs["candidate"]),
                         {"requested_utc", "profile_fingerprint", "wrapper", "server"})

    def test_adapter_restores_bound_root_and_only_stops_started_generations(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.owned_runs = {}
        adapter.launch_requests = {}
        adapter.owned_commands = {}
        events = []
        adapter.layouts = {}
        for arm in ("baseline", "candidate", "restoration_target"):
            root = self.root / arm
            root.mkdir()
            adapter.layouts[arm] = SimpleNamespace(
                root=root, run_record=root / "run.json", lock_file=root / "state.lock",
                profile=SimpleNamespace(fingerprint=self.manifest[arm]["profile_fingerprint"]))
        def command(arm, script, args, timeout, **kwargs):
            events.append((arm, script, args[0]))
            if args[0] == "start":
                atomic_write_json(adapter.layouts[arm].run_record, {
                    "requested_utc": "2026-10-23T00:00:00Z",
                    "profile_fingerprint": adapter.layouts[arm].profile.fingerprint,
                    "runtime_identity_sha256": "a" * 64,
                    "state": "ready",
                    "launch_id": "fixture-token",
                    "experiment_launch_id": kwargs.get("env", {}).get("OMP_STRATA_EXPERIMENT_LAUNCH"),
                    "wrapper": {"pid": 101, "created": "fixture"}, "server": {"pid": 102, "created": "fixture"}})
            return {"gate": "G10", "pass_observed": True, "run_id": "g10-20261024T000000Z-abcdef",
                    "profile_fingerprint": adapter.layouts[arm].profile.fingerprint,
                    "runtime_identity_sha256": "a" * 64}
        adapter.command = command
        with patch.object(loop.lifecycle, "running", return_value={}), \
                patch.object(loop.lifecycle, "stop", return_value={"state": "stopped"}) as stop, \
                patch.object(loop.lifecycle, "status", return_value={"state": "healthy"}):
            # A never-started baseline/candidate is not our process merely because the root is bound.
            adapter.stop("baseline", 120)
            stop.assert_not_called()
            adapter.start("candidate", 120)
            with contextlib.ExitStack() as custody:
                result = adapter.restore(self.manifest, custody=custody)
            self.assertTrue(result["serving"])
            self.assertEqual(result["profile_id"], NEXT)
            target = adapter.layouts["restoration_target"]
            self.assertTrue(target.run_record.with_name("g10.json").exists(),
                            "a private receipt alone cannot bind the installed restoration's G10")
            bound_g10 = json.loads(target.run_record.with_name("g10.json").read_text())
            self.assertEqual(bound_g10["g10_run_id"], result["gate"]["run_id"])
            self.assertEqual(bound_g10["run"], adapter.owned_runs["restoration_target"])
            self.assertEqual(bound_g10["runtime_identity_sha256"], "a" * 64)
            self.assertEqual(stop.call_count, 1)
            self.assertIs(stop.call_args.args[0], adapter.layouts["candidate"])
            self.assertEqual(events, [("candidate", "omp_strata.py", "start"),
                                      ("restoration_target", "omp_strata.py", "start"),
                                      ("restoration_target", "realhost_gates.py", "g10")])
            self.assertNotIn("candidate", adapter.owned_runs)
            # Even a legitimate root restarted by somebody else is not this trial's generation.
            record = adapter.layouts["restoration_target"].run_record
            changed = json.loads(record.read_text())
            changed["server"]["pid"] = 999
            atomic_write_json(record, changed)
            with self.assertRaisesRegex(loop.ExperimentError, "owned_generation_changed"):
                adapter.stop("restoration_target", 120)
            self.assertEqual(stop.call_count, 1)

    def test_restore_revalidates_state_health_and_generation_inside_receipt_lock_and_keeps_custody(self):
        real_lock = loop.lifecycle.FileLock
        for transition in ("stop_after_restore", "stop", "exited", "generation", "unhealthy", "exit_during_status",
                           "generation_during_status"):
            with self.subTest(transition=transition), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                adapter = FakeAdapter()
                adapter.layouts = {}
                adapter.owned_runs = {}
                adapter.restoration_runtime_identity = "a" * 64
                for arm in ("baseline", "candidate", "restoration_target"):
                    layout = loop.Layout(root / arm, loop.load(loop.ROOT / "profiles" / (
                        self.manifest[arm]["profile_id"] + ".json")))
                    adapter.layouts[arm] = layout
                target = adapter.layouts["restoration_target"]
                generation = {"requested_utc": "2026-10-24T00:00:00Z",
                              "profile_fingerprint": target.profile.fingerprint,
                              "wrapper": {"pid": 101, "created": "fixture"},
                              "server": {"pid": 102, "created": "fixture"}}
                atomic_write_json(target.install_record, {"profile_fingerprint": target.profile.fingerprint,
                                                          "runtime_identity_sha256": "a" * 64})
                receipt_lock_active = [False]
                observations = []
                late_stop_refused = []
                hold_at_receipt_unlock = []

                def start_target(arm, timeout):
                    self.assertEqual(arm, "restoration_target")
                    adapter.owned_runs[arm] = copy.deepcopy(generation)
                    atomic_write_json(target.run_record, {**generation, "state": "ready",
                                                          "runtime_identity_sha256": "a" * 64})

                def command(*_args):
                    return {"gate": "G10", "pass_observed": True, "run_id": "g10-20261024T000000Z-abcdef",
                            "profile_fingerprint": target.profile.fingerprint, "runtime_identity_sha256": "a" * 64}

                class InterleavingLock:
                    def __init__(self, path, *, timeout=0):
                        self.lock = real_lock(path, timeout=timeout)

                    def __enter__(self):
                        # A real ordinary stop completes before the receipt writer acquires the same lock.
                        if transition == "stop":
                            with patch.object(loop.lifecycle, "FileLock", real_lock):
                                loop.lifecycle.stop(target, log=lambda _line: None)
                        elif transition in ("exited", "generation"):
                            current = json.loads(target.run_record.read_text())
                            if transition == "exited":
                                current["state"] = "exited"
                                current["exit_code"] = 1
                            else:
                                current["server"] = {"pid": 999, "created": "fixture"}
                            atomic_write_json(target.run_record, current)
                        self.lock.__enter__()
                        receipt_lock_active[0] = True
                        return self

                    def __exit__(self, *args):
                        hold_at_receipt_unlock.append((root / "locks" / (adapter.lock_id + ".lock")).exists())
                        receipt_lock_active[0] = False
                        return self.lock.__exit__(*args)

                def status(_layout):
                    observations.append(receipt_lock_active[0])
                    if not receipt_lock_active[0]:
                        return {"state": "healthy"}
                    with self.assertRaises(loop.lifecycle.LifecycleError):
                        with real_lock(target.lock_file):
                            self.fail("receipt health check did not hold the lifecycle lock")
                    if transition in ("exit_during_status", "generation_during_status"):
                        current = json.loads(target.run_record.read_text())
                        if transition == "exit_during_status":
                            current["state"] = "exited"
                            current["exit_code"] = 1
                        else:
                            current["server"] = {"pid": 999, "created": "fixture"}
                        atomic_write_json(target.run_record, current)
                    return {"state": "degraded" if transition == "unhealthy" else "healthy"}

                def restore(manifest, **kwargs):
                    result = loop.HostAdapter.restore(adapter, manifest, **kwargs)
                    if transition == "stop_after_restore":
                        try:
                            with patch.object(loop.lifecycle, "FileLock", real_lock):
                                loop.lifecycle.stop(target, log=lambda _line: None)
                        except loop.lifecycle.LifecycleError:
                            late_stop_refused.append(True)
                    return result
                adapter.restore = restore
                adapter.command = command
                # Only restoration uses the real host-adapter boundary; trial work stays host-free.
                original_start = adapter.start
                def start(arm, timeout):
                    return start_target(arm, timeout) if arm == "restoration_target" else original_start(arm, timeout)
                adapter.start = start
                with patch.object(loop.lifecycle, "FileLock", InterleavingLock), \
                        patch.object(loop.lifecycle, "status", side_effect=status), \
                        patch.object(loop.lifecycle.procs, "matches", return_value=None), \
                        patch.object(loop.lifecycle, "port_in_use", return_value=False):
                    directory = loop.run(self.manifest, adapter, claim=self.claim, bindings=self.bindings,
                                         manifest_bytes=self.raw, releases=root / "trials", lock_directory=root / "locks")
                if transition == "stop_after_restore":
                    self.assertEqual(late_stop_refused, [True],
                                     "the receipt lock must remain held through evidence and physical custody release")
                    self.assertEqual(json.loads(target.run_record.read_text())["state"], "ready")
                    self.assertIs(json.loads((directory / "restoration.json").read_text())["serving"], True)
                    self.assertFalse((root / "locks" / (adapter.lock_id + ".lock")).exists())
                    self.assertEqual(hold_at_receipt_unlock, [False])
                    continue
                self.assertEqual(json.loads((directory / "measurements.json").read_text())["status"],
                                 "restoration_failed")
                self.assertIs(json.loads((directory / "restoration.json").read_text())["serving"], False)
                self.assertFalse(target.run_record.with_name("g10.json").exists())
                lock = root / "locks" / (adapter.lock_id + ".lock")
                self.assertIs(json.loads(lock.read_text())["persistent_hold"], True)
                self.assertIn("restoration_target", adapter.owned_runs)
                self.assertTrue(all(observations), "restoration health must never be cached before the receipt lock")
                if transition in ("stop", "exited"):
                    current = json.loads(target.run_record.read_text())
                    self.assertEqual({key: current[key] for key in generation}, generation)
                    self.assertEqual(current["state"], "stopped" if transition == "stop" else "exited")

    def test_adapter_refuses_preexisting_runtime_without_claiming_or_stopping_it(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.owned_runs = {}
        adapter.launch_requests = {}
        adapter.owned_commands = {}
        adapter.layouts = {"baseline": SimpleNamespace()}
        with patch.object(loop.lifecycle, "running", return_value={"server": object()}), \
                patch.object(loop.lifecycle, "stop", side_effect=AssertionError("foreign stop")):
            with self.assertRaisesRegex(loop.ExperimentError, "root_already_running"):
                adapter.start("baseline", 120)
            self.assertEqual(adapter.stop("baseline", 120)["state"], "not_owned")
            self.assertEqual(adapter.owned_runs, {})

    def test_warm_handoff_adopts_only_the_bound_generation_under_the_root_lock(self):
        adapter = object.__new__(loop.HostAdapter)
        root = self.root / "warm"
        root.mkdir()
        profile = self.manifest["restoration_target"]
        layout = SimpleNamespace(root=root, install_record=root / "install.json", run_record=root / "run.json",
                                 lock_file=root / "lifecycle.lock",
                                 profile=SimpleNamespace(id=profile["profile_id"], fingerprint=profile["profile_fingerprint"]))
        generation = {"requested_utc": "2026-10-24T00:00:00Z", "profile_fingerprint": profile["profile_fingerprint"],
                      "wrapper": {"pid": 101, "created": "fixture"}, "server": {"pid": 102, "created": "fixture"}}
        atomic_write_json(layout.install_record, {"profile_fingerprint": profile["profile_fingerprint"],
                                                  "runtime_identity_sha256": "b" * 64})
        atomic_write_json(layout.run_record, generation)
        adapter.layouts = {"restoration_target": layout}
        adapter.owned_runs = {}
        adapter.launch_requests = {}
        adapter.owned_commands = {}
        adapter.guard = lambda arm, timeout: None
        def stopped(target, **kwargs):
            self.assertTrue(layout.lock_file.exists())
            self.assertIs(target, layout)
            self.assertIs(kwargs["locked"], True)
            return {"state": "stopped"}
        with patch.object(loop.lifecycle, "stop", side_effect=stopped) as stop:
            adapter.warm_incumbent = None
            with self.assertRaisesRegex(loop.ExperimentError, "binding_required"):
                adapter.quiesce(self.manifest, 120)
            adapter.warm_incumbent = {"runtime_identity_sha256": "b" * 64, "run": copy.deepcopy(generation)}
            adapter.warm_incumbent["run"]["server"]["pid"] = 999
            with self.assertRaisesRegex(loop.ExperimentError, "identity_mismatch"):
                adapter.quiesce(self.manifest, 120)
            self.assertEqual(adapter.owned_runs, {})
            stop.assert_not_called()
            adapter.warm_incumbent["run"] = generation
            receipt = adapter.quiesce(self.manifest, 120)
            self.assertEqual(receipt["mode"], "loop_quiesced_warm")
            self.assertEqual(receipt["runtime_identity_sha256"], "b" * 64)
            self.assertEqual(stop.call_count, 1)
            self.assertEqual(adapter.owned_runs, {})

    def test_candidate_cannot_alias_the_claim_incumbent_root(self):
        roots = {arm: str(self.root.resolve() / arm) for arm in ("baseline", "candidate")}
        self.bindings["roots"] = {**roots, "restoration_target": roots["candidate"]}
        with patch.object(loop.sys, "platform", "win32"), \
                self.assertRaisesRegex(loop.ExperimentError, "incumbent_root_not_isolated"):
            loop.HostAdapter(self.manifest, self.bindings, claim=self.claim)

    def test_evaluator_cannot_reclaim_failed_restoration_mutex_after_worker_exit(self):
        self.adapter.restore_serving = False
        self.run_claim()
        path = self.locks / (self.adapter.lock_id + ".lock")
        original = path.read_bytes()
        with patch.object(eval_taskset.os, "kill", side_effect=ProcessLookupError):
            self.assertFalse(eval_taskset.take_pid_file(path))
        self.assertEqual(path.read_bytes(), original)

    def test_evaluator_keeps_ambiguous_owners_but_reclaims_ordinary_dead_workers(self):
        path = self.root / "ordinary.lock"
        for raw in ('', '{"pid":', '[]', '{"pid":"invalid"}'):
            with self.subTest(raw=raw):
                path.write_text(raw)
                with patch.object(eval_taskset.os, "kill", side_effect=AssertionError("ambiguous PID")):
                    self.assertFalse(eval_taskset.take_pid_file(path))
                self.assertEqual(path.read_text(), raw)
        path.write_text('{"pid":12345}')
        with patch.object(eval_taskset.os, "kill", side_effect=ProcessLookupError):
            self.assertTrue(eval_taskset.take_pid_file(path))


if __name__ == "__main__":
    unittest.main()
