#!/usr/bin/env python3
"""COSMOS 작업 실행기 — 작업 그래프 + 입력 해시 캐시.

    python tasks.py                 작업 목록
    python tasks.py setup           uv.lock 그대로 .venv 구성
    python tasks.py check           CI sim job의 check 단계와 같은 검사 (CI 전체는 아님, 아래 참고)
    python tasks.py check --force   캐시 무시하고 전부 다시 실행
    python tasks.py graph           작업 그래프와 캐시 상태 보기
    python tasks.py lock            의존성 다시 풀고 uv.lock/requirements.txt 갱신
    python tasks.py train           PPO 본 학습 (200k 스텝, 오래 걸림)

check와 CI: CI(.github/workflows/ci.yml)의 sim job이 `python tasks.py check`를 그대로 돌린다.
CI는 그 밖에 학습 자료 목록·내부 링크 검사와 펌웨어 PlatformIO 빌드를 ci.yml에서 직접 돌린다.
이 둘은 check에 없다. 로컬에서 check를 통과해도 이 둘은 따로 확인한다(명령은 ci.yml).
check가 돌리는 단계는 `python tasks.py graph`의 check 줄을 본다.

왜 Makefile이 아니라 이 파일인가: 팀 개발 환경이 Windows 위주인데 Windows엔 `make`가 기본으로
없다. 반면 파이썬은 소프트웨어팀이 어차피 설치해야 한다. 표준 라이브러리만 쓰므로 추가 설치도
없고, Mac/Linux에서도 같은 명령이 그대로 동작한다.

왜 캐시가 붙었나: 검사가 늘어날수록 "안 바뀐 것까지 매번 다시 도는" 시간이 쌓인다. 각 작업은
자기가 읽는 파일 목록(inputs)을 선언하고, 그 파일들의 내용 해시가 지난번과 같으면 건너뛴다.
파일을 하나라도 고치면 그 작업과, 그 작업에 의존하는 작업이 전부 다시 돈다. 캐시가 의심스러우면
`--force`로 무시하거나 `python tasks.py clean`으로 비운다.

캐시가 보장하는 것과 보장하지 않는 것 (알고 쓰라고 적어둔다):
  보장한다  - 선언된 입력 파일의 내용이 지난번 통과 때와 같다.
             - .venv에 설치된 패키지 목록과 파이썬 버전이 uv.lock과 같다(실행 시작 시
               `uv sync --locked`로 맞추고, 그 지문을 캐시 키에 넣는다).
  보장 안 함 - .venv 안 파일의 '내용'까지 멀쩡한지는 보지 않는다. 손으로 site-packages를
               고쳤거나 동기화 도구가 파일을 망가뜨린 경우, 캐시 히트로 통과할 수 있다.
               deck의 산출물도 존재만 보고 내용은 보지 않는다. 확인하려면 `--force`.
  왜 여기까지만 - 측정값(이 저장소, OneDrive 폴더): 캐시 히트 check 0.9초, 전부 실행 10.9초.
               여기에 site-packages 18,005개 파일 해싱을 더하면 +2.6초(≈3.5초),
               import 프로브를 더하면 +3.7초(≈4.6초)다. 못 쓸 정도는 아니지만,
               막으려는 게 "사람이 venv를 손으로 헤집는" 드문 경우라 값이 비싸다.
               흔한 쪽(환경 삭제·패키지 변경)은 이미 지문으로 잡고 있다.
  그래서     - 최종 판정은 CI다. CI는 러너를 새로 띄우므로 항상 캐시 없이 전부 돈다.

의존성 관리는 여기가 아니라 uv가 한다(pyproject.toml + uv.lock). 이 파일은 "무엇을 어떤
순서로 실행할지"만 안다 — 둘을 섞지 않는다.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

def _survive_console_encoding():
    """출력이 콘솔 인코딩에 걸려 죽지 않게 한다.

    한국어 Windows의 기본 콘솔 인코딩은 cp949인데, 여기엔 em dash(—) 같은 문자가 없다.
    파이썬은 진짜 콘솔에 붙어 있을 때는 UTF-8로 쓰지만, 출력을 파이프로 넘기거나 파일로
    리다이렉트하면 locale 인코딩(cp949)으로 떨어져서 UnicodeEncodeError로 죽는다.
    즉 `python tasks.py check > log.txt` 나 CI 로그 수집에서만 터진다 — 제일 나쁜 종류다.

    인코딩을 UTF-8로 바꾸지는 않는다. cp949 콘솔에 UTF-8 바이트를 쓰면 한글이 전부
    깨져 보이기 때문이다. 인코딩은 그대로 두고 '못 쓰는 문자만 대체'로 바꾼다.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # 리다이렉트된 특수 스트림 등 — 여기서 실패해도 작업 실행엔 지장 없다


