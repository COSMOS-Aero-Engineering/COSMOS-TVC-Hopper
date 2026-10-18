"""ship.py 단위 검사(#109). gh와 git을 부르지 않는다. 가짜 응답으로 경우를 하나씩 확인한다.

    python -m unittest test_ship        `python tasks.py check`가 같이 돌린다(작업 이름 shiptest)

표준 라이브러리만 쓴다. ship.py와 같은 이유로 부원 PC(Windows)에서도 그대로 돈다.
"""
import argparse
import io
import json
import re
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import ship

REPO_API = "https://api.github.com/repos/o/r"
ISSUE_RE = re.compile(r"repos/\{owner\}/\{repo\}/issues/(\d+)(/sub_issues)?$")
PERMISSION_DENIED = (1, '{"message":"Must have admin rights to Repository."}',
                     "gh: Must have admin rights to Repository. (HTTP 403)")


def issue(number, body=None, state="open", labels=(), parent=None, pr=False):
    """REST `GET /repos/{owner}/{repo}/issues/{n}` 응답 중 ship.py가 읽는 필드만."""
    data = {"id": 5_000_000 + number, "number": number, "state": state, "body": body,
            "labels": [{"name": name} for name in labels], "parent_issue_url": parent,
            "repository_url": REPO_API, "html_url": f"https://github.com/o/r/issues/{number}"}
    if pr:
        data["pull_request"] = {"url": f"{REPO_API}/pulls/{number}"}
    return data


def form_body(value):
    """task.yml 양식으로 만든 이슈 본문. 다른 칸에도 `#번호`를 넣어 칸 경계를 함께 검사한다."""
    return f"### 상위 PRD\n\n{value}\n\n### 목적\n\n#77 참고.\n\n### 배경\n\nPR #63.\n"


class FakeGh:
    """subprocess.run 대신 쓴다. `gh api` 경로마다 정한 응답을 돌려주고 호출을 기록한다."""

    def __init__(self, *issues, post=(0, "{}", "")):
        self.issues = {i["number"]: i for i in issues}
        self.post = post
        self.calls = []

    def __call__(self, cmd, **_):
        args = list(cmd[1:])
        self.calls.append(args)
        assert args[0] == "api", args
        method = args[args.index("-X") + 1] if "-X" in args else "GET"
        path = next(a for a in args[1:] if a.startswith("repos/"))
        m = ISSUE_RE.fullmatch(path)
        assert m, path
        if method == "POST":
            assert m.group(2), path
            rc, out, err = self.post
        elif int(m.group(1)) in self.issues:
            rc, out, err = 0, json.dumps(self.issues[int(m.group(1))]), ""
        else:
            rc, out, err = 1, '{"message":"Not Found"}', "gh: Not Found (HTTP 404)"
        return subprocess.CompletedProcess(cmd, rc, out, err)

    def posts(self):
        return [c for c in self.calls if "-X" in c]


def run_link(fake, n):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(ship.subprocess, "run", fake), \
            mock.patch.object(ship.shutil, "which", lambda name: name), \
            redirect_stdout(out), redirect_stderr(err):
        rc = ship.link_issue(n)
    return rc, out.getvalue(), err.getvalue()


