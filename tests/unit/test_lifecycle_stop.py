"""Stop selection, evidence and ordering in accounted host-free process worlds."""
import contextlib
import itertools
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from omp_strata import cli, lifecycle, procs
from omp_strata.common import atomic_write_json, read_json
from omp_strata.layout import Layout
from omp_strata.profile import Profile
from tests.candidate import PROFILE
from tests.unit.test_lifecycle import gpu_fact
from tests.unit.test_profile import multi_gpu_data, single_gpu_data
from tests.unit.test_lifecycle_evidence import EvidenceFixture, complete_table, native_matches


TOKEN = "a" * 32


class UnrecordedOwnershipTests(EvidenceFixture):
    def stop_result(self):
        try:
            return lifecycle.stop(self.layout, log=None, locked=True), None
        except lifecycle.LifecycleError as exc:
            return None, str(exc)

    def test_runtime_alias_does_not_own_another_roots_process(self):
        other_runtime = self.layout.root / "root-b" / "runtime" / "strata"
        other_runtime.mkdir(parents=True)
        self.layout.strata.parent.mkdir(parents=True)
        self.layout.strata.symlink_to(other_runtime, target_is_directory=True)
        foreign = procs.ProcInfo(20, 1, "20", str(other_runtime / "engine"))
        self.world = {20: foreign}
        before = lifecycle.verdict(self.layout)
        with patch.object(procs, "terminate", side_effect=self.terminate):
            result, failure = self.stop_result()
        self.assertEqual([], self.ended)
        self.assertIsNone(result)
        self.assertIn("stop does not own", failure)
        self.assertIn("by hand", failure)
        self.assertEqual(1, failure.count("pid 20"))
        self.assertEqual({20: foreign}, self.world)
        self.assertEqual(before.live, lifecycle.verdict(self.layout).live)
        self.assertFalse(before.idle or lifecycle.verdict(self.layout).quiescent)
        self.assertFalse(self.layout.run_record.exists())

    def test_live_foreign_parent_is_not_an_orphan_or_an_owned_parent(self):
        cases = 0
        for windows, parent_kind in itertools.product((False, True),
                ("foreign", "orphan", "missing", "owned", "newer", "system")):
            with self.subTest(windows=windows, parent=parent_kind), \
                    patch.object(lifecycle, "WINDOWS", windows), patch.object(procs, "WINDOWS", windows):
                self.ended.clear()
                self.layout.run_record.unlink(missing_ok=True)
                ppid = 1 if parent_kind == "orphan" else (4 if windows else 1) if parent_kind == "system" else 10
                child = procs.ProcInfo(20, ppid, "20", str(self.layout.strata / "engine"))
                parent = procs.ProcInfo(ppid, 0, "30" if parent_kind == "newer" else "10", "/outside/program")
                self.world = {20: child}
                if parent_kind not in ("orphan", "missing"):
                    self.world[ppid] = parent
                if parent_kind == "owned":
                    atomic_write_json(self.layout.run_record, {"state": "ready", "server": parent.as_dict()})
                before = lifecycle.verdict(self.layout)
                with patch.object(procs, "terminate", side_effect=self.terminate):
                    result, failure = self.stop_result()
                expected = [] if parent_kind == "foreign" else [20, 10] if parent_kind == "owned" else [20]
                self.assertEqual(expected, [proc.pid for proc in self.ended])
                if parent_kind == "foreign":
                    self.assertIsNone(result)
                    self.assertIn("stop does not own", failure)
                    self.assertIn("by hand", failure)
                    self.assertEqual(1, failure.count("pid 20"))
                    self.assertEqual(before.live, lifecycle.verdict(self.layout).live)
                    self.assertNotIn(lifecycle.status(self.layout)["state"], lifecycle.IDLE_STATES)
                    with patch.object(lifecycle, "FileLock", return_value=contextlib.nullcontext()), \
                            self.assertRaisesRegex(lifecycle.LifecycleError, "integration-owned processes"):
                        lifecycle.start(self.layout, tool_argv=[], log=None)
                else:
                    self.assertIsNone(failure)
                    self.assertEqual("stopped", result["state"])
                self.assertEqual(parent_kind == "owned", self.layout.run_record.exists())
                cases += 1
        self.assertEqual(12, cases)

    def test_unowned_runtime_subtree_is_left_but_recorded_cleanup_proceeds(self):
        self.world = {10: procs.ProcInfo(10, 1, "10", "/outside/program"),
                      30: procs.ProcInfo(30, 10, "30", "/outside/server")}
        self.world.update({pid: procs.ProcInfo(pid, parent, str(pid), str(self.layout.strata / f"p{pid}"))
                           for pid, parent in ((20, 10), (21, 20), (22, 21))})
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": self.world[30].as_dict(),
                                                   "tree_verified_empty": TOKEN})
        with patch.object(procs, "terminate", side_effect=self.terminate):
            result, failure = self.stop_result()
        self.assertEqual([30], [proc.pid for proc in self.ended])
        self.assertIsNone(result)
        self.assertEqual({10, 20, 21, 22}, set(self.world))
        self.assertEqual({20, 21, 22}, {proc.pid for proc in lifecycle.verdict(self.layout).live.values()})
        for pid in (20, 21, 22):
            self.assertEqual(1, failure.count(f"pid {pid}"))
        self.assertIn("stop does not own", failure)
        self.assertIn("by hand", failure)
        saved = read_json(self.layout.run_record)
        self.assertEqual("stop_incomplete", saved["state"])
        self.assertNotIn("tree_verified_empty", saved)

    def test_alias_of_root_itself_keeps_its_own_runtime_eligible(self):
        root = self.layout.root
        alias = root / "root-alias"
        alias.symlink_to(root, target_is_directory=True)
        self.world = {20: self.process()}
        self.layout = Layout(alias, self.layout.profile)
        with patch.object(procs, "terminate", side_effect=self.terminate):
            result, failure = self.stop_result()
        self.assertIsNone(failure)
        self.assertEqual("stopped", result["state"])
        self.assertEqual([20], [proc.pid for proc in self.ended])
        self.assertFalse(self.layout.run_record.exists())