ROOT = Path(__file__).resolve().parent
SIM = ROOT / "sim"
STAGE1 = SIM / "sim_stage1"
CONNECTOME = SIM / "connectome"
DECK = ROOT / "docs" / "presentation"
VENV = ROOT / ".venv"
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
        '           Windows PowerShell:  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n'
        "           Mac/Linux:           curl -LsSf https://astral.sh/uv/install.sh | sh",
    )


def child_env():
    """자식 프로세스도 같은 이유(cp949)로 죽지 않게 한다.

    sanity_check.py·train.py 출력에도 em dash가 들어 있어서, 위 _survive_console_encoding()은
    이 파일의 출력만 지켜준다. 자식에게는 PYTHONIOENCODING으로 같은 정책을 물려준다 —
    인코딩은 부모(또는 사용자가 이미 정한 값)와 같게 두고, 오류 처리만 replace로 맞춘다.
    """
    env = os.environ.copy()
    parent = getattr(sys.stdout, "encoding", None) or "utf-8"
    # 이미 설정돼 있어도 오류 처리 정책은 replace로 덮는다. cp949:strict 처럼 잡혀
    # 있으면 자식이 그대로 죽어서, 여기서 하려던 보호가 성립하지 않는다. 인코딩
    # 자체는 사용자가 정한 값을 존중한다. 단 ":replace" 처럼 콜론 앞이 비어 있으면
    # 그건 "인코딩은 기본값 그대로"라는 뜻이므로 부모 인코딩을 쓴다.
    encoding = (env.get("PYTHONIOENCODING") or "").split(":", 1)[0] or parent
    env["PYTHONIOENCODING"] = f"{encoding}:replace"
    return env


def run(cmd, cwd=None):
    where = f" (cwd: {Path(cwd).relative_to(ROOT)})" if cwd else ""
    print(f"\n$ {' '.join(str(c) for c in cmd)}{where}", flush=True)
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, env=child_env())
    if result.returncode != 0:
        die(f"위 명령이 실패했다 (exit {result.returncode}).")


def sync_to_lock(verbose=False):
    """.venv를 uv.lock에 맞춘다. 환경을 건드리는 경로는 전부 여기를 지나간다.

    --locked 인 이유: CI가 쓰는 판정과 같게 하려는 것이다. --frozen 은 lock이
    pyproject.toml보다 낡아도 그냥 통과시키므로, 로컬은 초록불인데 CI만 빨간불인
    상황이 만들어진다. 로컬에서 먼저 걸리는 편이 낫다.

    이미 맞는 환경이면 0.1초로 끝나므로 조건을 걸지 않고 늘 부른다 — "환경이 lock과
    같다"를 실행 시작 시점에 참으로 만들어 두는 게, 어떤 작업이 먼저 도느냐에 따라
    캐시 판정이 달라지는 것보다 낫다.
    """
    if verbose:
        print("[준비] .venv 를 uv.lock 기준으로 맞춘다.")
    result = subprocess.run([str(uv()), "sync", "--locked"], cwd=ROOT, env=child_env(),
                            capture_output=not verbose, text=True, encoding="utf-8",
                            errors="replace")
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        die("환경을 uv.lock 에 맞추지 못했다.\n"
            "     pyproject.toml 을 고쳤다면 `python tasks.py lock` 으로 lock을 갱신할 것.\n"
            "     네트워크 문제라면 연결을 확인하고 다시 시도.")


def uv_run(args, cwd=None):
    """워크스페이스 환경에서 실행. --frozen이라 uv.lock을 그대로 쓴다(멋대로 갱신하지 않는다).

    uv run은 실행 전에 .venv를 uv.lock에 맞춰 알아서 맞춰주므로, setup을 먼저 돌리지
    않아도 된다. cwd를 sim 안으로 바꿔도 --project로 워크스페이스 루트를 짚어준다.
    """
    run([uv(), "run", "--frozen", "--project", ROOT, *args], cwd=cwd)


