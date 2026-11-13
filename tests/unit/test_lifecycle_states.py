"""The lifecycle's closed state table, walked (docs/OPERATIONS.md, "Lifecycle states").

The walk crosses everything the code can write (install record, run record state and flags) with everything the
process table can show (which recorded processes live, unrecorded processes of the root, a pid reused by a stranger,
a failed read, the port), using a process world kept in memory, and checks that status, start, stop and
idle_generation act on one verdict and that every row of the closed table is reached.
"""
from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from omp_strata import lifecycle, procs
from omp_strata.common import atomic_write_json, read_json
from omp_strata.layout import Layout
from omp_strata.profile import Profile
from tests.candidate import PROFILE
from tests.mock.test_remote_support import free_port
from tests.unit.test_profile import single_gpu_data

FULL = ("wrapper", "server", "engine", "server_tree")
TOKEN = "a" * 32
# Rows whose `stop` refuses on this platform: custody unknown, a publishing wrapper, an unreadable record, and (off
# Windows) any process-tree record. An unreadable table ends verified recorded processes, then refuses.
STOP_REFUSES = {"unreadable-record", "custody-unknown", "wrapper-publishing", "unreadable-table"}


class Admitted(Exception):
    """`start` passed every root check and reached the install check."""


def ident(pid: int, ppid: int, exe: str) -> procs.ProcInfo:
    return procs.ProcInfo(pid, ppid, f"created-{pid}", exe)


