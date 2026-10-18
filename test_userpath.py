"""tasks.py의 userpath 검사(#96) 단위 검사. 검사기가 걸러야 할 경로를 실제로 거르는지 본다.

    python -m unittest test_userpath    `python tasks.py check`가 같이 돌린다(작업 이름 userpath)

검사기가 고장 나면 아무것도 못 찾고 조용히 통과한다. 그래서 걸려야 하는 예와 걸리면 안 되는
예를 여기에 둔다. 이 파일은 kicad/_tools 밖에 있어서 userpath 검사 대상이 아니다.
표준 라이브러리만 쓴다. 부원 PC(Windows)에서도 그대로 돈다.
"""
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import tasks

# 값은 소스 파일에 적힌 글자 그대로다. 문자열 안의 이중 역슬래시도 r"" 안에 두 글자로 적었다.
MUST_HIT = {
    "Windows 슬래시": ('KICAD = "C:/Users/x/y"', "C:/Users"),
    "Windows 역슬래시(raw 문자열)": (r'KICAD = r"C:\Users\x\y"', r"C:\Users"),
    "Windows 이중 역슬래시(일반 문자열)": (r'KICAD = "C:\\Users\\x\\y"', r"C:\\Users"),
    "Linux 사용자 폴더": ('OUT = "/home/x/y"', "/home/"),
    "macOS 사용자 폴더": ('OUT = "/Users/x/y"', "/Users/"),
    "C가 아닌 드라이브": (r'KICAD = r"D:\Users\x"', r"D:\Users"),
    "소문자 드라이브와 폴더": ('KICAD = "c:/users/x"', "c:/users"),
    "대문자 폴더": (r'KICAD = r"C:\USERS\x"', r"C:\USERS"),
    "Users 뒤 구분자 없음": (r'BASE = r"C:\Users"', r"C:\Users"),
    "WSL에서 본 Windows 폴더": ('OUT = "/mnt/c/Users/x"', "/Users/"),
    "Git Bash에서 본 Windows 폴더": ('OUT = "/c/Users/x"', "/Users/"),
    "Windows에서 본 WSL 폴더": (r'OUT = r"\\wsl.localhost\Ubuntu\home\x"', "\\home\\"),
    "긴 경로 접두사": (r'OUT = r"\\?\C:\Users\x"', r"C:\Users"),
    "file URL": ('URL = "file:///C:/Users/x"', "C:/Users"),
    "주석": ("# 예전 경로: /home/x/kicad", "/home/"),
}

# 지금 main의 kicad/_tools에 있는 시스템 경로와, 사용자 경로로 오해하기 쉬운 글자.
MUST_PASS = {
    "Linux 설치 폴더": '"/usr/share/kicad/symbols"',
    "Linux 로컬 설치 폴더": '"/usr/local/share/kicad/symbols"',
    "macOS 앱 폴더": '"/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"',
    "Windows 환경변수 경로": r'r"  %LOCALAPPDATA%\Programs\KiCad\<version>\share\kicad\symbols"',
    "Windows 설치 폴더": r'r"C:\Program Files\KiCad\9.0"',
    "설치 폴더 글롭": '"Programs/KiCad/*/share/kicad/symbols"',
    "홈 폴더를 실행 때 찾기": 'Path.home() / "x", os.path.expanduser("~/x")',
    "웹 API 주소(소문자 users)": '"https://api.github.com/users/x"',
    "Users로 시작하는 다른 폴더": r'r"C:\UsersGuide"',
    "한 글자가 아닌 접두사": '"ab:/users/x"',
    "낱말 Users와 home": '"Users must pass --out; home position"',
}


