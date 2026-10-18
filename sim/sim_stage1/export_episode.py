"""
Stage 1 에피소드를 웹 대시보드 CSV 형식(docs/design/02-web-dashboard-design.md §4)으로 저장한다.

실물 시험 로그(펌웨어)와 같은 컬럼을 쓰므로, 웹 3D 뷰어 하나로 시뮬레이션과 실기를 똑같이 재생할 수 있다.

컬럼: t_ms, source, mode, phi, theta, psi, qw, qx, qy, qz, wx, wy, wz,
      servo1, servo2, servo3, servo4, throttle, batt_v, rpm, reward
- source = SIM (실측 데이터와 섞이지 않게 구분)
- mode   = PID(PD 기준 제어기) | RL(PPO 모델) | MANUAL(무입력)
- servo1..4 = 액션 a1..a4 그대로(-1~1), 순서 FWD/LEFT/AFT/RIGHT (01-avionics §1)
- throttle  = 0-1, 변화율 제한(#120) 뒤 환경이 실제로 쓴 값(step()의 info["throttle"])
- qw..qz    = ZYX 오일러각에서 계산한 쿼터니언 (§5-3, 뷰어의 짐벌락 회피용)
- batt_v, rpm 은 시뮬레이션에 없어서 비워 둔다
- reward    = 그 행의 상태에서 액션을 낸 뒤 받은 보상. 마지막 행(최종 상태)은 비어 있다

각 CSV 옆에 같은 이름의 .meta.json을 남긴다(시드, 랜덤화 설정, 이번 에피소드에 뽑힌 물리 상수,
종료 사유, git 커밋). 같은 시드와 커밋이면 같은 궤적이 다시 나온다.

실행 예:
  python export_episode.py --policy pd --no-dr --seed 0
  python export_episode.py --policy pd --episodes 5
  python export_episode.py --policy ppo --model hopper_attitude_ppo.zip   (stable-baselines3 필요)
"""
import argparse
import csv
import json
import os
import subprocess
from datetime import date

import numpy as np

from hopper_aviary import HopperAttitudeEnv

COLUMNS = [
    "t_ms", "source", "mode",
    "phi", "theta", "psi",
    "qw", "qx", "qy", "qz",
    "wx", "wy", "wz",
    "servo1", "servo2", "servo3", "servo4",
    "throttle", "batt_v", "rpm", "reward",
]

MODE_BY_POLICY = {"pd": "PID", "zero": "MANUAL", "ppo": "RL"}


def euler_zyx_to_quat(phi, theta, psi):
    cr, sr = np.cos(phi / 2), np.sin(phi / 2)
    cp, sp = np.cos(theta / 2), np.sin(theta / 2)
    cy, sy = np.cos(psi / 2), np.sin(psi / 2)
    return (
        cr * cp * cy + sr * sp * sy,
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
    )


def pd_policy(obs, kp=8.0, kd=2.0):
    """롤/피치 PD 기준 제어기. 부호는 tau_x=(F1+F3)l, tau_y=-(F2+F4)l 에 맞춘 것(이슈 #21과 동일)."""
    phi, theta, _psi, wx, wy, _wz = obs
    ux = float(np.clip(-kp * phi - kd * wx, -1, 1))
    uy = float(np.clip(kp * theta + kd * wy, -1, 1))
    return np.array([ux, uy, ux, uy, 1.0], dtype=np.float32)


def zero_policy(_obs):
    return np.array([0, 0, 0, 0, 1.0], dtype=np.float32)


def make_policy(name, model_path):
    if name == "pd":
        return pd_policy
    if name == "zero":
        return zero_policy
    try:
        from stable_baselines3 import PPO
    except ImportError as e:
        raise SystemExit("--policy ppo 는 stable-baselines3가 필요합니다 (sim/README.md 환경 세팅).") from e
    model = PPO.load(model_path)
    return lambda obs: model.predict(obs, deterministic=True)[0]


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def state_row(t_ms, mode, obs):
    phi, theta, psi, wx, wy, wz = (float(v) for v in obs)
    qw, qx, qy, qz = euler_zyx_to_quat(phi, theta, psi)
    return {
        "t_ms": t_ms, "source": "SIM", "mode": mode,
        "phi": phi, "theta": theta, "psi": psi,
        "qw": qw, "qx": qx, "qy": qy, "qz": qz,
        "wx": wx, "wy": wy, "wz": wz,
        "servo1": "", "servo2": "", "servo3": "", "servo4": "",
        "throttle": "", "batt_v": "", "rpm": "", "reward": "",
    }


