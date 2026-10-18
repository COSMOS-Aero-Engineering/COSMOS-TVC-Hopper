"""tasks.py의 cp949 검사(#171) 단위 검사. 검사기가 걸러야 할 출력 문자열을 실제로 거르는지 본다.

    python -m unittest test_cp949    `python tasks.py check`가 같이 돌린다(작업 이름 cp949)

검사기가 고장 나면 아무것도 못 찾고 조용히 통과한다. 그래서 걸려야 하는 예와 걸리면 안 되는
예를 여기에 둔다. 이 파일도 cp949 검사 대상이다. 그래서 cp949에 없는 글자는 `\\u2014` 처럼
이스케이프로 적는다. 표준 라이브러리만 쓴다. 부원 PC(Windows)에서도 그대로 돈다.
"""
import unittest

import tasks

EM = "\u2014"  # em dash. cp949에 없다.

# 이름: (소스, 찾아야 할 (줄, 글자, 자리) 목록)
MUST_HIT = {
    # #147에서 고친 sim/sim_stage1/train.py:44의 옛 문자열
    "옛 train.py:44": (f'print("학습 완료 {EM} hopper_attitude_ppo.zip 저장됨")\n',
                       [(1, EM, "print")]),
    # #170에서 고친 sim/connectome/check.py:43의 옛 문자열(f-string 안의 고정된 부분)
    "옛 check.py:43 f-string": (
        f'print(f"  [{{mark}}] {{label}}" + (f" {EM} {{detail}}" if detail else ""))\n',
        [(1, EM, "print")]),
    "stderr로 내는 print": (f'print("a {EM} b", file=sys.stderr)\n', [(1, EM, "print")]),
    "sep 인자": (f'print("a", "b", sep=" {EM} ")\n', [(1, EM, "print")]),
    "raise": (f'raise ValueError("edge_w {EM} x")\n', [(1, EM, "raise")]),
    "sys.exit": (f'sys.exit("a {EM} b")\n', [(1, EM, "sys.exit")]),
    "die": (f'die(f"{{n}}건 {EM} 고칠 것")\n', [(1, EM, "die")]),
    "sys.stdout.write": (f'sys.stdout.write("a {EM} b\\n")\n', [(1, EM, "sys.stdout.write")]),
    "여러 줄 호출의 리터럴 줄": (f'x = 1\nprint(\n    "ok",\n    "a {EM} b",\n)\n',
                           [(4, EM, "print")]),
    "BMP 밖 글자": ('print("done \\U0001f600")\n', [(1, "\U0001f600", "print")]),
    "한 리터럴의 같은 글자 두 번은 한 건": (f'print("{EM}a{EM}")\n', [(1, EM, "print")]),
}

MUST_PASS = {
    "cp949에 있는 글자": 'print("한글 · → … § ° ± × ① ㄱ")\n',
    "출력하지 않는 리터럴(SVG 같은 파일 쓰기)": (
        f'LABEL = "a {EM} b"\nf.write("<text>{EM}</text>")\nout.write_text("{EM}")\n'),
    "docstring과 주석": f'def f():\n    """설명 {EM} 여기."""\n    # 주석 {EM}\n    return 1\n',
    "file= 인자": f'print("ok", file=open("{EM}.txt", "w"))\n',
    # 알려진 한계: 변수에 담았다가 출력하는 글은 보지 않는다(#169의 ste-ko-lint.py가 이 경우였다).
    "변수에 담은 글": f'msg = "a {EM} b"\nprint(msg)\n',
}


class FindNonCp949(unittest.TestCase):
    def test_hits_every_form(self):
        for name, (source, want) in MUST_HIT.items():
            with self.subTest(name):
                got = [(line, ch, where) for line, _, ch, where in tasks.find_non_cp949(source)]
                self.assertEqual(got, want)

    def test_passes_safe_source(self):
        for name, source in MUST_PASS.items():
            with self.subTest(name):
                self.assertEqual(tasks.find_non_cp949(source), [])

    def test_column_points_at_literal(self):
        # 칸은 1부터 센다. `print(` 6글자 뒤의 따옴표가 7번째 칸이다.
        hits = tasks.find_non_cp949(f'print("{EM}")\n')
        self.assertEqual([(h[0], h[1]) for h in hits], [(1, 7)])

    def test_syntax_error_is_raised(self):
        with self.assertRaises(SyntaxError):
            tasks.find_non_cp949("print(\n")


if __name__ == "__main__":
    unittest.main()
