"""PD baseline — 학습 없이 사람이 게인을 정하는 비교군.

AGENTS.md의 "PID vs RL 비교 실험 프로토콜"에서 baseline 자리다. 여기 있는 이유는 하나:
**RL 쪽만 여럿 두고 baseline을 대충 두면 비교가 성립하지 않기 때문이다.** 그래서 게인을
작은 격자에서 실제로 탐색해 가장 좋은 걸 쓴다 — baseline을 일부러 약하게 두고 "RL이 이겼다"고
하는 게 이 프로젝트에서 제일 하면 안 되는 일이다.

적분항(I)이 없어서 PID가 아니라 PD인 이유: Stage 1은 위치가 구속돼 있고 중력 토크가 없다.
잔류 편향은 도메인 랜덤화의 무게중심 오프셋(cg_offset)에서만 오는데, 이건 에피소드마다
새로 뽑히는 값이라 적분항이 따라잡기 전에 에피소드가 끝난다. 실기에서는 상황이 달라지므로
그때 다시 볼 것.

베인 배분 (hopper_aviary.py 의 토크 식을 그대로 뒤집은 것)
---------------------------------------------------------
환경은 이렇게 토크를 만든다:
    tau_x = (F1 + F3) * l
    tau_y = -(F2 + F4) * l
    tau_z = (F1 - F2 - F3 + F4) * r          (F_i = CLalpha * Ft * alpha_i)

그래서 롤/피치/요를 따로 잡으려면 베인각을 이렇게 섞어야 한다:
    a1 = u_roll + u_yaw      a3 = u_roll - u_yaw
    a2 = -u_pitch - u_yaw    a4 = -u_pitch + u_yaw

이러면 롤 식에서는 u_yaw 가 (+u_yaw) + (-u_yaw) 로 지워지고, 요 식에서는 u_roll/u_pitch 가
지워진다. 즉 세 축이 서로 간섭하지 않는다. 롤/피치만 같은 부호로 묶는 단순 배분을 쓰면
요 토크가 항상 0이 되어 psi를 아예 제어할 수 없다 — 처음에 그렇게 짰다가 발견했다.
"""
from __future__ import annotations

import numpy as np


class PDController:
    """관측 -> 액션. RL 정책과 같은 인터페이스(predict)를 갖춰 평가 코드를 공유한다."""

    def __init__(self, kp: float = 3.0, kd: float = 0.4, kp_yaw: float = 1.0,
                 kd_yaw: float = 0.2, throttle: float = 0.6):
        self.kp, self.kd = kp, kd
        self.kp_yaw, self.kd_yaw = kp_yaw, kd_yaw
        # 액션 공간이 -1~1 대칭이고 환경이 (throttle_norm + 1) / 2 로 되돌리므로 역변환.
        self.throttle_norm = float(np.clip(throttle, 0.0, 1.0) * 2.0 - 1.0)

    def predict(self, obs, deterministic: bool = True):
        phi, theta, psi, wx, wy, wz = np.asarray(obs, dtype=np.float64)
        u_roll = -(self.kp * phi + self.kd * wx)
        u_pitch = -(self.kp * theta + self.kd * wy)
        u_yaw = -(self.kp_yaw * psi + self.kd_yaw * wz)

        action = np.array([
            u_roll + u_yaw,
            -u_pitch - u_yaw,
            u_roll - u_yaw,
            -u_pitch + u_yaw,
            self.throttle_norm,
        ], dtype=np.float32)
        return np.clip(action, -1.0, 1.0), None


# 게인 격자. 넓게 훑기보다 "합리적인 범위를 성실히" — 어차피 물리 상수가 PLACEHOLDER라
# 지금 찾은 최적 게인의 절대값은 의미가 없고, 실측 후 다시 돌려야 한다.
GAIN_GRID = [
    {"kp": kp, "kd": kd, "throttle": th}
    for kp in (1.0, 3.0, 6.0, 10.0)
    for kd in (0.1, 0.4, 0.8)
    for th in (0.4, 0.7, 1.0)
]


def tune(env_factory, evaluate_fn, episodes: int = 20, verbose: bool = True):
    """격자를 다 돌려 평균 보상이 가장 높은 게인을 고른다.

    evaluate_fn(policy, env, episodes) -> dict  형태를 받는다(evaluate.py의 run_episodes).
    """
    best, best_metrics = None, None
    for gains in GAIN_GRID:
        pd = PDController(**gains)
        m = evaluate_fn(pd, env_factory(), episodes=episodes)
        if best_metrics is None or m["mean_reward"] > best_metrics["mean_reward"]:
            best, best_metrics = gains, m
    if verbose:
        print(f"[PD 튜닝] {len(GAIN_GRID)}개 조합 중 최적: {best} "
              f"-> 평균보상 {best_metrics['mean_reward']:.1f}")
    return PDController(**best), best, best_metrics