# ─────────────────────────────────────────────────────────────────────────────
# Windows: torch가 쓰는 VC++ 런타임 확인 (#108)
# ─────────────────────────────────────────────────────────────────────────────

# 새 Windows PC에는 Microsoft Visual C++ 재배포 패키지가 없을 수 있다. 그러면 torch가 c10.dll을
# 불러오지 못하고 `OSError: [WinError 126]`으로 멈춘다. torch를 쓰는 작업이 돌기 전에 이것을 찾아서,
# 영어 오류 대신 설치 명령을 보여 준다.
#
# 내려받기 주소: https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist 의 x64 고정 링크.
# winget 패키지 ID: microsoft/winget-pkgs 저장소의 manifests/m/Microsoft/VCRedist/2015+/x64.
VC_INSTALL_CMD = "winget install --id Microsoft.VCRedist.2015+.x64 --exact --source winget"
VC_INSTALL_URL = "https://aka.ms/vc14/vc_redist.x64.exe"

# .venv의 파이썬으로 실행하는 검사 코드. 이 파이썬이 torch를 불러오는 파이썬이다. tasks.py를
# 실행한 파이썬으로 검사하면 결과가 다를 수 있다. 실행 파일 폴더와 32/64비트가 다를 수 있기 때문이다.
#
# DLL 목록: torch 2.14.0 Windows 휠의 c10.dll이 가져오는 VC++ 런타임 DLL 세 개다. torch/__init__.py도
# c10.dll을 불러오기 전에 이 세 이름을 같은 순서로 불러 보고, ARM64에서는 vcruntime140_1.dll을
# 건너뛴다. 이 DLL은 torch 휠(torch/lib)에 들어 있지 않다.
#
# winmode=0: Windows 기본 DLL 검색 순서(실행 파일 폴더, System32, Windows 폴더, 현재 폴더, PATH)로
# 찾는다. torch는 PATH를 빼고 먼저 찾고, 못 찾으면 PATH를 더해 다시 찾는다. 그래서 여기서도 PATH까지
# 본다. 그래야 torch가 실제로 실패하는 경우에만 멈춘다. ctypes 기본값(winmode=None)은 PATH를 보지 않는다.
VC_PROBE = """\
import ctypes, json, platform
names = ["vcruntime140.dll", "msvcp140.dll"]
if platform.machine() != "ARM64":
    names.append("vcruntime140_1.dll")
missing = []
for name in names:
    try:
        ctypes.WinDLL(name, winmode=0)
    except OSError:
        missing.append(name)
print(json.dumps(missing))
"""