class ParentPrdTest(unittest.TestCase):
    def test_reads_number_only_from_its_own_section(self):
        self.assertEqual(ship.parent_prd(form_body("#27")), (27, "#27"))

    def test_windows_line_endings(self):
        self.assertEqual(ship.parent_prd(form_body("#26").replace("\n", "\r\n"))[0], 26)

    def test_extra_text_and_repeated_number(self):
        self.assertEqual(ship.parent_prd(form_body("#26 (CAD), 같은 #26"))[0], 26)

    def test_korean_particle_after_number(self):
        # 파이썬 3의 `\b`는 한글을 단어 글자로 본다. `#26번`도 26으로 읽어야 한다.
        # `상위#26`: GitHub도 #26으로 링크한다. `\w`가 한글을 단어 글자로 보면 놓친다.
        for value in ("#26번", "#26의 하위 작업", "PRD(#26)", "상위#26", "#26."):
            with self.subTest(value=value):
                self.assertEqual(ship.parent_prd(form_body(value))[0], 26)

    def test_other_repo_reference_is_not_this_repo(self):
        # `PRD#26`, `#26a`: GitHub도 링크하지 않는다. 저장소 이름을 붙인 참조는 이 저장소 이름이어도 읽지 않는다.
        for value in ("org/repo#26", "someorg/otherrepo#26", "org/my-repo.js#26", "PRD#26", "#26a",
                      "COSMOS-Aero-Engineering/COSMOS-TVC-Hopper#26"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ship.parent_prd(form_body(value))
        # 다른 저장소 참조가 함께 있어도 이 저장소 번호 하나만 센다.
        self.assertEqual(ship.parent_prd(form_body("#26 (org/repo#5 참고)"))[0], 26)

    def test_no_parent_values(self):
        for value in ("", "_No response_", "없음", "없음(PRD 아래 작업이 아니다)"):
            with self.subTest(value=value):
                self.assertIsNone(ship.parent_prd(form_body(value))[0])

    def test_no_section(self):
        for body in (None, "", "### 목적\n\n#27 하위 작업\n"):
            with self.subTest(body=body):
                self.assertEqual(ship.parent_prd(body), (None, ""))

    def test_bad_values(self):
        for value in ("26", "PRD 27", "#26, #28"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ship.parent_prd(form_body(value))


class LinkTest(unittest.TestCase):
    def test_links_with_rest_id_not_number(self):
        fake = FakeGh(issue(98, form_body("#27")), issue(27, labels=("prd", "sim")))
        rc, out, _ = run_link(fake, 98)
        self.assertEqual(rc, 0)
        self.assertEqual(len(fake.posts()), 1)
        post = fake.posts()[0]
        self.assertIn("repos/{owner}/{repo}/issues/27/sub_issues", post)
        self.assertIn(f"sub_issue_id={5_000_098}", post)
        self.assertFalse(any("replace_parent" in a for a in post))
        self.assertIn("이었다", out)

    def test_already_under_same_prd_changes_nothing(self):
        fake = FakeGh(issue(93, form_body("#29"), parent=f"{REPO_API}/issues/29"),
                      issue(29, labels=("prd",), state="closed"))
        rc, out, _ = run_link(fake, 93)
        self.assertEqual(rc, 0)
        self.assertEqual(fake.posts(), [])
        self.assertIn("이미", out)

    def test_other_parent_changes_nothing(self):
        fake = FakeGh(issue(98, form_body("#27"), parent=f"{REPO_API}/issues/26"),
                      issue(27, labels=("prd",)))
        rc, _, err = run_link(fake, 98)
        self.assertEqual(rc, 1)
        self.assertEqual(fake.posts(), [])
        self.assertIn("#26", err)

    def test_no_parent_values_succeed_without_change(self):
        for body in (form_body("없음(PRD 아래 작업이 아니다)"), form_body("_No response_"), "본문"):
            with self.subTest(body=body):
                fake = FakeGh(issue(109, body))
                rc, _, _ = run_link(fake, 109)
                self.assertEqual(rc, 0)
                self.assertEqual(len(fake.calls), 1)  # 이슈를 읽기만 한다

    def test_bad_input_changes_nothing(self):
        cases = {
            "형식": (issue(50, form_body("26")),),
            "번호 둘": (issue(50, form_body("#26, #28")),),
            # 열린 PRD #26을 둔다. 다른 저장소 참조를 이 저장소의 #26으로 읽으면 잇게 된다.
            "다른 저장소": (issue(50, form_body("someorg/otherrepo#26")), issue(26, labels=("prd",))),
            # 라벨 prd를 붙여 둔다. 자기 자신 검사가 없으면 다른 검사를 모두 지나 잇게 된다.
            "자기 자신": (issue(50, form_body("#50"), labels=("prd",)),),
            "없는 이슈": (issue(50, form_body("#999")),),
            "닫힌 PRD": (issue(50, form_body("#27")), issue(27, labels=("prd",), state="closed")),
            "라벨 prd 없음": (issue(50, form_body("#77")), issue(77, labels=("sim",))),
            "PR": (issue(50, form_body("#63")), issue(63, labels=("prd",), pr=True)),
        }
        for name, issues in cases.items():
            with self.subTest(name):
                fake = FakeGh(*issues)
                rc, _, err = run_link(fake, 50)
                self.assertEqual(rc, 1)
                self.assertEqual(fake.posts(), [])
                self.assertIn("[잇지 않음]", err)

    def test_target_is_missing_or_pr(self):
        for fake in (FakeGh(), FakeGh(issue(55, form_body("#26"), pr=True))):
            with self.subTest(issues=list(fake.issues)):
                rc, _, _ = run_link(fake, 55)
                self.assertEqual(rc, 1)
                self.assertEqual(fake.posts(), [])

    def test_permission_denied_prints_manual_way(self):
        fake = FakeGh(issue(98, form_body("#26")), issue(26, labels=("prd",)),
                      post=PERMISSION_DENIED)
        rc, _, err = run_link(fake, 98)
        self.assertEqual(rc, 1)
        self.assertEqual(len(fake.posts()), 1)
        self.assertIn("triage", err)
        self.assertIn("Add existing issue", err)
        self.assertIn("https://github.com/o/r/issues/26", err)

    def test_other_api_error_fails(self):
        fake = FakeGh(issue(98, form_body("#26")), issue(26, labels=("prd",)),
                      post=(1, "{}", "gh: Validation Failed (HTTP 422)"))
        rc, _, err = run_link(fake, 98)
        self.assertEqual(rc, 1)
        self.assertIn("HTTP 422", err)
        self.assertNotIn("triage", err)


class CmdTest(unittest.TestCase):
    def run_wt(self, link, existing):
        """cmd_wt를 git·gh 없이 돌린다. stdout 마지막 줄, stderr 줄 목록, worktree 경로를 돌려준다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            path = Path(tmp) / "repo-wt" / "issue-7"
            if existing:
                path.mkdir(parents=True)

            def fake_call(cmd, check=True, capture=False, cwd=None):
                if cmd[:2] == ["git", "rev-parse"]:
                    out = str(root / ".git")
                elif cmd[:3] == ["gh", "issue", "view"]:
                    out = json.dumps({"title": "[infra] x", "labels": [], "state": "OPEN"})
                else:
                    out = "infra/7"
                return subprocess.CompletedProcess(cmd, 0, out + "\n", "")

            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(ship, "ensure_gh_login"), \
                    mock.patch.object(ship, "call", fake_call), \
                    mock.patch.object(ship, "link_issue", side_effect=link) as linked, \
                    redirect_stdout(out), redirect_stderr(err):
                ship.cmd_wt(argparse.Namespace(issue=7, tag=None))
            linked.assert_called_once_with(7, root)
            return out.getvalue().splitlines()[-1], err.getvalue().splitlines(), str(path)

    def test_wt_link_failure_does_not_block_worktree(self):
        for existing in (False, True):
            for link in (lambda *_: 1, RuntimeError("network down")):
                with self.subTest(existing=existing, link=link):
                    last, err, path = self.run_wt(link, existing)
                    self.assertEqual(last, path)
                    # ship-issue 스킬 3단계: 경로 바로 앞 줄이 브랜치 이름이다. link 출력은 그 앞에 둔다.
                    self.assertEqual(err[-1], "브랜치: infra/7")
                    self.assertTrue(any(line.startswith("[주의] worktree는 그대로 쓴다.")
                                        for line in err), err)

    def test_link_command_exit_code(self):
        for rc in (0, 1):
            with self.subTest(rc=rc), mock.patch.object(ship, "ensure_gh_login"), \
                    mock.patch.object(ship, "link_issue", return_value=rc), \
                    self.assertRaises(SystemExit) as stop:
                ship.cmd_link(argparse.Namespace(issue=98))
            self.assertEqual(stop.exception.code, rc)


if __name__ == "__main__":
    unittest.main()
