"""생성 회로도의 KiCad 형식 번호 검사(#139).

    python -m unittest test_kicad_version    `python tasks.py check`가 같이 돌린다(작업 이름 kicadver)

생성기는 설치된 KiCad 심볼 라이브러리에서 심볼 정의를 복사한다. 그래서 파일 머리의 형식 번호가
복사한 라이브러리의 KiCad 버전과 같아야 한다. 예전에는 KiCad 9 번호(20250114)를 적고 KiCad 10
토큰(in_pos_files)을 복사해서 KiCad 9.0.9가 파일을 열지 못했다.
CI에는 KiCad가 없다. 그래서 KiCad로 여는 확인은 PR에서 사람이나 에이전트가 하고, 여기서는
커밋된 생성물의 머리와 라이브러리 버전 판정만 본다. 표준 라이브러리만 쓴다.
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "kicad" / "_tools"))
import gen_schematic  # noqa: E402  (위 경로를 넣은 뒤에 불러야 한다)

SCHEMATIC = ROOT / "kicad" / "cosmos-avionics" / "cosmos-avionics.kicad_sch"


def write_libraries(folder, version):
    """folder에 생성기가 읽는 라이브러리 파일 3개를 version 머리로 만든다."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in gen_schematic.LIB_FILES.values():
        (folder / name).write_text(
            f'(kicad_symbol_lib\n\t(version {version})\n\t(generator "kicad_symbol_editor")\n)\n',
            encoding="utf-8")
    return folder


class CommittedSchematic(unittest.TestCase):
    def test_header_matches_generator(self):
        # 생성기 상수만 바꾸고 재생성을 빠뜨리거나, 머리를 손으로 고치면 여기서 걸린다.
        head = SCHEMATIC.read_text(encoding="utf-8")[:400]
        version = re.search(r"\(version (\d+)\)", head)
        generator_version = re.search(r'\(generator_version "([^"]*)"\)', head)
        self.assertIsNotNone(version, head)
        self.assertIsNotNone(generator_version, head)
        self.assertEqual(int(version.group(1)), gen_schematic.SCH_FILE_VERSION)
        self.assertEqual(generator_version.group(1), gen_schematic.SCH_GENERATOR_VERSION)


class LibraryVersion(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_kicad10_library_is_accepted(self):
        folder = write_libraries(self.tmp / "k10", gen_schematic.KICAD10_SYMBOL_LIB_VERSION)
        self.assertIsNone(gen_schematic._library_problem(folder))

    def test_kicad9_and_newer_libraries_are_rejected(self):
        cases = {
            "KiCad 9": gen_schematic.KICAD9_SYMBOL_LIB_VERSION,
            "KiCad 10보다 새 형식": gen_schematic.KICAD10_SYMBOL_LIB_VERSION + 1,
        }
        for name, version in cases.items():
            with self.subTest(name):
                folder = write_libraries(self.tmp / str(version), version)
                problem = gen_schematic._library_problem(folder)
                self.assertIsNotNone(problem)
                self.assertIn(str(version), problem)

    def test_missing_header_is_rejected(self):
        folder = write_libraries(self.tmp / "k10", gen_schematic.KICAD10_SYMBOL_LIB_VERSION)
        (folder / "Device.kicad_sym").write_text("(kicad_symbol_lib)\n", encoding="utf-8")
        self.assertIn("Device.kicad_sym", gen_schematic._library_problem(folder))

    def test_override_with_kicad9_library_stops(self):
        folder = write_libraries(self.tmp / "k9", gen_schematic.KICAD9_SYMBOL_LIB_VERSION)
        with self.assertRaises(SystemExit) as caught:
            gen_schematic.find_symbols_dir(str(folder))
        self.assertIn("KiCad 10", str(caught.exception))

    def test_auto_detect_skips_kicad9_library(self):
        # KICAD_SYMBOL_DIR가 KiCad 9를 가리켜도 건너뛰고 다음 후보인 KiCad 10을 고른다.
        k9 = write_libraries(self.tmp / "k9", gen_schematic.KICAD9_SYMBOL_LIB_VERSION)
        k10 = write_libraries(self.tmp / "k10", gen_schematic.KICAD10_SYMBOL_LIB_VERSION)
        env = {"KICAD_SYMBOL_DIR": str(k9), "KICAD10_SYMBOL_DIR": str(k10)}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(gen_schematic.find_symbols_dir(None), k10)


if __name__ == "__main__":
    unittest.main()