class UnvouchedFallbackOrderTests(EvidenceFixture):
    def test_reciprocal_parent_numbers_do_not_skip_verified_cleanup(self):
        cases = 0
        for first, second, expected in (
                ("20", "30", [30, 20]),
                ("starttime:20", "starttime:30", [30, 20]),
                ("20", "20", [20, 30]),
                ("20", "starttime:30", [20, 30]),
                ("Sat Jan  1 00:00:00 2022", "Sat Jan  1 00:00:01 2022", [20, 30])):
            with self.subTest(first=first, second=second):
                self.ended.clear()
                self.world = {20: procs.ProcInfo(20, 30, first, "/outside/server"),
                              30: procs.ProcInfo(30, 20, second, "/outside/wrapper")}
                atomic_write_json(self.layout.run_record, {"state": "ready", "server": self.world[20].as_dict(),
                                                           "wrapper": self.world[30].as_dict()})
                with patch.object(lifecycle, "process_table", side_effect=procs.TableUnavailable("fixture census unavailable")), \
                        patch.object(procs, "matches", side_effect=lambda record: native_matches(
                            self.world.get(record["pid"]), record)), \
                        patch.object(procs, "terminate", side_effect=self.terminate):
                    with self.assertRaises(lifecycle.LifecycleError) as failure:
                        lifecycle.stop(self.layout, log=None, locked=True)
                self.assertEqual(expected, [proc.pid for proc in self.ended])
                self.assertEqual({}, self.world)
                self.assertIn("census unavailable", str(failure.exception))
                self.assertNotIn("cycle", str(failure.exception))
                saved = read_json(self.layout.run_record)
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)
                cases += 1
        self.assertEqual(5, cases)


class UnidentifiedRoleStopWalk(EvidenceFixture):
    def test_unknown_recorded_role_never_completes_stop(self):
        import itertools
        cases = 0
        for role, state in itertools.product(("wrapper", "server", "engine", "server_tree[0]", "launcher"),
                (None, "launching", "starting", "ready", "exited", "stopped", "stop_incomplete")):
            with self.subTest(role=role, state=state):
                run = dict(self.install, state=state)
                process = self.process()
                if role == "server_tree[0]":
                    run["server_tree"] = [process.as_dict()]
                else:
                    run[role] = process.as_dict()
                atomic_write_json(self.layout.run_record, run)
                with patch.object(lifecycle, "process_table", return_value=complete_table(unidentified={20})), \
                        patch.object(procs, "matches", return_value=None), patch.object(procs, "terminate") as terminate:
                    with self.assertRaisesRegex(lifecycle.LifecycleError, "cannot prove absence or PID reuse"):
                        lifecycle.stop(self.layout, log=lambda line: None, locked=True)
                    terminate.assert_not_called()
                saved = read_json(self.layout.run_record)
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)
                cases += 1
        self.assertEqual(35, cases)


class UncertainCleanupTests(EvidenceFixture):
    def test_unknown_roles_retain_identified_cleanup(self):
        cases = 0
        for role in ("wrapper", "server", "engine", "server_tree[0]", "launcher"):
            with self.subTest(role=role):
                self.ended.clear()
                unknown = self.process(owned=False).as_dict()
                run = {"state": "launching" if role == "launcher" else "ready"}
                run["server_tree" if role == "server_tree[0]" else role] = [unknown] if role == "server_tree[0]" else unknown
                self.world = {77: self.process(pid=77)}
                atomic_write_json(self.layout.run_record, run)
                with patch.object(lifecycle, "process_table", side_effect=lambda: complete_table(self.world, unidentified={20})), \
                        patch.object(procs, "matches", return_value=None), \
                        patch.object(procs, "terminate", side_effect=self.terminate):
                    with self.assertRaisesRegex(lifecycle.LifecycleError, "cannot prove absence or PID reuse") as failure:
                        lifecycle.stop(self.layout, log=None, locked=True)
                self.assertIn(role, str(failure.exception))
                self.assertIn("pid 20", str(failure.exception))
                self.assertEqual([77], [p.pid for p in self.ended])
                self.assertEqual({}, self.world)
                saved = read_json(self.layout.run_record)
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)
                cases += 1
        self.assertEqual(5, cases)

    def test_malformed_roles_never_reach_individual_fallback(self):
        good = self.process(pid=77, owned=False)
        bads = ({}, "bad identity", {"pid": "20", "created": "20", "exe": "/foreign/engine"},
                {"pid": 20, "created": "20"})
        cases = 0
        for role, bad in zip(("wrapper", "server", "engine", "server_tree[0]"), bads):
            with self.subTest(role=role):
                self.ended.clear()
                self.world = {77: good}
                run = {"state": "ready", "server" if role != "server" else "wrapper": good.as_dict()}
                run["server_tree" if role == "server_tree[0]" else role] = [bad] if role == "server_tree[0]" else bad
                atomic_write_json(self.layout.run_record, run)
                before = self.layout.run_record.read_bytes()
                def matches(record):
                    self.assertTrue(procs.valid_identity(record), "malformed role reached native reader")
                    return native_matches(self.world.get(record["pid"]), record)
                with patch.object(lifecycle, "process_table", side_effect=procs.TableUnavailable("fixture unavailable")), \
                        patch.object(procs, "matches", side_effect=matches), \
                        patch.object(procs, "terminate", side_effect=self.terminate):
                    with self.assertRaises(lifecycle.LifecycleError):
                        lifecycle.stop(self.layout, log=None, locked=True)
                self.assertEqual([77], [p.pid for p in self.ended])
                self.assertEqual(before, self.layout.run_record.read_bytes())
                cases += 1
        self.assertEqual(4, cases)

    def test_last_owner_cleanup_activates_uncertain_launcher(self):
        self.world = {77: self.process(pid=77)}
        atomic_write_json(self.layout.run_record, {"state": "ready", "launcher": self.process(owned=False).as_dict()})
        def end(proc, timeout):
            result = self.terminate(proc, timeout)
            if proc.pid == 77:
                self.world[78] = self.process(pid=78)
            return result
        with patch.object(lifecycle, "process_table", side_effect=lambda: complete_table(self.world, unidentified={20})), \
                patch.object(procs, "terminate", side_effect=end):
            self.assertEqual("orphans", lifecycle.verdict(self.layout).row)
            with self.assertRaisesRegex(lifecycle.LifecycleError, "launcher pid 20"):
                lifecycle.stop(self.layout, log=None, locked=True)
        self.assertEqual([77, 78], [p.pid for p in self.ended])
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])


