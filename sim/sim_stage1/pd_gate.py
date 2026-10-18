"""
RL 학습 전 합격 기준(#27): 도메인 랜덤화를 켠 상태에서 PD 기준 제어기가 안정화하는가.

실행: python pd_gate.py                       PD만 평가, 기준 미달이면 exit 1
      python pd_gate.py --model hopper_attitude_ppo.zip   같은 평가 seed로 PPO도 평가

합격: 평가 seed 0~199에서 PD(kp=8, kd=2)의 넘어짐 ≤ 5%, 최종 기울기 중앙값 ≤ 5°.
베인 측력 상한(축당 ≤ Ft·sin(alpha_max))은 HopperAttitudeEnv 생성 시 vane_lift_gain()이 검사한다.

평가 seed(0~199)는 학습 seed(train.py의 TRAIN_SEED)와 겹치지 않게 둔다 — 학습 때 본 초기 조건으로
평가하면 일반화가 아니라 암기를 재는 것이 된다(SB3 RL Tips and Tricks, 자료실 R05).
PD 게인과 정책 정의는 #21 재현 스크립트와 같다.
"""
import argparse
import sys

import numpy as np

from hopper_aviary import N_STATE, HopperAttitudeEnv

EVAL_SEEDS = range(200)
MAX_CRASH = 0.05
MAX_MEDIAN_TILT_DEG = 5.0


def pd(obs, kp=8.0, kd=2.0):
    phi, theta, psi, wx, wy, wz = obs[:N_STATE]   # obs[6]은 제한 뒤 스로틀(#186). PD는 쓰지 않는다
    ux = np.clip(-kp * phi - kd * wx, -1, 1)   # tau_x = (F1+F3)*l
    uy = np.clip(kp * theta + kd * wy, -1, 1)  # tau_y = -(F2+F4)*l
    return np.array([ux, uy, ux, uy, 1.0], dtype=np.float32)


def model_policy(model):
    """SB3 모델을 관측 → 행동 함수로 바꾼다.

    #186 전 모델(관측 6차원, 저장소의 hopper_attitude_ppo.zip)은 앞 N_STATE개만 받는다. 동역학은 #186 전과 같아서
    이 모델의 평가 결과도 #186 전과 같다. 관측 차원이 6도 환경 관측 차원도 아니면 멈춘다.
    """
    n_model = int(model.observation_space.shape[0])
    n_env = int(HopperAttitudeEnv().observation_space.shape[0])
    if n_model not in (N_STATE, n_env):
        raise ValueError(f"모델 관측 {n_model}차원: 환경 관측 {n_env}차원이나 #186 전 {N_STATE}차원이어야 한다.")
    return lambda o: model.predict(o[:n_model], deterministic=True)[0]


def evaluate(policy, seeds=EVAL_SEEDS):
    env = HopperAttitudeEnv()
    if not env.dr.get("enabled", False):
        # 랜덤화를 끄면 명목값 한 점만 재게 되어 기준의 의미가 없어진다.
        raise ValueError("params.yaml의 domain_rand.enabled가 false다. 합격 기준은 랜덤화를 켠 상태에서만 잰다.")
    returns, lengths, crashes, tilts = [], [], [], []
    for s in seeds:
        obs, _ = env.reset(seed=s)
        ret, t, done = 0.0, 0, False
        while not done:
            obs, r, term, trunc, _ = env.step(policy(obs))
            ret += r
            t += 1
            done = term or trunc
        returns.append(ret)
        lengths.append(t)
        crashes.append(term)
        tilts.append(np.degrees(np.hypot(obs[0], obs[1])))
    return {
        "return": float(np.mean(returns)),
        "length": float(np.mean(lengths)),
        "crash": float(np.mean(crashes)),
        "median_tilt_deg": float(np.median(tilts)),
    }


def row(name, m):
    return (f"| {name} | {m['return']:.2f} | {m['length']:.1f} | {m['crash'] * 100:.1f} % "
            f"| {m['median_tilt_deg']:.1f}° |")


def gate_passes(m):
    return m["crash"] <= MAX_CRASH and m["median_tilt_deg"] <= MAX_MEDIAN_TILT_DEG


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="같은 평가 seed로 비교할 SB3 PPO 모델(.zip)")
    args = ap.parse_args()

    results = {"PD (kp=8, kd=2)": evaluate(pd)}
    if args.model:
        from stable_baselines3 import PPO
        model = PPO.load(args.model, device="cpu")
        results[f"PPO ({args.model})"] = evaluate(model_policy(model))

    print(f"평가 seed {EVAL_SEEDS.start}~{EVAL_SEEDS.stop - 1}, 도메인 랜덤화 켬\n")
    print("| 정책 | 평균 리턴 | 평균 길이(step) | 넘어짐 | 최종 기울기 중앙값 |")
    print("|---|---|---|---|---|")
    for name, m in results.items():
        print(row(name, m))

    m = results["PD (kp=8, kd=2)"]
    ok = gate_passes(m)
    print(f"\nPD 판정: {'합격' if ok else '불합격'} "
          f"(기준: 넘어짐 ≤ {MAX_CRASH * 100:.0f} %, 중앙값 ≤ {MAX_MEDIAN_TILT_DEG:.0f}°)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
