#!/usr/bin/env python3
"""COSMOS ship-issue 도구 — 이슈에서 PR까지(AGENTS.md §작업 순서)에 필요한 명령을 모든 PC에 준다.

    python ship.py tools                  필요한 도구 확인, 없으면 설치 (gh, opencode)
    python ship.py wt <이슈 번호>          ../<저장소>-wt/issue-<n> worktree + 브랜치 <태그>/<n>
    python ship.py capped 8G -- <명령...>  메모리 상한을 걸고 명령 실행
    python ship.py review --author claude  작성한 모델과 다른 계열의 모델로 교차 리뷰
    python ship.py skills [--check]        .claude/skills를 .agents/skills(Codex용)로 복사, --check는 비교만
    python ship.py link <이슈 번호>        본문 "### 상위 PRD" 칸의 PRD 아래 sub-issue로 잇기 (wt도 부른다)

왜 이 파일이 있나: 김준원의 서버에는 `wt`, `capped`, `codex`가 깔려 있지만 부원 PC(Windows 위주)에는
없다. 없다고 그 단계를 빼면 사람마다 작업 순서가 달라진다. 그래서 같은 동작을 표준 라이브러리만으로
여기 구현하고, 없는 외부 도구는 처음 쓸 때 설치한다. 설치할 수 없는 경우(Linux의 gh는 관리자 권한
필요, Node.js가 없으면 opencode)는 설치 방법을 출력하고 멈춘다. Windows의 `capped`는 Job Object로
상한을 건다. 이 동작은 GitHub Windows 러너에서 64비트와 32비트 파이썬으로 확인했다(#80).

사람만 할 수 있는 단계(로그인)는 설치해도 대신하지 못한다. 그때는 무엇을 입력하면 되는지 출력하고
멈춘다. OpenCode의 무료 모델은 로그인 없이 쓸 수 있어서, 리뷰는 로그인이 없어도 돈다.
"""
import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAGS = ("cad", "fw", "sim", "web", "kicad", "data", "docs", "infra")
# 이슈 라벨 → 브랜치 태그. 제목에 [태그]가 없을 때만 쓴다.
LABEL_TAGS = {"fw": "fw", "sim": "sim", "web": "web", "cad": "cad", "kicad": "kicad",
              "documentation": "docs"}
# 리뷰 모델 계열. 작성자와 같은 계열은 리뷰어로 고르지 않는다.
OPENCODE_REVIEWERS = ("mimo", "muse-spark", "deepseek", "nemotron")
# 스킬 정본과 Codex용 복사본. Claude Code는 .claude/skills만, Codex는 .agents/skills만 읽는다(#39).
SKILLS_SRC = ROOT / ".claude" / "skills"
SKILLS_DST = ROOT / ".agents" / "skills"
REVIEW_PROMPT = ("Review the changes on this branch against {base}. Report concrete findings "
                 "with file and line. Do not edit files.")
# 리뷰어에게 표준 입력으로 넘기는 GitHub 기록(#167). Codex 리뷰어는 read-only 샌드박스라 네트워크가
# 막혀 gh로 PR·이슈를 읽지 못한다. 기록은 리뷰 요청 문장과 따로 넘기고, 요청 문장은 범위만 둔다.
RECORD_FIELDS = "number,title,state,url,author,createdAt,body,comments"
# PR이면 더 읽는 필드. `gh issue view`의 comments에는 PR 리뷰(승인·변경 요청)가 없다.
PR_FIELDS = "mergedAt,commits,reviews"
# 줄 단위 리뷰 댓글. `gh pr view --json`에 이 필드가 없어서 REST API로 읽는다. 한 줄에 JSON 하나다.
INLINE_JQ = (".[] | {author: .user.login, createdAt: .created_at, path, "
             "line: (.line // .original_line), body}")
MAX_REFERENCED = 20
# PR 템플릿. 본문에 고치지 않고 남은 템플릿 줄(예: "- [ ] 이슈 #21 ...")의 `#번호`는 읽지 않는다.
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"


def die(msg):
    print(f"\n[중단] {msg}", file=sys.stderr)
    sys.exit(1)


def say(cmd):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)


def exe_of(name):
    # Windows에서 npm·opencode 같은 .cmd 래퍼는 shutil.which가 찾은 전체 경로로 불러야 한다.
    path = shutil.which(str(name))
    if not path:
        die(f"명령을 찾지 못했다: {name}")
    return path


def call(cmd, check=True, capture=False, cwd=None, input=None):
    say(cmd)
    r = subprocess.run([exe_of(cmd[0]), *map(str, cmd[1:])], cwd=cwd, text=True, encoding="utf-8",
                       errors="replace", capture_output=capture, input=input)
    if check and r.returncode != 0:
        if capture:
            sys.stderr.write(r.stdout + r.stderr)
        die(f"위 명령이 실패했다 (exit {r.returncode}).")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 도구 설치
# ─────────────────────────────────────────────────────────────────────────────

