"""tasks.py의 Windows VC++ 런타임 확인(#108) 단위 검사.

    python -m unittest test_vcruntime    `python tasks.py check`가 같이 돌린다(작업 이름 vcruntime)

실제 확인은 Windows에서만 돈다. CI는 Linux라서 그 경로를 한 번도 지나지 않는다. 그래서 여기서
DLL 로더(ctypes.WinDLL)와 자식 프로세스 응답을 가짜로 바꿔 검사 코드와 판정을 돌린다.
표준 라이브러리만 쓴다. 부원 PC(Windows)에서도 그대로 돈다.
"""
import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import tasks

ALL = ["vcruntime140.dll", "msvcp140.dll", "vcruntime140_1.dll"]


def run_probe(missing=(), machine="AMD64"):
    """VC_PROBE를 이 프로세스에서 실행한다. (출력한 JSON, WinDLL 호출 목록)을 돌려준다.

    missing에 든 이름은 실제 Windows처럼 OSError(WinError 126)를 낸다.
    """
    calls = []

    def fake_windll(name, **kwargs):
        calls.append((name, kwargs))
        if name in missing:
            raise OSError(22, "지정된 모듈을 찾을 수 없습니다", None, 126)
        return object()

    out = io.StringIO()
    # Linux의 ctypes에는 WinDLL이 없어서 create=True로 만든다.
    with mock.patch("ctypes.WinDLL", fake_windll, create=True), \
            mock.patch("platform.machine", return_value=machine), redirect_stdout(out):
        exec(compile(tasks.VC_PROBE, "<VC_PROBE>", "exec"), {"__name__": "__main__"})
    return json.loads(out.getvalue()), calls