class FindUserPaths(unittest.TestCase):
    def test_hits_every_form(self):
        for name, (line, found) in MUST_HIT.items():
            with self.subTest(name):
                hits = tasks.find_user_paths(line)
                self.assertEqual(len(hits), 1, hits)
                self.assertEqual(hits[0][2], found)

    def test_passes_system_paths_and_lookalikes(self):
        for name, line in MUST_PASS.items():
            with self.subTest(name):
                self.assertEqual(tasks.find_user_paths(line), [])

    def test_line_and_column_start_at_one(self):
        text = "a = 1\nb = 2\nKICAD = 'C:/Users/x'\n"
        self.assertEqual(tasks.find_user_paths(text), [(3, 10, "C:/Users")])

    def test_form_feed_does_not_shift_line_numbers(self):
        # str.splitlines()는 폼 피드에서도 줄을 나눈다. 편집기와 파이썬은 나누지 않는다.
        text = "a = 1\x0cb = 2\nOUT = '/home/x'\n"
        self.assertEqual(tasks.find_user_paths(text), [(2, 8, "/home/")])

    def test_checker_does_not_hit_its_own_source(self):
        # tasks.py는 검사 대상이 아니다. 그래도 정규식과 주석이 자기 자신에 걸리지 않게 둔다(#96).
        source = Path(tasks.__file__).read_text(encoding="utf-8")
        self.assertEqual(tasks.find_user_paths(source), [])


class Registration(unittest.TestCase):
    def test_task_is_registered_and_wired_into_check(self):
        self.assertIn("userpath", tasks.TASKS)
        self.assertIn("userpath", tasks.TASKS["check"].deps)

    def test_scanned_files_are_cache_inputs(self):
        # 검사 대상이 inputs에 없으면 파일을 고쳐도 캐시 히트로 건너뛴다.
        for pattern in tasks.USER_PATH_SCAN:
            self.assertIn(pattern, tasks.TASKS["userpath"].inputs)


class ScanTree(unittest.TestCase):
    """임시 폴더를 저장소로 보고 scan_user_paths()와 task_userpath()를 돌린다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.tools = self.root / "kicad" / "_tools"
        self.tools.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text, newline="\n", encoding="utf-8"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode(encoding))

    def test_reports_file_and_line_only_inside_scan_scope(self):
        self.write("kicad/_tools/clean.py", "import os\n")
        self.write("kicad/_tools/dirty.py", "import os\nKICAD = 'C:/Users/x'\n", newline="\r\n")
        self.write("kicad/_tools/sub/deep.py", "OUT = '/home/x'\n")  # *.py는 하위 폴더를 보지 않는다
        self.write("kicad/README.md", "C:/Users/x\n")                 # 문서 예시는 제외(#96)
        files, hits = tasks.scan_user_paths(self.root, tasks.USER_PATH_SCAN)
        self.assertEqual(files, ["kicad/_tools/clean.py", "kicad/_tools/dirty.py"])
        self.assertEqual(hits, [("kicad/_tools/dirty.py", 2, 10, "C:/Users")])

    def test_bom_does_not_shift_first_line_column(self):
        # PowerShell 5.1의 Out-File -Encoding utf8은 파일 앞에 BOM을 붙인다. 편집기는 BOM을
        # 칸으로 세지 않는다. 그래서 BOM이 있어도 1줄 칸 번호가 BOM이 없을 때와 같아야 한다.
        self.write("kicad/_tools/bom.py", "KICAD = 'C:/Users/x'\n", encoding="utf-8-sig")
        _, hits = tasks.scan_user_paths(self.root, tasks.USER_PATH_SCAN)
        self.assertEqual(hits, [("kicad/_tools/bom.py", 1, 10, "C:/Users")])

    def run_task(self):
        out, err = io.StringIO(), io.StringIO()
        # run()은 이 단위 검사를 다시 부른다. 여기서는 막는다. 안 막으면 끝없이 반복한다.
        with mock.patch.object(tasks, "ROOT", self.root), mock.patch.object(tasks, "run"), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                tasks.task_userpath()
                code = 0
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def test_task_fails_with_file_and_line(self):
        self.write("kicad/_tools/gen.py", "import os\n\nOUT = '/Users/x/y'\n")
        code, out, err = self.run_task()
        self.assertEqual(code, 1)
        self.assertIn("kicad/_tools/gen.py:3:8: ", out)
        self.assertIn("1건", err)

    def test_task_passes_clean_tree(self):
        self.write("kicad/_tools/gen.py", "import os\n")
        code, out, _ = self.run_task()
        self.assertEqual(code, 0)
        self.assertIn("1개 파일 검사", out)

    def test_task_fails_when_nothing_to_scan(self):
        code, _, err = self.run_task()
        self.assertEqual(code, 1)
        self.assertIn("검사할 파일을 찾지 못했다", err)


if __name__ == "__main__":
    unittest.main()
