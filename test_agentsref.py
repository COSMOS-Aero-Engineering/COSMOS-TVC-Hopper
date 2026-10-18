"""tasks.py의 agentsref 검사(#183) 단위 검사. 없는 AGENTS.md 절 이름을 실제로 찾는지 본다.

    python -m unittest test_agentsref    `python tasks.py check`가 같이 돌린다(작업 이름 agentsref)

검사기가 고장 나면 아무 참조도 못 찾고 조용히 통과한다. 그래서 걸려야 하는 예와 걸리면 안 되는
예를 여기에 둔다. 이 파일은 없는 절 이름을 일부러 담으므로 agentsref 검사 대상에서 뺐다
(tasks.py의 AGENTS_REF_SKIP). 이 검사가 쓰는 파일 목록 함수 glob_inputs()도 여기서 본다.
표준 라이브러리만 쓴다. 부원 PC(Windows)에서도 그대로 돈다.
"""
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

import tasks

# 지금 AGENTS.md 제목과 같은 형식의 제목. 번호, 콜론, 끝 괄호가 있다.
AGENTS_TEXT = """# COSMOS

## 1. 핵심 규칙 (사람과 모든 AI 도구 공통, 2026-10-16)

## 2. 작업 순서: 이슈에서 PR까지 (ship-issue 방식, 2026-10-16)

## 3. 프로젝트 한눈에

## 7. 부원이 AI에게 자기 과제를 물을 때

## 8. 안전 원칙 (필수)

### 하위 제목은 절이 아니다

```
## 코드 블록 안의 줄도 절이 아니다
```

## 12. 교훈
"""
NAMES = tasks.agents_sections(AGENTS_TEXT)

# 다른 문서에서 맞는 참조. 지금 저장소에 있는 형식(백틱, 규칙 번호, 조사, 괄호)을 그대로 옮겼다.
MUST_PASS = {
    "백틱": "정본 절차는 `AGENTS.md` §작업 순서다.",
    "백틱 없음": "(AGENTS.md §작업 순서).",
    "규칙 번호": "사람만 하는 일(`AGENTS.md` §핵심 규칙 8)이면",
    "단계 번호": "AGENTS.md §작업 순서 1단계대로 한다.",
    "조사 의": "`AGENTS.md` §프로젝트 한눈에의 좌표계",
    "조사 에도": "AGENTS.md §교훈에도 한 줄 추가한다.",
    "겹친 조사 에서는": "`AGENTS.md` §교훈에서는 절 이름을 쓰라고 한다.",
    "조사 부터": "`AGENTS.md` §안전 원칙부터 읽는다.",
    "조사 까지": "`AGENTS.md` §작업 순서까지 끝낸다.",
    "서술격 조사 이다": "근거는 `AGENTS.md` §핵심 규칙이다.",
    "조사 으로": "`AGENTS.md` §교훈으로 옮긴다.",
    "어미 인지": "`AGENTS.md` §작업 순서인지 본다.",
    "한계: 한글 낱말이 이어짐": "`AGENTS.md` §교훈들",
    "공백 있는 긴 이름": "(`AGENTS.md` §부원이 AI에게 자기 과제를 물을 때). 그다음",
    "괄호 앞": "순서는 `AGENTS.md` §작업 순서(이슈 → PR)을 따른다.",
    "콜론 앞뒤 전체": "`AGENTS.md` §작업 순서: 이슈에서 PR까지",
    "괄호를 뺀 이름": "(#24, `AGENTS.md` §안전 원칙).",
    "줄 끝": "`AGENTS.md` §교훈",
    "AGENTS.md가 없는 §": "01 문서 §8.4, README §협업 규칙 6, §없는절",
}