def venv_python():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def probe_vc_runtime(python):
    """python으로 VC_PROBE를 실행해 찾지 못한 DLL 이름 목록을 돌려준다.

    검사 자체를 하지 못하면(파이썬 실행 실패, 시간 초과, 알 수 없는 출력) None을 돌려준다.
    """
    try:
        result = subprocess.run([str(python), "-I", "-c", VC_PROBE], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    lines = (result.stdout or "").strip().splitlines()
    try:
        missing = json.loads(lines[-1])
    except (IndexError, ValueError):
        return None
    if not isinstance(missing, list) or not all(isinstance(n, str) for n in missing):
        return None
    return missing


def ensure_vc_runtime(windows=None):
    """Windows에서 torch에 필요한 VC++ 런타임 DLL이 없으면 설치 방법을 출력하고 멈춘다(#108).

    Windows가 아니면 아무것도 하지 않는다. 검사 자체를 하지 못하면 경고만 하고 진행한다.
    검사 코드가 틀려서 멀쩡한 PC를 막는 것보다, torch가 원래 오류를 내게 두는 편이 낫다.
    windows는 단위 검사(test_vcruntime.py)가 Linux에서 Windows 경로를 돌릴 때만 준다.
    """
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return
    missing = probe_vc_runtime(venv_python())
    if missing is None:
        print("\n[경고] Microsoft Visual C++ 재배포 패키지가 있는지 확인하지 못했다. 그대로 진행한다.\n"
              "     torch가 c10.dll 오류(WinError 126)로 멈추면 PowerShell에서 아래 명령으로 설치한다.\n"
              f"     {VC_INSTALL_CMD}", file=sys.stderr, flush=True)
        return
    if missing:
        die("torch에 필요한 Microsoft Visual C++ 재배포 패키지(x64)가 이 PC에 없다(#108).\n"
            f"     찾지 못한 DLL: {', '.join(missing)}\n"
            "     이대로 실행하면 torch가 c10.dll을 불러오지 못하고 OSError [WinError 126]으로 멈춘다.\n"
            "     1) PowerShell에서 설치한다:\n"
            f"          {VC_INSTALL_CMD}\n"
            "        winget이 없다는 오류가 나면 아래 파일을 받아 실행한다:\n"
            f"          {VC_INSTALL_URL}\n"
            "     2) 관리자 권한 확인 창(UAC)이 뜨면 \"예\"를 누른다.\n"
            "     3) 설치가 끝나면 방금 실행한 python tasks.py 명령을 다시 실행한다.")


# ─────────────────────────────────────────────────────────────────────────────
# 입력 해시 캐시
# ─────────────────────────────────────────────────────────────────────────────

def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_inputs(patterns, root=None):
    """글롭 패턴들을 (저장소 기준 상대경로, 내용해시) 목록으로 펼친다.

    tasks.py 자신은 항상 포함한다 — 무엇을 실행할지가 여기 적혀 있으므로, 이 파일이
    바뀌면 모든 캐시가 무효가 되는 게 맞다.

    root는 단위 검사가 임시 폴더를 저장소 대신 줄 때만 쓴다(test_userpath.py). 기본은 ROOT.
    """
    root = ROOT if root is None else root
    found = set()
    for pattern in list(patterns) + ["tasks.py"]:
        for p in root.glob(pattern):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if SKIP_DIRS & set(rel.parts):
                continue
            found.add(rel.as_posix())
    return sorted((rel, _digest(root / rel)) for rel in found)


def env_fingerprint():
    """.venv의 상태 요약. 캐시가 "환경이 멀쩡하다"를 함께 기억하게 하려는 것.

    입력 파일만 해싱하면 이런 구멍이 생긴다: check를 통과한 뒤 .venv를 지워도 sanity와
    smoke가 캐시 히트로 건너뛰어서, 환경이 없는데 check가 성공한다. 검사의 목적이
    "환경이 살아 있는가"인데 그걸 확인하지 않고 통과시키는 셈이다.

    설치된 패키지 목록(dist-info 이름)까지 넣으므로, 손으로 pip install해서 버전을
    어긋나게 만든 경우에도 캐시가 무효가 된다.
    """
    cfg = VENV / "pyvenv.cfg"
    if not cfg.exists():
        return "no-venv"
    h = hashlib.sha256()
    h.update(_digest(cfg).encode())
    site_dirs = [VENV / "Lib" / "site-packages", *(VENV / "lib").glob("python*/site-packages")]
    for site in site_dirs:
        if site.is_dir():
            for name in sorted(p.name for p in site.iterdir() if p.name.endswith(".dist-info")):
                h.update(name.encode())
    return h.hexdigest()


def cache_key(task, dep_keys):
    h = hashlib.sha256()
    h.update(CACHE_VERSION.encode())
    h.update(task.name.encode())
    for k in sorted(dep_keys):
        h.update(k.encode())
    for rel, digest in collect_inputs(task.inputs):
        h.update(rel.encode())
        h.update(digest.encode())
    if task.uses_env:
        h.update(env_fingerprint().encode())
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
    if not (CACHE_DIR / name / key).exists():
        return False
    # 결과물을 만드는 작업은 그 결과물이 실제로 있어야 "이미 했다"고 말할 수 있다.
    # (예: deck의 pptx를 지운 뒤 다시 돌리면 입력은 그대로라 캐시가 맞지만, 파일은 없다.)
    return all((ROOT / out).exists() for out in TASKS[name].outputs)


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
    def __init__(self, name, doc, run=None, deps=(), inputs=(), outputs=(),
                 cacheable=True, uses_env=False, needs_torch=False):
        self.name = name
        self.doc = doc
        self.run = run or (lambda: None)
        self.deps = tuple(deps)
        self.inputs = tuple(inputs)       # 이 파일들의 내용이 그대로면 건너뛴다
        self.outputs = tuple(outputs)     # 이 파일들이 없으면 캐시가 맞아도 다시 만든다
        self.cacheable = cacheable
        self.uses_env = uses_env          # .venv 상태를 캐시 키에 포함할지
        self.needs_torch = needs_torch    # torch를 불러오는지. Windows에서 VC++ 런타임을 먼저 확인한다(#108)


def task_setup():
    # ensure_env와 같은 판정(--locked)을 쓴다. setup만 --frozen이면 낡은 lock으로
    # 환경이 만들어지고, 정작 check와 CI는 그 lock을 거부하는 엇갈림이 생긴다.
    sync_to_lock(verbose=True)
    # 새 Windows PC는 여기까지 성공하고 check의 smoke에서야 torch 오류로 멈췄다(#108).
    # 설치를 마쳤다고 알리기 전에 VC++ 런타임부터 확인한다.
    ensure_vc_runtime()
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
        "# uv 없이 pip만으로 환경을 맞춰야 할 때 쓰라고 남겨둔 사본이다.\n"
        "#\n"
        "#   Windows / macOS:  pip install -r sim/requirements.txt\n"
        "#   Linux:            pip install -r sim/requirements.txt \\\n"
        "#                       --extra-index-url https://download.pytorch.org/whl/cpu\n"
        "#\n"
        "# 리눅스만 인덱스를 더 주는 이유: 아래 torch 줄이 리눅스에서는 2.14.0+cpu인데\n"
        "# 그 휠은 PyPI에 없고 PyTorch 인덱스에만 있다. 반대로 이 인덱스를 파일 안에\n"
        "# --extra-index-url 로 박아버리면 Windows에서도 그 인덱스를 뒤지게 되고,\n"
        "# pip는 로컬 버전이 붙은 2.14.0+cpu 를 2.14.0 보다 높다고 보기 때문에\n"
        "# uv.lock이 지정한 PyPI 휠 대신 CPU 휠을 깔아버린다 — lock과 어긋난다.\n"
        "\n"
    )
    out.write_text(banner + out.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"\n갱신: uv.lock, {out.relative_to(ROOT)}")