def ensure_gh():
    if shutil.which("gh"):
        return
    if os.name == "nt" and shutil.which("winget"):
        call(["winget", "install", "--id", "GitHub.cli", "-e", "--accept-source-agreements",
              "--accept-package-agreements"])
        die("gh를 설치했다. 새 터미널을 열어 PATH를 다시 읽은 뒤 같은 명령을 다시 실행한다.")
    if sys.platform == "darwin" and shutil.which("brew"):
        call(["brew", "install", "gh"])
        return
    die("gh(GitHub CLI)가 없다. 설치: https://cli.github.com/\n"
        "     Linux는 관리자 권한이 필요해서 자동으로 설치하지 않는다.")


def ensure_gh_login():
    ensure_gh()
    if call(["gh", "auth", "status"], check=False, capture=True).returncode != 0:
        die("gh에 로그인돼 있지 않다. 사람이 직접 실행한다:  gh auth login")


def ensure_opencode():
    if shutil.which("opencode"):
        return
    if not shutil.which("npm"):
        die("opencode를 설치하려면 Node.js(npm)가 필요하다. 설치: https://nodejs.org/\n"
            "     설치한 뒤 같은 명령을 다시 실행하면 opencode를 자동으로 설치한다.")
    call(["npm", "install", "-g", "opencode-ai"])
    if not shutil.which("opencode"):
        die("opencode를 설치했지만 PATH에서 찾지 못했다. 새 터미널을 열고 다시 실행한다.")


def cmd_tools(_):
    ensure_gh()
    ensure_opencode()
    for tool in ("git", "gh", "opencode", "codex", "claude", "uv", "pio"):
        print(f"  {tool:<9} {shutil.which(tool) or '없음'}")
    print("\ngh 로그인 상태:")
    call(["gh", "auth", "status"], check=False)
    print("\ncodex·claude는 선택이다. 없으면 `review`가 OpenCode 무료 모델로 리뷰한다.")


# ─────────────────────────────────────────────────────────────────────────────
# wt — 이슈 하나에 worktree 하나
# ─────────────────────────────────────────────────────────────────────────────

def issue_tag(info):
    m = re.match(r"\s*\[([a-z]+)\]", info["title"])
    if m and m.group(1) in TAGS:
        return m.group(1)
    for label in info["labels"]:
        if label["name"] in LABEL_TAGS:
            return LABEL_TAGS[label["name"]]
    return None


def cmd_wt(a):
    ensure_gh_login()
    git_common = call(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                      capture=True, cwd=ROOT).stdout.strip()
    root = Path(git_common).parent
    path = root.parent / f"{root.name}-wt" / f"issue-{a.issue}"
    info = json.loads(call(["gh", "issue", "view", str(a.issue), "--json", "title,labels,state"],
                           capture=True, cwd=root).stdout)
    if info["state"] != "OPEN":
        die(f"이슈 #{a.issue}가 열려 있지 않다({info['state']}).")
    if path.exists():
        branch = call(["git", "-C", path, "branch", "--show-current"], capture=True).stdout.strip()
        print("이미 있는 worktree를 쓴다.", file=sys.stderr)
        link_after_wt(a.issue, root)
        # 새 worktree와 같다: 끝에서 둘째 줄은 브랜치, 마지막 줄은 경로다.
        print(f"브랜치: {branch}", file=sys.stderr)
        print(path)
        return
    tag = a.tag or issue_tag(info)
    if tag not in TAGS:
        die(f"이슈 제목이나 라벨에서 태그를 못 찾았다. --tag 로 정한다: {', '.join(TAGS)}")
    branch = f"{tag}/{a.issue}"
    call(["git", "-C", root, "fetch", "origin", "--quiet"])
    path.parent.mkdir(parents=True, exist_ok=True)
    call(["git", "-C", root, "worktree", "add", "--quiet", path, "-b", branch, "origin/main"])
    link_after_wt(a.issue, root)
    # 마지막 줄은 경로만 쓴다. 스크립트가 `cd "$(python ship.py wt 12 | tail -1)"`처럼 쓸 수 있게.
    print(f"브랜치: {branch}", file=sys.stderr)
    print(path)


# ─────────────────────────────────────────────────────────────────────────────
# link — 작업 이슈를 상위 PRD의 sub-issue로 잇기 (#79, #109)
# ─────────────────────────────────────────────────────────────────────────────
# 웹 양식(.github/ISSUE_TEMPLATE/task.yml, id parent-prd)으로 만든 이슈 본문에는 `### 상위 PRD` 제목과
# 값만 남는다. 칸을 비우면 값은 `_No response_`다. sub-issue 관계는 생기지 않는다. 이 명령이 값을 읽어 잇는다.
#
# gh의 `issue edit --add-sub-issue`가 아니라 `gh api`를 쓰는 이유: 그 옵션은 gh 2.94.0(2026-06)에 처음
# 들어갔다. 부원 PC의 gh는 그보다 오래됐을 수 있다. `gh api`와 `{owner}/{repo}` 자리표시는 훨씬 오래된
# 버전에도 있다. REST: https://docs.github.com/en/rest/issues/sub-issues
#
# 관계는 POST 한 번으로만 바꾼다. replace_parent를 보내지 않으므로 이미 있는 상위 이슈를 바꾸지 않는다.

