"""tasks.py의 parity 작업(#408) 중 컴파일러 찾기와 건너뛰기 판정의 단위 검사.

    python -m unittest test_hostcxx    `python tasks.py parity`와 `python tasks.py check`가 같이 돌린다

C++ 컴파일러, .venv, SB3 없이 돈다. 부원 PC(Windows)에서 컴파일러가 없어도 그대로 돈다.
검사하는 것: 컴파일러가 없으면 PC에서는 건너뛰고 CI에서는 실패한다. 이 판정이 틀리면 부원 PC의
`python tasks.py check`가 깨지거나, CI가 비교 검사를 조용히 빼먹는다.
"""
import contextlib
import io
import os
import subprocess
import unittest
from unittest import mock

import tasks


def fake_which(found):
    return lambda name: found.get(name)


class FindHostCxx(unittest.TestCase):
    def test_none_when_nothing_on_path(self):
        with mock.patch.object(tasks.shutil, "which", fake_which({})):
            self.assertIsNone(tasks.find_host_cxx())

    def test_uses_first_name_that_runs(self):
        ok = subprocess.CompletedProcess([], 0)
        with mock.patch.object(tasks.shutil, "which", fake_which({"g++": "/x/g++", "clang++": "/x/clang++"})), \
                mock.patch.object(tasks.subprocess, "run", return_value=ok) as run:
            self.assertEqual(tasks.find_host_cxx(), "/x/g++")
        self.assertEqual(run.call_args.args[0], ["/x/g++", "--version"])

    def test_skips_compiler_whose_version_fails(self):
        def run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1 if cmd[0] == "/x/c++" else 0)
        with mock.patch.object(tasks.shutil, "which", fake_which({"c++": "/x/c++", "g++": "/x/g++"})), \
                mock.patch.object(tasks.subprocess, "run", side_effect=run):
            self.assertEqual(tasks.find_host_cxx(), "/x/g++")

    def test_skips_compiler_that_cannot_start(self):
        with mock.patch.object(tasks.shutil, "which", fake_which({"c++": "/x/c++"})), \
                mock.patch.object(tasks.subprocess, "run", side_effect=OSError("bad exe")):
            self.assertIsNone(tasks.find_host_cxx())

    def test_cl_is_accepted_without_version_flag(self):
        with mock.patch.object(tasks.shutil, "which", fake_which({"cl": "/x/cl"})), \
                mock.patch.object(tasks.subprocess, "run") as run:
            self.assertEqual(tasks.find_host_cxx(), "/x/cl")
        run.assert_not_called()

    def test_fingerprint_changes_with_compiler(self):
        with mock.patch.object(tasks, "find_host_cxx", return_value=None):
            self.assertEqual(tasks.host_cxx_fingerprint(), "no-cxx")
        with mock.patch.object(tasks, "find_host_cxx", return_value="/x/g++"):
            self.assertEqual(tasks.host_cxx_fingerprint(), "/x/g++")


class ParityWithoutCompiler(unittest.TestCase):
    def run_task(self, env):
        out = io.StringIO()
        with mock.patch.object(tasks, "find_host_cxx", return_value=None), \
                mock.patch.object(tasks, "run"), \
                mock.patch.object(tasks, "uv_run") as uv_run, \
                mock.patch.dict(os.environ, env), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            if "CI" not in env:
                os.environ.pop("CI", None)
            try:
                result = tasks.task_parity()
            except SystemExit as exit_info:
                return exit_info.code, out.getvalue(), uv_run
        return result, out.getvalue(), uv_run

    def test_skips_off_ci_and_says_why(self):
        result, out, uv_run = self.run_task({})
        self.assertIs(result, tasks.SKIPPED)
        self.assertIn("[건너뜀] parity", out)
        self.assertIn("컴파일러", out)
        uv_run.assert_not_called()

    def test_fails_on_ci(self):
        result, out, uv_run = self.run_task({"CI": "true"})
        self.assertEqual(result, 1)
        uv_run.assert_not_called()


class ParityWithCompiler(unittest.TestCase):
    def test_runs_unit_test_then_parity_with_that_compiler(self):
        with mock.patch.object(tasks, "find_host_cxx", return_value="/x/g++"), \
                mock.patch.object(tasks, "run"), \
                mock.patch.object(tasks, "uv_run") as uv_run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(tasks.task_parity())
        self.assertEqual([c.args[0] for c in uv_run.call_args_list],
                         [["python", "test_normalization.py"],
                          ["python", "check_parity.py", "--cxx", "/x/g++"]])
        self.assertTrue(all(c.kwargs["cwd"] == tasks.DEPLOY for c in uv_run.call_args_list))


class ParityWiring(unittest.TestCase):
    def test_check_depends_on_parity(self):
        self.assertIn("parity", tasks.TASKS["check"].deps)

    def test_parity_makes_the_bench_header(self):
        header = tasks.PARITY_HEADER.relative_to(tasks.ROOT).as_posix()
        self.assertIn(header, tasks.TASKS["parity"].outputs)


if __name__ == "__main__":
    unittest.main()