def task_compile():
    """검사 대상을 inputs 선언에서 그대로 뽑는다 — 둘이 어긋날 수 없게.

    예전엔 `compileall sim`처럼 디렉터리를 넘겼는데 두 방향으로 틀렸다.
    (1) 남아 있는 sim/venv 안의 파일 수천 개까지 컴파일했다. 그것들은 inputs에서는
        제외돼 있어서, 거기서 나는 실패는 캐시 키와 아무 관계가 없었다.
    (2) 반대로 새로 만든 test_foo.py는 inputs 패턴에는 걸려 캐시를 무효화하면서도
        실제 컴파일 대상에는 없었다 — 문법 오류가 그대로 통과했다.
    """
    files = [rel for rel, _ in collect_inputs(TASKS["compile"].inputs) if rel.endswith(".py")]
    if not files:
        # 인자가 비면 compileall이 sys.path 전체를 컴파일한다. 조용히 엉뚱한 일을 하느니 멈춘다.
        die("컴파일할 파이썬 파일을 찾지 못했다. compile 작업의 inputs 패턴을 확인할 것.")
    uv_run(["python", "-m", "compileall", "-q", *files], cwd=ROOT)


def task_sanity():
    uv_run(["python", "sanity_check.py"], cwd=STAGE1)


def task_gate():
    uv_run(["python", "pd_gate.py"], cwd=STAGE1)


def task_yaw():
    uv_run(["python", "yaw_check.py"], cwd=STAGE1)


def task_smoke():
    uv_run(["python", "-c", SMOKE], cwd=STAGE1)


def task_connectome():
    """커넥톰 그래프(합성 + 셔플 대조군)를 만든다.

    결과물을 커밋하지 않는 이유: build_subgraph.py가 고정된 규칙으로 결정론적으로
    만들어내므로 저장소에 둘 이유가 없고, 생성기와 npz가 따로 놀다가 어긋나는 사고를
    아예 없앤다. FlyWire 실측 그래프는 애초에 수백 MB 원본이 필요해 여기 못 들어온다.
    """
    uv_run(["python", "build_subgraph.py", "--source", "synthetic"], cwd=CONNECTOME)
    uv_run(["python", "shuffle.py",
            "--in", "graphs/synthetic.npz",
            "--out", "graphs/synthetic_shuffled.npz"], cwd=CONNECTOME)


def task_conncheck():
    uv_run(["python", "check.py"], cwd=CONNECTOME)


def task_skills():
    """Codex용 스킬 복사본(.agents/skills)이 정본(.claude/skills)과 같은지 본다(#39).

    비교 코드는 ship.py에 하나만 둔다. 어긋났을 때 맞추는 명령(`python ship.py skills`)과
    같은 코드여야 검사와 수정이 서로 다른 판정을 내리지 않는다.
    """
    run([sys.executable, "ship.py", "skills", "--check"], cwd=ROOT)