class StateTableWalk(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        data = single_gpu_data()
        data["server"].update(port=free_port(), stop_timeout_s=0)
        self.layout = Layout(Path(directory) / "root", Profile(PROFILE, data))
        self.layout.run_record.parent.mkdir(parents=True, exist_ok=True)
        engine = str(self.layout.strata / "engine" / "strata")
        self.p = {"launcher": ident(10, 1, "/tools/python3"), "wrapper": ident(11, 1, "/tools/python3"),
                  "server": ident(12, 11, "/tools/python3"), "server_tree": ident(13, 12, "/usr/bin/python3"),
                  "engine": ident(14, 13, engine)}
        self.engine_exe = engine

    def record(self, template):
        fingerprint = self.layout.profile.fingerprint
        base = {"profile_fingerprint": fingerprint, "runtime_identity_sha256": "a" * 64, "launch_id": "walked"}
        full: dict = {role: self.p[role].as_dict() for role in ("wrapper", "server", "engine")}
        full["server_tree"] = [self.p["server_tree"].as_dict()]
        return {
            "absent": (None, ()),
            "unreadable": ("{", ()),
            "launching": (dict(base, state="launching", launcher=self.p["launcher"].as_dict()), ("launcher",)),
            "publishing": (dict(base, state="starting", unpublished_child=True, wrapper=full["wrapper"]),
                           ("wrapper",)),
            "starting": (dict(base, state="starting", wrapper=full["wrapper"], server=full["server"]),
                         ("wrapper", "server")),
            "ready": (dict(base, state="ready", **full), FULL),
            "exited-0": (dict(base, state="exited", exit_code=0, **full), FULL),
            "exited-1": (dict(base, state="exited", exit_code=1, **full), FULL),
            "stopped": (dict(base, state="stopped", **full), FULL),
            "stop_incomplete": (dict(base, state="stop_incomplete", **full), FULL),
            "job-ready": (dict(base, state="ready", tree_token=TOKEN, **full), FULL),
            "job-stopped": (dict(base, state="stopped", tree_token=TOKEN, tree_verified_empty=TOKEN, **full), FULL),
        }[template]

    def write(self, path, value):
        if value is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")

    @staticmethod
    def owners(world, alive_roles, p, runtime_pids):
        """Ground truth, independent of the verdict: recorded processes alive, their current descendants, and every
        process running the root's runtime. A launcher is not a process of the root; it only makes a launch pending."""
        roots = {p[role].pid for role in alive_roles if role != "launcher"}
        found, frontier = set(roots), list(roots)
        while frontier:
            parent = frontier.pop()
            for proc in world.values():
                if proc.ppid == parent and proc.pid not in found:
                    found.add(proc.pid)
                    frontier.append(proc.pid)
        return found | runtime_pids

    def test_every_combination_lands_in_one_row_and_every_consumer_acts_on_it(self):
        world: dict[int, procs.ProcInfo] = {}
        readable = {"value": True}
        port = {"held": False}
        terminated: list[int] = []

        def table():
            if not readable["value"]:
                raise procs.TableUnavailable("fixture process table unreadable")
            return dict(world)

        def matches(recorded):
            proc = world.get(int(recorded["pid"])) if recorded else None
            return proc if proc is not None and procs.same_identity(proc, recorded) else None

        def terminate(proc, timeout):
            terminated.append(proc.pid)
            world.pop(proc.pid, None)
            return True

        def fast_write(path, value):
            Path(path).write_text(json.dumps(value), encoding="utf-8")

        def not_installed(_layout):
            raise Admitted

        patches = (
            patch.object(lifecycle, "process_table", side_effect=table),
            patch.object(lifecycle.procs, "matches", side_effect=matches),
            patch.object(lifecycle.procs, "terminate", side_effect=terminate),
            patch.object(lifecycle.procs, "descendants",
                         side_effect=lambda pid: [proc for proc in world.values() if proc.ppid == pid]),
            patch.object(lifecycle, "port_in_use", side_effect=lambda *args: port["held"]),
            patch.object(lifecycle, "read_key", return_value="x" * 32),
            patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}),
            patch.object(lifecycle, "verify_install_fast", side_effect=not_installed),
            patch.object(lifecycle.ProcessJob, "scan", return_value={}),
            patch.object(lifecycle, "atomic_write_json", side_effect=fast_write),
        )
        for active in patches:
            self.enterContext(active)
        installs = {"absent": None, "this": {"profile_fingerprint": self.layout.profile.fingerprint,
                                             "runtime_identity_sha256": "a" * 64},
                    "other": {"profile_fingerprint": "0" * 64, "runtime_identity_sha256": "a" * 64},
                    "stale": {"profile_fingerprint": self.layout.profile.fingerprint,
                              "runtime_identity_sha256": "b" * 64}}
        templates = ("absent", "unreadable", "launching", "publishing", "starting", "ready", "exited-0", "exited-1",
                     "stopped", "stop_incomplete", "job-ready", "job-stopped")
        seen_rows, combinations, started = set(), 0, time.monotonic()
        for template in templates:
            record, roles = self.record(template)
            for alive in itertools.product((False, True), repeat=len(roles)):
                alive_roles = {role for role, up in zip(roles, alive) if up}
                for install, extra, can_read, held in itertools.product(
                        installs, ("none", "engine", "helper", "reused"), (True, False), (False, True)):
                    if not can_read and (extra != "none" or held):
                        continue  # An unread table hides processes and port alike: one case covers it.
                    if extra == "reused" and "wrapper" in alive_roles:
                        continue  # The wrapper's pid is taken by the wrapper itself.
                    combinations += 1
                    world.clear()
                    world.update({self.p[role].pid: self.p[role] for role in alive_roles})
                    parent = next((self.p[role].pid for role in ("server_tree", "server") if role in alive_roles), 1)
                    if extra == "engine":  # an engine nobody recorded, e.g. restarted by the server tree
                        world[20] = ident(20, parent, self.engine_exe)
                    elif extra == "helper":  # a helper outside the runtime, under the server if it lives
                        world[21] = ident(21, self.p["server"].pid if "server" in alive_roles else 1, "/usr/bin/helper")
                    elif extra == "reused":  # a stranger now holding the recorded wrapper's pid
                        world[11] = procs.ProcInfo(11, 1, "created-other", "/tools/python3")
                    readable["value"], port["held"] = can_read, held
                    self.write(self.layout.install_record, installs[install])
                    self.write(self.layout.run_record, record)
                    runtime = {pid for pid, proc in world.items() if proc.exe == self.engine_exe}
                    truth = self.owners(world, alive_roles, self.p, runtime)
                    case = (template, sorted(alive_roles), install, extra, can_read, held)
                    with self.subTest(case=case):
                        seen_rows.add(self.check(record, truth, readable["value"], held, installs[install], world,
                                                 terminated))
        self.combinations, self.seconds = combinations, time.monotonic() - started
        print(f"\nstate-table walk: {combinations} combinations in {self.seconds:.1f} s", file=sys.stderr)
        self.assertEqual(set(lifecycle.ROWS), seen_rows)  # Every row of the closed table is reachable.

    def check(self, record, truth, readable, held, install, world, terminated):
        run = record if isinstance(record, dict) else {}
        verdict = lifecycle.verdict(self.layout)
        # I6: every combination is in exactly one row of the closed table.
        self.assertIn(verdict.row, lifecycle.ROWS)
        token = run.get("tree_token")
        expected_idle = (readable and isinstance(record, (dict, type(None))) and not truth
                         and run.get("state") != "launching" and not run.get("unpublished_child")
                         and (not token or (run.get("state") == "stopped" and run.get("tree_verified_empty") == token))
                         and not held and (install is None or install["profile_fingerprint"]
                                           == self.layout.profile.fingerprint))
        # I1: idle exactly when no process of the root is alive, no launch is pending, custody is known, the table
        # was read and nothing else holds the port.
        self.assertEqual(expected_idle, verdict.idle, verdict)
        if readable and verdict.row not in ("unreadable-record",):
            self.assertEqual(truth, {proc.pid for proc in verdict.live.values()}, verdict)
        # I4: the status document carries the verdict, and its state is idle exactly when the verdict is.
        reported = lifecycle.status(self.layout)
        self.assertEqual(verdict.idle, reported["state"] in lifecycle.IDLE_STATES, reported)
        if not (verdict.row == "server-live" and verdict.state == "healthy"):
            self.assertEqual(verdict.state, reported["state"])
        # I3: start passes its root checks exactly when the verdict is idle, and refuses with the verdict's reason.
        admitted = None
        try:
            lifecycle.start(self.layout, tool_argv=[sys.executable], log=lambda line: None)
        except Admitted:
            admitted = True
        except lifecycle.LifecycleError as exc:
            admitted = False
            self.assertEqual(verdict.refusal, str(exc))
        self.assertEqual(verdict.idle, admitted)
        try:
            lifecycle.idle_generation(self.layout)
            accepted = True
        except lifecycle.LifecycleError:
            accepted = False
        self.assertTrue(not accepted or verdict.quiescent, verdict)
        self.assertTrue(not accepted or not run or (run.get("tree_verified_empty") == token and token), verdict)
        # I2: stop ends exactly the verdict's live set; I5: no status problem advises a stop that refuses.
        terminated.clear()
        recorded_alive = {proc.pid for role, identity in lifecycle.recorded_processes(run)
                          if identity and (proc := world.get(int(identity["pid"]))) is not None
                          and procs.same_identity(proc, identity)}
        try:
            lifecycle.stop(self.layout, log=lambda line: None)
            refused = False
        except lifecycle.LifecycleError:
            refused = True
        advises = any("run `stop`" in problem for problem in verdict.problems)
        self.assertFalse(refused and advises, verdict)
        if refused:
            self.assertTrue(verdict.row in STOP_REFUSES or (token and not lifecycle.WINDOWS), verdict)
            if verdict.row == "unreadable-table":
                self.assertLessEqual(set(terminated), recorded_alive)
                if isinstance(record, dict) and not run.get("unpublished_child") and not token:
                    self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
            return verdict.row
        self.assertEqual({proc.pid for proc in verdict.live.values()}, set(terminated), verdict)
        after = lifecycle.verdict(self.layout)
        self.assertEqual({}, after.live, after)
        self.assertNotIn(after.row, ("launch-pending", "launch-abandoned"), after)
        self.assertTrue(after.idle or after.state == "mismatched" or after.row == "port-held", after)
        return verdict.row