PARENT_HEADING = "상위 PRD"  # task.yml parent-prd 칸의 label과 같아야 한다
EMPTY_FORM_VALUE = "_No response_"  # 이슈 양식에서 칸을 비웠을 때 본문에 남는 값
NO_PARENT_WORD = "없음"
# 칸의 값에서 이 저장소의 이슈 번호를 찾는다(#133).
# 읽는다: `#26`, `(#26)`, `#26번`, `#26의 하위`, `상위#26`, `-#26`, `/#26`.
# 읽지 않는다: `org/repo#26`(이 저장소 이름이어도), `org/repo-#26`, `PRD#26`, `_#26`, `#26a`.
# 1. OTHER_REPO_REF: 저장소 이름을 붙인 참조를 먼저 지운다. 계정·저장소 이름 자리에는 ASCII 영문자·숫자·`_`·`.`·`-`만 본다.
#    바로 이어 붙은 번호도 함께 지운다(`org/repo#26#27`). GitHub은 이 값에서 아무것도 링크하지 않는다.
# 2. 남은 값에서 `#<번호>`를 앞뒤 글자와 관계없이 센다. 서로 다른 번호가 둘 이상이면 오류다(`#26/#27`, `#26#27`).
# 3. ISSUE_REF: 번호 하나를 읽는다. `#` 바로 앞과 번호 바로 뒤에 ASCII 영문자·숫자·`_`가 없어야 한다.
# 3의 `#` 앞 규칙은 GitHub 자동 링크와 같다. `gh api markdown`으로 확인했다: `상위#26`, `-#26`, `.#26`, `/#26`은 링크하고
# `PRD#26`, `_#26`은 링크하지 않는다. GitHub과 다른 곳은 둘이다. `#26번`은 GitHub이 링크하지 않지만 이 칸에서는 읽는다.
# `#26#27`은 GitHub이 #26만 링크하지만 이 칸에서는 2단계에서 오류다.
# re.ASCII를 쓰는 이유: 파이썬 3의 str 정규식에서 `\w`는 한글도 단어 글자로 본다. 그러면 `#26번`과 `상위#26`을 놓친다.
OTHER_REPO_REF = re.compile(r"[\w.-]+/[\w.-]+(?:#[0-9]+)+", re.ASCII)
ISSUE_REF = re.compile(r"(?<!\w)#([0-9]+)(?!\w)", re.ASCII)


def parent_prd(body):
    """본문의 `### 상위 PRD` 칸을 읽는다. (PRD 번호 또는 None, 칸의 값)을 돌려준다.

    칸이 없거나, 비었거나, `_No response_`이거나, `없음`으로 시작하면 번호는 None이다.
    값이 있는데 이 저장소의 `#<번호>`(ISSUE_REF)가 없으면 ValueError를 낸다. 저장소 이름을 붙인 참조를 뺀 값에
    서로 다른 `#<번호>`가 둘 이상 있어도 ValueError를 낸다.
    """
    text = (body or "").replace("\r\n", "\n")
    m = re.search(rf"^###[ \t]+{re.escape(PARENT_HEADING)}[ \t]*$(.*?)(?=^###[ \t]|\Z)", text,
                  re.M | re.S)
    if not m:
        return None, ""
    value = m.group(1).strip()
    if not value or value == EMPTY_FORM_VALUE or value.startswith(NO_PARENT_WORD):
        return None, value
    rest = OTHER_REPO_REF.sub(" ", value)
    seen = sorted({int(n) for n in re.findall(r"#([0-9]+)", rest)})
    if len(seen) > 1:
        raise ValueError(f"번호가 {len(seen)}개다(칸의 값: {value!r}). 상위 이슈는 하나만 둘 수 있다.")
    numbers = ISSUE_REF.findall(rest)
    if not numbers:
        raise ValueError(f"`#<번호>` 형식의 번호가 없다(칸의 값: {value!r}). 예: #26\n"
                         "     저장소 이름을 붙인 참조(`org/repo#26`)는 이 저장소 이름이어도 읽지 않는다.\n"
                         "     `PRD#26`, `_#26`, `#26a`처럼 `#` 바로 앞이나 번호 바로 뒤에 영문자·숫자·`_`가 붙어도"
                         " 읽지 않는다.")
    return int(numbers[0]), value


def gh_api(path, cwd=None, method=None, fields=()):
    """`gh api`를 한 번 부른다. (종료 코드, JSON 또는 None, HTTP 상태 코드 또는 None, 오류 글)."""
    cmd = ["gh", "api", *(["-X", method] if method else []), path]
    for f in fields:
        cmd += ["-F", f]
    say(cmd)
    r = subprocess.run([exe_of("gh"), *cmd[1:]], cwd=cwd, text=True, encoding="utf-8",
                       errors="replace", capture_output=True)
    try:
        data = json.loads(r.stdout) if r.stdout.strip() else None
    except ValueError:
        data = None
    # gh는 실패하면 stderr에 `gh: Not Found (HTTP 404)`처럼 쓴다.
    m = re.search(r"\(HTTP (\d{3})\)", r.stderr)
    return r.returncode, data, int(m.group(1)) if m else None, r.stderr.strip()