def run_episode(env, policy, mode, seed):
    obs, _ = env.reset(seed=seed)
    rows = []
    step = 0
    terminated = truncated = False
    total = 0.0
    while not (terminated or truncated):
        action = np.clip(np.asarray(policy(obs), dtype=np.float32), -1, 1)
        row = state_row(round(step * env.dt * 1000), mode, obs)
        row.update({f"servo{i + 1}": float(action[i]) for i in range(4)})
        obs, reward, terminated, truncated, info = env.step(action)
        row["throttle"] = float(info["throttle"])   # 정책 명령이 아니라 변화율 제한 뒤 값(#120)
        row["reward"] = float(reward)
        total += reward
        rows.append(row)
        step += 1
    rows.append(state_row(round(step * env.dt * 1000), mode, obs))
    info = {
        "steps": step,
        "return": total,
        "end": "crashed" if terminated else "time_limit",
        "final_tilt_deg": float(np.degrees(np.hypot(obs[0], obs[1]))),
    }
    return rows, info


def episode_params(env):
    return {
        "Jxx": env.Jxx, "Jyy": env.Jyy, "Jzz": env.Jzz,
        "vane_arm_l": env.l, "vane_arm_r": env.r,
        "Kf": env.Kf,
        "cg_offset_x_m": env.cg_offset_x, "cg_offset_y_m": env.cg_offset_y,
        # 회전자 상수도 에피소드마다 뽑는다(#121). rotor.enabled가 꺼져 있으면 환경이 쓰지 않는다
        "rotor_inertia": env.rotor_inertia, "rotor_omega_max": env.rotor_omega_max, "rotor_tau": env.rotor_tau,
    }


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--policy", choices=sorted(MODE_BY_POLICY), default="pd")
    ap.add_argument("--model", default=os.path.join(here, "hopper_attitude_ppo.zip"))
    ap.add_argument("--seed", type=int, default=0, help="첫 에피소드 시드 (이후 +1씩)")
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--no-dr", action="store_true", help="도메인 랜덤화를 끄고 명목값으로 실행")
    ap.add_argument("--out", default=os.path.join(here, "episode_logs"))
    args = ap.parse_args()

    env = HopperAttitudeEnv()
    if args.no_dr:
        env.dr = {"enabled": False}
    policy = make_policy(args.policy, args.model)
    mode = MODE_BY_POLICY[args.policy]
    os.makedirs(args.out, exist_ok=True)
    commit = git_commit()
    tag = "nodr" if args.no_dr else "dr"

    for k in range(args.episodes):
        seed = args.seed + k
        rows, info = run_episode(env, policy, mode, seed)
        stem = f"{date.today():%Y%m%d}-SIM-{args.policy}-{tag}-s{seed}"
        csv_path = os.path.join(args.out, stem + ".csv")
        write_csv(csv_path, rows)
        meta = {
            "schema": "docs/design/02-web-dashboard-design.md §4",
            "policy": args.policy, "mode": mode,
            "model": args.model if args.policy == "ppo" else None,
            "seed": seed, "dt_s": env.dt, "max_steps": env.max_steps,
            "domain_rand": env.dr,
            # 회전자 항 스위치와 명목 상수(#86). 켜고 끈 에피소드를 meta만 보고 구별하려고 남긴다.
            # 이번 에피소드에 뽑힌 값은 episode_params의 rotor_*에 있다(#121)
            "rotor": {"enabled": env.rotor_enabled, "inertia": env.nominal_rotor_inertia,
                      "omega_max": env.nominal_rotor_omega_max, "tau": env.nominal_rotor_tau,
                      "spin_dir": env.rotor_spin_dir},
            # 스로틀 변화율 제한(1/s, null이면 없음, #120). CSV throttle 열은 이 제한 뒤 값이다
            "throttle_slew_rate": env.throttle_slew_rate,
            "episode_params": episode_params(env),
            "result": info,
            "git_commit": commit,
        }
        with open(os.path.join(args.out, stem + ".meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"{csv_path}: {info['steps']} steps, return {info['return']:.2f}, "
              f"{info['end']}, final tilt {info['final_tilt_deg']:.1f} deg")


if __name__ == "__main__":
    main()