def task_shiptest():
    """ship.py 단위 검사(test_ship.py, #109). gh·git을 부르지 않고 가짜 응답으로 돈다.

    .venv가 필요 없다. ship.py처럼 표준 라이브러리만 쓰므로 이 파이썬으로 바로 돌린다.
    """
    run([sys.executable, "-m", "unittest", "test_ship"], cwd=ROOT)


def task_vcruntime():
    """Windows VC++ 런타임 확인(#108)의 단위 검사(test_vcruntime.py).

    실제 확인은 Windows에서만 돌아서 CI(Linux)에서는 늘 건너뛴다. 그래서 검사 코드와 판정을
    가짜 DLL 로더와 가짜 응답으로 여기서 돌린다. 표준 라이브러리만 쓰므로 .venv가 필요 없다.
    """
    run([sys.executable, "-m", "unittest", "test_vcruntime"], cwd=ROOT)


# kicad/_tools 스크립트에 작성자 PC의 사용자 홈 폴더 경로가 다시 들어오면 다른 PC에서
# FileNotFoundError로 죽는다(#67). userpath 작업이 이것을 막는다(#96).
USER_PATH_SCAN = ["kicad/_tools/*.py"]
# 이 정규식과 아래 주석에는 실제 경로 예시를 쓰지 않는다. tasks.py를 검사해도 자기 자신에
# 걸리지 않게 하려는 것이다. 걸리는 예와 안 걸리는 예는 test_userpath.py에 있다.
USER_PATH_RE = re.compile(
    # Windows 사용자 폴더: 드라이브 문자, 구분자(슬래시, 역슬래시, 문자열 안의 이중 역슬래시),
    # Users 폴더. 드라이브 문자는 전부 본다. 사용자 폴더를 다른 드라이브로 옮길 수 있다.
    # Users는 대소문자를 가리지 않는다. Windows 경로가 대소문자를 가리지 않기 때문이다.
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]+(?i:users)(?![A-Za-z0-9_])"
    # macOS 사용자 폴더. Git Bash와 WSL에서 본 Windows 사용자 폴더 경로에도 이 부분이 있다.
    # 대소문자를 가린다. 소문자 users는 웹 API 주소에 흔하다.
    r"|[\\/]Users[\\/]"
    # Linux 사용자 폴더. Windows에서 WSL 안의 이 폴더를 열면 구분자가 역슬래시라서 둘 다 본다.
    r"|[\\/]home[\\/]"
)


def find_user_paths(text):
    """text에서 사용자 홈 폴더 경로를 찾는다. (줄 번호, 칸 번호, 찾은 글자) 목록을 돌려준다.

    줄과 칸은 1부터 센다. 줄은 줄바꿈 문자 하나로만 나눈다. str.splitlines()는 폼 피드 같은
    문자에서도 줄을 나눠서 편집기와 줄 번호가 달라진다. 주석도 검사한다. 주석의 경로도
    작성자 PC에서만 맞다.
    """
    hits = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        for m in USER_PATH_RE.finditer(line):
            hits.append((lineno, m.start() + 1, m.group()))
    return hits


def scan_user_paths(root, patterns):
    """patterns에 걸리는 root 아래 파일을 검사한다. (검사한 파일 목록, 찾은 목록)을 돌려준다.

    찾은 목록의 한 항목은 (저장소 기준 상대경로, 줄 번호, 칸 번호, 찾은 글자)다.

    파일 목록은 collect_inputs()로 만든다. 작업의 inputs 선언과 검사 대상이 어긋나지 않게
    하려는 것이다. collect_inputs()가 늘 넣는 tasks.py는 검사 대상이 아니라서 뺀다.
    """
    files = [rel for rel, _ in collect_inputs(patterns, root) if rel != "tasks.py"]
    hits = []
    for rel in files:
        # read_text는 줄바꿈 \r\n과 \r을 \n으로 바꿔 읽는다. 그래서 Windows 파일도 줄 번호가 맞다.
        # utf-8-sig는 파일 맨 앞의 BOM을 빼고 읽고, BOM이 없는 파일은 utf-8과 같게 읽는다.
        # utf-8로 읽으면 BOM이 글자 하나로 남아서 1줄 칸 번호가 편집기보다 1 크다.
        text = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        hits.extend((rel, *hit) for hit in find_user_paths(text))
    return files, hits


