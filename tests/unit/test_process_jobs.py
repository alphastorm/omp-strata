"""Host-free Win32 kernel boundary; the production ProcessJob policy is never replaced."""
import ctypes
import json
import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import patch

from omp_strata import lifecycle


class KernelStub:
    def __init__(self):
        self.handles = {}
        self.jobs = {}
        self.members = {}
        self.live = {}
        self.serial = 10
        self.current = 500
        self.fail = None
        self.events = []

    def handle(self, token):
        self.serial += 1
        self.handles[self.serial] = token
        return self.serial

    def CreateJobObjectW(self, _security, name):
        self.events.append("create")
        self.jobs[name] = name
        return self.handle(name)

    def OpenJobObjectW(self, _access, _inherit, name):
        return self.handle(name) if name in self.jobs else 0

    def SetInformationJobObject(self, handle, kind, limits, size):
        self.events.append(("limits", limits._obj.basic.flags))
        return self.fail != "limits"

    def CloseHandle(self, handle):
        token = self.handles.pop(handle, None)
        if token and token not in self.handles.values():
            self.TerminateToken(token)
            self.jobs.pop(token, None)
        self.events.append("close")
        return 1

    def GetCurrentProcess(self):
        return self.current

    def IsProcessInJob(self, process, handle, result):
        result._obj.value = self.members.get(process) == self.handles[handle]
        return self.fail != "membership"

    def AssignProcessToJobObject(self, handle, process):
        self.events.append("assign")
        if self.fail == "assign":
            return 0
        self.members[process] = self.handles[handle]
        return 1

    def QueryInformationJobObject(self, handle, kind, values, size, length):
        if self.fail == "query":
            return 0
        pids = [pid for pid, token in self.members.items() if token == self.handles[handle] and pid in self.live]
        values._obj.assigned = values._obj.count = len(pids)
        for i, pid in enumerate(pids):
            values._obj.items[i] = pid
        return 1

    def TerminateToken(self, token):
        for pid in list(self.live):
            if self.members.get(pid) == token:
                self.live.pop(pid, None)

    def TerminateJobObject(self, handle, code):
        self.events.append("terminate")
        if self.fail == "terminate":
            return 0
        self.TerminateToken(self.handles[handle])
        return 1

    def OpenProcess(self, access, inherit, pid):
        return pid if pid in self.live else 0

    def DuplicateHandle(self, source, handle, target, result, access, inherit, options):
        self.events.append("duplicate")
        if self.fail == "duplicate":
            return 0
        if handle in self.handles:
            result._obj.value = self.handle(self.handles[handle])
        else:
            self.serial += 1
            result._obj.value = self.serial
        return 1

    def ResumeThread(self, thread):
        self.events.append("resume")
        return 0xFFFFFFFF if self.fail == "resume" else 1

    def cim(self, *_args, **_kwargs):
        if self.fail == "enumerate":
            raise OSError("CIM unavailable")
        rows = [{"ProcessId": 1, "ParentProcessId": 0, "CreationDate": "0001", "CommandLine": "system"}]
        for pid in self.live:
            token = self.members.get(pid, "").removeprefix("Local\\omp-strata-")
            rows.append({"ProcessId": pid, "ParentProcessId": 1, "CreationDate": str(pid),
                         "CommandLine": "python -X omp_strata_tree=" + token})
        return SimpleNamespace(returncode=0, stdout=json.dumps(rows))


