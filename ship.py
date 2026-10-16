#!/usr/bin/env python3
"""COSMOS ship-issue 도구 — 이슈에서 PR까지(AGENTS.md §작업 순서)에 필요한 명령을 모든 PC에 준다.

    python ship.py tools                  필요한 도구 확인, 없으면 설치 (gh, opencode)
    python ship.py wt <이슈 번호>          ../<저장소>-wt/issue-<n> worktree + 브랜치 <태그>/<n>
    python ship.py capped 8G -- <명령...>  메모리 상한을 걸고 명령 실행
    python ship.py review --author claude  작성한 모델과 다른 계열의 모델로 교차 리뷰

왜 이 파일이 있나: 김준원의 서버에는 `wt`, `capped`, `codex`가 깔려 있지만 부원 PC(Windows 위주)에는
없다. 없다고 그 단계를 빼면 사람마다 작업 순서가 달라진다. 그래서 같은 동작을 표준 라이브러리만으로
여기 구현하고, 없는 외부 도구는 처음 쓸 때 설치한다. 설치할 수 없는 경우(Linux의 gh는 관리자 권한
필요, Node.js가 없으면 opencode)는 설치 방법을 출력하고 멈춘다. Windows의 `capped`는 상한을 걸지
못하고 경고만 낸다.

사람만 할 수 있는 단계(로그인)는 설치해도 대신하지 못한다. 그때는 무엇을 입력하면 되는지 출력하고
멈춘다. OpenCode의 무료 모델은 로그인 없이 쓸 수 있어서, 리뷰는 로그인이 없어도 돈다.
"""
import argparse
import json
import os
import re
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
REVIEW_PROMPT = ("Review the changes on this branch against {base}. Report concrete findings "
                 "with file and line. Do not edit files.")


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


def call(cmd, check=True, capture=False, cwd=None):
    say(cmd)
    r = subprocess.run([exe_of(cmd[0]), *map(str, cmd[1:])], cwd=cwd, text=True, encoding="utf-8",
                       errors="replace", capture_output=capture)
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
        print(f"이미 있는 worktree를 쓴다. 브랜치: {branch}", file=sys.stderr)
        print(path)
        return
    tag = a.tag or issue_tag(info)
    if tag not in TAGS:
        die(f"이슈 제목이나 라벨에서 태그를 못 찾았다. --tag 로 정한다: {', '.join(TAGS)}")
    branch = f"{tag}/{a.issue}"
    call(["git", "-C", root, "fetch", "origin", "--quiet"])
    path.parent.mkdir(parents=True, exist_ok=True)
    call(["git", "-C", root, "worktree", "add", "--quiet", path, "-b", branch, "origin/main"])
    # 마지막 줄은 경로만 쓴다. 스크립트가 `cd "$(python ship.py wt 12 | tail -1)"`처럼 쓸 수 있게.
    print(f"브랜치: {branch}", file=sys.stderr)
    print(path)


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
    # Windows: Job Object로 걸 수 있지만 여기서는 시험하지 못해서 넣지 않았다.
    print("[주의] Windows에서는 메모리 상한을 걸지 못한다. 상한 없이 실행한다. "
          "작업 관리자로 메모리를 지켜본다.", file=sys.stderr)
    sys.exit(subprocess.run([exe_of(cmd[0]), *cmd[1:]]).returncode)


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


def cmd_review(a):
    author = family(a.author)
    prompt = REVIEW_PROMPT.format(base=a.base)
    call(["git", "fetch", "origin", "--quiet"])
    # 리뷰 요청에는 범위만 넣는다(AGENTS.md §작업 순서 6). 힌트나 체크리스트를 넣지 않는다.
    if author != "openai" and logged_in(["codex", "login", "status"]):
        reviewer, cmd = "codex", ["codex", "exec", "--sandbox", "read-only", prompt]
    elif author != "claude" and logged_in(["claude", "auth", "status"]):
        reviewer, cmd = "claude", ["claude", "-p", "--permission-mode", "plan", prompt]
    else:
        model = opencode_model(author)
        reviewer, cmd = model, ["opencode", "run", "--agent", "plan", "-m", model, prompt]
    print(f"작성자 계열: {author} / 리뷰어: {reviewer}\n", flush=True)
    r = call(cmd, check=False)
    print(f"\nPR 템플릿 \"교차 리뷰\"에 적는다: `{reviewer}: 지적 N건, 고침 <커밋> / "
          "받아들이지 않음 <이유>`")
    sys.exit(r.returncode)


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
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