class StopOrderWalk(EvidenceFixture):
    def test_outside_intermediary_does_not_grant_ownership_or_order(self):
        ancestor = self.process(pid=50)
        outsider = procs.ProcInfo(51, 50, "51", "/outside/helper")
        server = procs.ProcInfo(20, 51, "52", "/outside/server")
        self.world = {50: ancestor, 51: outsider, 20: server}
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": server.as_dict()})
        with patch.object(procs, "terminate", side_effect=self.terminate):
            result = lifecycle.stop(self.layout, log=None, locked=True)
            final = lifecycle.verdict(self.layout)
        self.assertEqual([50, 20], [p.pid for p in self.ended])
        self.assertEqual({51: outsider}, self.world)
        self.assertEqual(("stopped", {}), (result["state"], final.live))

    def test_entire_vouched_tree_precedes_its_ancestors(self):
        cases = 0
        for reverse, uncertain, tree_reverse in itertools.product((False, True), repeat=3):
            with self.subTest(reverse=reverse, uncertain=uncertain, tree_reverse=tree_reverse):
                self.ended.clear()
                edges = {10: 1, 50: 0 if uncertain else 10, 20: 50, 30: 20, 40: 30, 60: 20, 70: 1}
                rows = [procs.ProcInfo(pid, parent, str(index + 1), str(self.layout.strata / f"p{pid}"))
                        for index, (pid, parent) in enumerate(edges.items())]
                self.world = {p.pid: p for p in (reversed(rows) if reverse else rows)}
                tree = [self.world[30].as_dict(), self.world[60].as_dict()]
                run = {"state": "ready", "wrapper": self.world[10].as_dict(), "server": self.world[20].as_dict(),
                       "engine": self.world[40].as_dict(), "server_tree": list(reversed(tree)) if tree_reverse else tree}
                atomic_write_json(self.layout.run_record, run)
                def end(proc, timeout):
                    self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
                    return self.terminate(proc, timeout)
                with patch.object(procs, "terminate", side_effect=end):
                    result = lifecycle.stop(self.layout, log=None, locked=True)
                self.assertEqual("stopped", result["state"])
                self.assertEqual(set(edges), {p.pid for p in self.ended})
                positions = {p.pid: index for index, p in enumerate(self.ended)}
                for child in edges:
                    parent = edges[child]
                    while parent in edges:
                        self.assertLess(positions[child], positions[parent], (child, parent, positions))
                        parent = edges[parent]
                self.assertEqual({}, self.world)
                cases += 1
        self.assertEqual(8, cases)


class JobCleanupTests(EvidenceFixture):
    def prepare(self):
        self.world[20] = self.process()
        atomic_write_json(self.layout.run_record, dict(self.install, state="ready", tree_token=TOKEN,
                                                       tree_verified_empty=TOKEN))
        self.enterContext(patch.object(lifecycle, "WINDOWS", True))
        self.enterContext(patch.object(procs, "terminate", side_effect=self.terminate))

    def test_identity_reused_after_job_termination_is_not_a_cleanup_failure(self):
        self.prepare()

        def end_job(timeout):
            self.world[20] = self.process(created="120", owned=False)

        job = SimpleNamespace(token=TOKEN, stop=end_job, close=lambda: None)
        with patch.object(lifecycle, "ProcessJob", return_value=job) as factory, \
                patch.object(procs, "terminate", side_effect=self.terminate) as terminate:
            factory.scan.return_value = {}
            result = lifecycle.stop(self.layout, log=lambda line: None, locked=True)
            terminate.assert_not_called()
        self.assertEqual("stopped", result["state"])
        self.assertEqual([], self.ended)
        self.assertEqual(TOKEN, read_json(self.layout.run_record)["tree_verified_empty"])

    def test_job_failure_preserves_cleanup_but_revokes_previous_empty_proof(self):
        for error in (lifecycle.LifecycleError("job denied"), subprocess.TimeoutExpired("powershell", 1)):
            with self.subTest(error=type(error).__name__):
                self.prepare()
                job = SimpleNamespace(token=TOKEN, stop=lambda timeout: None, close=lambda: None)
                with patch.object(job, "stop", side_effect=error), patch.object(lifecycle, "ProcessJob", return_value=job) as factory:
                    factory.scan.return_value = {}
                    with self.assertRaises(lifecycle.LifecycleError):
                        lifecycle.stop(self.layout, log=lambda line: None, locked=True)
                self.assertEqual({}, self.world)
                saved = read_json(self.layout.run_record)
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)