def task_userpath():
    """kicad/_tools/*.py에 사용자 홈 폴더 경로가 없는지 본다(#96).

    검사기가 고장 나서 아무것도 못 찾으면 이 작업은 조용히 통과한다. 그래서 검사기 자체의
    단위 검사(test_userpath.py)를 먼저 돌린다.
    """
    run([sys.executable, "-m", "unittest", "-q", "test_userpath"], cwd=ROOT)
    files, hits = scan_user_paths(ROOT, USER_PATH_SCAN)
    if not files:
        # 폴더를 옮기거나 지우면 검사할 파일이 0개가 되고 검사가 늘 통과한다. 그렇게 두지 않는다.
        die(f"검사할 파일을 찾지 못했다: {', '.join(USER_PATH_SCAN)}\n"
            "     폴더를 옮겼다면 tasks.py의 USER_PATH_SCAN을 고칠 것.")
    for rel, lineno, col, match in hits:
        # 파일:줄:칸: 형식이다. 편집기와 CI 로그 도구가 이 형식으로 해당 줄을 연다.
        print(f"{rel}:{lineno}:{col}: 사용자 홈 폴더 경로 '{match}'", flush=True)
    if hits:
        die(f"kicad/_tools에서 사용자 홈 폴더 경로 {len(hits)}건을 찾았다(#96).\n"
            "     작성자 PC에서만 있는 경로라 다른 PC에서 스크립트가 죽는다(#67).\n"
            "     스크립트 위치(Path(__file__)) 기준 경로, 명령행 인자, 환경변수 중 하나로 바꿀 것.")
    print(f"사용자 홈 폴더 경로 없음 - {len(files)}개 파일 검사")


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
# 커넥톰 점검은 환경(Stage 1)까지 같이 쓰므로 양쪽을 다 입력으로 잡는다.
CONN_IN = ["sim/connectome/*.py", *SIM_IN]

TASKS = {t.name: t for t in [
    Task("setup", "uv.lock 그대로 .venv 구성 (Windows는 VC++ 재배포 패키지도 확인, #108)", task_setup,
         inputs=DEPS_IN, cacheable=False),
    Task("lock", "의존성 재해석 - uv.lock + sim/requirements.txt 갱신", task_lock, cacheable=False),
    Task("compile", "파이썬 문법 체크", task_compile,
         inputs=["sim/**/*.py", "test_*.py", "ship.py", *DEPS_IN], uses_env=True),
    Task("sanity", "환경이 살아 있는지 20스텝 확인", task_sanity, inputs=SIM_IN, uses_env=True),
    Task("gate", "RL 전 합격 기준 - 랜덤화 켠 PD 200 에피소드 (#27)", task_gate, inputs=SIM_IN,
         uses_env=True),
    Task("yaw", "요 축 검사 - 토크·회전자 항 손계산 + 요 PD 200 seed × 6조건(스로틀 고정·계단, 회전자 항 끔·켬) (#65, #86)",
         task_yaw,
         inputs=SIM_IN, uses_env=True),
    Task("smoke", "SB3-환경 연결 확인 (256스텝, 학습 아님)", task_smoke, inputs=SIM_IN,
         uses_env=True, needs_torch=True),
    Task("connectome", "커넥톰 그래프 생성 (합성 + 셔플 대조군)", task_connectome,
         inputs=CONN_IN,
         outputs=["sim/connectome/graphs/synthetic.npz",
                  "sim/connectome/graphs/synthetic_shuffled.npz"],
         uses_env=True),
    Task("conncheck", "커넥톰 정책망 점검 (그래프/셔플/수치/SB3연결)", task_conncheck,
         inputs=CONN_IN, uses_env=True, needs_torch=True),
    Task("skills", "Codex용 스킬 복사본이 정본과 같은지 확인 (#39)", task_skills,
         inputs=[".claude/skills/**/*", ".agents/skills/**/*", "ship.py"]),
    Task("shiptest", "ship.py 단위 검사 - gh 없이 가짜 응답으로 (#109)", task_shiptest,
         inputs=["ship.py", "test_ship.py"]),
    Task("userpath", "kicad/_tools/*.py에 사용자 홈 폴더 경로가 없는지 확인 (#96)", task_userpath,
         inputs=[*USER_PATH_SCAN, "test_userpath.py"]),
    Task("vcruntime", "Windows VC++ 런타임 확인의 단위 검사 - 가짜 응답으로 (#108)", task_vcruntime,
         inputs=["test_vcruntime.py"]),
    Task("check", "CI sim job의 check 단계와 같은 검사 (학습 자료 검사·펌웨어 빌드는 빠짐,"
         " 단계 목록은 graph)", task_check,
         deps=["skills", "shiptest", "userpath", "vcruntime", "compile", "sanity", "gate", "yaw",
               "smoke", "conncheck"]),
    Task("train", "PPO 본 학습 (200k 스텝, 오래 걸림)", task_train, cacheable=False,
         uses_env=True, needs_torch=True),
    Task("deck", "설명회 pptx 다시 생성 (node 필요)", task_deck,
         inputs=["docs/presentation/build_deck.js", "docs/presentation/speaker-notes.md"],
         outputs=["docs/presentation/cosmos-info-session.pptx"]),
    Task("clean", "작업 캐시 비우기", task_clean, cacheable=False),
]}