class Probe(unittest.TestCase):
    """VC_PROBE: .venv 파이썬에서 실제로 실행하는 검사 코드."""

    def test_all_found(self):
        missing, calls = run_probe()
        self.assertEqual(missing, [])
        self.assertEqual([name for name, _ in calls], ALL)

    def test_reports_missing_in_order(self):
        # #108 VM에서 System32에 없던 두 파일이다.
        missing, _ = run_probe(missing={"vcruntime140_1.dll", "msvcp140.dll"})
        self.assertEqual(missing, ["msvcp140.dll", "vcruntime140_1.dll"])

    def test_keeps_checking_after_a_miss(self):
        missing, calls = run_probe(missing={"vcruntime140.dll"})
        self.assertEqual(missing, ["vcruntime140.dll"])
        self.assertEqual(len(calls), 3)

    def test_arm64_skips_vcruntime140_1(self):
        # torch/__init__.py도 ARM64에서는 vcruntime140_1.dll을 불러 보지 않는다.
        missing, calls = run_probe(missing={"vcruntime140_1.dll"}, machine="ARM64")
        self.assertEqual(missing, [])
        self.assertEqual([name for name, _ in calls], ALL[:2])

    def test_searches_path_like_torch_fallback(self):
        # winmode=0이어야 Windows 기본 검색 순서(PATH 포함)로 찾는다. 기본값 None은 PATH를 보지 않는다.
        _, calls = run_probe()
        for name, kwargs in calls:
            with self.subTest(name):
                self.assertEqual(kwargs, {"winmode": 0})


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class ProbeResult(unittest.TestCase):
    """probe_vc_runtime: 자식 파이썬의 응답을 목록 또는 None(확인 못 함)으로 바꾼다."""

    def probe(self, **kw):
        with mock.patch.object(tasks.subprocess, "run", **kw) as run:
            return tasks.probe_vc_runtime("venv-python"), run

    def test_runs_probe_isolated_in_given_python(self):
        missing, run = self.probe(return_value=completed('["msvcp140.dll"]\n'))
        self.assertEqual(missing, ["msvcp140.dll"])
        self.assertEqual(run.call_args.args[0], ["venv-python", "-I", "-c", tasks.VC_PROBE])
        self.assertIn("timeout", run.call_args.kwargs)

    def test_empty_list_means_all_found(self):
        missing, _ = self.probe(return_value=completed("[]\n"))
        self.assertEqual(missing, [])

    def test_reads_last_line(self):
        missing, _ = self.probe(return_value=completed('다른 출력\n["msvcp140.dll"]\n'))
        self.assertEqual(missing, ["msvcp140.dll"])

    def test_cannot_tell(self):
        cases = {
            "자식 실패": dict(return_value=completed('[]', returncode=1)),
            "출력 없음": dict(return_value=completed("")),
            "출력 None": dict(return_value=completed(None)),
            "JSON 아님": dict(return_value=completed("Traceback ...")),
            "목록 아님": dict(return_value=completed('{"a": 1}')),
            "문자열 아닌 항목": dict(return_value=completed("[1]")),
            ".venv 파이썬 없음": dict(side_effect=FileNotFoundError("python.exe")),
            "시간 초과": dict(side_effect=subprocess.TimeoutExpired("python", 120)),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                missing, _ = self.probe(**kw)
                self.assertIsNone(missing)


class Ensure(unittest.TestCase):
    """ensure_vc_runtime: Windows에서만 확인하고, 없으면 설치 방법을 출력하고 멈춘다."""

    def ensure(self, probe_result, windows=True):
        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(tasks, "probe_vc_runtime", return_value=probe_result) as probe, \
                redirect_stderr(err), redirect_stdout(out):
            try:
                tasks.ensure_vc_runtime(windows=windows)
                code = None
            except SystemExit as e:
                code = e.code
        return code, err.getvalue() + out.getvalue(), probe

    def test_not_windows_does_nothing(self):
        code, text, probe = self.ensure(["msvcp140.dll"], windows=False)
        self.assertIsNone(code)
        self.assertEqual(text, "")
        probe.assert_not_called()

    def test_default_follows_os(self):
        # 이 검사를 Windows에서 돌리면 실제 OS가 Windows라서 확인이 돈다. 그 경우는 따로 본다.
        with mock.patch.object(tasks.os, "name", "posix"), \
                mock.patch.object(tasks, "probe_vc_runtime") as probe:
            tasks.ensure_vc_runtime()
        probe.assert_not_called()

    def test_missing_stops_with_install_steps(self):
        code, text, probe = self.ensure(["msvcp140.dll", "vcruntime140_1.dll"])
        self.assertEqual(code, 1)
        probe.assert_called_once_with(tasks.venv_python())
        for needed in ("winget install --id Microsoft.VCRedist.2015+.x64 --exact --source winget",
                       "https://aka.ms/vc14/vc_redist.x64.exe",
                       "msvcp140.dll, vcruntime140_1.dll", "c10.dll", "#108"):
            with self.subTest(needed):
                self.assertIn(needed, text)

    def test_all_found_is_silent(self):
        code, text, _ = self.ensure([])
        self.assertIsNone(code)
        self.assertEqual(text, "")

    def test_cannot_tell_warns_and_continues(self):
        code, text, _ = self.ensure(None)
        self.assertIsNone(code)
        self.assertIn("[경고]", text)
        self.assertIn(tasks.VC_INSTALL_CMD, text)


class Wiring(unittest.TestCase):
    """확인이 setup과 torch를 쓰는 작업 앞에서 도는지 본다."""

    def test_torch_tasks_are_marked(self):
        # torch를 불러오는 작업: smoke와 train은 stable_baselines3, conncheck는 torch를 직접 불러온다.
        marked = {name for name, task in tasks.TASKS.items() if task.needs_torch}
        self.assertEqual(marked, {"smoke", "conncheck", "train"})

    def ensure_env(self, name):
        order = mock.Mock()
        with mock.patch.object(tasks, "sync_to_lock", order.sync), \
                mock.patch.object(tasks, "ensure_vc_runtime", order.vc):
            tasks.ensure_env(name)
        return [c[0] for c in order.mock_calls]

    def test_check_probes_once_after_sync(self):
        self.assertEqual(self.ensure_env("check"), ["sync", "vc"])

    def test_train_probes(self):
        self.assertEqual(self.ensure_env("train"), ["sync", "vc"])

    def test_env_task_without_torch_skips_probe(self):
        self.assertEqual(self.ensure_env("sanity"), ["sync"])

    def test_task_without_env_does_nothing(self):
        self.assertEqual(self.ensure_env("shiptest"), [])

    def test_setup_probes_before_reporting_success(self):
        order = mock.Mock()
        out = io.StringIO()
        with mock.patch.object(tasks, "sync_to_lock", order.sync), \
                mock.patch.object(tasks, "ensure_vc_runtime", order.vc), redirect_stdout(out):
            order.vc.side_effect = SystemExit(1)
            with self.assertRaises(SystemExit):
                tasks.task_setup()
        self.assertEqual([c[0] for c in order.mock_calls], ["sync", "vc"])
        self.assertNotIn("설치 완료", out.getvalue())

    def test_check_runs_this_test(self):
        self.assertIn("vcruntime", tasks.TASKS["check"].deps)


if __name__ == "__main__":
    unittest.main()