class StopBoundaryWalk(EvidenceFixture):
    prepare = JobCleanupTests.prepare
    def test_job_outcomes_and_identity_reuse_preserve_completion_proof(self):
        import itertools
        import sys
        import time
        started = time.monotonic()
        # Each failure boundary the stop loop owns; native job internals have their own tests.
        outcomes = ("present", "missing", "open-denied", "open-os", "token-mismatch",
                    "stop-denied", "stop-os", "stop-timeout", "stop-value", "close-denied", "stop-and-close",
                    "scan-denied", "scan-os", "scan-timeout", "scan-value")
        schedules = ((True, True, True), (False, True, True), (True, False, True), (True, True, False))
        cases = 0
        unidentified = set()
        self.enterContext(patch.object(procs, "matches", side_effect=lambda rec:
            self.world.get(rec["pid"]) if rec and rec["pid"] in self.world and rec["pid"] not in unidentified
            and native_matches(self.world[rec["pid"]], rec) is not None else None))
        for outcome, reuse, schedule in itertools.product(outcomes, ("same", "exit", "foreign", "owned", "unidentified"), schedules):
            with self.subTest(outcome=outcome, reuse=reuse, schedule=schedule):
                self.prepare()
                self.ended.clear()
                unidentified.clear()
                original = self.world[20]
                run = read_json(self.layout.run_record)
                run["server"] = original.as_dict()
                atomic_write_json(self.layout.run_record, run)
                reads = []
                final_phase = False

                def census():
                    if len(reads) == 1:
                        if reuse == "exit":
                            self.world.clear()
                        elif reuse == "unidentified":
                            unidentified.add(20)
                        elif reuse != "same":
                            self.world[20] = self.process(created="120", owned=reuse == "owned")
                    available = schedule[2] if final_phase else schedule[0] if not reads else schedule[1] if len(reads) == 1 else True
                    reads.append((available, dict(self.world)))
                    if not available:
                        raise procs.TableUnavailable("model census unavailable")
                    return complete_table({pid: proc for pid, proc in self.world.items() if pid not in unidentified},
                                          unidentified=unidentified)

                def end_job(timeout):
                    errors = {"stop-denied": lifecycle.LifecycleError("stop denied"),
                              "stop-os": OSError("stop os error"),
                              "stop-timeout": subprocess.TimeoutExpired("job helper", 1),
                              "stop-value": ValueError("stop parse error"),
                              "stop-and-close": lifecycle.LifecycleError("stop denied")}
                    if outcome in errors:
                        raise errors[outcome]

                def terminate_known(proc, timeout):
                    if proc.pid in unidentified:
                        raise PermissionError("native identity unreadable")
                    return self.terminate(proc, timeout)

                def close():
                    if outcome in ("close-denied", "stop-and-close"):
                        raise lifecycle.LifecycleError("close denied")

                job = SimpleNamespace(token="b" * 32 if outcome == "token-mismatch" else TOKEN,
                                      stop=end_job, close=close)
                with patch.object(lifecycle, "process_table", side_effect=census), \
                        patch.object(procs, "terminate", side_effect=terminate_known), \
                        patch.object(lifecycle, "ProcessJob", return_value=job) as factory:
                    if outcome == "missing":
                        factory.side_effect = lifecycle.MissingProcessJob("missing")
                    elif outcome == "open-denied":
                        factory.side_effect = lifecycle.LifecycleError("open denied")
                    elif outcome == "open-os":
                        factory.side_effect = OSError("open os error")
                    scan_errors = {"scan-denied": lifecycle.LifecycleError("scan denied"),
                                   "scan-os": OSError("scan os error"),
                                   "scan-timeout": subprocess.TimeoutExpired("job helper", 1),
                                   "scan-value": ValueError("scan parse error")}
                    def scan(*args, **kwargs):
                        nonlocal final_phase
                        final_phase = True
                        if outcome in scan_errors:
                            raise scan_errors[outcome]
                        return {}
                    factory.scan.side_effect = scan
                    result, failure = None, None
                    try:
                        result = lifecycle.stop(self.layout, log=lambda line: None, locked=True)
                    except lifecycle.LifecycleError as exc:
                        failure = exc
                saved = read_json(self.layout.run_record)
                self.assertFalse(any(p.exe.startswith(str(self.layout.strata) + "/") for pid, p in self.world.items()
                                     if pid not in unidentified), "available census cleanup was skipped")
                expected_success = outcome in ("present", "missing") and all(schedule) and not unidentified
                self.assertEqual(expected_success, result is not None, str(failure))
                self.assertEqual(not expected_success, failure is not None)
                self.assertFalse(any(p == original for p in self.ended) and reuse != "same")
                self.assertFalse(any(p.exe == "/foreign/engine" for p in self.ended))
                if result:
                    self.assertTrue(reads, "stopped without reading a census")
                    self.assertTrue(reads[-1][0])
                    self.assertFalse(any(p.exe.startswith(str(self.layout.strata) + "/") for p in reads[-1][1].values()))
                    self.assertNotEqual(original, reads[-1][1].get(20))
                    self.assertEqual(TOKEN, saved["tree_verified_empty"])
                else:
                    self.assertEqual("stop_incomplete", saved["state"])
                    self.assertNotIn("tree_verified_empty", saved)
                    if outcome == "stop-and-close":
                        self.assertIn("stop denied", str(failure))
                        self.assertIn("close denied", str(failure))
                cases += 1
        self.assertEqual(300, cases)
        print(f"\nstop boundary walk: {cases} cases in {time.monotonic() - started:.2f} s", file=sys.stderr)