def link_fail(msg):
    print(f"[잇지 않음] {msg}", file=sys.stderr, flush=True)
    return 1


def link_issue(n, cwd=None):
    """이슈 #n을 본문 "상위 PRD" 칸이 가리키는 PRD의 sub-issue로 잇는다. 종료 코드를 돌려준다.

    0: 이었다. 이미 그 PRD의 하위 이슈다. 상위 PRD가 없다(칸 없음, 빈 칸, `_No response_`, `없음`).
    1: 잇지 않았다. 칸의 값이 틀렸다, 다른 상위 이슈가 이미 있다, 권한이 없다, API가 실패했다.
    """
    issue_path = "repos/{owner}/{repo}/issues/"
    rc, issue, status, err = gh_api(f"{issue_path}{n}", cwd)
    if rc != 0 or not isinstance(issue, dict):
        if status in (404, 410):
            return link_fail(f"없는 이슈 번호다: #{n} (HTTP {status}).")
        return link_fail(f"이슈 #{n} 정보를 읽지 못했다: {err}")
    if issue.get("pull_request"):
        return link_fail(f"PR 번호다: #{n}. 작업 이슈 번호를 준다.")
    try:
        prd, value = parent_prd(issue.get("body"))
    except ValueError as e:
        return link_fail(f"#{n} 본문의 `### {PARENT_HEADING}` 칸을 읽지 못했다. {e}\n"
                         f"     이슈 본문의 칸을 `#<PRD 번호>` 하나로 고친 뒤 다시 실행한다.")
    if prd is None:
        why = f"칸의 값: {value!r}" if value else f"본문에 `### {PARENT_HEADING}` 칸이 없다"
        print(f"#{n}: 상위 PRD가 없다({why}). 잇지 않는다.", flush=True)
        return 0
    if prd == n:
        return link_fail(f"#{n} 본문의 상위 PRD 칸이 이 이슈 자신을 가리킨다. 칸의 번호를 고친다.")

    # 중복 실행: 지금 상위 이슈를 먼저 본다. 이미 이 PRD 아래면 아무것도 바꾸지 않는다.
    same_repo = f"{issue.get('repository_url')}/issues/"
    current = issue.get("parent_issue_url")
    if current == f"{same_repo}{prd}":
        print(f"이미 PRD #{prd}의 하위 이슈다: #{n}. 바꾸지 않는다.", flush=True)
        return 0
    if current:
        shown = f"#{current[len(same_repo):]}" if current.startswith(same_repo) else current
        return link_fail(f"#{n}의 상위 이슈가 이미 있다: {shown}. 칸의 PRD #{prd}로 바꾸지 않는다.\n"
                         "     칸의 PRD가 맞으면 부장·차장이 웹에서 상위 이슈를 옮긴다. "
                         "지금 상위 이슈가 맞으면 칸을 고친다.")

    rc, parent, status, err = gh_api(f"{issue_path}{prd}", cwd)
    if rc != 0 or not isinstance(parent, dict):
        if status in (404, 410):
            return link_fail(f"칸의 번호로 이슈를 찾지 못했다: #{prd} (HTTP {status}). 칸의 번호를 고친다.")
        return link_fail(f"PRD #{prd} 정보를 읽지 못했다: {err}")
    if parent.get("pull_request"):
        return link_fail(f"칸의 번호가 PR 번호다: #{prd}. PRD 이슈 번호로 고친다.")
    if parent.get("state") != "open":
        return link_fail(f"칸의 PRD가 닫혀 있다: #{prd} ({parent.get('state')}). 잇지 않는다.")
    labels = {label.get("name") for label in parent.get("labels", [])}
    if "prd" not in labels:
        return link_fail(f"칸의 이슈에 라벨 `prd`가 없다: #{prd}. PRD 이슈 번호인지 확인한다.")

    # sub_issue_id는 이슈 번호가 아니라 REST의 id다.
    rc, _, status, err = gh_api(f"{issue_path}{prd}/sub_issues", cwd, method="POST",
                                fields=[f"sub_issue_id={issue['id']}"])
    if rc != 0:
        if status in (401, 403, 404):
            return link_fail(
                f"PRD #{prd} 아래로 이슈 #{n} 잇기에 실패했다: {err}\n"
                f"     원인: 이 gh 계정에 저장소의 triage 이상 권한이 없거나 로그인이 풀린 것으로 보인다"
                f"(HTTP {status}). sub-issue는 triage 이상 권한으로만 잇는다.\n"
                f"     손으로 잇기: 권한이 있는 사람(부장·차장)이 {parent.get('html_url', f'PRD #{prd}')} "
                f"본문 아래 \"Create sub-issue\" 옆 화살표를 누르고 \"Add existing issue\"에서 이 이슈(#{n})를 고른다.\n"
                f"     또는 그 사람이 다음 명령을 실행한다: python ship.py link {n}")
        return link_fail(f"PRD #{prd} 아래로 이슈 #{n} 잇기에 실패했다: {err}")
    print(f"PRD #{prd}의 하위 이슈로 이었다: #{n} ({parent.get('html_url', '')})", flush=True)
    return 0


