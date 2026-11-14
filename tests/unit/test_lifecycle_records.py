"""Role-schema, released-writer null and reader-edge contracts; host-free."""
import contextlib
import itertools
import json
from unittest.mock import patch

from omp_strata import cli, lifecycle, procs, remote
from omp_strata.common import atomic_write_json
from types import SimpleNamespace
from tests.unit.test_lifecycle_evidence import EvidenceFixture, complete_table, native_matches


class RecordedRoleShapeWalk(EvidenceFixture):
    def test_present_roles_are_never_silently_absent(self):
        states = (None, "launching", "starting", "ready", "exited", "stopped", "stop_incomplete")
        forms = ("omitted", "null", "empty", "not-object", "missing-pid", "missing-created", "missing-exe",
                 "wrong-pid", "wrong-created", "wrong-exe", "duplicate-null-valid", "duplicate-valid-null", "valid")
        cases = 0
        identity = self.process(created="20").as_dict()
        survivor = self.process(pid=77, created="77")
        for role, state, windows, form, remaining in itertools.product(
                ("wrapper", "server", "engine", "launcher", "server_tree[0]"), states, (False, True), forms, (False, True)):
            with self.subTest(role=role, state=state, windows=windows, form=form, remaining=remaining), \
                    patch.object(lifecycle, "WINDOWS", windows), patch.object(procs, "WINDOWS", windows):
                cases += 1
                self.world.clear()
                if remaining:
                    self.world[survivor.pid] = survivor
                run = {} if state is None else {"state": state}
                key = "server_tree" if role == "server_tree[0]" else role
                value = dict(identity)
                if form == "null":
                    value = None
                elif form == "empty":
                    value = {}
                elif form == "not-object":
                    value = "not an identity"
                elif form.startswith("missing-"):
                    value.pop(form.removeprefix("missing-"))
                elif form.startswith("wrong-"):
                    field = form.removeprefix("wrong-")
                    value[field] = "20" if field == "pid" else 101
                if form != "omitted":
                    run[key] = [value] if key == "server_tree" else value
                if form.startswith("duplicate-"):
                    good = [identity] if key == "server_tree" else identity
                    run[key] = None if form == "duplicate-null-valid" else good
                    second = good if form == "duplicate-null-valid" else None
                    text = json.dumps(run)[:-1] + "," + json.dumps(key) + ":" + json.dumps(second) + "}"
                else:
                    text = json.dumps(run)
                self.layout.run_record.write_text(text)
                active = role != "launcher" or state == "launching" or not remaining
                invalid = (form.startswith("duplicate-")
                           or active and form not in ("omitted", "valid") and not (role == "engine" and form == "null"))
                root = lifecycle.verdict(self.layout)
                self.assertEqual(invalid, root.row == "unreadable-record")
                self.assertEqual({77} if remaining else set(), {p.pid for p in root.live.values()})
                if invalid:
                    self.assertFalse(root.idle or root.quiescent)
                    self.assertIn("run", root.details["unreadable_records"])
                    if state == "stopped" and not windows and not remaining:
                        with self.assertRaises(lifecycle.LifecycleError):
                            lifecycle.start(self.layout, tool_argv=["fixture"], log=lambda _: None)
                        with patch.object(cli, "_layout", return_value=self.layout), \
                                patch.object(cli.install_mod, "install") as install:
                            with self.assertRaises(lifecycle.LifecycleError):
                                cli.cmd_install(SimpleNamespace(idle_generation=None))
                            install.assert_not_called()
                        with self.assertRaises(lifecycle.LifecycleError):
                            lifecycle.idle_generation(self.layout)
                else:
                    self.assertEqual(not remaining and state != "launching", root.quiescent)
        self.assertEqual(1820, cases)

    def test_server_tree_collection_requires_a_list_of_identities(self):
        for value in (None, {}, "", 0, [None], [{}], []):
            with self.subTest(value=value):
                atomic_write_json(self.layout.run_record, {"state": "stopped", "server_tree": value})
                root = lifecycle.verdict(self.layout)
                self.assertEqual(value != [], root.row == "unreadable-record")
                self.assertEqual(value == [], root.quiescent)

    def test_released_engine_null_is_identical_to_an_omitted_role(self):
        for state, alive in itertools.product(("starting", "ready", "exited", "stopped", "stop_incomplete"), (False, True)):
            with self.subTest(state=state, alive=alive):
                server = self.process(created="20")
                self.world.clear()
                if alive:
                    self.world[server.pid] = server
                run = {"state": state, "server": server.as_dict(), "server_tree": []}
                atomic_write_json(self.layout.run_record, run)
                before = lifecycle.verdict(self.layout)
                atomic_write_json(self.layout.run_record, {**run, "engine": None})
                after = lifecycle.verdict(self.layout)
                self.assertEqual((before.row, before.state, before.quiescent, before.live, before.details),
                                 (after.row, after.state, after.quiescent, after.live, after.details))