class JobHelperErrorTests(EvidenceFixture):
    def test_helper_errors_use_lifecycle_error_for_stop_and_idle_generation(self):
        self.layout.profile.data["server"]["stop_timeout_s"] = 1
        self.install["profile_fingerprint"] = self.layout.profile.fingerprint
        atomic_write_json(self.layout.install_record, self.install)
        errors = (OSError("helper unavailable"), subprocess.TimeoutExpired("powershell", 1),
                  subprocess.CalledProcessError(1, "powershell"),
                  UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"), "invalid-json")
        cases = 0
        for error in errors:
            for consumer in ("closed-job", "stop", "idle-generation"):
                with self.subTest(error=type(error).__name__, consumer=consumer):
                    cases += 1
                    atomic_write_json(self.layout.run_record, dict(self.install, state="ready" if consumer == "stop" else "stopped", tree_token=TOKEN,
                                                                   tree_verified_empty=TOKEN))
                    closed = object.__new__(lifecycle.ProcessJob)
                    closed.token, closed.handle, closed.verified_empty, closed.observed = TOKEN, None, True, {}
                    with patch.object(lifecycle, "WINDOWS", True), patch.object(lifecycle.subprocess, "run") as helper:
                        if isinstance(error, Exception):
                            helper.side_effect = error
                        else:
                            helper.return_value = subprocess.CompletedProcess(["powershell"], 0, "{")
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "CIM enumeration unavailable"):
                            if consumer == "closed-job":
                                closed.stop(timeout=1)
                            elif consumer == "stop":
                                lifecycle.stop(self.layout, log=lambda line: None, locked=True, job=closed)
                            else:
                                lifecycle.idle_generation(self.layout, timeout=1)
                        helper.assert_called_once()
        self.assertEqual(15, cases)

    def test_reuse_during_an_earlier_rank_is_not_signalled_or_counted_as_failure(self):
        self.world.update({20: self.process(), 21: self.process(pid=21)})
        atomic_write_json(self.layout.run_record, dict(self.install, state="ready"))

        def end(proc, timeout):
            result = self.terminate(proc, timeout)
            if proc.pid == 20:
                self.world[21] = self.process(pid=21, created="120", owned=False)
            return result

        with patch.object(procs, "terminate", side_effect=end):
            result = lifecycle.stop(self.layout, log=lambda line: None, locked=True)
        self.assertEqual("stopped", result["state"])
        self.assertEqual([20], [p.pid for p in self.ended])
        self.assertEqual("/foreign/engine", self.world[21].exe)


class RecheckOutcomeWalk(EvidenceFixture):
    def test_failed_termination_dismisses_only_proved_absence_or_reuse(self):
        import itertools
        cases = 0
        for effect, outcome in itertools.product(("false", "denied"), ("same", "another", "absent", "unknown", "unavailable")):
            with self.subTest(effect=effect, outcome=outcome):
                original = self.process()
                self.world = {20: original}
                atomic_write_json(self.layout.run_record, dict(self.install, state="ready", server=original.as_dict()))
                changed = False
                checked = False

                def census():
                    nonlocal checked
                    if changed and not checked:
                        checked = True
                        if outcome == "unknown":
                            return complete_table(unidentified={20})
                        if outcome == "unavailable":
                            raise procs.TableUnavailable("recheck unavailable")
                    return complete_table(self.world)

                def end(proc, timeout):
                    nonlocal changed
                    changed = True
                    if outcome == "another":
                        self.world[20] = self.process(created="120", owned=False)
                    elif outcome != "same":
                        self.world.clear()
                    if effect == "denied":
                        raise PermissionError("native identity check refused")
                    return False

                with patch.object(lifecycle, "process_table", side_effect=census), \
                        patch.object(procs, "terminate", side_effect=end), \
                        patch.object(procs, "matches", side_effect=AssertionError("single-process read cannot prove table absence")):
                    if outcome in ("another", "absent"):
                        self.assertEqual("stopped", lifecycle.stop(self.layout, log=lambda line: None, locked=True)["state"])
                    else:
                        message = "did not exit" if effect == "false" else "native identity check refused"
                        with self.assertRaisesRegex(lifecycle.LifecycleError, message):
                            lifecycle.stop(self.layout, log=lambda line: None, locked=True)
                        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
                self.assertTrue(checked)
                cases += 1
        self.assertEqual(10, cases)