# 다른 문서에서 틀린 참조와 오류 메시지에 나올 참조 글자.
MUST_HIT = {
    "없는 절": ("`AGENTS.md` §없는절을 본다.", "§없는절을 본다"),
    "백틱 없는 없는 절": ("AGENTS.md §없는절", "§없는절"),
    "공백을 뺀 이름": ("`AGENTS.md` §작업순서", "§작업순서"),
    "번호 참조": ("AGENTS.md §2", "§2"),
    "숫자가 이어짐": ("`AGENTS.md` §교훈2", "§교훈2"),
    "영문자가 이어짐": ("`AGENTS.md` §교훈s", "§교훈s"),
    "하위 제목": ("`AGENTS.md` §하위 제목은 절이 아니다", "§하위 제목은 절이 아니다"),
    "코드 블록 안 제목": ("`AGENTS.md` §코드 블록 안의 줄도 절이 아니다", "§코드 블록 안의 줄도 절이"),
    "띄어 쓴 한글 낱말이 이어짐": ("`AGENTS.md` §교훈 목록을 본다.", "§교훈 목록을 본다"),
    "띄어 쓴 영문자가 이어짐": ("`AGENTS.md` §교훈 list", "§교훈 list"),
}

# 절 이름을 앞부분만 남기고 줄였을 때 옛 이름 참조가 걸리는지 본다. 예: "안전 원칙" → "안전".
SHORTENED_NAMES = tasks.agents_sections(AGENTS_TEXT.replace("## 8. 안전 원칙 (필수)", "## 8. 안전 (필수)")
                                        .replace("## 2. 작업 순서:", "## 2. 작업:"))
SHORTENED_HIT = {
    "줄 끝": ("`AGENTS.md` §안전 원칙", "§안전 원칙"),
    "조사": ("`AGENTS.md` §안전 원칙의 시험 순서", "§안전 원칙의 시험 순서"),
    "괄호": ("(`AGENTS.md` §안전 원칙).", "§안전 원칙"),
    "번호": ("`AGENTS.md` §작업 순서 1단계대로", "§작업 순서 1단계대로"),
}

# AGENTS.md 안에서 파일 이름 없이 쓴 참조.
SELF_PASS = {
    "맞는 절": "자세한 순서는 바로 아래 §작업 순서에 있다.",
    "다른 문서 번호": "01 문서 §8.4, 마스터 §5.3, PRD §0, `docs/x.md` §0",
    "README 절": "README §협업 규칙 6도 임의로 지우지 않는다고 정한다.",
    "조사 붙은 README 절": "README의 §협업 규칙 6, 01 문서에서 §8.4, `docs/x.md`의 §없는절",
    "다른 md 파일 절": "`docs/x.md` §없는절",
}
SELF_HIT = {
    "없는 절": ("위 §없는절 표).", "§없는절 표"),
    "괄호 뒤": ('"이해 먼저"(§없는절, PRD §0)', "§없는절"),
    "AGENTS.md를 붙인 없는 절": ("`AGENTS.md` §없는절", "§없는절"),
    "조사 붙은 AGENTS.md 뒤 없는 절": ("`AGENTS.md`의 §없는절", "§없는절"),
    "조사만 있는 낱말 뒤": ("이 파일의 §없는절", "§없는절"),
}