def link_after_wt(n, cwd):
    """wt 끝에 부른다. 잇지 못해도 worktree는 이미 있으므로 wt를 실패로 끝내지 않는다."""
    print(f"\n상위 PRD 잇기 (python ship.py link {n}):", file=sys.stderr, flush=True)
    try:
        rc = link_issue(n, cwd)
    except Exception as e:  # 잇기가 어떻게 실패해도 폴더 경로 출력(wt의 결과)은 지킨다
        print(f"[잇지 않음] 예상하지 못한 오류: {e!r}", file=sys.stderr)
        rc = 1
    if rc != 0:
        print("[주의] worktree는 그대로 쓴다. 위 안내대로 고친 뒤 다음 명령을 다시 실행한다: "
              f"python ship.py link {n}", file=sys.stderr, flush=True)


def cmd_link(a):
    ensure_gh_login()
    sys.exit(link_issue(a.issue, ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# capped — 메모리 상한
# ─────────────────────────────────────────────────────────────────────────────

def parse_size(text):
    m = re.fullmatch(r"(\d+)([KMG]?)", text.upper())
    if not m:
        die(f"크기 형식이 틀렸다: {text} (예: 8G, 512M)")
    return int(m.group(1)) * {"": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30}[m.group(2)]


def cmd_capped(a):
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        die("실행할 명령이 없다. 예: python ship.py capped 8G -- python tasks.py check")
    limit = parse_size(a.size)
    exe_of(cmd[0])  # 없는 명령이면 상한을 걸기 전에 멈춘다
    if sys.platform.startswith("linux") and shutil.which("systemd-run"):
        probe = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "true"],
                               capture_output=True)
        if probe.returncode == 0:
            # 서버의 capped와 같은 방식: cgroup이 자식 프로세스까지 묶어서 상한을 건다.
            os.execvp("systemd-run", ["systemd-run", "--user", "--scope", "--quiet",
                                      f"-pMemoryMax={limit}", "-pMemorySwapMax=0", "--", *cmd])
    if os.name == "posix":
        import resource
        def limit_as():
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        if sys.platform == "darwin":
            print("[주의] macOS는 RLIMIT_AS를 강제하지 않을 수 있다. 상한이 안 걸릴 수 있다.",
                  file=sys.stderr)
        sys.exit(subprocess.run([exe_of(cmd[0]), *cmd[1:]], preexec_fn=limit_as).returncode)
    try:
        win_job_cap(limit)
    except OSError as e:
        die(f"Windows Job Object로 메모리 상한을 걸지 못했다: {e}")
    sys.exit(subprocess.run([exe_of(cmd[0]), *cmd[1:]]).returncode)


