#!/usr/bin/env python3
"""COSMOS 작업 실행기 — 자주 쓰는 명령을 한 곳에 모아둔 것.

    python tasks.py              사용 가능한 작업 목록
    python tasks.py setup        sim 가상환경 만들고 고정 버전 의존성 설치
    python tasks.py sanity       환경이 살아 있는지 20스텝 확인
    python tasks.py smoke        SB3-환경 연결 확인 (256스텝, 학습 아님)
    python tasks.py check        문법 + sanity + smoke  ← CI가 도는 것과 같음
    python tasks.py train        PPO 본 학습 (200k 스텝, 오래 걸림)
    python tasks.py deck         설명회 pptx 다시 생성 (node 필요)

왜 Makefile이 아니라 이 파일인가: 팀 개발 환경이 Windows 위주인데 Windows엔 `make`가 기본으로
없다. 반면 파이썬은 소프트웨어팀이 어차피 설치해야 한다. 표준 라이브러리만 쓰므로 추가 설치도 없고,
Mac/Linux에서도 같은 명령이 그대로 동작한다.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIM = ROOT / "sim"
STAGE1 = SIM / "sim_stage1"
VENV = SIM / "venv"
IS_WIN = os.name == "nt"

# CI(.github/workflows/ci.yml)의 PPO 스모크와 같은 내용. 한쪽만 고치지 말 것.
SMOKE = """
from hopper_aviary import HopperAttitudeEnv
from stable_baselines3 import PPO

env = HopperAttitudeEnv()
PPO("MlpPolicy", env, n_steps=64, batch_size=64, verbose=0).learn(total_timesteps=256)
print("PPO 스모크 통과 - 환경과 SB3 연결 정상")
"""


def venv_python(required=True):
    """sim/venv의 파이썬 경로. 없으면 setup을 안내하고 종료."""
    exe = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
    if exe.exists():
        return str(exe)
    if required:
        die("가상환경이 없다. 먼저 실행:  python tasks.py setup")
    return sys.executable


def die(msg):
    print(f"\n[중단] {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, cwd=None):
    where = f" (cwd: {Path(cwd).relative_to(ROOT)})" if cwd else ""
    print(f"\n$ {' '.join(str(c) for c in cmd)}{where}", flush=True)
    result = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if result.returncode != 0:
        die(f"위 명령이 실패했다 (exit {result.returncode}).")


def task_setup():
    """sim 가상환경 생성 + 고정 버전 의존성 설치."""
    if VENV.exists():
        print(f"기존 가상환경 발견: {VENV} — 의존성만 다시 맞춘다.")
    else:
        run([sys.executable, "-m", "venv", str(VENV)])
    py = venv_python()
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    run([py, "-m", "pip", "install", "-r", str(SIM / "requirements.txt")])
    activate = r"sim\venv\Scripts\activate" if IS_WIN else "source sim/venv/bin/activate"
    print(
        "\n설치 완료. 확인하려면:  python tasks.py sanity"
        f"\n직접 python을 쓰고 싶으면 먼저 활성화:  {activate}"
    )


def task_sanity():
    """환경이 깨지지 않았는지 20스텝 무작위 액션으로 확인."""
    run([venv_python(), "sanity_check.py"], cwd=STAGE1)


def task_smoke():
    """SB3와 환경의 연결 확인. 학습이 아니라 배선 점검이다."""
    run([venv_python(), "-c", SMOKE], cwd=STAGE1)


def task_check():
    """CI와 같은 검사를 로컬에서. PR 올리기 전에 이걸 돌려볼 것."""
    run([sys.executable, "-m", "compileall", "-q", "sim", "test_cartpole.py", "test_pendulum.py"], cwd=ROOT)
    task_sanity()
    task_smoke()
    print("\n전부 통과. PR 올려도 된다.")


def task_train():
    """PPO 본 학습 — 200k 스텝, 수십 분 걸린다."""
    print("200k 스텝 학습을 시작한다. 중간에 끊으려면 Ctrl+C.")
    run([venv_python(), "train.py"], cwd=STAGE1)


def task_deck():
    """설명회 pptx 재생성 (docs/presentation/build_deck.js)."""
    deck_dir = ROOT / "docs" / "presentation"
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not (npm and node):
        die("node/npm이 없다. https://nodejs.org 에서 설치 후 다시 시도.")
    if not (deck_dir / "node_modules" / "pptxgenjs").exists():
        run([npm, "install", "pptxgenjs"], cwd=deck_dir)
    run([node, "build_deck.js"], cwd=deck_dir)


TASKS = {
    "setup": task_setup,
    "sanity": task_sanity,
    "smoke": task_smoke,
    "check": task_check,
    "train": task_train,
    "deck": task_deck,
}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("사용법: python tasks.py <작업>\n")
        for name, fn in TASKS.items():
            print(f"  {name:<8} {(fn.__doc__ or '').splitlines()[0]}")
        print("\nPR 올리기 전엔 `python tasks.py check`.")
        return 0
    name = args[0]
    if name not in TASKS:
        die(f"그런 작업은 없다: {name}\n     가능한 작업: {', '.join(TASKS)}")
    TASKS[name]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