class LauncherEvidenceTests(EvidenceFixture):
    def test_missing_gone_and_unidentified_launcher_have_distinct_reasons(self):
        launcher = self.process(created="20", owned=False)
        for kind, expected in (("missing", "launch-unrecorded"), ("gone", "launch-abandoned"),
                               ("unidentified", "unreadable-table")):
            with self.subTest(kind=kind):
                run = {"state": "launching"}
                if kind != "missing":
                    run["launcher"] = launcher.as_dict()
                atomic_write_json(self.layout.run_record, run)
                unknown = {launcher.pid} if kind == "unidentified" else set()
                with patch.object(lifecycle, "process_table", return_value=complete_table(unidentified=unknown)):
                    root = lifecycle.verdict(self.layout)
                    self.assertEqual(expected, root.row)
                    self.assertFalse(root.idle or root.quiescent)
                    message = " ".join(root.problems)
                    if kind == "missing":
                        self.assertIn("identity is not recorded", message)
                    if kind != "gone":
                        self.assertNotIn("is gone", message)


class VouchedParentEdgeWalk(EvidenceFixture):
    def test_verdict_consumes_only_reader_vouched_edges(self):
        cases = 0
        for source, delta, windows in itertools.product(("windows", "procfs", "ps"), (-1, 0, 1), (False, True)):
            with self.subTest(source=source, delta=delta, windows=windows), patch.object(procs, "WINDOWS", windows):
                cases += 1
                if source == "windows":
                    stamps = "100", str(100 + delta)
                elif source == "procfs":
                    stamps = "starttime:100", "starttime:" + str(100 + delta)
                else:
                    stamps = "Fri Nov 13 12:34:56 2026", f"Fri Nov 13 12:34:{56 + delta:02d} 2026"
                parent = procs.ProcInfo(20, 1, stamps[0], "/outside/python")
                child = procs.ProcInfo(21, 20, stamps[1], "/outside/helper")
                atomic_write_json(self.layout.run_record, {"server": parent.as_dict()})
                table = complete_table({20: parent, 21: child})
                table = procs._checked_table(table.identified, table.unidentified)
                with patch.object(lifecycle, "process_table", return_value=table):
                    root = lifecycle.verdict(self.layout)
                kept = source == "ps" or delta >= 0
                self.assertEqual({20, 21} if kept else {20}, {p.pid for p in root.live.values()})
                self.assertEqual(kept, 21 in root.under)
        self.assertEqual(18, cases)


