"""tasks.py의 cad 검사(#61) 단위 검사. 검사기가 걸러야 할 출력을 실제로 거르는지 본다.

    python -m unittest test_cadcheck    `python tasks.py cad`와 `python tasks.py check`가 같이 돌린다

검사기가 고장 나면 아무것도 못 찾고 조용히 통과한다. 그래서 실패해야 하는 예를 여기에 둔다.
- 출력 판정(scan_cad_output)은 OpenSCAD 없이 돈다.
- OpenSCAD로 진짜 .scad를 돌리는 검사는 OpenSCAD가 있을 때만 돈다. CI는 OpenSCAD를 설치하므로
  CI에서는 항상 돈다. 없는 PC에서는 건너뛴다.
표준 라이브러리만 쓴다. 부원 PC(Windows)에서도 그대로 돈다.
"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import tasks

OPENSCAD = tasks.find_openscad()


class ScanOutput(unittest.TestCase):
    def test_normal_echo(self):
        echoes, alarms, problems = tasks.scan_cad_output('ECHO: "간격 3mm → 정상"\n')
        self.assertEqual(len(echoes), 1)
        self.assertEqual(alarms, [])
        self.assertEqual(problems, [])

    def test_alarm(self):
        _, alarms, _ = tasks.scan_cad_output('ECHO: "정상"\nECHO: "!! 겹침 !!"\n')
        self.assertEqual(alarms, ['ECHO: "!! 겹침 !!"'])

    def test_warning_and_error(self):
        text = ("WARNING: Ignoring unknown variable 'x' in file a.scad, line 1\n"
                "ERROR: Parser error: syntax error in file a.scad, line 3\n"
                "TRACE: called by 'echo' in file a.scad, line 1\n")
        _, _, problems = tasks.scan_cad_output(text)
        self.assertEqual(len(problems), 2)

    def test_windows_newlines(self):
        echoes, alarms, _ = tasks.scan_cad_output('ECHO: "a"\r\nECHO: "!! b"\r\n')
        self.assertEqual(len(echoes), 2)
        self.assertEqual(len(alarms), 1)


class SkipWithoutOpenscad(unittest.TestCase):
    def setUp(self):
        # task_cad는 맨 처음 이 단위 검사를 다시 부른다. 여기서는 그 호출을 막는다.
        patcher = mock.patch.object(tasks, "run")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_skip_locally(self):
        env = {k: v for k, v in os.environ.items() if k != "CI"}
        with mock.patch.object(tasks, "find_openscad", return_value=None), \
                mock.patch.dict(os.environ, env, clear=True), redirect_stdout(io.StringIO()) as out:
            self.assertIs(tasks.task_cad(), tasks.SKIPPED)
        self.assertIn("[건너뜀] cad", out.getvalue())

    def test_fail_in_ci(self):
        with mock.patch.object(tasks, "find_openscad", return_value=None), \
                mock.patch.dict(os.environ, {"CI": "true"}), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                tasks.task_cad()
        self.assertEqual(cm.exception.code, 1)

    def test_skip_is_not_cached(self):
        task = tasks.Task("fake_skip", "건너뛰는 가짜 작업", lambda: tasks.SKIPPED)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(tasks.TASKS, {"fake_skip": task}), \
                mock.patch.object(tasks, "CACHE_DIR", Path(tmp)), \
                mock.patch.object(tasks, "SKIPPED_TASKS", []) as skipped, \
                redirect_stdout(io.StringIO()):
            tasks.execute("fake_skip", mock.Mock(force=False), {}, set())
            self.assertFalse((Path(tmp) / "fake_skip").exists())
            self.assertEqual(skipped, ["fake_skip"])


@unittest.skipUnless(OPENSCAD, "OpenSCAD가 없다")
class RealOpenscad(unittest.TestCase):
    """작은 .scad로 check_cad_file이 실패해야 할 때 실패하는지 본다."""

    def check(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            scad = Path(tmp) / "t.scad"
            scad.write_text(source, encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                return tasks.check_cad_file(OPENSCAD, scad, tmp)

    def test_pass(self):
        src = 'render_mode = "preview";\ncube(1);\necho(str("간격 ", 3, "mm → 정상"));\n'
        self.assertEqual(self.check(src), [])

    def test_alarm_fails(self):
        src = 'render_mode = "preview";\necho("!! 겹침 !!");\n'
        self.assertTrue(any("'!!'" in f for f in self.check(src)))

    def test_unknown_variable_fails(self):
        src = 'render_mode = "preview";\necho(str("x=", no_such_var));\n'
        self.assertTrue(any("WARNING" in f for f in self.check(src)))

    def test_unknown_module_only_in_print_branch_fails(self):
        src = ('render_mode = "preview";\necho("정상");\n'
               'if (render_mode == "print") no_such_module();\n')
        failures = self.check(src)
        self.assertTrue(any(f.startswith("print:") for f in failures))
        self.assertFalse(any(f.startswith("preview:") for f in failures))

    def test_syntax_error_fails(self):
        self.assertTrue(any("exit" in f for f in self.check('echo("a")\ncube(1)\n')))

    def test_no_echo_fails(self):
        self.assertTrue(any("0줄" in f for f in self.check('render_mode = "preview";\ncube(1);\n')))


if __name__ == "__main__":
    unittest.main()