class StopIdentityWalk(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        data = single_gpu_data()
        data["server"].update(port=free_port(), stop_timeout_s=0)
        self.layout = Layout(Path(directory), Profile(PROFILE, data))
        self.install = {"profile_fingerprint": self.layout.profile.fingerprint,
                        "runtime_identity_sha256": "a" * 64}
        atomic_write_json(self.layout.install_record, self.install)

    def walk(self, event, reverse=False, reused_pid=10, generations=1):
        """Termination can re-issue an ended PID, not just delete a process from a fixed world."""
        engine = str(self.layout.strata / "engine" / "strata")
        original = {10: ident(10, 1, engine), 11: ident(11, 10, engine)}
        world = dict(reversed(list(original.items()))) if reverse else dict(original)
        ended, snapshots = [], []
        issued = 0

        def table():
            snapshots.append(dict(world))
            return dict(world)

        def terminate(proc, timeout):
            nonlocal issued
            self.assertEqual(proc, world.pop(proc.pid), "stop tried to terminate a stale identity")
            ended.append(proc)
            if not world and event != "none" and issued < generations:
                issued += 1
                previous = original[reused_pid]
                created = f"{previous.created}-generation-{issued}" if event == "creation" else previous.created
                exe = f"{engine}-{issued}" if event == "executable" else engine
                world[reused_pid] = procs.ProcInfo(reused_pid, 1, created, exe)
            return True

        atomic_write_json(self.layout.run_record, dict(self.install, state="ready"))
        with patch.object(lifecycle, "process_table", side_effect=table), \
                patch.object(procs, "terminate", side_effect=terminate), \
                patch.object(lifecycle, "port_in_use", return_value=False):
            result, failure = None, None
            try:
                result = lifecycle.stop(self.layout, log=lambda line: None)
            except lifecycle.LifecycleError as exc:
                failure = exc
            after = lifecycle.verdict(self.layout)
        self.assertFalse(result and result["state"] == "stopped" and after.live,
                         f"stop reported stopped while the verdict still counts {after.live}")
        if event != "none":
            self.assertNotEqual(original[reused_pid], snapshots[1][reused_pid])
        exhausted = event != "none" and generations == 2
        self.assertEqual(exhausted, failure is not None)
        self.assertEqual(exhausted, bool(after.live))
        self.assertEqual("stop_incomplete" if exhausted else "stopped", read_json(self.layout.run_record)["state"])
        self.assertEqual(2 + (event != "none"), len(ended))
        if exhausted:
            self.assertIn("still alive after stop", str(failure))
        else:
            self.assertTrue(after.idle)
        return len(snapshots)

    def test_stop_never_reports_stopped_while_a_reused_pid_is_still_counted(self):
        for event in ("creation", "executable"):
            with self.subTest(identity_change=event):
                self.walk(event)

    def test_stop_identity_walk_reissues_ended_pids_between_passes(self):
        started, snapshots, cases = time.monotonic(), 0, 0
        for event, reverse, pid, generations in itertools.product(
                ("none", "creation", "executable"), (False, True), (10, 11), (1, 2)):
            with self.subTest(event=event, reverse=reverse, pid=pid, generations=generations):
                snapshots += self.walk(event, reverse, pid, generations)
                cases += 1
        print(f"\nstop identity walk: {cases} schedules, {snapshots} snapshots in "
              f"{time.monotonic() - started:.3f} s", file=sys.stderr)


@unittest.skipIf(procs.WINDOWS, "POSIX ps boundary; native Windows is unexercised")
class ProcessTableTests(unittest.TestCase):
    def test_malformed_ps_rows_are_left_out_without_losing_valid_rows(self):
        text = ("987654321 1 Fri Nov 13 12:34:56 2026 /fixture/path with spaces/python\n"
                "truncated\n"
                "not-a-pid 1 Fri Nov 13 12:34:56 2026 /fixture/python\n"
                "987654320 not-a-parent Fri Nov 13 12:34:56 2026 /fixture/python\n")
        self.assertEqual({987654321: procs.ProcInfo(987654321, 1, "Fri Nov 13 12:34:56 2026",
                                                   "/fixture/path with spaces/python")}, procs.parse_ps_table(text))

    def test_failed_timed_out_or_empty_ps_is_unavailable_not_an_empty_census(self):
        cases = (("failed", subprocess.CompletedProcess(["ps"], 1, "", "denied")),
                 ("timed out", subprocess.TimeoutExpired(["ps"], 10)),
                 ("empty", subprocess.CompletedProcess(["ps"], 0, "", "")))
        for name, result in cases:
            with self.subTest(case=name), patch.object(procs.subprocess, "run") as run:
                if isinstance(result, Exception):
                    run.side_effect = result
                else:
                    run.return_value = result
                with self.assertRaises(procs.TableUnavailable):
                    procs.table()
                run.assert_called_once_with(["ps", "-A", "-o", "pid=,ppid=,lstart=,comm="], capture_output=True,
                                            text=True, stdin=subprocess.DEVNULL, timeout=10)


def interruption_driver(root, data, point, role):
    """Run the real writer in a killable process; only host checks and the stock server are substitutes."""
    layout = Layout(Path(root), Profile(PROFILE, data))

    def wait_for(name):
        deadline = time.monotonic() + 15
        while not (layout.root / name).exists():
            if time.monotonic() >= deadline:
                raise RuntimeError(f"interruption driver timed out waiting for {name}")
            time.sleep(0.01)

    def hold():
        (layout.root / "held").touch()
        wait_for("release")

    real_write, real_info = lifecycle.atomic_write_json, procs.info

    def write(path, value):
        state = value.get("state")
        if role == "start" and point == 0 and state == "launching":
            hold()
        real_write(path, value)
        if role == "start" and ((point == 1 and state == "launching") or (point == 6 and state == "ready")):
            hold()
        if role == "serve" and ((point == 3 and value.get("unpublished_child"))
                               or (point == 5 and value.get("server") and state == "starting")
                               or (point == 8 and state == "exited")):
            hold()

    def info(pid, **kwargs):
        result = real_info(pid, **kwargs)
        if role == "serve" and pid != os.getpid():
            (layout.root / "server.pid").write_text(str(pid))
            if point == 4:
                hold()
        return result

    def dispatch(argv, **kwargs):
        atomic_write_json(layout.root / "dispatch.json", {"launch_id": argv[-1]})
        wait_for("dispatched")
        if point in (2, 3, 4, 5, 8):
            (layout.root / "launcher-held").touch()
            wait_for("launcher-release")

    def health(*args, **kwargs):
        if point == 7:
            raise lifecycle.LifecycleError("injected readiness failure")
        return {"ready": True, "problems": []}

    real_terminate = procs.terminate

    def terminate(proc, timeout):
        if point == 7:
            hold()  # The real failure cleanup entered stop, before its first process effect.
        return real_terminate(proc, timeout)

    with patch.object(lifecycle, "atomic_write_json", side_effect=write), \
            patch.object(procs, "info", side_effect=info), \
            patch.object(lifecycle, "read_key", return_value="x" * 32):
        if role == "serve":
            if point == 2:
                (layout.root / "wrapper-waiting").touch()
                wait_for("wrapper-release")
            engine = layout.strata / "engine" / "strata"
            argv = ["/bin/sh", "-c", '"$1" -c "import time; time.sleep(600)" & echo $! > "$2"; wait',
                    "stub-server", str(engine), str(layout.root / "engine.pid")]
            with patch.object(lifecycle, "server_argv", return_value=argv):
                try:
                    lifecycle.serve(layout, log_path=layout.logs / "server.log",
                                    launch_id=read_json(layout.root / "dispatch.json")["launch_id"])
                except lifecycle.LifecycleError as exc:
                    (layout.root / "refused").write_text(str(exc))
                    raise
        else:
            with patch.object(lifecycle, "verify_install_fast", return_value=read_json(layout.install_record)), \
                    patch.object(lifecycle, "gpu_facts", return_value={}), \
                    patch.object(lifecycle, "gpu_busy", return_value=None), \
                    patch.object(procs, "memory", return_value={"available": 1 << 40}), \
                    patch.object(lifecycle, "_launch_detached", side_effect=dispatch), \
                    patch.object(lifecycle, "runtime_checks", side_effect=health), \
                    patch.object(procs, "terminate", side_effect=terminate):
                lifecycle.start(layout, tool_argv=[sys.executable], log=lambda line: None)


@unittest.skipIf(procs.WINDOWS, "POSIX interruption drivers; native Windows is unexercised")
class InterruptionWalk(unittest.TestCase):
    def wait_for(self, predicate, detail):
        deadline = time.monotonic() + 15
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail(f"timed out waiting for {detail}")
            time.sleep(0.01)

    def test_every_interruption_preserves_a_nonidle_verdict_until_custody_is_resolved(self):
        started = time.monotonic()
        for point, expected in enumerate(("idle", "launch-abandoned", "launch-abandoned", "custody-unknown",
                                          "custody-unknown", "server-live", "server-live", "server-live", "orphans")):
            with self.subTest(point=f"P{point}"), tempfile.TemporaryDirectory() as directory:
                data = single_gpu_data()
                data["server"].update(port=free_port(), stop_timeout_s=2)
                layout = Layout(Path(directory) / "root", Profile(PROFILE, data))
                layout.strata.mkdir(parents=True)
                engine = layout.strata / "engine" / "strata"
                engine.parent.mkdir()
                shutil.copy(procs.info(os.getpid()).exe, engine)
                atomic_write_json(layout.install_record, {
                    "profile_fingerprint": layout.profile.fingerprint, "runtime_identity_sha256": "a" * 64})
                atomic_write_json(layout.strata_config, {"log": str(layout.root.resolve() / "engine.log")})
                children, identities = [], []
                killed = set()

                def spawn(role):
                    code = ("import json,sys; from tests.unit.test_lifecycle_states import interruption_driver; "
                            "interruption_driver(sys.argv[1],json.loads(sys.argv[2]),int(sys.argv[3]),sys.argv[4])")
                    output = open(layout.root / (role + ".log"), "wb")
                    try:
                        child = subprocess.Popen([sys.executable, "-c", code, str(layout.root), json.dumps(data),
                                                  str(point), role], stdin=subprocess.DEVNULL,
                                                 stdout=output, stderr=subprocess.STDOUT)
                    finally:
                        output.close()
                    children.append(child)
                    threading.Thread(target=child.wait, daemon=True).start()
                    return child

                def marker(name):
                    def ready():
                        if (layout.root / name).exists():
                            return True
                        for child in children:
                            if child not in killed and child.poll() is not None:
                                logs = "\n".join(path.read_text() for path in layout.root.glob("*.log"))
                                self.fail(f"P{point} driver exited before {name}:\n{logs}")
                        return False
                    self.wait_for(ready, f"P{point} {name}")

                def kill(child):
                    killed.add(child)
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)

                def observe(row):
                    verdict = lifecycle.verdict(layout)
                    self.assertIn(verdict.row, lifecycle.ROWS)
                    self.assertEqual(row, verdict.row, verdict)
                    self.assertEqual(point == 0, verdict.idle, verdict)
                    if verdict.idle:
                        self.assertFalse(verdict.live)
                        self.assertFalse(verdict.details.get("pending"))
                    return verdict

                try:
                    launcher = spawn("start")
                    wrapper = None
                    if point >= 2:
                        marker("dispatch.json")
                        wrapper = spawn("serve")
                        (layout.root / "dispatched").touch()
                    if point == 2:
                        marker("wrapper-waiting")
                        marker("launcher-held")
                        observe("launch-pending")
                    elif point == 8:
                        marker("launcher-held")
                        marker("server.pid")
                    else:
                        marker("held")
                    if point in (3, 4):
                        observe("wrapper-publishing")
                    if point >= 4:
                        marker("engine.pid")
                        for name in ("server", "engine"):
                            pid = int((layout.root / (name + ".pid")).read_text())
                            self.wait_for(lambda: (proc := procs.info(pid)) is not None
                                          and (name != "engine" or proc.exe == str(engine)), f"{name} exec")
                            identities.append(procs.info(pid))
                    if point == 1:
                        observe("launch-pending")
                    kill(launcher)
                    if point in (3, 4, 5):
                        kill(wrapper)
                    if point == 8:
                        os.kill(identities[0].pid, signal.SIGKILL)
                        marker("held")  # serve published the real child exit.
                        kill(wrapper)
                    verdict = observe(expected)
                    print(f"\nP{point}: {verdict.row} ({verdict.state}), idle={verdict.idle}", file=sys.stderr)
                    if point == 2:
                        lifecycle.stop(layout, log=lambda line: None)
                        (layout.root / "wrapper-release").touch()
                        wrapper.wait(timeout=5)
                        self.assertNotEqual(0, wrapper.returncode)
                        self.assertIn("generation changed or stopped", (layout.root / "refused").read_text())
                        self.assertEqual("idle", lifecycle.verdict(layout).row)
                        self.assertFalse((layout.root / "server.pid").exists())
                        print("P2 fenced: idle; late wrapper refused without spawning", file=sys.stderr)
                    elif point in (3, 4):
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "unpublished child"):
                            lifecycle.stop(layout, log=lambda line: None)
                    elif point >= 5:
                        lifecycle.stop(layout, log=lambda line: None)
                        self.assertTrue(lifecycle.verdict(layout).idle)
                finally:
                    # Deepest first: the shell reaps its engine, serve reaps the shell, and our waiters reap drivers.
                    for proc in reversed(identities):
                        if procs.matches(proc.as_dict()):
                            self.assertTrue(procs.terminate(proc, 2), f"leftover process {proc}")
                    for child in reversed(children):
                        kill(child)
                    for proc in identities:
                        self.assertIsNone(procs.matches(proc.as_dict()), f"leftover process {proc}")
        print(f"\ninterruption walk: P0-P8 in {time.monotonic() - started:.2f} s", file=sys.stderr)


@unittest.skipIf(procs.WINDOWS, "POSIX process fixture; native Windows is unexercised")
class CensusResidualTests(unittest.TestCase):
    def test_an_unrecorded_process_outside_the_runtime_is_not_counted_or_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            data = single_gpu_data()
            data["server"]["port"] = free_port()
            layout = Layout(Path(directory), Profile(PROFILE, data))
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            try:
                # The child has no recorded ancestor, executes outside the runtime and does not hold its port.
                before = lifecycle.verdict(layout)
                self.assertEqual("idle", before.row)
                self.assertEqual({}, before.live)
                self.assertEqual([], lifecycle.stop(layout, log=lambda line: None)["stopped"])
                self.assertIsNone(child.poll())
                self.assertFalse(layout.run_record.exists())
            finally:
                child.kill()
                child.wait(timeout=5)
            self.assertIsNone(procs.info(child.pid))


if __name__ == "__main__":
    unittest.main()