def win_job_cap(limit):
    """Windows: 이 프로세스(ship.py)를 커밋 메모리 상한이 걸린 Job Object에 넣는다.

    자식을 먼저 띄우고 Job에 넣으면, 넣기 전에 자식이 할당하거나 손자 프로세스를 띄울 수 있다.
    subprocess는 CREATE_SUSPENDED로 띄운 자식의 스레드 핸들을 닫아 버려서 ResumeThread를 못 쓴다.
    그래서 ship.py 자신을 먼저 Job에 넣는다. 그 뒤 띄우는 자식과 손자는 Job에 자동으로 들어간다.
    JOB_MEMORY는 Job 전체 합계 상한이다(Linux systemd-run의 MemoryMax처럼). ship.py 자신이 쓰는
    메모리도 합계에 들어간다. KILL_ON_JOB_CLOSE: ship.py가 끝나 마지막 Job 핸들이 닫히면 남은
    자식도 끝난다. Job 핸들은 일부러 닫지 않는다.
    """
    import ctypes
    from ctypes import wintypes

    JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),  # ULONG_PTR: 포인터 크기의 부호 없는 정수
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    if limit >= 1 << (8 * ctypes.sizeof(ctypes.c_size_t)):
        die(f"상한 {limit}바이트가 이 파이썬(32비트)의 SIZE_T 범위를 넘는다.")

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            wintypes.DWORD)
    k32.SetInformationJobObject.restype = wintypes.BOOL
    k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    k32.AssignProcessToJobObject.restype = wintypes.BOOL
    k32.GetCurrentProcess.argtypes = ()
    k32.GetCurrentProcess.restype = wintypes.HANDLE

    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = (JOB_OBJECT_LIMIT_JOB_MEMORY
                                             | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
    info.JobMemoryLimit = limit
    if not k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                       ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return job


# ─────────────────────────────────────────────────────────────────────────────
# review — 다른 계열의 모델로 교차 리뷰
# ─────────────────────────────────────────────────────────────────────────────

def family(name):
    name = name.lower()
    if "claude" in name or "anthropic" in name:
        return "claude"
    if "codex" in name or "openai" in name or "gpt" in name:
        return "openai"
    for f in OPENCODE_REVIEWERS:
        if f in name:
            return f
    return name


def logged_in(cmd):
    if not shutil.which(cmd[0]):
        return False
    return subprocess.run([shutil.which(cmd[0]), *cmd[1:]], capture_output=True).returncode == 0


def opencode_model(author):
    ensure_opencode()
    models = call(["opencode", "models"], capture=True).stdout.split()
    for f in OPENCODE_REVIEWERS:
        if f == author:
            continue
        for m in models:
            if m.startswith("opencode/") and f in m and m.endswith("-free"):
                return m
    die("OpenCode 무료 모델 중 쓸 수 있는 리뷰어를 못 찾았다. `opencode models`로 목록을 본다.")


def gh_json(cmd):
    """gh 명령의 JSON 출력을 읽는다. 실패하면 None."""
    r = call(cmd, check=False, capture=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def gh_json_lines(cmd):
    """한 줄에 JSON 하나를 내는 gh 명령(`--jq '.[]'`)의 출력을 목록으로 읽는다. 실패하면 None."""
    r = call(cmd, check=False, capture=True)
    if r.returncode != 0:
        return None
    try:
        return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]
    except ValueError:
        return None


def format_record(rec, pr_extra=None, marker=""):
    """이슈나 PR 하나를 리뷰어가 읽을 텍스트로 만든다. 본문과 댓글은 고치지 않고 그대로 둔다.

    본문에도 `##` 제목이 있어서 기록 경계는 태그로 표시한다. ship.py가 쓰는 태그와 `--- ... ---`
    구분 줄에는 marker를 넣는다. 공개 저장소라 누구나 댓글에 같은 꼴의 태그·구분 줄을 쓸 수 있다.
    marker는 실행마다 새로 뽑아서 댓글 작성자가 미리 알 수 없다. pr_extra가 `{}`이면 PR의 머지 시각과
    커밋을 읽지 못한 것이다. 이때는 "머지 안 됨"으로 보이지 않게 읽지 못했다고 쓴다. 댓글, 리뷰,
    줄 단위 리뷰 댓글은 시각 순서로 섞어서 쓴다. 답글이 어느 리뷰에 대한 것인지 보이게 하려는 것이다.
    """
    login = (rec.get("author") or {}).get("login", "?")
    kind = "pr" if pr_extra is not None else "issue"
    lines = [f'<github_record kind="{kind}" number="{rec["number"]}" marker="{marker}">',
             f"title: {rec.get('title', '')}",
             f"url: {rec.get('url', '')} | state: {rec.get('state', '')} | "
             f"author: {login} | created: {rec.get('createdAt', '')}"]
    events = [(c.get("createdAt") or "", f"comment by {(c.get('author') or {}).get('login', '?')}",
               c.get("body") or "") for c in rec.get("comments") or []]
    if pr_extra == {}:
        lines.append("merged, commits, reviews: not available (gh pr view failed)")
    elif pr_extra is not None:
        lines.append(f"merged: {pr_extra.get('mergedAt') or '-'}")
        for c in pr_extra.get("commits") or []:
            lines.append(f"commit {c.get('oid', '')[:7]} authored {c.get('authoredDate', '')} "
                         f"committed {c.get('committedDate', '')}: {c.get('messageHeadline', '')}")
        for v in pr_extra.get("reviews") or []:
            who = (v.get("author") or {}).get("login", "?")
            events.append((v.get("submittedAt") or "", f"review by {who} ({v.get('state', '')})",
                           v.get("body") or ""))
        inline = pr_extra.get("inline")
        if inline is None:
            lines.append("inline review comments: not available (gh api failed)")
        for c in inline or []:
            events.append((c.get("createdAt") or "",
                           f"inline review comment by {c.get('author') or '?'} on "
                           f"{c.get('path', '')}:{c.get('line') or '-'}", c.get("body") or ""))
    lines += ["", rec.get("body") or "(no body)"]
    for at, what, body in sorted(events, key=lambda e: e[0]):
        lines += ["", f"--- {marker} {what} at {at} ---", body]
    lines.append(f'</github_record marker="{marker}">')
    return "\n".join(lines)


def fetch_record(n, marker=""):
    """이슈나 PR #n을 읽어 텍스트로 만든다. 못 읽으면 None. PR이면 리뷰와 줄 단위 리뷰 댓글도 읽는다."""
    rec = gh_json(["gh", "issue", "view", str(n), "--json", RECORD_FIELDS])
    if rec is None:
        return None
    pr_extra = None
    if "/pull/" in (rec.get("url") or ""):
        pr_extra = gh_json(["gh", "pr", "view", str(n), "--json", PR_FIELDS]) or {}
        if pr_extra:
            pr_extra["inline"] = gh_json_lines(
                ["gh", "api", "--paginate", f"repos/{{owner}}/{{repo}}/pulls/{n}/comments",
                 "--jq", INLINE_JQ])
    return format_record(rec, pr_extra, marker)


def template_lines():
    """PR 템플릿의 줄(앞뒤 공백 제거). 파일이 없으면 빈 집합."""
    try:
        text = PR_TEMPLATE.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {line.strip() for line in text.splitlines() if line.strip()}


def body_refs(text, skip=frozenset()):
    """본문의 이 저장소 `#번호`를 나온 순서대로 돌려준다. 저장소 이름을 붙인 참조는 뺀다.

    skip에 든 줄은 건너뛴다. PR 템플릿 줄을 넘기면 고치지 않고 남은 템플릿 문구의 번호를 읽지 않는다.
    """
    kept = "\n".join(line for line in (text or "").splitlines() if line.strip() not in skip)
    return [int(n) for n in ISSUE_REF.findall(OTHER_REPO_REF.sub(" ", kept))]


def ref_list(numbers):
    return ", ".join(f"#{n}" for n in numbers) or "-"


def review_records():
    """이 브랜치 PR, 그 PR이 닫는 이슈, 두 본문이 가리키는 `#번호` 기록을 모은다(#167).

    (기록 텍스트, 요약)을 돌려준다. gh가 없거나 이 브랜치의 PR이 없으면 (None, 이유)다.
    본문이 가리키는 기록은 한 단계만, 최대 MAX_REFERENCED개를 읽는다.
    """
    if not shutil.which("gh"):
        return None, "gh가 없다"
    r = call(["gh", "pr", "view", "--json", "number,url,body,closingIssuesReferences"],
             check=False, capture=True)
    if r.returncode != 0:
        # PR이 없을 때와 gh 로그인·네트워크가 실패할 때를 가리지 않게 gh의 오류 문장을 그대로 보인다.
        err = " / ".join(line.strip() for line in (r.stderr or "").splitlines() if line.strip())
        return None, (f"이 브랜치의 PR을 읽지 못했다 ({err or f'exit {r.returncode}'}). "
                      "PR이 없으면 PR을 연 뒤에 리뷰를 돌린다. 그러면 PR·이슈 기록도 넘긴다")
    try:
        pr = json.loads(r.stdout)
    except ValueError:
        return None, "이 브랜치의 PR 정보를 읽지 못했다 (gh pr view가 JSON이 아닌 출력을 냈다)"
    marker = secrets.token_hex(4)
    repo = pr["url"].rsplit("/pull/", 1)[0] + "/"
    closing = [ref["number"] for ref in pr.get("closingIssuesReferences") or []
               if (ref.get("url") or "").startswith(repo)]
    texts, parts, seen = [pr.get("body")], [], {pr["number"]}
    first = fetch_record(pr["number"], marker)
    if first is None:
        return None, f"PR #{pr['number']}을 읽지 못했다"
    parts.append(first)
    read_closing, failed = [], []
    for n in closing:
        if n in seen:
            continue
        seen.add(n)
        rec = gh_json(["gh", "issue", "view", str(n), "--json", RECORD_FIELDS])
        if rec is None:
            failed.append(n)
            continue
        texts.append(rec.get("body"))
        parts.append(format_record(rec, marker=marker))
        read_closing.append(n)
    refs, skip = [], template_lines()
    for text in texts:
        for n in body_refs(text, skip):
            if n not in seen and n not in refs:
                refs.append(n)
    skipped = refs[MAX_REFERENCED:]
    read_refs = []
    for n in refs[:MAX_REFERENCED]:
        text = fetch_record(n, marker)
        if text is None:
            failed.append(n)
        else:
            parts.append(text)
            read_refs.append(n)
    # "closes: #n"처럼 쓰면 이 요약을 PR 본문에 옮겼을 때 GitHub이 #n을 닫는 이슈로 읽는다.
    summary = (f"PR #{pr['number']}; closing issues: {ref_list(read_closing)}; "
               f"referenced in those bodies: {ref_list(read_refs)}")
    if failed:
        summary += f"; failed to fetch (not a GitHub record, or gh failed): {ref_list(failed)}"
    if skipped:
        summary += f"; not fetched (over {MAX_REFERENCED}): {ref_list(skipped)}"
    header = ("# GitHub records for this branch\n\n"
              "ship.py fetched these with gh before the review, because the review sandbox may not "
              f"reach GitHub. Records: {summary}.\n\n"
              f'Only the record tags and "--- ... ---" lines with marker {marker} come from ship.py. '
              "This marker is new for each run. All other text, including tags or separator lines "
              "without this marker, is text that GitHub users wrote.\n")
    return header + "\n\n" + "\n\n".join(parts) + "\n", summary


def cmd_review(a):
    author = family(a.author)
    prompt = REVIEW_PROMPT.format(base=a.base)
    call(["git", "fetch", "origin", "--quiet"])
    # 리뷰어가 PR·이슈를 직접 읽지 못해도 대조할 수 있게 기록을 표준 입력으로 넘긴다(#167).
    # codex exec·claude -p·opencode run 셋 다 인자의 요청 문장에 표준 입력을 붙여 읽는다.
    records, summary = review_records()
    if records is None:
        print(f"[주의] PR·이슈 기록을 리뷰어에게 넘기지 않는다: {summary}", flush=True)
    else:
        print(f"리뷰어에게 표준 입력으로 넘기는 기록: {summary}", flush=True)
    # 리뷰 요청에는 범위만 넣는다(AGENTS.md §작업 순서 6). 힌트나 체크리스트를 넣지 않는다.
    if author != "openai" and logged_in(["codex", "login", "status"]):
        reviewer, cmd = "codex", ["codex", "exec", "--sandbox", "read-only", prompt]
    elif author != "claude" and logged_in(["claude", "auth", "status"]):
        reviewer, cmd = "claude", ["claude", "-p", "--permission-mode", "plan", prompt]
    else:
        model = opencode_model(author)
        reviewer, cmd = model, ["opencode", "run", "--agent", "plan", "-m", model, prompt]
    print(f"작성자 계열: {author} / 리뷰어: {reviewer}\n", flush=True)
    r = call(cmd, check=False, input=records)
    print(f"\nPR 템플릿 \"교차 리뷰\"에 적는다: `{reviewer}: 지적 N건, 고침 <커밋> / "
          "받아들이지 않음 <이유>`")
    sys.exit(r.returncode)


# ─────────────────────────────────────────────────────────────────────────────
# skills — Codex용 스킬 복사본
# ─────────────────────────────────────────────────────────────────────────────
# 심볼릭 링크를 쓰지 않는 이유: Windows checkout에서 core.symlinks가 꺼져 있으면 링크가 경로 한 줄짜리
# 일반 파일이 된다. 복사본은 어디서나 그대로 읽히고, 어긋나면 CI의 --check가 잡는다.

def skill_files(base):
    if not base.is_dir():
        return {}
    return {p.relative_to(base).as_posix(): p.read_bytes() for p in sorted(base.rglob("*"))
            if p.is_file() and "__pycache__" not in p.relative_to(base).parts}


def cmd_skills(a):
    src, dst = skill_files(SKILLS_SRC), skill_files(SKILLS_DST)
    if not src:
        die(f"스킬 정본이 없다: {SKILLS_SRC}")
    diff = sorted(k for k in src.keys() | dst.keys() if src.get(k) != dst.get(k))
    if a.check:
        if diff:
            for k in diff:
                state = "없음" if k not in dst else "남는 파일" if k not in src else "내용 다름"
                print(f"  {state}: .agents/skills/{k}", file=sys.stderr)
            die(".agents/skills가 .claude/skills와 다르다. `python ship.py skills`로 맞춘 뒤 커밋한다.")
        print(f"스킬 복사본이 정본과 같다 (파일 {len(src)}개).")
        return
    for k in diff:
        target = SKILLS_DST / k
        if k in src:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src[k])
        else:
            target.unlink()
    # 정본에서 지운 스킬의 빈 폴더를 정리한다. 깊은 폴더부터 지운다.
    for d in sorted((d for d in SKILLS_DST.rglob("*") if d.is_dir()), key=lambda d: len(d.parts),
                    reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    print(f"바꾼 파일 {len(diff)}개. .agents/skills가 .claude/skills와 같다.")


def main():
    p = argparse.ArgumentParser(prog="ship.py", description="COSMOS ship-issue 도구")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools", help="필요한 도구 확인, 없으면 설치").set_defaults(fn=cmd_tools)
    w = sub.add_parser("wt", help="이슈용 worktree와 브랜치 만들기")
    w.add_argument("issue", type=int)
    w.add_argument("--tag", choices=TAGS, help="브랜치 태그 (기본: 이슈 제목의 [태그])")
    w.set_defaults(fn=cmd_wt)
    c = sub.add_parser("capped", help="메모리 상한을 걸고 명령 실행")
    c.add_argument("size", help="예: 8G")
    c.add_argument("command", nargs=argparse.REMAINDER)
    c.set_defaults(fn=cmd_capped)
    r = sub.add_parser("review", help="다른 계열의 모델로 교차 리뷰")
    r.add_argument("--author", required=True,
                   help="이 브랜치를 쓴 모델 (예: claude, codex, mimo, muse-spark)")
    r.add_argument("--base", default="origin/main", help="비교 기준 (기본: origin/main)")
    r.set_defaults(fn=cmd_review)
    k = sub.add_parser("skills", help=".claude/skills를 .agents/skills(Codex용)로 복사")
    k.add_argument("--check", action="store_true", help="복사하지 않고 같은지만 확인 (CI용)")
    k.set_defaults(fn=cmd_skills)
    ln = sub.add_parser("link", help="작업 이슈를 본문 \"상위 PRD\" 칸의 PRD 아래 sub-issue로 잇기")
    ln.add_argument("issue", type=int)
    ln.set_defaults(fn=cmd_link)
    a = p.parse_args()
    # link와 wt는 사람이 쓴 이슈 본문을 출력한다. cp949 콘솔에 없는 문자(이모지 등)가 있어도 멈추지
    # 않게 못 쓰는 문자만 바꿔 쓴다. 인코딩 자체는 바꾸지 않는다(tasks.py의 같은 처리 참고).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    a.fn(a)


if __name__ == "__main__":
    main()