class CannotSayConsumerWalk(EvidenceFixture):
    def assert_refusals_name(self, evidence, *, pid=None):
        root = lifecycle.verdict(self.layout)
        self.assertFalse(root.idle or root.quiescent)
        report = lifecycle.status(self.layout)
        self.assertEqual("degraded", report["state"])
        self.assertIn(evidence, "; ".join(report["problems"]))
        if pid is not None:
            for required in (f"pid {pid}", "cannot prove", "by hand", str(self.layout.run_record)):
                self.assertIn(required, "; ".join(report["problems"]))
        with patch.object(lifecycle, "FileLock", side_effect=lambda *args, **kwargs: contextlib.nullcontext()), \
                patch.object(lifecycle, "verify_install_fast", side_effect=AssertionError("start admitted")), \
                patch.object(cli, "_layout", return_value=self.layout), \
                patch.object(cli.install_mod, "install", side_effect=AssertionError("install admitted")), \
                patch.object(lifecycle.ProcessJob, "scan", side_effect=AssertionError("candidate scan admitted")):
            callers = {
                "start": lambda: lifecycle.start(self.layout, tool_argv=["fixture"], log=lambda _: None),
                "install": lambda: cli.cmd_install(SimpleNamespace(idle_generation=None)),
                "candidate": lambda: lifecycle.idle_generation(self.layout),
                "fenced-candidate": lambda: lifecycle.idle_generation(self.layout, expected="changed"),
            }
            for name, caller in callers.items():
                with self.subTest(consumer=name), self.assertRaises(lifecycle.LifecycleError) as failure:
                    caller()
                message = str(failure.exception)
                self.assertIn(evidence, message)
                self.assertRegex(message, r"retry|reconcile|inspect|change the port|retain custody")
                if pid is not None:
                    for required in (f"pid {pid}", "cannot prove", "by hand", str(self.layout.run_record)):
                        self.assertIn(required, message)

    def test_each_cannot_say_cause_refuses_every_consumer_for_every_recorded_role(self):
        states = (None, "launching", "starting", "ready", "exited", "stopped", "stop_incomplete")
        causes = ("unidentified", "changed-executable", "calendar", "mixed-clock", "unrecognised", "lossy",
                  "calendar-executable", "mixed-clock-executable", "unrecognised-executable")
        cases = 0
        for role, state, windows, cause in itertools.product(
                ("wrapper", "server", "engine", "server_tree[0]", "launcher"), states, (False, True), causes):
            with self.subTest(role=role, state=state, windows=windows, cause=cause), \
                    patch.object(lifecycle, "WINDOWS", windows), patch.object(procs, "WINDOWS", windows):
                process = self.process(created="101", owned=False)
                record = process.as_dict()
                unknown = {20} if cause == "unidentified" else set()
                if cause == "changed-executable":
                    record["exe"] = "/before/engine"
                elif cause.startswith("calendar"):
                    process = self.process(created="Fri Nov 13 12:34:56 2026", owned=False)
                    record["created"] = "Fri Nov 13 13:34:56 2026"
                elif cause.startswith("mixed-clock"):
                    record["created"] = "starttime:101"
                elif cause.startswith("unrecognised"):
                    process = self.process(created="sample-a", owned=False)
                    record["created"] = "sample-b"
                elif cause == "lossy":
                    record.update(created="102", exe="/runtime/\ufffdengine")
                if cause.endswith("-executable"):
                    record["exe"] = "/before/engine"
                run = {} if state is None else {"state": state}
                run["server_tree" if role == "server_tree[0]" else role] = [record] if role == "server_tree[0]" else record
                atomic_write_json(self.layout.run_record, run)
                rows = {77: self.process(pid=77, created="200")}
                if not unknown:
                    rows[20] = process
                with patch.object(lifecycle, "process_table", return_value=complete_table(rows, unidentified=unknown)):
                    root = lifecycle.verdict(self.layout)
                    self.assertEqual({77}, {p.pid for p in root.live.values()})
                    if role == "launcher" and state != "launching":
                        self.assertEqual("orphans", root.row)
                        self.assertNotIn("unidentified_records", root.details)
                        self.assert_refusals_name("unrecorded[77]")
                    else:
                        self.assertEqual("unreadable-table", root.row)
                        self.assertEqual([role], root.details["unidentified_records"])
                        self.assert_refusals_name(role, pid=20)
                cases += 1
        self.assertEqual(630, cases)

    def test_unknown_identity_names_the_pid_and_manual_record_recovery(self):
        process = self.process(created="Fri Nov 13 12:34:57 2026", owned=False)
        self.world[20] = process
        record = dict(process.as_dict(), created="Fri Nov 13 12:34:56 2026")
        atomic_write_json(self.layout.run_record, {"state": "stopped", "server": record})
        self.assert_refusals_name("server", pid=20)

    def test_each_unreadable_input_is_named_by_every_consumer(self):
        for kind, name in (("run", "run record"), ("install", "install record"),
                           ("census", "process census"), ("job", "process-tree generation"),
                           ("unpublished", "child"), ("port", "PID unavailable"), ("probe", "configured port")):
            with self.subTest(kind=kind), contextlib.ExitStack() as stack:
                run = {"state": "stopped"}
                if kind == "job":
                    run["tree_token"] = "a" * 32
                elif kind == "unpublished":
                    run["unpublished_child"] = True
                atomic_write_json(self.layout.run_record, run)
                atomic_write_json(self.layout.install_record, self.install)
                if kind in ("run", "install"):
                    getattr(self.layout, kind + "_record").write_text("{")
                elif kind == "census":
                    stack.enter_context(patch.object(lifecycle, "process_table", side_effect=procs.TableUnavailable()))
                elif kind == "probe":
                    stack.enter_context(patch.object(lifecycle, "port_in_use", side_effect=OSError("descriptor unavailable")))
                elif kind == "port":
                    stack.enter_context(patch.object(lifecycle, "port_in_use", return_value=True))
                    stack.enter_context(patch.object(remote, "listener_pids", side_effect=remote.RemoteError("unreadable")))
                self.assert_refusals_name(name)