# ─────────────────────────────────────────────────────────────────────────────
# 그래프 실행
# ─────────────────────────────────────────────────────────────────────────────

def needed_tasks(name, seen=None):
    """name과 그 의존 작업 전체."""
    seen = seen if seen is not None else set()
    if name in seen:
        return seen
    seen.add(name)
    for dep in TASKS[name].deps:
        needed_tasks(dep, seen)
    return seen


def ensure_env(name):
    """캐시를 판정하기 전에 .venv를 먼저 확정한다.

    안 그러면 캐시 판정이 작업 순서에 딸려 간다: .venv를 지운 상태에서 check를 돌리면
    먼저 실행된 compile이 .venv를 복구해버리고, 그 뒤에 키가 계산되는 sanity·smoke는
    캐시 히트가 된다. 결과 자체는 옳지만(환경이 lock 기준으로 복구됐으니) 판정 근거가
    "그 순간 .venv가 있었느냐"라는 우연에 걸린다.

    먼저 환경을 만들어 두면 이 실행 내내 env_fingerprint()가 고정되고, 캐시는
    "이 환경 + 이 입력으로 이미 통과했는가"라는 한 가지 질문에만 답하게 된다.

    torch를 쓰는 작업이 있으면 환경을 맞춘 직후 VC++ 런타임도 확인한다(#108). torch 작업
    바로 앞이 아니라 여기서 하는 이유: check에서 smoke는 gate·yaw 뒤에 돈다. 그 앞에서 멈춰야
    부원이 기다리지 않고 바로 설치 명령을 본다.
    """
    needed = needed_tasks(name)
    if not any(TASKS[n].uses_env for n in needed):
        return
    sync_to_lock(verbose=not (VENV / "pyvenv.cfg").exists())
    if any(TASKS[n].needs_torch for n in needed):
        ensure_vc_runtime()


def execute(name, opts, memo, done):
    if name in done:
        return
    task = TASKS[name]
    for dep in task.deps:
        execute(dep, opts, memo, done)

    key = resolve_key(name, memo)
    if task.cacheable and not opts.force and cache_hit(name, key):
        print(f"[캐시] {name} - 입력이 그대로다, 건너뛴다.")
        done.add(name)
        return

    print(f"[실행] {name} - {task.doc}")
    task.run()
    if task.cacheable:
        # 실행 전 키가 아니라 '실행 후' 키를 저장한다. uses_env 작업은 실행 과정에서
        # .venv가 만들어지거나 갱신될 수 있어서, 실행 전 키를 저장하면 다음 번에 절대
        # 맞지 않아 매번 다시 돌게 된다. 다음 실행 시점의 상태와 같은 키를 남긴다.
        cache_write(name, resolve_key(name, {}))
    done.add(name)


def show_graph():
    memo = {}
    print("작업 그래프:\n")
    for name, task in TASKS.items():
        if not task.cacheable:
            status = "캐시 안 함 - 항상 실행"
        elif cache_hit(name, resolve_key(name, memo)):
            status = "캐시됨 - 건너뜀"
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

    # CLI로 실행될 때만 스트림을 건드린다. import 시점에 하면 이 파일을 모듈로
    # 불러다 쓰는 쪽(테스트 등)의 sys.stdout 정책까지 조용히 바꿔놓게 된다.
    _survive_console_encoding()

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

    ensure_env(opts.task)
    execute(opts.task, opts, {}, set())
    return 0


if __name__ == "__main__":
    sys.exit(main())