class AgentsSections(unittest.TestCase):
    def test_strips_number_parenthesis_and_takes_colon_head(self):
        self.assertEqual(NAMES, {"핵심 규칙", "작업 순서", "작업 순서: 이슈에서 PR까지",
                                 "프로젝트 한눈에", "부원이 AI에게 자기 과제를 물을 때",
                                 "안전 원칙", "교훈"})

    def test_real_agents_md_has_sections(self):
        # 절 이름은 바꿀 수 있어야 한다. 그래서 특정 이름 대신 제목을 하나 이상 읽는지만 본다.
        text = (Path(tasks.ROOT) / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(tasks.agents_sections(text))


class FindAgentsRefs(unittest.TestCase):
    def test_passes_existing_sections_and_other_documents(self):
        for name, line in MUST_PASS.items():
            with self.subTest(name):
                self.assertEqual(tasks.find_agents_refs(line, NAMES), [])

    def test_hits_missing_sections(self):
        for name, (line, word) in MUST_HIT.items():
            with self.subTest(name):
                hits = tasks.find_agents_refs(line, NAMES)
                self.assertEqual(len(hits), 1, hits)
                self.assertEqual(hits[0][2], word)

    def test_hits_old_name_after_shortening_section(self):
        self.assertIn("안전", SHORTENED_NAMES)
        for name, (line, word) in SHORTENED_HIT.items():
            with self.subTest(name):
                hits = tasks.find_agents_refs(line, SHORTENED_NAMES)
                self.assertEqual([h[2] for h in hits], [word])

    def test_self_refs_in_agents_md(self):
        for name, line in SELF_PASS.items():
            with self.subTest(name):
                self.assertEqual(tasks.find_agents_refs(line, NAMES, self_refs=True), [])
        for name, (line, word) in SELF_HIT.items():
            with self.subTest(name):
                hits = tasks.find_agents_refs(line, NAMES, self_refs=True)
                self.assertEqual([h[2] for h in hits], [word])

    def test_bare_section_outside_agents_md_is_not_a_ref(self):
        # 다른 문서의 "§작업 순서"는 그 문서 자신의 절일 수 있다. AGENTS.md를 붙인 참조만 본다.
        self.assertEqual(list(tasks.iter_agents_refs("아래 §없는절 참고")), [])

    def test_line_and_column_start_at_one(self):
        text = "a\nb\n`AGENTS.md` §없는절\n"
        self.assertEqual(tasks.find_agents_refs(text, NAMES), [(3, 13, "§없는절")])

    def test_form_feed_does_not_shift_line_numbers(self):
        text = "a\x0cb\nAGENTS.md §없는절\n"
        self.assertEqual(tasks.find_agents_refs(text, NAMES), [(2, 11, "§없는절")])


class ScanAgentsRefs(unittest.TestCase):
    def make_repo(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return root

    def test_reports_path_line_and_skips_own_test_file(self):
        root = self.make_repo({
            "AGENTS.md": AGENTS_TEXT + "\n아래 §교훈.\n위 §없는절1.\n",
            "docs/a.md": "x\n`AGENTS.md` §작업 순서\n`AGENTS.md` §없는절2\n",
            "tool.py": "# AGENTS.md §핵심 규칙 3\n",
            "test_agentsref.py": "# AGENTS.md §없는절3\n",
            "notes.pdf": "AGENTS.md §없는절4\n",
        })
        names, count, hits = tasks.scan_agents_refs(root, tasks.AGENTS_REF_SCAN)
        self.assertEqual(names, NAMES)
        self.assertEqual(count, 5)
        self.assertEqual(sorted(hits), [("AGENTS.md", 22, 3, "§없는절1"),
                                        ("docs/a.md", 3, 13, "§없는절2")])

    def test_dies_without_agents_md(self):
        root = self.make_repo({"docs/a.md": "`AGENTS.md` §교훈\n"})
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            tasks.scan_agents_refs(root, tasks.AGENTS_REF_SCAN)
        self.assertEqual(cm.exception.code, 1)

    def test_dies_when_agents_md_has_no_sections(self):
        root = self.make_repo({"AGENTS.md": "# 제목만\n### 하위\n"})
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            tasks.scan_agents_refs(root, tasks.AGENTS_REF_SCAN)
        self.assertEqual(cm.exception.code, 1)


class GlobInputs(unittest.TestCase):
    """collect_inputs()가 쓰는 파일 목록이 root.glob()을 쓸 때와 같은지 본다.

    collect_inputs()는 파일만 받고 SKIP_DIRS 안의 경로를 버린다. 양쪽에 같은 거르기를 한다.
    """

    def files(self, root, paths):
        rels = (p.relative_to(root) for p in paths if p.is_file())
        return sorted(r.as_posix() for r in rels if not tasks.SKIP_DIRS & set(r.parts))

    def expected(self, root, pattern):
        return self.files(root, root.glob(pattern))

    def actual(self, root, pattern):
        return self.files(root, tasks.glob_inputs(root, pattern))

    def test_matches_glob_on_temp_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ["a.md", "b.py", ".github/c.yml", ".claude/skills/x/SKILL.md", "docs/d/e.md",
                        ".venv/lib/f.md", "sim/venv/g.md", "docs/node_modules/h.md", "docs/sub.md/i.txt"]:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("x", encoding="utf-8")
            for pattern in ["**/*.md", "**/*.yml", "**/*", "docs/**/*.md", "*.py"]:
                with self.subTest(pattern):
                    self.assertEqual(self.actual(root, pattern), self.expected(root, pattern))

    def test_matches_glob_on_repo(self):
        # root.glob()은 .venv 안까지 돌아서 패턴마다 느리다. 패턴 하나만 비교한다.
        root = Path(tasks.ROOT)
        self.assertEqual(self.actual(root, "**/*.md"), self.expected(root, "**/*.md"))


if __name__ == "__main__":
    unittest.main()