class NativeComparisonFixtureTests(EvidenceFixture):
    def test_start_fixtures_record_the_same_reader_identity_as_their_census(self):
        import os
        from tests.unit import test_lifecycle as fixtures

        cases = 0
        for case, stamp, exe in itertools.product(
                (fixtures.SingleGpuLifecycleTests, fixtures.MultiGpuLifecycleTests),
                ("101", "Fri Nov 13 12:34:56 2026"), ("/native/reader", "/host-free/reader")):
            cases += 1
            def lookup(pid, *args, **kwargs):
                return procs.ProcInfo(pid, 0, stamp, exe)
            with self.subTest(fixture=case.__name__, stamp=stamp, exe=exe), \
                    patch.object(procs, "info", side_effect=lookup), contextlib.ExitStack() as cleanup:
                fixture = case()
                cleanup.callback(fixture.doCleanups)
                fixture.setUp()
                identity = procs.info(os.getpid())
                self.assertIs(procs.Presence.SAME, complete_table().observe(identity.as_dict()))
                self.assertEqual(lookup(identity.pid + 1), procs.info(identity.pid + 1))
        self.assertEqual(8, cases)

    def test_fake_native_lookup_retains_the_legacy_comparison(self):
        process = self.process(created="101", owned=False)
        for windows, created, exe in itertools.product((False, True), ("101", "102"), (process.exe, process.exe.upper())):
            with self.subTest(windows=windows, created=created, exe=exe), patch.object(procs, "WINDOWS", windows), \
                    patch.object(procs.ProcessTable, "observe", side_effect=AssertionError("not the native comparator")):
                record = dict(process.as_dict(), created=created, exe=exe)
                expected = process if created == "101" and (windows or exe == process.exe) else None
                self.assertIs(expected, native_matches(process, record))


class HostClockAdmissionWalk(EvidenceFixture):
    assert_refusals_name = CannotSayConsumerWalk.assert_refusals_name

    def test_pid_reuse_admission_depends_on_the_host_clock_proof(self):
        class Admitted(Exception):
            pass

        hosts = (("windows", "101", "102"), ("procfs", "starttime:101", "starttime:102"),
                 ("calendar", "Fri Nov 13 12:34:56 2026", "Fri Nov 13 12:34:57 2026"))
        cases = 0
        for (host, before, after), role, changed_executable in itertools.product(
                hosts, ("wrapper", "server", "engine", "server_tree[0]", "launcher"), (False, True)):
            with self.subTest(host=host, role=role, changed_executable=changed_executable), \
                    patch.object(lifecycle, "WINDOWS", host == "windows"), \
                    patch.object(procs, "WINDOWS", host == "windows"):
                recorded = self.process(created=before, owned=False).as_dict()
                current = self.process(created=after, owned=False)
                if changed_executable:
                    current = procs.ProcInfo(current.pid, current.ppid, current.created, "/another/program")
                self.world = {20: current}
                token = "a" * 32
                run = {"state": "stopped", "tree_token": token, "tree_verified_empty": token}
                run["server_tree" if role == "server_tree[0]" else role] = [recorded] if role == "server_tree[0]" else recorded
                atomic_write_json(self.layout.run_record, run)
                root = lifecycle.verdict(self.layout)
                if host == "calendar":
                    self.assertEqual("unreadable-table", root.row)
                    self.assert_refusals_name(role, pid=20)
                else:
                    self.assertTrue(root.idle and root.quiescent)
                    self.assertEqual("stopped", lifecycle.status(self.layout)["state"])
                    with patch.object(lifecycle, "FileLock", side_effect=lambda *args, **kwargs: contextlib.nullcontext()), \
                            patch.object(lifecycle, "verify_install_fast", side_effect=Admitted), \
                            patch.object(cli, "_layout", return_value=self.layout), \
                            patch.object(cli.install_mod, "install", side_effect=Admitted), \
                            patch.object(lifecycle.ProcessJob, "scan", return_value={}):
                        with self.assertRaises(Admitted):
                            lifecycle.start(self.layout, tool_argv=["fixture"], log=lambda _: None)
                        with self.assertRaises(Admitted):
                            cli.cmd_install(SimpleNamespace(idle_generation=None))
                        generation = lifecycle.idle_generation(self.layout)
                        self.assertEqual(generation, lifecycle.idle_generation(self.layout, expected=generation))
                cases += 1
        self.assertEqual(30, cases)


