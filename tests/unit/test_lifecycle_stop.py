"""Stop selection, evidence and ordering in accounted host-free process worlds."""
import itertools
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from omp_strata import lifecycle, procs
from omp_strata.common import atomic_write_json, read_json
from tests.unit.test_lifecycle_evidence import EvidenceFixture, complete_table, native_matches


TOKEN = "a" * 32


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
        with patch.object(lifecycle, "process_table", side_effect=lambda: complete_table(self.world, unidentified={20})), \
                patch.object(procs, "terminate", side_effect=self.terminate):
            self.assertEqual("orphans", lifecycle.verdict(self.layout).row)
            with self.assertRaisesRegex(lifecycle.LifecycleError, "launcher pid 20"):
                lifecycle.stop(self.layout, log=None, locked=True)
        self.assertEqual([77], [p.pid for p in self.ended])
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])


class StopOrderWalk(EvidenceFixture):
    def test_outside_intermediary_does_not_grant_ownership_or_order(self):
        ancestor = self.process(pid=50)
        outsider = procs.ProcInfo(51, 50, "51", "/outside/helper")
        server = procs.ProcInfo(20, 51, "20", "/outside/server")
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
                rows = [procs.ProcInfo(pid, parent, str(pid), str(self.layout.strata / f"p{pid}"))
                        for pid, parent in edges.items()]
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
        with patch.object(lifecycle, "ProcessJob", return_value=job) as factory:
            factory.scan.return_value = {}
            result = lifecycle.stop(self.layout, log=lambda line: None, locked=True)
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