class BaseStopOrderWalk(EvidenceFixture):
    @staticmethod
    def base_order(run, world):
        # 4dc46740 stop: server tree, wrapper tree, prepend recorded orphans, deduplicate PID.
        def descendants(root):
            found, frontier, seen = [], [root], {root.pid}
            while frontier:
                following = []
                for parent in frontier:
                    for child in world.values():
                        if child.ppid == parent.pid and child.pid not in seen:
                            seen.add(child.pid)
                            found.append(child)
                            following.append(child)
                frontier = following
            return list(reversed(found))

        targets = []
        for role in ("server", "wrapper"):
            record = run.get(role)
            root = world.get(record["pid"]) if record else None
            if root is not None:
                targets.extend(descendants(root))
                targets.append(root)
        for record in [run.get("engine"), *run.get("server_tree", [])]:
            orphan = world.get(record["pid"]) if record else None
            if orphan is not None and all(orphan.pid != target.pid for target in targets):
                targets.insert(0, orphan)
        return list({proc.pid: proc for proc in targets}.values())

    def test_complete_base_selection_keeps_its_signal_sequence(self):
        topologies = (
            ("server", {20: 1}, {"server": 20}),
            ("chain", {10: 1, 20: 10, 30: 20, 40: 30},
             {"wrapper": 10, "server": 20, "engine": 40, "server_tree": [30]}),
            ("orphans-and-server-child", {10: 1, 20: 1, 30: 20, 40: 1, 50: 1},
             {"wrapper": 10, "server": 20, "engine": 40, "server_tree": [50]}),
            ("separate-subtrees", {10: 1, 11: 10, 20: 1, 21: 20}, {"wrapper": 10, "server": 20}),
            ("branching-recorded-descendants", {10: 1, 11: 10, 20: 1, 30: 20, 31: 30, 40: 20, 41: 40},
             {"wrapper": 10, "server": 20, "engine": 40, "server_tree": [31, 41]}),
        )
        cases = 0
        for (name, edges, roles), reverse, record_reverse, state in itertools.product(
                topologies, (False, True), (False, True), ("ready", "stopped")):
            with self.subTest(topology=name, reverse=reverse, record_reverse=record_reverse, state=state):
                self.ended.clear()
                rows = [procs.ProcInfo(pid, parent, str(pid), f"/outside/p{pid}") for pid, parent in edges.items()]
                self.world = {proc.pid: proc for proc in (reversed(rows) if reverse else rows)}
                roles = dict(roles)
                if record_reverse and "engine" in roles:
                    engine, *tree = [roles["engine"], *roles["server_tree"]][::-1]
                    roles.update(engine=engine, server_tree=tree)
                run = {"state": state, **{role: [self.world[pid].as_dict() for pid in value]
                       if role == "server_tree" else self.world[value].as_dict() for role, value in roles.items()}}
                expected = self.base_order(run, self.world)
                self.assertEqual(set(edges), {proc.pid for proc in expected}, "base selection must be complete")
                atomic_write_json(self.layout.run_record, run)
                with patch.object(procs, "terminate", side_effect=self.terminate):
                    result = lifecycle.stop(self.layout, log=None, locked=True)
                self.assertEqual(expected, self.ended)
                self.assertEqual(("stopped", {}), (result["state"], self.world))
                cases += 1
        self.assertEqual(40, cases)


class NativeExitStopTests(EvidenceFixture):
    def test_lookup_error_rechecks_and_continues_to_the_other_root(self):
        cases = 0
        for remains in (False, True):
            with self.subTest(remains=remains):
                self.ended.clear()
                self.world = {20: self.process(), 30: self.process(pid=30)}
                atomic_write_json(self.layout.run_record, {"state": "ready", "server": self.world[20].as_dict(),
                                                           "wrapper": self.world[30].as_dict()})
                events = []
                def census():
                    events.append(("read", tuple(self.world)))
                    return complete_table(self.world)
                def end(proc, timeout):
                    events.append(("attempt", proc.pid))
                    if proc.pid == 20:
                        if not remains:
                            self.world.pop(20)
                        raise ProcessLookupError("server disappeared during signal")
                    return self.terminate(proc, timeout)
                with patch.object(lifecycle, "process_table", side_effect=census), \
                        patch.object(procs, "terminate", side_effect=end):
                    if remains:
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "server disappeared during signal"):
                            lifecycle.stop(self.layout, log=None, locked=True)
                    else:
                        self.assertEqual("stopped", lifecycle.stop(self.layout, log=None, locked=True)["state"])
                self.assertEqual([30], [proc.pid for proc in self.ended])
                self.assertEqual([20, 30], [value for event, value in events if event == "attempt"])
                self.assertEqual(("read", (20,) if remains else ()), events[-1])
                self.assertEqual("stop_incomplete" if remains else "stopped", read_json(self.layout.run_record)["state"])
                cases += 1
        self.assertEqual(2, cases)

    def test_other_native_errors_still_propagate(self):
        self.world = {20: self.process()}
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": self.world[20].as_dict()})
        error = OSError("unhandled native failure")
        with patch.object(procs, "terminate", side_effect=error), self.assertRaises(OSError) as raised:
            lifecycle.stop(self.layout, log=None, locked=True)
        self.assertIs(error, raised.exception)
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])


