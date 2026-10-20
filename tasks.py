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
check의 cad 작업은 OpenSCAD가 필요하다. 없는 PC에서는 건너뛰고, CI는 OpenSCAD를 설치해서 돌린다(#61).

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
import ast
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
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

# PPO 스모크 코드. 정본은 이 상수 하나다. ci.yml에는 복사본이 없다.
# CI sim job의 check 단계(`python3 tasks.py check`)가 smoke 작업(task_smoke)으로 이 코드를 돌린다.
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

    위 _survive_console_encoding()은 이 파일의 출력만 지켜준다. sim/ 스크립트의 print 문자열에서
    cp949에 없는 문자(em dash 등)는 뺐다(#137, #147). 그래도 라이브러리 출력이나 경로처럼 글자를
    고를 수 없는 출력이 있다. 그래서 자식에게는 PYTHONIOENCODING으로 같은 정책을 물려준다.
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
# 찾는 방법은 torch/__init__.py의 _load_dll_libraries()와 같게 한다. torch가 실제로 실패할 때만
# 멈추려는 것이다. torch는 아래 순서로 찾는다.
#   1) torch/lib, <venv>/Library/bin 같은 폴더를 os.add_dll_directory로 더한 뒤, 실행 파일 폴더,
#      더한 폴더, System32에서 찾는다. ctypes 기본값(winmode=None)이 이 방식이다.
#   2) 못 찾으면 더한 폴더를 PATH 앞에 붙이고 Windows 표준 검색 순서로 다시 찾는다. 표준 검색
#      순서는 PATH까지 본다. winmode=0이 이 방식이다.
# torch는 CUDA 빌드에서만 CUDA 폴더를 더한다. 우리 torch는 CPU 빌드라서 그 폴더는 뺐다.
VC_PROBE = """\
import ctypes, importlib.util, json, os, platform, sys, sysconfig
spec = importlib.util.find_spec("torch")
userbase = sysconfig.get_config_var("userbase")
dirs = [
    os.path.join(os.path.dirname(spec.origin), "lib") if spec and spec.origin else "",
    os.path.join(sys.exec_prefix, "Library", "bin"),
    os.path.join(sys.base_exec_prefix, "Library", "bin") if sys.exec_prefix != sys.base_exec_prefix else "",
    os.path.join(userbase, "Library", "bin") if userbase else "",
    os.path.join(sys.exec_prefix, "bin"),
]
dirs = [d for d in dirs if d and os.path.exists(d)]
for d in dirs:
    os.add_dll_directory(d)
os.environ["PATH"] = os.pathsep.join(dirs + [os.environ.get("PATH", "")])
names = ["vcruntime140.dll", "msvcp140.dll"]
if platform.machine() != "ARM64":
    names.append("vcruntime140_1.dll")
missing = []
for name in names:
    try:
        ctypes.WinDLL(name)
    except OSError:
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


def glob_inputs(root, pattern):
    """root.glob(pattern)과 같은 경로를 낸다. 단 "**/이름" 형식이면 SKIP_DIRS 안으로 들어가지 않는다.

    root.glob("**/*.md")는 .venv의 파일 약 1만 8천 개 사이를 전부 돈다. 그 결과는 collect_inputs()가
    SKIP_DIRS로 버리지만, 도는 데만 패턴 하나에 약 0.17초가 든다(2026-10-19 서버 측정, #183).
    그래서 이 형식만 os.walk로 돌면서 SKIP_DIRS를 건너뛴다. 결과는 root.glob()에서 SKIP_DIRS 안의
    경로를 뺀 것과 같다(test_agentsref.py가 비교한다). 다른 형식은 root.glob()을 그대로 쓴다.
    fnmatch.filter()는 root.glob()처럼 Windows에서만 대소문자를 가리지 않는다.
    """
    head, sep, name = pattern.partition("/")
    if head != "**" or not sep or "/" in name or "**" in name:
        yield from root.glob(pattern)
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in fnmatch.filter(filenames, name):
            yield Path(dirpath) / filename


def collect_inputs(patterns, root=None):
    """글롭 패턴들을 (저장소 기준 상대경로, 내용해시) 목록으로 펼친다.

    tasks.py 자신은 항상 포함한다 — 무엇을 실행할지가 여기 적혀 있으므로, 이 파일이
    바뀌면 모든 캐시가 무효가 되는 게 맞다.

    root는 단위 검사가 임시 폴더를 저장소 대신 줄 때만 쓴다(test_userpath.py). 기본은 ROOT.
    """
    root = ROOT if root is None else root
    found = set()
    for pattern in list(patterns) + ["tasks.py"]:
        for p in glob_inputs(root, pattern):
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
    if task.tool:
        h.update(task.tool().encode())
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

# 작업 함수가 이 값을 돌려주면 "실행할 수 없어서 건너뛰었다"는 뜻이다. execute()는 이 결과를
# 캐시하지 않는다. 캐시하면 도구를 설치한 뒤에도 검사가 캐시 히트로 계속 빠진다.
SKIPPED = object()
# 이번 실행에서 건너뛴 작업 이름. main()이 마지막에 알린다.
SKIPPED_TASKS = []


class Task:
    def __init__(self, name, doc, run=None, deps=(), inputs=(), outputs=(),
                 cacheable=True, uses_env=False, tool=None, needs_torch=False):
        self.name = name
        self.doc = doc
        self.run = run or (lambda: None)
        self.deps = tuple(deps)
        self.inputs = tuple(inputs)       # 이 파일들의 내용이 그대로면 건너뛴다
        self.outputs = tuple(outputs)     # 이 파일들이 없으면 캐시가 맞아도 다시 만든다
        self.cacheable = cacheable
        self.uses_env = uses_env          # .venv 상태를 캐시 키에 포함할지
        self.tool = tool                  # 외부 도구의 경로·버전 문자열을 돌려주는 함수. 캐시 키에 넣는다
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


# CAD 검증 echo(#61). hopper_params.scad 맨 아래 echo()가 조립 정합성을 계산하고, 문제가 있으면
# 문구에 "!!"를 넣는다. 예전에는 사람이 OpenSCAD 콘솔을 열어야만 이 경고를 봤다.
CAD_SCAD = ROOT / "cad" / "hopper_params.scad"
# 두 모드를 다 돌린다. echo는 모드와 관계없이 나오지만, 없는 모듈·변수 경고는 그 모드의 조립
# 분기를 실행해야 나온다.
CAD_MODES = ("preview", "print")
OPENSCAD_HOW = (
    "https://openscad.org/downloads.html\n"
    "           Windows: 설치 파일로 설치한다. 기본 폴더(C:\\Program Files\\OpenSCAD)에 두면 자동으로 찾는다.\n"
    "           Ubuntu:  sudo apt-get install openscad\n"
    "           다른 폴더에 두었으면 환경변수 OPENSCAD에 openscad 실행 파일 경로를 넣는다."
)


def find_openscad():
    """실제로 실행되는 OpenSCAD 경로를 돌려준다. 없으면 None.

    찾는 순서: 환경변수 OPENSCAD, PATH의 openscad, Windows 기본 설치 폴더.
    Windows에서 설치 폴더에 실행 파일만 남고 설치가 깨진 일이 있었다(cad/README.md, 2026-09-18).
    그래서 파일이 있는지만 보지 않고 `--version`이 성공하는지 본다.
    """
    cands = [os.environ.get("OPENSCAD"), shutil.which("openscad")]
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                cands.append(str(Path(base) / "OpenSCAD" / "openscad.exe"))
    for cand in cands:
        if cand and Path(cand).is_file() and openscad_version(cand) is not None:
            return cand
    return None


def openscad_version(exe):
    """`exe --version`의 출력을 돌려준다. 실패하면 None.

    OpenSCAD 2021.01은 Linux와 Windows 모두 버전을 stderr에 쓴다. 그래서 stdout과 stderr를 합친다.
    """
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (r.stdout + r.stderr).strip() if r.returncode == 0 else None


def openscad_fingerprint():
    """cad 작업의 캐시 키에 넣는 OpenSCAD 경로와 버전.

    이 값이 키에 없으면 한 번 통과한 뒤 OpenSCAD를 지우거나 바꿔도 cad가 캐시 히트로 통과한다.
    없으면 "no-openscad"다. 그러면 키가 달라져서 cad가 다시 돌고 [건너뜀]을 출력한다.
    """
    exe = find_openscad()
    return f"{exe}\n{openscad_version(exe)}" if exe else "no-openscad"


def scan_cad_output(text):
    """OpenSCAD 출력에서 (ECHO 줄, "!!" 경고가 있는 ECHO 줄, WARNING·ERROR 줄)을 돌려준다.

    OpenSCAD는 없는 변수·모듈을 WARNING으로만 알리고 exit 0으로 끝난다. 그런 echo는 값이
    undef라서 "!!" 판정이 틀릴 수 있다. 그래서 WARNING도 실패로 본다.
    """
    lines = [line.strip() for line in text.splitlines()]
    echoes = [line for line in lines if line.startswith("ECHO:")]
    alarms = [line for line in echoes if "!!" in line]
    problems = [line for line in lines if line.startswith(("WARNING:", "ERROR:"))]
    return echoes, alarms, problems


def check_cad_file(exe, scad, workdir):
    """scad를 CAD_MODES마다 OpenSCAD로 실행하고 실패 이유 목록을 돌려준다. 빈 목록이면 통과다.

    `-o <파일>.echo`는 echo() 출력과 경고를 텍스트 파일로 쓴다(OpenSCAD 매뉴얼, 명령행 사용).
    판정은 이 파일과 stderr를 같이 읽는다. Windows의 openscad.exe는 stderr를 비워 둘 수 있다.
    형상(CGAL) 계산은 하지 않는다. 그래서 파일 하나에 1초 안쪽으로 끝난다.
    """
    failures = []
    for mode in CAD_MODES:
        out = Path(workdir) / f"{mode}.echo"
        out.unlink(missing_ok=True)
        cmd = [exe, "-D", f'render_mode="{mode}"', "-o", str(out), str(scad)]
        print(f"\n$ {' '.join(cmd)}", flush=True)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=600)
        except subprocess.TimeoutExpired:
            failures.append(f"{mode}: OpenSCAD가 600초 안에 끝나지 않았다.")
            continue
        text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
        echoes, alarms, problems = scan_cad_output(text)
        # stderr에도 같은 줄이 나올 수 있다. 같은 줄을 두 번 세지 않는다.
        problems += [p for p in scan_cad_output(r.stderr)[2] if p not in problems]
        print(f"{mode}: echo {len(echoes)}줄, '!!' 경고 {len(alarms)}건, "
              f"WARNING·ERROR {len(problems)}건 (exit {r.returncode})", flush=True)
        for line in alarms + problems:
            # die()는 stderr로 쓴다. flush하지 않으면 CI 로그에서 이 줄이 [중단] 뒤에 찍힌다.
            print(f"  {line}", flush=True)
        if r.returncode != 0:
            tail = r.stderr.strip()[-1000:]
            failures.append(f"{mode}: OpenSCAD가 exit {r.returncode}로 끝났다." + (f"\n{tail}" if tail else ""))
        elif not out.exists():
            failures.append(f"{mode}: OpenSCAD가 exit 0이지만 {out.name}을 만들지 않았다.")
        elif not echoes:
            # 검사기가 아무것도 읽지 못하면 늘 통과한다. echo가 0줄이면 실패로 본다.
            failures.append(f"{mode}: echo가 0줄이다. 검증 echo()를 지웠거나 출력을 읽지 못했다.")
        if alarms:
            failures.append(f"{mode}: '!!' 경고 {len(alarms)}건")
        if problems:
            failures.append(f"{mode}: WARNING·ERROR {len(problems)}건")
    return failures


def task_cad():
    """hopper_params.scad의 검증 echo에 "!!" 경고나 OpenSCAD 경고가 없는지 본다(#61).

    OpenSCAD가 없는 PC에서는 이유와 설치 방법을 출력하고 건너뛴다. 건너뛴 결과는 캐시하지
    않는다. CI(환경변수 CI가 있음)에서는 건너뛰지 않고 실패한다. CI가 OpenSCAD 설치 단계를
    잃으면 이 검사가 조용히 빠지기 때문이다. ci.yml의 sim job이 OpenSCAD를 설치한다.

    검사기 자체의 단위 검사(test_cadcheck.py)를 먼저 돌린다.
    """
    run([sys.executable, "-m", "unittest", "-q", "test_cadcheck", "test_interference"], cwd=ROOT)
    exe = find_openscad()
    if not exe:
        if os.environ.get("CI"):
            die("CI에서 OpenSCAD를 찾지 못했다. ci.yml sim job의 OpenSCAD 설치 단계를 확인할 것.\n"
                f"     설치: {OPENSCAD_HOW}")
        print("[건너뜀] cad - OpenSCAD를 찾지 못했다. CI는 이 검사를 돌린다.\n"
              f"     설치: {OPENSCAD_HOW}")
        return SKIPPED
    if not CAD_SCAD.is_file():
        die(f"{CAD_SCAD.relative_to(ROOT)}이 없다. 파일을 옮겼다면 tasks.py의 CAD_SCAD를 고칠 것.")
    with tempfile.TemporaryDirectory() as tmp:
        failures = check_cad_file(exe, CAD_SCAD, tmp)
    if failures:
        die("CAD 검증 실패:\n     " + "\n     ".join(failures) +
            f"\n     {CAD_SCAD.relative_to(ROOT)}를 고친 뒤 다시 실행할 것.")
    print("CAD 검증 echo 통과 - '!!' 경고와 OpenSCAD 경고 없음")
    # 발주 STL 검사(#59, PR #60): 부품별 STL을 임시 폴더에 뽑고 열린 모서리·빈 STL·OpenSCAD 경고를 본다.
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable, str(ROOT / "cad" / "tools" / "export_print_parts.py"), "--out", tmp],
                           cwd=ROOT, env=dict(os.environ, OPENSCAD=exe, PYTHONIOENCODING="utf-8"),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        die("발주 STL 검사 실패(cad/tools/export_print_parts.py):\n" + (r.stdout + r.stderr)[-3000:])
    print(r.stdout.strip())
    print("발주 STL 검사 통과")


# 한국어 Windows에서 출력을 파일이나 파이프로 돌리면 파이썬은 cp949로 쓴다. 출력 문자열에
# em dash(U+2014)처럼 cp949에 없는 글자가 있으면 UnicodeEncodeError로 멈춘다(#137, #147, #170, #169).
# CI는 Linux(UTF-8)에서 돌아서 이 결함을 보지 못한다. cp949 작업이 이것을 막는다(#171).
# 범위는 부원 PC에서 돌 수 있는 저장소의 파이썬 파일이다. .agents/skills는 정본(.claude/skills)의
# 복사본이라 뺀다. skills 작업이 두 폴더가 같은지 본다.
CP949_SCAN = ["*.py", "sim/**/*.py", ".claude/skills/**/*.py", "kicad/_tools/*.py", "cad/**/*.py",
              "web/tools/*.py", "docs/learning/**/*.py", "docs/design/tools/*.py"]
# 인자를 그대로 출력하는 호출. die는 tasks.py와 ship.py의 die()다. raise 뒤의 식도 본다.
CP949_CALLS = {"print", "die", "sys.exit", "sys.stdout.write", "sys.stderr.write"}
STE_KO_LINT = Path(".claude/skills/ste-ko/scripts/ste-ko-lint.py")


def _call_name(func):
    """호출 대상을 `sys.stdout.write` 같은 점 이름으로 바꾼다. 이름으로 쓸 수 없으면 None."""
    parts = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if not isinstance(func, ast.Name):
        return None
    parts.append(func.id)
    return ".".join(reversed(parts))


def find_non_cp949(source, filename="<source>"):
    """출력하는 문자열 리터럴에서 cp949에 없는 글자를 찾는다. (줄, 칸, 글자, 자리) 목록을 돌려준다.

    자리는 `print`, `raise` 같은 출력 자리의 이름이다. 줄과 칸은 1부터 세고, 글자가 든 리터럴이
    시작하는 곳을 가리킨다. f-string의 고정된 부분도 본다. `file=` 인자는 출력할 글이 아니라서 뺀다.
    변수에 담았다가 출력하는 글은 보지 않는다. 문법이 틀린 소스는 SyntaxError를 낸다.
    """
    # ast의 col_offset은 줄 앞부터 센 UTF-8 바이트 수다. 칸은 글자 수로 바꿔서 쓴다.
    # 줄은 ast와 같이 \r\n, \r, \n에서 나눈다.
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    hits = set()
    for node in ast.walk(ast.parse(source, filename)):
        if isinstance(node, ast.Call) and _call_name(node.func) in CP949_CALLS:
            where = _call_name(node.func)
            roots = [*node.args, *(k.value for k in node.keywords if k.arg != "file")]
        elif isinstance(node, ast.Raise) and node.exc is not None:
            where, roots = "raise", [node.exc]
        else:
            continue
        for root in roots:
            for lit in ast.walk(root):
                if not (isinstance(lit, ast.Constant) and isinstance(lit.value, str)):
                    continue
                for ch in set(lit.value):
                    try:
                        ch.encode("cp949")
                    except UnicodeEncodeError:
                        line = lines[lit.lineno - 1].encode("utf-8")
                        col = len(line[:lit.col_offset].decode("utf-8")) + 1
                        hits.add((lit.lineno, col, ch, where))
    return sorted(hits)


def task_cp949():
    """출력 문자열에 cp949에 없는 글자가 없는지 본다(#171).

    userpath 작업과 같은 이유로 검사기의 단위 검사(test_cp949.py)를 먼저 돌린다.
    찾은 글자는 그대로 출력하지 않고 U+2014 같은 코드로 쓴다. 이 출력도 cp949로 쓸 수 있어야 한다.
    """
    run([sys.executable, "-m", "unittest", "-q", "test_cp949"], cwd=ROOT)
    files = [rel for rel, _ in collect_inputs(CP949_SCAN)]
    hits = []
    for rel in files:
        text = (ROOT / rel).read_text(encoding="utf-8-sig")
        try:
            found = find_non_cp949(text, rel)
        except SyntaxError as e:
            die(f"{rel}:{e.lineno}: 파이썬 {sys.version.split()[0]}이 이 파일을 읽지 못했다: {e.msg}")
        hits.extend((rel, *hit) for hit in found)
    for rel, lineno, col, ch, where in hits:
        name = unicodedata.name(ch, "")
        print(f"{rel}:{lineno}:{col}: {where} 문자열에 cp949에 없는 글자 U+{ord(ch):04X} {name}",
              flush=True)
    if hits:
        die(f"출력 문자열에서 cp949에 없는 글자 {len(hits)}건을 찾았다(#171).\n"
            "     한국어 Windows에서 출력을 파일이나 파이프로 돌리면 UnicodeEncodeError로 멈춘다.\n"
            "     em dash는 콜론이나 마침표로 바꾼다(AGENTS.md §교훈 2026-10-18).")
    print(f"cp949에 없는 출력 글자 없음 - {len(files)}개 파일 검사")
    # ste-ko-lint.py는 지적 메시지를 목록에 모았다가 출력해서 위 검사가 보지 못한다(#169).
    # 그 파일의 --self-test가 메시지를 cp949로 인코딩해 본다.
    run([sys.executable, STE_KO_LINT, "--self-test"], cwd=ROOT)


def task_kicadver():
    """생성 회로도의 KiCad 형식 번호가 생성기와 같고, KiCad가 저장한 형식인지 본다(#139, #140).

    .kicad_pro의 PCB 설정과 .kicad_pcb가 함께 커밋됐는지(#197), KiCad 10.0.6이 쓴 null이 없는지(#196)도 본다.

    실제 XML 넷리스트 fixture의 전체 핀 연결 회귀 검사도 함께 실행한다(#66).
    KiCad가 없어도 돈다. KiCad로 실제로 여는 확인은 kicad/README.md의 kicad-cli 명령으로 한다.
    """
    run([sys.executable, "-m", "unittest", "-q", "test_kicad_version", "test_netlist"], cwd=ROOT)


# 다른 문서가 글로 쓴 AGENTS.md 절 이름이 AGENTS.md 제목에 실제로 있는지 본다(#183).
# AGENTS.md를 가리킬 때는 번호 대신 절 이름을 쓴다(AGENTS.md §교훈, 2026-10-16). 그래서 참조가
# 마크다운 링크가 아닌 글이고, docs/learning/check_library.py의 링크 검사에 걸리지 않는다.
# 검사할 파일 형식. 지금 참조는 .md, .py, .yml에만 있다. 주석이나 문서 문자열에 참조를 쓸 수 있는
# 다른 글 형식도 넣는다. 이진 파일(.pdf, .png)은 넣지 않는다.
AGENTS_REF_SCAN = ["**/*.md", "**/*.py", "**/*.yml", "**/*.yaml", "**/*.toml", "**/*.js",
                   "**/*.html", "**/*.scad", "**/*.ino", "**/*.cpp", "**/*.h", "**/*.ps1",
                   "**/*.sh"]
# 검사기 단위 검사 파일은 없는 절 이름을 일부러 담는다. 그래서 검사 대상에서 뺀다.
AGENTS_REF_SKIP = {"test_agentsref.py"}
# 다른 문서의 참조 형식: AGENTS.md 또는 `AGENTS.md` 바로 뒤의 §. 저장소의 참조는 전부 이 형식이다.
AGENTS_REF_RE = re.compile(r"AGENTS\.md`?[ \t]*§")
# AGENTS.md 안의 참조 형식: 앞에 파일 이름 없이 쓴 §. "§0"이나 "§8.4"처럼 숫자로 시작하면
# 다른 문서의 번호 참조라서 보지 않는다.
AGENTS_SELF_REF_RE = re.compile(r"§(?=[^\s\d])")
# AGENTS.md 안에서 § 앞 낱말이 이 형식이면 다른 문서의 절이다. 예: "README §협업 규칙 6".
# 낱말 끝의 조사는 먼저 뗀다(AGENTS_PARTICLE_RE). 예: "README의 §협업 규칙 6".
AGENTS_FOREIGN_RE = re.compile(r"(?:README|\.md`?|문서|마스터|PRD)$")
# § 앞 낱말 끝에 붙는 조사. 하나만 뗀다.
AGENTS_PARTICLE_RE = re.compile(r"(?:의|에서|에|와|과|도|은|는)$")
# 절 이름 바로 뒤에 오면 참조가 그 절이 아니라고 보는 글자. _cites_section() 참고.
AGENTS_REF_TAIL_RE = re.compile(r"[A-Za-z0-9_]|\s+[^\W\d_]")


def agents_sections(text):
    """AGENTS.md 본문에서 참조로 쓸 수 있는 절 이름 집합을 돌려준다.

    `## ` 제목만 본다. 제목 앞 번호("2. ")와 끝의 괄호("(필수)",
    "(사람과 모든 AI 도구 공통, 2026-10-16)")는 뺀다.
    콜론이 있으면 콜론 앞부분도 이름으로 받는다. "작업 순서: 이슈에서 PR까지"는 "§작업 순서"로 쓴다.
    코드 블록 안의 줄은 제목이 아니다.
    """
    names = set()
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        m = re.match(r"## (?!#)(.+)", line)
        if fenced or not m:
            continue
        title = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", m.group(1).strip())
        title = re.sub(r"\s*\([^()]*\)$", "", title).strip()
        if not title:
            continue
        names.add(title)
        if ":" in title:
            names.add(title.split(":", 1)[0].strip())
    return names


def _cites_section(rest, names):
    """§ 바로 뒤 글자 rest가 names 중 하나로 시작하는지 본다.

    참조는 글 속에 있어서 절 이름이 어디서 끝나는지 글자만으로는 모른다. "§교훈에서는",
    "§작업 순서인지", "§핵심 규칙 8"이 그 예다. 한국어 조사와 어미는 종류가 많고 겹쳐 붙는다.
    그래서 절 이름으로 시작하고 그 바로 뒤가 아래 둘이 아니면 맞는 참조로 본다.
    - 영문자, 숫자, 밑줄이 바로 붙음("§교훈2").
    - 띄어쓰기 뒤에 글자(한글, 영문자)가 옴("§안전 원칙"을 절 "안전"으로 줄인 경우). 옛 이름의
      뒷부분인지 다음 낱말인지 구별할 수 없어서 틀렸다고 본다. 띄어쓰기 뒤 숫자("§핵심 규칙 8")와
      문장 부호는 받는다.
    한계: 절 이름 뒤에 한글이 바로 붙으면 조사인지 낱말의 일부인지 구별하지 않는다. 절 "교훈"이
    있으면 "§교훈들"도 통과한다.
    """
    for name in names:
        if rest.startswith(name) and not AGENTS_REF_TAIL_RE.match(rest[len(name):]):
            return True
    return False


def _cited_word(rest):
    """오류 메시지에 쓸 참조 글자. 절 이름에 공백이 있을 수 있어서 공백에서는 자르지 않는다.
    문장 부호 앞까지, 많아야 15글자까지 자른다."""
    return re.match(r"[^.,;:()`'\"\]]{0,15}", rest).group().rstrip()


def iter_agents_refs(text, self_refs=False):
    """text의 AGENTS.md 절 참조를 전부 낸다. (줄 번호, 칸 번호, § 뒤 글자)를 하나씩 낸다.

    줄과 칸은 1부터 세고, 칸은 § 위치다. 줄은 find_user_paths()와 같게 줄바꿈 문자로만 나눈다.
    self_refs가 참이면 text가 AGENTS.md 자신이다. 이때는 파일 이름 없이 쓴 "§이름"도 이 파일의
    절로 본다. 단 § 앞 낱말이 다른 문서 이름이면 보지 않는다. 낱말 끝의 조사는 떼고 본다.
    """
    for lineno, line in enumerate(text.split("\n"), start=1):
        starts = {m.end() for m in AGENTS_REF_RE.finditer(line)}
        if self_refs:
            for m in AGENTS_SELF_REF_RE.finditer(line):
                before = line[:m.start()].split()
                word = AGENTS_PARTICLE_RE.sub("", before[-1]) if before else ""
                if AGENTS_FOREIGN_RE.search(word) and not word.rstrip("`").endswith("AGENTS.md"):
                    continue
                starts.add(m.end())
        for start in sorted(starts):
            yield lineno, start, line[start:]


def find_agents_refs(text, names, self_refs=False):
    """text에서 names에 없는 AGENTS.md 절 참조를 찾는다.

    (줄 번호, 칸 번호, 참조 글자) 목록을 돌려준다. 줄, 칸, self_refs는 iter_agents_refs()와 같다.
    """
    return [(lineno, col, "§" + _cited_word(rest))
            for lineno, col, rest in iter_agents_refs(text, self_refs)
            if not _cites_section(rest, names)]


def scan_agents_refs(root, patterns):
    """root 아래 문서의 AGENTS.md 절 참조를 검사한다.

    (절 이름 집합, 검사한 참조 수, 찾은 목록)을 돌려준다.

    찾은 목록의 한 항목은 (저장소 기준 상대경로, 줄 번호, 칸 번호, 참조 글자)다.
    파일 목록은 scan_user_paths()와 같게 collect_inputs()로 만든다. tasks.py도 검사한다.
    tasks.py의 주석에도 참조를 쓸 수 있기 때문이다.
    """
    agents = root / "AGENTS.md"
    if not agents.is_file():
        die(f"{agents} 이(가) 없다. 절 참조를 대조할 수 없다.")
    names = agents_sections(agents.read_text(encoding="utf-8-sig"))
    if not names:
        die("AGENTS.md에서 `## ` 제목을 하나도 찾지 못했다.\n"
            "     제목 형식이 바뀌었으면 agents_sections()를 고칠 것.")
    files = [rel for rel, _ in collect_inputs(patterns, root) if rel not in AGENTS_REF_SKIP]
    count, hits = 0, []
    for rel in files:
        text = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        self_refs = rel == "AGENTS.md"
        count += sum(1 for _ in iter_agents_refs(text, self_refs))
        hits.extend((rel, *hit) for hit in find_agents_refs(text, names, self_refs))
    return names, count, hits


def task_agentsref():
    """다른 문서가 글로 쓴 AGENTS.md 절 이름이 AGENTS.md 제목에 있는지 본다(#183).

    userpath 작업과 같은 이유로 검사기의 단위 검사(test_agentsref.py)를 먼저 돌린다.
    """
    run([sys.executable, "-m", "unittest", "-q", "test_agentsref"], cwd=ROOT)
    names, count, hits = scan_agents_refs(ROOT, AGENTS_REF_SCAN)
    if not count:
        # 참조 형식 정규식이 고장 나면 참조를 0건 찾고 늘 통과한다. 그렇게 두지 않는다.
        die("AGENTS.md 절 참조를 하나도 찾지 못했다. 참조 형식을 바꿨다면 AGENTS_REF_RE를 고칠 것.")
    for rel, lineno, col, word in hits:
        # 파일:줄:칸: 형식이다. 편집기와 CI 로그 도구가 이 형식으로 해당 줄을 연다.
        print(f"{rel}:{lineno}:{col}: AGENTS.md에 없는 절 '{word}'", flush=True)
    if hits:
        die(f"AGENTS.md에 없는 절 이름 참조 {len(hits)}건을 찾았다(#183).\n"
            f"     지금 절 이름: {', '.join(sorted(names))}\n"
            "     절 이름은 AGENTS.md의 `## ` 제목에서 앞 번호와 끝 괄호를 뺀 것이다.\n"
            "     절을 지웠거나 이름을 바꿨으면 참조를 지금 이름으로 고칠 것.\n"
            "     절 이름 뒤에 띄어 쓴 낱말도 틀렸다고 본다(옛 이름의 일부일 수 있다).\n"
            "     맞는 참조라면 조사를 붙이거나(§안전 원칙을 확인) 괄호로 감쌀 것((§안전 원칙) 확인).")
    print(f"AGENTS.md 절 참조 {count}건 확인 - 없는 절 없음")


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
    Task("yaw", "요 축 검사 - 토크·회전자 항·스로틀 변화율·서보 손계산 + 요 PD 200 seed × 6조건(스로틀 고정·계단, 회전자 항 끔·켬) (#65, #86, #120, #161)",
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
    Task("cad", "CAD 검증 echo와 발주 STL(열린 모서리·경고) 확인, OpenSCAD 없으면 건너뜀 (#61, #59)",
         task_cad, inputs=["cad/hopper_params.scad", "cad/tools/*.py", "test_cadcheck.py", "test_interference.py"], tool=openscad_fingerprint),
    Task("cp949", "print·raise 등 출력 문자열에 cp949에 없는 글자가 없는지 확인 (#171)."
         f" 범위: {', '.join(CP949_SCAN)}", task_cp949,
         inputs=[*CP949_SCAN, "test_cp949.py",
                 ".claude/skills/ste-ko/references/upstream/dictionary.md"]),
    Task("vcruntime", "Windows VC++ 런타임 확인의 단위 검사 - 가짜 응답으로 (#108)", task_vcruntime,
         inputs=["test_vcruntime.py"]),
    Task("kicadver", "생성 회로도의 KiCad 형식 번호와 저장 형식, .kicad_pro의 저장 버전과 PCB 설정"
         " 확인 (#139, #140, #196, #197)", task_kicadver,
         inputs=["kicad/_tools/*.py", "kicad/cosmos-avionics/*.kicad_sch",
                 "kicad/cosmos-avionics/*.kicad_pro", "kicad/cosmos-avionics/*.kicad_pcb",
                 "test_kicad_version.py", "test_netlist.py", "kicad/reports/2026-10-19/netlist.xml"]),
    Task("agentsref", "다른 문서가 쓴 AGENTS.md 절 이름이 AGENTS.md 제목에 있는지 확인 (#183)",
         task_agentsref, inputs=AGENTS_REF_SCAN),
    Task("check", "CI sim job의 check 단계와 같은 검사 (학습 자료 검사·펌웨어 빌드는 빠짐,"
         " 단계 목록은 graph)", task_check,
         deps=["skills", "shiptest", "userpath", "kicadver", "cp949", "agentsref", "cad",
               "vcruntime", "compile", "sanity", "gate", "yaw", "smoke", "conncheck"]),
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
    if task.run() is SKIPPED:
        SKIPPED_TASKS.append(name)
        done.add(name)
        return
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
    # check가 캐시 히트면 task_check는 돌지 않는다. 그래서 건너뛴 작업은 여기서 알린다.
    if SKIPPED_TASKS:
        print(f"\n건너뛴 작업: {', '.join(SKIPPED_TASKS)}. 이유는 위 [건너뜀] 줄을 본다. CI는 이 작업도 돌린다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
