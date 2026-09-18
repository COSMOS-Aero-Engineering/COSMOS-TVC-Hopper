#!/usr/bin/env python3
"""COSMOS 작업 실행기 — 작업 그래프 + 입력 해시 캐시.

    python tasks.py                 작업 목록
    python tasks.py setup           uv.lock 그대로 .venv 구성
    python tasks.py check           CI와 같은 검사 (compile → sanity → smoke)
    python tasks.py check --force   캐시 무시하고 전부 다시 실행
    python tasks.py graph           작업 그래프와 캐시 상태 보기
    python tasks.py lock            의존성 다시 풀고 uv.lock/requirements.txt 갱신
    python tasks.py train           PPO 본 학습 (200k 스텝, 오래 걸림)

왜 Makefile이 아니라 이 파일인가: 팀 개발 환경이 Windows 위주인데 Windows엔 `make`가 기본으로
없다. 반면 파이썬은 소프트웨어팀이 어차피 설치해야 한다. 표준 라이브러리만 쓰므로 추가 설치도
없고, Mac/Linux에서도 같은 명령이 그대로 동작한다.

왜 캐시가 붙었나: 검사가 늘어날수록 "안 바뀐 것까지 매번 다시 도는" 시간이 쌓인다. 각 작업은
자기가 읽는 파일 목록(inputs)을 선언하고, 그 파일들의 내용 해시가 지난번과 같으면 건너뛴다.
파일을 하나라도 고치면 그 작업과, 그 작업에 의존하는 작업이 전부 다시 돈다. 캐시가 의심스러우면
`--force`로 무시하거나 `python tasks.py clean`으로 비운다.

의존성 관리는 여기가 아니라 uv가 한다(pyproject.toml + uv.lock). 이 파일은 "무엇을 어떤
순서로 실행할지"만 안다 — 둘을 섞지 않는다.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIM = ROOT / "sim"
STAGE1 = SIM / "sim_stage1"
DECK = ROOT / "docs" / "presentation"
CACHE_DIR = ROOT / ".cosmos-cache"

# 캐시 형식이 바뀌면 이 값을 올린다 — 옛 캐시가 조용히 재사용되는 걸 막는다.
CACHE_VERSION = "1"

# 입력 파일을 모을 때 통째로 건너뛸 디렉터리. venv 안의 수만 개 .py를 해싱하면
# 캐시 확인이 검사보다 느려진다.
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".cosmos-cache", ".omc"}

# CI(.github/workflows/ci.yml)의 PPO 스모크와 같은 내용. 한쪽만 고치지 말 것.
SMOKE = (
    "from hopper_aviary import HopperAttitudeEnv\n"
    "from stable_baselines3 import PPO\n"
    "\n"
    "env = HopperAttitudeEnv()\n"
    'PPO("MlpPolicy", env, n_steps=64, batch_size=64, verbose=0).learn(total_timesteps=256)\n'
    'print("PPO 스모크 통과 - 환경과 SB3 연결 정상")\n'
)


# ─────────────────────────────────────────────────────────────────────────────
# 실행 도우미
# ─────────────────────────────────────────────────────────────────────────────

def die(msg):
    print(f"\n[중단] {msg}", file=sys.stderr)
    sys.exit(1)


def need(tool, how):
    """외부 도구가 있는지 확인하고 경로를 돌려준다. 없으면 설치 방법을 안내하고 종료."""
    path = shutil.which(tool)
    if not path:
        die(f"{tool} 이(가) 없다.\n     설치: {how}")
    return path


def uv():
    return need(
        "uv",
        "https://docs.astral.sh/uv/getting-started/installation/\n"
        "           Windows PowerShell:  irm https://astral.sh/uv/install.ps1 | iex\n"
        "           Mac/Linux:           curl -LsSf https://astral.sh/uv/install.sh | sh",
    )


def run(cmd, cwd=None):
    where = f" (cwd: {Path(cwd).relative_to(ROOT)})" if cwd else ""
    print(f"\n$ {' '.join(str(c) for c in cmd)}{where}", flush=True)
    result = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if result.returncode != 0:
        die(f"위 명령이 실패했다 (exit {result.returncode}).")


def uv_run(args, cwd=None):
    """워크스페이스 환경에서 실행. --frozen이라 uv.lock을 그대로 쓴다(멋대로 갱신하지 않는다).

    uv run은 실행 전에 .venv를 uv.lock에 맞춰 알아서 맞춰주므로, setup을 먼저 돌리지
    않아도 된다. cwd를 sim 안으로 바꿔도 --project로 워크스페이스 루트를 짚어준다.
    """
    run([uv(), "run", "--frozen", "--project", ROOT, *args], cwd=cwd)


# ─────────────────────────────────────────────────────────────────────────────
# 입력 해시 캐시
# ─────────────────────────────────────────────────────────────────────────────

def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_inputs(patterns):
    """글롭 패턴들을 (저장소 기준 상대경로, 내용해시) 목록으로 펼친다.

    tasks.py 자신은 항상 포함한다 — 무엇을 실행할지가 여기 적혀 있으므로, 이 파일이
    바뀌면 모든 캐시가 무효가 되는 게 맞다.
    """
    found = set()
    for pattern in list(patterns) + ["tasks.py"]:
        for p in ROOT.glob(pattern):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if SKIP_DIRS & set(rel.parts):
                continue
            found.add(rel.as_posix())
    return sorted((rel, _digest(ROOT / rel)) for rel in found)


def cache_key(task, dep_keys):
    h = hashlib.sha256()
    h.update(CACHE_VERSION.encode())
    h.update(task.name.encode())
    for k in sorted(dep_keys):
        h.update(k.encode())
    for rel, digest in collect_inputs(task.inputs):
        h.update(rel.encode())
        h.update(digest.encode())
    return h.hexdigest()


def resolve_key(name, memo, stack=()):
    """실행하지 않고 캐시 키만 계산한다. 그래프 출력과 실행이 같은 키를 쓰게 하려는 것."""
    if name in memo:
        return memo[name]
    if name in stack:
        die(f"작업 의존성이 순환한다: {' -> '.join(stack + (name,))}")
    task = TASKS[name]
    dep_keys = [resolve_key(d, memo, stack + (name,)) for d in task.deps]
    memo[name] = cache_key(task, dep_keys)
    return memo[name]


# 작업당 기억해둘 과거 입력 상태의 개수. 작업당 슬롯이 1개면 브랜치를 오갈 때마다
# 전체가 다시 돈다 — 되돌아온 상태도 "이미 통과한 입력"이므로 건너뛸 수 있어야 한다.
CACHE_KEEP = 16


def cache_hit(name, key):
    return (CACHE_DIR / name / key).exists()


def cache_write(name, key):
    slot = CACHE_DIR / name
    slot.mkdir(parents=True, exist_ok=True)
    # 캐시 폴더는 통째로 추적 대상이 아니다. .gitignore를 안에 두면 저장소 루트
    # .gitignore를 건드리지 않고도 자기 자신을 가린다.
    gitignore = CACHE_DIR / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    (slot / key).write_text(
        json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False),
        encoding="utf-8",
    )
    stale = sorted(slot.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[CACHE_KEEP:]
    for p in stale:
        p.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 작업 정의
# ─────────────────────────────────────────────────────────────────────────────

class Task:
    def __init__(self, name, doc, run=None, deps=(), inputs=(), cacheable=True):
        self.name = name
        self.doc = doc
        self.run = run or (lambda: None)
        self.deps = tuple(deps)
        self.inputs = tuple(inputs)
        self.cacheable = cacheable


def task_setup():
    run([uv(), "sync", "--frozen"], cwd=ROOT)
    activate = r".venv\Scripts\activate" if os.name == "nt" else "source .venv/bin/activate"
    print(
        "\n설치 완료. 확인하려면:  python tasks.py check"
        f"\n직접 python을 쓰고 싶으면 먼저 활성화:  {activate}"
        "\n(예전 sim/venv 는 더 이상 쓰지 않는다. 지워도 된다.)"
    )


def task_lock():
    run([uv(), "lock"], cwd=ROOT)
    out = SIM / "requirements.txt"
    # -o 에 넘긴 경로가 생성 파일 주석에 그대로 박히므로 상대경로로 준다.
    # 절대경로를 주면 사람마다 다른 경로가 커밋되어 매번 diff가 생긴다.
    run([uv(), "export", "--frozen", "--no-hashes", "--package", "cosmos-sim",
         "-o", "sim/requirements.txt"], cwd=ROOT)
    banner = (
        "# 이 파일은 생성물이다. 손으로 고치지 마라.\n"
        "#\n"
        "# 정본은 sim/pyproject.toml 이고, 버전을 바꾼 뒤 `python tasks.py lock` 을 돌리면\n"
        "# uv.lock 과 이 파일이 함께 갱신된다. 여기만 고치면 uv.lock 과 어긋나는데, CI는\n"
        "# uv.lock 기준으로 돌기 때문에 로컬과 CI가 서로 다른 버전을 쓰게 된다.\n"
        "#\n"
        "# uv 없이 pip만으로 환경을 맞춰야 할 때 쓰라고 남겨둔 사본이다:\n"
        "#   pip install -r sim/requirements.txt\n"
        "#\n"
        "# 아래 --extra-index-url 은 리눅스용 torch(2.14.0+cpu)가 PyPI엔 없고 PyTorch\n"
        "# 인덱스에만 있어서 필요하다. 이 줄이 없으면 리눅스에서 pip 설치가 실패한다.\n"
        "\n"
        "--extra-index-url https://download.pytorch.org/whl/cpu\n"
        "\n"
    )
    out.write_text(banner + out.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"\n갱신: uv.lock, {out.relative_to(ROOT)}")


def task_compile():
    uv_run(["python", "-m", "compileall", "-q", "sim", "test_cartpole.py", "test_pendulum.py"],
           cwd=ROOT)


def task_sanity():
    uv_run(["python", "sanity_check.py"], cwd=STAGE1)


def task_smoke():
    uv_run(["python", "-c", SMOKE], cwd=STAGE1)


def task_check():
    print("\n전부 통과. PR 올려도 된다.")


def task_train():
    print("200k 스텝 학습을 시작한다. 중간에 끊으려면 Ctrl+C.")
    uv_run(["python", "train.py"], cwd=STAGE1)


def task_deck():
    npm = need("npm", "https://nodejs.org 에서 Node.js 설치")
    node = need("node", "https://nodejs.org 에서 Node.js 설치")
    if not (DECK / "node_modules" / "pptxgenjs").exists():
        run([npm, "install", "pptxgenjs"], cwd=DECK)
    run([node, "build_deck.js"], cwd=DECK)


def task_clean():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"캐시를 비웠다: {CACHE_DIR.relative_to(ROOT)}")
    else:
        print("비울 캐시가 없다.")


# 의존성 입력 — 이게 바뀌면 sim을 쓰는 작업은 전부 다시 돌아야 한다.
DEPS_IN = ["uv.lock", "pyproject.toml", "sim/pyproject.toml"]
SIM_IN = ["sim/sim_stage1/*.py", "sim/sim_stage1/*.yaml", *DEPS_IN]

TASKS = {t.name: t for t in [
    Task("setup", "uv.lock 그대로 .venv 구성", task_setup, inputs=DEPS_IN, cacheable=False),
    Task("lock", "의존성 재해석 — uv.lock + sim/requirements.txt 갱신", task_lock, cacheable=False),
    Task("compile", "파이썬 문법 체크", task_compile,
         inputs=["sim/**/*.py", "test_*.py", *DEPS_IN]),
    Task("sanity", "환경이 살아 있는지 20스텝 확인", task_sanity, inputs=SIM_IN),
    Task("smoke", "SB3-환경 연결 확인 (256스텝, 학습 아님)", task_smoke, inputs=SIM_IN),
    Task("check", "CI와 같은 검사 — compile + sanity + smoke", task_check,
         deps=["compile", "sanity", "smoke"]),
    Task("train", "PPO 본 학습 (200k 스텝, 오래 걸림)", task_train, cacheable=False),
    Task("deck", "설명회 pptx 다시 생성 (node 필요)", task_deck,
         inputs=["docs/presentation/build_deck.js", "docs/presentation/speaker-notes.md"]),
    Task("clean", "작업 캐시 비우기", task_clean, cacheable=False),
]}


# ─────────────────────────────────────────────────────────────────────────────
# 그래프 실행
# ─────────────────────────────────────────────────────────────────────────────

def execute(name, opts, memo, done):
    if name in done:
        return
    task = TASKS[name]
    for dep in task.deps:
        execute(dep, opts, memo, done)

    key = resolve_key(name, memo)
    if task.cacheable and not opts.force and cache_hit(name, key):
        print(f"[캐시] {name} — 입력이 그대로다, 건너뛴다.")
        done.add(name)
        return

    print(f"[실행] {name} — {task.doc}")
    task.run()
    if task.cacheable:
        cache_write(name, key)
    done.add(name)


def show_graph():
    memo = {}
    print("작업 그래프:\n")
    for name, task in TASKS.items():
        if not task.cacheable:
            status = "캐시 안 함 — 항상 실행"
        elif cache_hit(name, resolve_key(name, memo)):
            status = "캐시됨 — 건너뜀"
        else:
            status = "다시 실행 필요"
        dep = f"  ← 먼저: {', '.join(task.deps)}" if task.deps else ""
        print(f"  {name:<8} {task.doc}{dep}")
        detail = f"  inputs: {', '.join(task.inputs)}" if task.cacheable and task.inputs else ""
        print(f"  {'':<8} [{status}]{detail}")
    print(f"\n캐시 위치: {CACHE_DIR.relative_to(ROOT)}  (비우기: python tasks.py clean)")


def main():
    parser = argparse.ArgumentParser(prog="tasks.py", description="COSMOS 작업 실행기",
                                     add_help=False)
    parser.add_argument("task", nargs="?")
    parser.add_argument("-f", "--force", action="store_true", help="캐시를 무시하고 다시 실행")
    parser.add_argument("-h", "--help", action="store_true")
    opts = parser.parse_args()

    if opts.help or not opts.task or opts.task == "help":
        print("사용법: python tasks.py <작업> [--force]\n")
        for name, task in TASKS.items():
            print(f"  {name:<8} {task.doc}")
        print(f"  {'graph':<8} 작업 그래프와 캐시 상태 보기")
        print("\nPR 올리기 전엔 `python tasks.py check`.")
        return 0

    if opts.task == "graph":
        show_graph()
        return 0

    if opts.task not in TASKS:
        die(f"그런 작업은 없다: {opts.task}\n     가능한 작업: {', '.join(TASKS)}, graph")

    execute(opts.task, opts, {}, set())
    return 0


if __name__ == "__main__":
    sys.exit(main())