class AbsentRunStopTests(EvidenceFixture):
    def test_absent_noop_keeps_base_result_and_skips_final_port_wait(self):
        cases = 0
        for multi, available in itertools.product((False, True), repeat=2):
            with self.subTest(multi=multi, available=available):
                data = multi_gpu_data() if multi else single_gpu_data()
                data["server"]["stop_timeout_s"] = 0
                self.layout = Layout(self.layout.root, Profile(PROFILE, data))
                atomic_write_json(self.layout.install_record, {"profile_fingerprint": self.layout.profile.fingerprint})
                self.layout.run_record.unlink(missing_ok=True)
                facts = lambda index, **kwargs: gpu_fact(self.layout.profile, index) if available else {"available": False}
                with patch.object(lifecycle, "gpu_facts", side_effect=facts), \
                        patch.object(lifecycle, "port_in_use", side_effect=OSError("probe unavailable")) as port, \
                        patch.object(procs, "terminate") as terminate:
                    expected = {"state": "stopped", "stopped": []}
                    if multi:
                        expected.update(cards=lifecycle.card_observations(self.layout.profile), owned_gpus_released=None)
                    self.assertEqual(expected, lifecycle.stop(self.layout, log=None, locked=True))
                self.assertEqual(3, port.call_count, "only the three verdict observations may inspect the port")
                terminate.assert_not_called()
                self.assertFalse(self.layout.run_record.exists())
                cases += 1
        self.assertEqual(4, cases)

    def test_absent_run_with_cleanup_uses_active_gpu_result_and_port_wait(self):
        cases = 0
        for available, port_error in itertools.product((False, True), repeat=2):
            with self.subTest(available=available, port_error=port_error):
                self.ended.clear()
                data = multi_gpu_data()
                data["server"]["stop_timeout_s"] = 0
                self.layout = Layout(self.layout.root, Profile(PROFILE, data))
                atomic_write_json(self.layout.install_record, {"profile_fingerprint": self.layout.profile.fingerprint})
                self.layout.run_record.unlink(missing_ok=True)
                self.world = {20: self.process()}
                facts = lambda index, **kwargs: gpu_fact(self.layout.profile, index) if available else {"available": False}
                with patch.object(lifecycle, "gpu_facts", side_effect=facts), \
                        patch.object(lifecycle, "port_in_use", side_effect=OSError("probe unavailable") if port_error else None,
                                     return_value=False), patch.object(procs, "terminate", side_effect=self.terminate):
                    if port_error:
                        with self.assertRaisesRegex(OSError, "probe unavailable"):
                            lifecycle.stop(self.layout, log=None, locked=True)
                    else:
                        expected = lifecycle.card_observations(self.layout.profile, owned_pids={20})
                        result = lifecycle.stop(self.layout, log=None, locked=True)
                        self.assertEqual({"state": "stopped", "stopped": ["unrecorded:engine"], "cards": expected,
                                          "owned_gpus_released": available}, result)
                self.assertEqual([20], [proc.pid for proc in self.ended])
                self.assertEqual({}, self.world)
                self.assertFalse(self.layout.run_record.exists())
                cases += 1
        self.assertEqual(4, cases)


