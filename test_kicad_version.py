"""생성 회로도의 KiCad 형식 번호와 저장 형식 검사(#139, #140).

    python -m unittest test_kicad_version    `python tasks.py check`가 같이 돌린다(작업 이름 kicadver)

생성기는 설치된 KiCad 심볼 라이브러리에서 심볼 정의를 복사한다. 그래서 파일 머리의 형식 번호가
복사한 라이브러리의 KiCad 버전과 같아야 한다. 예전에는 KiCad 9 번호(20250114)를 적고 KiCad 10
토큰(in_pos_files)을 복사해서 KiCad 9.0.9가 파일을 열지 못했다.
CI에는 KiCad가 없다. 그래서 KiCad로 여는 확인은 PR에서 사람이나 에이전트가 하고, 여기서는
커밋된 생성물의 머리와 라이브러리 버전 판정만 본다. 표준 라이브러리만 쓴다.
#140부터 생성기는 결과를 kicad-cli로 다시 저장한다. 그래서 KiCad에서 열어 편집 없이 저장해도
파일이 바뀌지 않는다. 여기서는 커밋된 파일이 그 형식인지와 kicad-cli 단계의 보조 함수를 본다.
#197부터 .kicad_pro의 PCB 설정(board.design_settings)과 .kicad_pcb가 함께 커밋됐는지도 본다.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "kicad" / "_tools"))
import gen_schematic  # noqa: E402  (위 경로를 넣은 뒤에 불러야 한다)

SCHEMATIC = ROOT / "kicad" / "cosmos-avionics" / "cosmos-avionics.kicad_sch"
PROJECT = SCHEMATIC.with_suffix(".kicad_pro")
BOARD = SCHEMATIC.with_suffix(".kicad_pcb")


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

    def test_saved_by_kicad(self):
        # kicad-cli 단계를 건너뛴 생성물을 커밋하면 여기서 걸린다. 그런 파일은 KiCad가 저장할 때
        # 수천 줄이 바뀐다(#140).
        self.assert_saved_by_kicad(SCHEMATIC)

    def test_saved_by_kicad_accepts_crlf(self):
        # Windows KiCad가 저장하면 작업 폴더의 파일이 CRLF가 된다. git은 .gitattributes(eol=lf)로
        # 커밋할 때 LF로 바꾸므로 diff가 없다. 이 검사도 그 파일을 통과시켜야 한다(PR #192).
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        crlf = Path(tmp.name) / SCHEMATIC.name
        crlf.write_bytes(SCHEMATIC.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assert_saved_by_kicad(crlf)

    def assert_saved_by_kicad(self, path):
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertIn('(generator "eeschema")', text[:400])
        self.assertTrue(text.endswith("\n\t(embedded_fonts no)\n)\n"), text[-200:])


def board_settings_problem(project, board):
    """.kicad_pro의 PCB 설정과 .kicad_pcb가 함께 있는지 본다(#197). 문제가 없으면 None."""
    settings = json.loads(project.read_text(encoding="utf-8"))
    has_settings = bool(settings.get("board", {}).get("design_settings"))
    if has_settings and not board.is_file():
        return (f"{project.name} has PCB settings (board.design_settings), but {board.name} "
                f"is not committed. KiCad writes these settings when the PCB editor saves a "
                f"board. Commit them only with the board, or restore {project.name}. "
                f"See kicad/README.md (#197).")
    if board.is_file() and not has_settings:
        return (f"{board.name} is committed, but {project.name} has no PCB settings "
                f"(board.design_settings). KiCad keeps the board design rules in "
                f"{project.name}. Commit the {project.name} that KiCad saved with the board. "
                f"See kicad/README.md (#197).")
    return None


class ProjectFile(unittest.TestCase):
    """.kicad_pro의 PCB 설정은 .kicad_pcb와 같은 PR에 커밋한다(#197, kicad/README.md)."""

    def test_committed_project_and_board_agree(self):
        self.assertIsNone(board_settings_problem(PROJECT, BOARD))

    def test_board_settings_without_board_fail(self):
        folder = Path(self._tmp_dir())
        project = folder / PROJECT.name
        project.write_text(json.dumps({"board": {"design_settings": {"rules": {}}}}),
                           encoding="utf-8")
        problem = board_settings_problem(project, folder / BOARD.name)
        self.assertIn("is not committed", problem)

    def test_board_without_board_settings_fails(self):
        folder = Path(self._tmp_dir())
        project = folder / PROJECT.name
        project.write_text(json.dumps({"board": {"design_settings": {}}}), encoding="utf-8")
        (folder / BOARD.name).write_text("(kicad_pcb)\n", encoding="utf-8")
        problem = board_settings_problem(project, folder / BOARD.name)
        self.assertIn("has no PCB settings", problem)

    def test_board_with_board_settings_passes(self):
        folder = Path(self._tmp_dir())
        project = folder / PROJECT.name
        project.write_text(json.dumps({"board": {"design_settings": {"rules": {}}}}),
                           encoding="utf-8")
        (folder / BOARD.name).write_text("(kicad_pcb)\n", encoding="utf-8")
        self.assertIsNone(board_settings_problem(project, folder / BOARD.name))

    def _tmp_dir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name


class KicadSave(unittest.TestCase):
    """생성기가 kicad-cli로 다시 저장하는 단계의 보조 함수(#140). KiCad 없이 돈다."""

    def test_embedded_fonts_line_is_added_before_last_paren(self):
        text = "(kicad_sch\n\t(sheet_instances)\n)\n"
        self.assertEqual(gen_schematic.add_embedded_fonts(text),
                         "(kicad_sch\n\t(sheet_instances)\n\t(embedded_fonts no)\n)\n")

    def test_embedded_fonts_line_is_not_added_twice(self):
        text = "(kicad_sch\n\t(embedded_fonts no)\n)\n"
        self.assertEqual(gen_schematic.add_embedded_fonts(text), text)

    def test_embedded_fonts_keeps_crlf(self):
        text = "(kicad_sch\r\n\t(sheet_instances)\r\n)\r\n"
        self.assertEqual(gen_schematic.add_embedded_fonts(text),
                         "(kicad_sch\r\n\t(sheet_instances)\r\n\t(embedded_fonts no)\r\n)\r\n")

    def test_crlf_output_of_kicad_cli_is_written_as_lf(self):
        # Windows kicad-cli는 CRLF로 쓴다. 생성기는 커밋된 파일과 같게 LF로 써야 한다(PR #192).
        def fake_kicad_cli(args, **kwargs):
            Path(args[-1]).write_bytes(
                b'(kicad_sch\r\n\t(generator "eeschema")\r\n\t(sheet_instances)\r\n)\r\n')
            return subprocess.CompletedProcess(args, 0, "", "")
        with mock.patch.object(gen_schematic.subprocess, "run", side_effect=fake_kicad_cli):
            saved = gen_schematic.save_with_kicad("(kicad_sch)\n", Path("kicad-cli"))
        self.assertEqual(saved, '(kicad_sch\n\t(generator "eeschema")\n\t(sheet_instances)\n'
                                '\t(embedded_fonts no)\n)\n')

    def test_unexpected_end_stops(self):
        with self.assertRaises(SystemExit):
            gen_schematic.add_embedded_fonts("(kicad_sch\n\t(sheet_instances))")

    def test_uuid_depends_only_on_key(self):
        # KiCad는 항목을 UUID 순서로 저장한다. UUID가 실행마다 바뀌면 항목 순서도 바뀐다.
        self.assertEqual(gen_schematic.u("wire/J1/1"), gen_schematic.u("wire/J1/1"))
        self.assertNotEqual(gen_schematic.u("wire/J1/1"), gen_schematic.u("label/J1/1"))

    def test_committed_schematic_uses_generator_uuids(self):
        # 커밋된 파일의 J1 UUID가 생성기 규칙과 같아야 재생성해도 diff가 없다.
        text = SCHEMATIC.read_text(encoding="utf-8")
        self.assertIn(gen_schematic.u("symbol/J1"), text)

    def test_kicad_cli_next_to_symbol_folder(self):
        exe = "kicad-cli.exe" if os.name == "nt" else "kicad-cli"
        prefix = Path(self._tmp_dir()) / "KiCad" / "10.0"
        symbols = prefix / "share" / "kicad" / "symbols"
        first = next(gen_schematic._kicad_cli_candidates(symbols))
        self.assertEqual(first, prefix / "bin" / exe)

    def test_kicad_cli_of_other_major_version_stops(self):
        cli = Path(self._tmp_dir()) / "kicad-cli"
        cli.write_text("", encoding="utf-8")
        with mock.patch.object(gen_schematic, "kicad_cli_version", return_value="9.0.9"):
            with self.assertRaises(SystemExit) as caught:
                gen_schematic.find_kicad_cli(str(cli), None)
        self.assertIn("9.0.9", str(caught.exception))
        with mock.patch.object(gen_schematic, "kicad_cli_version", return_value="10.0.6"):
            self.assertEqual(gen_schematic.find_kicad_cli(str(cli), None), (cli, "10.0.6"))

    def test_relative_kicad_cli_becomes_absolute(self):
        # kicad-cli는 임시 폴더를 작업 폴더로 삼아 돈다. 상대 경로를 그대로 두면 못 찾는다.
        folder = Path(self._tmp_dir())
        (folder / "kicad-cli").write_text("", encoding="utf-8")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(folder)
        with mock.patch.object(gen_schematic, "kicad_cli_version", return_value="10.0.7"):
            cli, _ = gen_schematic.find_kicad_cli("kicad-cli", None)
        self.assertEqual(cli, (folder / "kicad-cli").absolute())

    def _tmp_dir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name


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