class LauncherRelevanceWalk(EvidenceFixture):
    def launcher(self, outcome):
        live = self.process(created="101", owned=False)
        recorded = live.as_dict()
        if outcome == "other":
            recorded["created"] = "100"
        elif outcome == "cannot-say":
            recorded["created"] = "Fri Nov 13 12:34:56 2026"
            live = self.process(created="Fri Nov 13 12:34:57 2026", owned=False)
        if outcome != "absent":
            self.world[live.pid] = live
        return recorded

    def test_serving_server_reaches_authentication_and_clients_despite_inactive_launcher(self):
        for outcome in ("same", "other", "absent", "cannot-say", "null", "malformed"):
            with self.subTest(outcome=outcome):
                self.world.clear()
                launcher = self.launcher(outcome)
                if outcome in ("null", "malformed"):
                    launcher = None if outcome == "null" else {}
                server = self.process(pid=21, created="21", owned=False)
                self.world[server.pid] = server
                atomic_write_json(self.layout.run_record,
                                  {"state": "ready", "server": server.as_dict(), "launcher": launcher})
                with patch.object(lifecycle, "read_key", return_value="key"), \
                        patch.object(lifecycle, "runtime_checks", return_value={"problems": []}) as checks, \
                        patch.object(procs, "descendants", return_value=[]):
                    self.assertEqual("healthy", lifecycle.status(self.layout)["state"])
                    self.assertEqual("key", lifecycle.ensure_healthy(self.layout))
                    self.assertEqual(2, checks.call_count)
                    checks.assert_called_with(self.layout, "key")
                self.assertFalse(lifecycle.verdict(self.layout).quiescent)

    def test_launcher_is_active_during_launch_or_before_quiescence(self):
        cases = 0
        for state, ownership, outcome in itertools.product(
                ("launching", "ready", "stopped"), ("none", "server", "orphan"),
                ("same", "other", "absent", "cannot-say")):
            with self.subTest(state=state, ownership=ownership, outcome=outcome):
                cases += 1
                self.world.clear()
                run = {"state": state, "launcher": self.launcher(outcome)}
                if ownership != "none":
                    proc = self.process(pid=77, created="77", owned=ownership == "orphan")
                    self.world[proc.pid] = proc
                    if ownership == "server":
                        run["server"] = proc.as_dict()
                atomic_write_json(self.layout.run_record, run)
                active = state == "launching" or ownership == "none"
                if active and outcome == "cannot-say":
                    expected = "unreadable-table"
                elif state == "launching":
                    expected = "launch-pending" if outcome == "same" else "launch-abandoned"
                else:
                    expected = {"none": "idle", "server": "server-live", "orphan": "orphans"}[ownership]
                root = lifecycle.verdict(self.layout)
                self.assertEqual(expected, root.row)
                self.assertEqual(expected == "idle", root.idle)
                self.assertEqual(expected == "idle", root.quiescent)
        self.assertEqual(36, cases)

    def test_stopped_root_retains_uncertain_launcher_until_quiescence_is_proved(self):
        atomic_write_json(self.layout.run_record,
                          {"state": "stopped", "launcher": self.launcher("cannot-say")})
        root = lifecycle.verdict(self.layout)
        self.assertEqual("unreadable-table", root.row)
        self.assertFalse(root.idle or root.quiescent)
        self.assertIn("launcher pid 20", root.refusal)
        self.assertIn("by hand", root.refusal)