class StopFailureReportingTests(EvidenceFixture):
    def test_repeated_evidence_problems_appear_once_in_first_seen_order(self):
        self.world = {20: self.process()}
        self.layout.install_record.write_text("{")
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": self.world[20].as_dict()})
        messages = ("install record unreadable; reconcile this root by hand",
                    "process census unavailable: first census; custody unknown, so the root is not reported idle (retry `status`)")
        reads = 0
        def census():
            nonlocal reads
            reads += 1
            if reads == 1:
                raise procs.TableUnavailable("first census")
            return complete_table(self.world)
        with patch.object(lifecycle, "process_table", side_effect=census), \
                patch.object(procs, "matches", side_effect=lambda rec: native_matches(self.world.get(rec["pid"]), rec)), \
                patch.object(procs, "terminate", side_effect=self.terminate):
            with self.assertRaises(lifecycle.LifecycleError) as failure:
                lifecycle.stop(self.layout, log=None, locked=True)
        self.assertEqual("; ".join(messages), str(failure.exception))
        self.assertEqual([20], [proc.pid for proc in self.ended])
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])

    def test_first_seen_order_is_not_sorted_uniqueness(self):
        self.world = {20: self.process()}
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": self.world[20].as_dict()})
        messages = ("process census unavailable: census-first; custody unknown, so the root is not reported idle (retry `status`)",
                    "install record unreadable; reconcile this root by hand")
        self.assertGreater(messages[0], messages[1])
        reads = 0
        def census():
            nonlocal reads
            reads += 1
            if reads == 1:
                self.layout.install_record.write_text("{")
                raise procs.TableUnavailable("census-first")
            return complete_table(self.world)
        with patch.object(lifecycle, "process_table", side_effect=census), \
                patch.object(procs, "matches", side_effect=lambda rec: native_matches(self.world.get(rec["pid"]), rec)), \
                patch.object(procs, "terminate", side_effect=self.terminate):
            with self.assertRaises(lifecycle.LifecycleError) as failure:
                lifecycle.stop(self.layout, log=None, locked=True)
        self.assertEqual("; ".join(messages), str(failure.exception))
        self.assertEqual([20], [proc.pid for proc in self.ended])
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])

    @contextlib.contextmanager
    def interrupted_cleanup_world(self, failure, cleanup):
        self.ended.clear()
        self.world.clear()
        self.layout.run_record.unlink(missing_ok=True)
        def dispatch(*args, **kwargs):
            self.world[20] = self.process()
            run = read_json(self.layout.run_record)
            run.update(state="ready", server=self.world[20].as_dict(), tree_token=TOKEN)
            atomic_write_json(self.layout.run_record, run)
        with patch.object(lifecycle, "WINDOWS", True), \
                patch.object(lifecycle, "FileLock", side_effect=lambda *args, **kwargs: contextlib.nullcontext()), \
                patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
                patch.object(lifecycle.dflash2, "is_pinned", return_value=False), \
                patch.object(lifecycle, "read_key", return_value="key"), \
                patch.object(lifecycle, "gpu_facts", return_value={}), patch.object(lifecycle, "gpu_busy", return_value=None), \
                patch.object(procs, "memory", return_value={"available": 1 << 50}), \
                patch.object(procs, "info", side_effect=lambda pid: complete_table(self.world).identified.get(pid)), \
                patch.object(procs, "terminate", side_effect=self.terminate), \
                patch.object(lifecycle, "_engine_log_path", return_value=self.layout.root.resolve() / "engine.log"), \
                patch.object(lifecycle, "_launch_detached", side_effect=dispatch), \
                patch.object(lifecycle, "_finish_start", side_effect=failure), \
                patch.object(lifecycle, "ProcessJob", side_effect=cleanup) as job, \
                patch.object(cli, "_layout", return_value=self.layout):
            yield
            job.assert_called_once_with(TOKEN, existing=True)

    def test_start_cleanup_failure_matrix_preserves_interrupt_type_and_text(self):
        cases = 0
        for start_interrupt, cleanup_interrupt in itertools.product((False, True), repeat=2):
            with self.subTest(start_interrupt=start_interrupt, cleanup_interrupt=cleanup_interrupt):
                cases += 1
                failure = KeyboardInterrupt("start interrupted") if start_interrupt else RuntimeError("readiness error")
                cleanup = KeyboardInterrupt("cleanup interrupted") if cleanup_interrupt else lifecycle.LifecycleError("job open denied")
                with self.interrupted_cleanup_world(failure, cleanup):
                    try:
                        lifecycle.start(self.layout, tool_argv=["not-executed"], log=None)
                    except BaseException as exc:
                        observed = exc
                    else:
                        self.fail("failure world unexpectedly succeeded")
                print(f"start/cleanup matrix {start_interrupt=}, {cleanup_interrupt=}: "
                      f"{type(observed).__name__}: {observed}", flush=True)
                self.assertIs(type(observed), KeyboardInterrupt if cleanup_interrupt else lifecycle.LifecycleError)
                expected = "cleanup interrupted" if cleanup_interrupt else (
                    f"start failed: {failure}; cleanup failed: process-tree cleanup failed: job open denied")
                self.assertEqual(expected, str(observed))
                if cleanup_interrupt:
                    self.assertIs(cleanup, observed)
                self.assertEqual([] if cleanup_interrupt else [20], [proc.pid for proc in self.ended])
                self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
        self.assertEqual(4, cases)

    def test_cli_cleanup_interrupt_does_not_become_exit_four(self):
        for interrupted in (False, True):
            with self.subTest(interrupted=interrupted):
                failure = RuntimeError("readiness error")
                cleanup = KeyboardInterrupt("cleanup interrupted") if interrupted else lifecycle.LifecycleError("job open denied")
                with self.interrupted_cleanup_world(failure, cleanup), patch.object(cli, "eprint") as error:
                    argv = ["start", "--profile", str(PROFILE), "--root", str(self.layout.root)]
                    if interrupted:
                        with self.assertRaises(KeyboardInterrupt) as raised:
                            cli.main(argv)
                        self.assertIs(cleanup, raised.exception)
                        error.assert_not_called()
                    else:
                        self.assertEqual(4, cli.main(argv))
                        error.assert_called_once_with("error: start failed: readiness error; cleanup failed: "
                                                      "process-tree cleanup failed: job open denied")

    def test_start_preserves_readiness_failure_when_cleanup_refuses(self):
        for damaged_install in (False, True):
            with self.subTest(damaged_install=damaged_install):
                self.ended.clear()
                self.world.clear()
                self.layout.run_record.unlink(missing_ok=True)
                atomic_write_json(self.layout.install_record, self.install)
                original = RuntimeError("original readiness failure")
                def dispatch(*args, **kwargs):
                    self.world[20] = self.process()
                    run = read_json(self.layout.run_record)
                    run.update(state="ready", server=self.world[20].as_dict())
                    atomic_write_json(self.layout.run_record, run)
                    if damaged_install:
                        self.layout.install_record.write_text("{")
                with patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
                        patch.object(lifecycle.dflash2, "is_pinned", return_value=False), \
                        patch.object(lifecycle, "read_key", return_value="key"), \
                        patch.object(lifecycle, "gpu_facts", return_value={}), patch.object(lifecycle, "gpu_busy", return_value=None), \
                        patch.object(procs, "memory", return_value={"available": 1 << 50}), \
                        patch.object(procs, "info", side_effect=lambda pid: complete_table(self.world).identified.get(pid)), \
                        patch.object(procs, "terminate", side_effect=self.terminate), \
                        patch.object(lifecycle, "_engine_log_path", return_value=self.layout.root.resolve() / "engine.log"), \
                        patch.object(lifecycle, "_launch_detached", side_effect=dispatch), \
                        patch.object(lifecycle, "_finish_start", side_effect=original):
                    if damaged_install:
                        with self.assertRaises(lifecycle.LifecycleError) as failure:
                            lifecycle.start(self.layout, tool_argv=["not-executed"], log=None)
                        self.assertEqual("start failed: original readiness failure; cleanup failed: "
                                         "install record unreadable; reconcile this root by hand", str(failure.exception))
                    else:
                        with self.assertRaises(RuntimeError) as failure:
                            lifecycle.start(self.layout, tool_argv=["not-executed"], log=None)
                        self.assertIs(original, failure.exception)
                self.assertEqual([20], [proc.pid for proc in self.ended])
                self.assertEqual("stop_incomplete" if damaged_install else "stopped", read_json(self.layout.run_record)["state"])


class ExecutableCaseStopTests(EvidenceFixture):
    def test_full_identity_folds_executable_only_on_windows(self):
        for windows in (False, True):
            with self.subTest(windows=windows):
                self.ended.clear()
                first = procs.ProcInfo(20, 1, "20", str(self.layout.strata / "Engine"))
                second = procs.ProcInfo(20, 1, "20", str(self.layout.strata / "engine"))
                self.world = {20: first}
                atomic_write_json(self.layout.run_record, {"state": "ready"})
                def end(proc, timeout):
                    result = self.terminate(proc, timeout)
                    if len(self.ended) == 1:
                        self.world[20] = second
                    return result
                with patch.object(procs, "WINDOWS", windows), patch.object(procs, "terminate", side_effect=end):
                    if windows:
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "still alive"):
                            lifecycle.stop(self.layout, log=None, locked=True)
                        self.assertEqual([first], self.ended)
                        self.assertEqual({20: second}, self.world)
                    else:
                        self.assertEqual("stopped", lifecycle.stop(self.layout, log=None, locked=True)["state"])
                        self.assertEqual([first, second], self.ended)
                        self.assertEqual({}, self.world)