class ProcessJobTests(unittest.TestCase):
    def setUp(self):
        self.kernel = KernelStub()
        self.token = "a" * 32
        self.job = lifecycle.ProcessJob(self.token, kernel=self.kernel)
        self.addCleanup(patch.stopall)
        patch.object(lifecycle.subprocess, "run", self.kernel.cim).start()

    def add_tree(self):
        for pid in (100, 101, 102):
            self.kernel.live[pid] = object()
            self.kernel.members[pid] = self.kernel.handles[self.job.handle]

    def test_limits_disable_both_breakaway_modes_and_stop_orphans(self):
        self.assertIn(("limits", 0x2000), self.kernel.events)
        self.add_tree()
        del self.kernel.live[100]
        self.job.stop()
        self.assertEqual(self.kernel.live, {})
        self.assertIsNone(self.job.handle)

    def test_all_kernel_and_independent_verification_failures_retain_handle(self):
        for failure in ("terminate", "query", "enumerate"):
            with self.subTest(failure=failure):
                self.add_tree()
                self.kernel.fail = failure
                with self.assertRaises(lifecycle.LifecycleError):
                    self.job.stop()
                self.assertIsNotNone(self.job.handle)
                self.kernel.fail = None
        self.job.stop()

    def test_foreign_token_is_never_terminated(self):
        other = lifecycle.ProcessJob("b" * 32, kernel=self.kernel)
        self.add_tree()
        self.kernel.live[999] = object()
        self.kernel.members[999] = self.kernel.handles[other.handle]
        self.job.stop()
        self.assertIn(999, self.kernel.live)

    def test_assignment_failure_prevents_spawn_and_borrowed_close_preserves_owner(self):
        self.kernel.fail = "assign"
        with self.assertRaises(lifecycle.LifecycleError):
            self.job.assign(100)
        self.kernel.fail = None
        borrowed = lifecycle.ProcessJob(self.token, kernel=self.kernel, existing=True)
        self.add_tree()
        borrowed.close()
        self.assertEqual(set(self.kernel.live), {100, 101, 102})
        self.job.stop()

    def test_cim_unavailable_still_terminates_but_cannot_release(self):
        self.add_tree()
        self.kernel.fail = "enumerate"
        with self.assertRaisesRegex(lifecycle.LifecycleError, "retain custody"):
            self.job.stop()
        self.assertEqual(self.kernel.live, {})
        self.assertIsNotNone(self.job.handle)

    def test_unsupported_platform_refuses_before_effects(self):
        with patch.object(lifecycle, "WINDOWS", False), self.assertRaisesRegex(
                lifecycle.LifecycleError, "unsupported"):
            lifecycle.ProcessJob(self.token)

    def test_handoff_duplicate_preserves_only_explicit_restored_generation(self):
        self.add_tree()
        with patch.object(lifecycle.procs, "matches", return_value=SimpleNamespace(pid=100)):
            self.job.handoff({"pid": 100})
        self.job.close()
        self.assertEqual(set(self.kernel.live), {100, 101, 102})
        self.assertIn("duplicate", self.kernel.events)

    def test_empty_or_malformed_cim_is_not_empty_tree_proof(self):
        for value in ([], {}, [{"ProcessId": 100}], None):
            with self.subTest(value=value), patch.object(lifecycle.subprocess, "run", return_value=SimpleNamespace(
                    stdout=json.dumps(value))), self.assertRaises(lifecycle.LifecycleError):
                self.job.stop()
        self.assertIsNotNone(self.job.handle)

    def test_suspended_native_spawn_assigns_before_resume_and_cleans_failed_assignment(self):
        for fail in (None, "assign", "resume"):
            with self.subTest(fail=fail):
                self.kernel.fail = fail
                self.kernel.events.clear()
                captured = {}

                def create(exe, line, pa, ta, inherit, flags, env, cwd, startup):
                    captured.update(exe=exe, line=line, flags=flags, env=env, startup=startup)
                    self.kernel.events.append("create_suspended")
                    self.kernel.live[100] = object()
                    return 100, 101, 100, 101

                def terminate(handle, _code):
                    self.kernel.live.pop(handle, None)

                api = SimpleNamespace(CreateProcess=create, CloseHandle=lambda _handle: None,
                    TerminateProcess=terminate, GetExitCodeProcess=lambda _handle: 1,
                    WaitForSingleObject=lambda handle, _ms: 258 if handle in self.kernel.live else 0)
                with patch.dict(sys.modules, {"_winapi": api,
                                             "msvcrt": SimpleNamespace(get_osfhandle=lambda fd: fd)}), \
                        patch.object(lifecycle.subprocess, "STARTUPINFO", SimpleNamespace, create=True), \
                        tempfile.TemporaryFile() as out:
                    if fail:
                        with self.assertRaises(lifecycle.LifecycleError):
                            self.job.spawn(["python.exe", "command.py"], stdout=out, stderr=out, env={})
                        self.assertNotIn(100, self.kernel.live)
                    else:
                        child = self.job.spawn(["python.exe", "command.py"], stdout=out, stderr=out, env={})
                        self.assertLess(self.kernel.events.index("assign"), self.kernel.events.index("resume"))
                        self.assertIsNone(child.poll())
                        child.kill()
                        child.wait(timeout=30)
                    self.assertTrue(captured["flags"] & 0x4)
                    self.assertEqual(captured["env"][lifecycle.TREE_TOKEN_ENV], self.token)
                    self.assertIn("omp_strata_tree=" + self.token, captured["line"])
                    self.kernel.members.pop(100, None)

    def test_partial_cim_missing_a_live_job_member_fails_closed(self):
        self.add_tree()
        with patch.object(lifecycle.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps([
                {"ProcessId": 1, "ParentProcessId": 0, "CreationDate": "1", "CommandLine": "system"}]))):
            with self.assertRaises(lifecycle.LifecycleError):
                self.job.stop()
        self.assertIsNotNone(self.job.handle)

    def test_experiment_wrapper_uses_native_job_not_a_late_wmi_broker(self):
        detached = []
        child = SimpleNamespace(detach=lambda: detached.append(True))
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(lifecycle, "WINDOWS", True), \
                patch.object(lifecycle, "_job_kernel", return_value=self.kernel), \
                patch.object(lifecycle.ProcessJob, "spawn", return_value=child) as spawn, \
                patch.object(lifecycle.subprocess, "run", side_effect=AssertionError("WMI dispatch")):
            lifecycle._launch_detached(["python.exe", "serve.py"], cwd=Path(directory),
                log=Path(directory) / "new-logs" / "serve.log", job_token=self.token)
            self.assertEqual(detached, [True])
            self.assertEqual(spawn.call_args.kwargs["cwd"], Path(directory))
        self.assertIsNotNone(self.job.handle)

    def test_repeated_stop_rechecks_independent_enumeration(self):
        self.add_tree()
        self.job.stop()
        self.job.stop()
        self.kernel.fail = "enumerate"
        with self.assertRaises(OSError):
            self.job.stop()

    def test_unrelated_system_process_without_creation_date_is_not_owned(self):
        with patch.object(lifecycle.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps([
                {"ProcessId": 0, "ParentProcessId": 0, "CreationDate": None, "CommandLine": None}]))):
            self.job.stop()
        self.assertIsNone(self.job.handle)
