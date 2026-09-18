"""비교군들을 같은 자로 재는 평가 코드.

AGENTS.md가 정한 지표 그대로다: **복원시간 · 오버슈트 · 정상상태오차**. 여기에 RL 비교에서만
의미가 있는 것 두 개(추락률, 평균보상)를 더했다.

가장 중요한 설계: **모든 비교군이 완전히 같은 초기조건을 본다.** 에피소드 k는 어느 정책을
평가하든 env.reset(seed=eval_seed_base + k) 로 시작한다. 도메인 랜덤화(관성·모멘트암·Kf·
무게중심 오프셋)도 그 시드에서 나오므로, 정책 A가 유독 쉬운 기체를 뽑아서 이기는 일이
생기지 않는다. 이걸 안 맞추면 시드 운으로 순위가 뒤집힌다 — RL 비교에서 제일 흔한 사고다.
"""
from __future__ import annotations

import numpy as np

# 복원 판정 각도. 이보다 작아진 뒤 끝까지 유지되면 "복원됐다"고 본다.
SETTLE_DEG = 2.0
EVAL_SEED_BASE = 10_000


def _tilt(state) -> float:
    """수평에서 얼마나 기울었나 — 롤/피치를 합친 한 개 숫자 (요는 따로 본다)."""
    return float(np.hypot(state[0], state[1]))


def run_episodes(policy, env, episodes: int = 30, seed_base: int = EVAL_SEED_BASE) -> dict:
    settle_times, overshoots, steady_errors, rewards = [], [], [], []
    crashes = 0
    censored = 0

    for k in range(episodes):
        obs, _ = env.reset(seed=seed_base + k)
        tilt0 = _tilt(obs)
        trace = [tilt0]
        total = 0.0

        while True:
            action, _ = policy.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            total += reward
            trace.append(_tilt(obs))
            if terminated or truncated:
                break

        trace = np.asarray(trace)
        rewards.append(total)
        if terminated:
            crashes += 1

        # 오버슈트: 시작보다 얼마나 더 나빠졌나. 0이면 한 번도 초기 기울기를 안 넘었다는 뜻.
        overshoots.append(float(max(0.0, trace[1:].max() - tilt0) / max(tilt0, 1e-9)))

        # 정상상태오차: 마지막 20% 구간의 평균 기울기 (deg)
        tail = trace[max(1, int(len(trace) * 0.8)):]
        steady_errors.append(float(np.rad2deg(tail.mean())))

        # 복원시간: 임계값 아래로 내려가서 '끝까지' 유지된 첫 시점
        thresh = np.deg2rad(SETTLE_DEG)
        above = np.flatnonzero(trace > thresh)
        if above.size == 0:
            settle_times.append(0.0)
        elif above[-1] >= len(trace) - 1:
            # 끝까지 못 내려왔다. 에피소드 길이로 기록하되 몇 번인지 따로 센다 —
            # 이걸 그냥 평균에 섞으면 "복원 못 한 정책"이 "느린 정책"으로 보인다.
            settle_times.append(float(len(trace) - 1) * env.dt)
            censored += 1
        else:
            settle_times.append(float(above[-1] + 1) * env.dt)

    return {
        "episodes": episodes,
        "mean_reward": float(np.mean(rewards)),
        "settle_s": float(np.mean(settle_times)),
        "settle_censored": censored,
        "overshoot": float(np.mean(overshoots)),
        "steady_err_deg": float(np.mean(steady_errors)),
        "crash_rate": crashes / episodes,
    }


def format_table(results: dict) -> str:
    """{이름: 지표dict} 를 사람이 읽는 표로."""
    head = (f"{'비교군':<22}{'평균보상':>10}{'복원(s)':>10}{'미복원':>8}"
            f"{'오버슈트':>10}{'정상오차(deg)':>14}{'추락률':>8}")
    lines = [head, "-" * len(head)]
    for name, m in results.items():
        lines.append(
            f"{name:<22}{m['mean_reward']:>10.1f}{m['settle_s']:>10.2f}"
            f"{m['settle_censored']:>8}{m['overshoot']:>10.2f}"
            f"{m['steady_err_deg']:>14.2f}{m['crash_rate']:>8.0%}"
        )
    lines.append("")
    lines.append(f"* 복원 판정 기준 {SETTLE_DEG}도 · '미복원' 은 끝까지 그 아래로 못 내려온 에피소드 수")
    lines.append("* 오버슈트 = (최대 기울기 - 초기 기울기) / 초기 기울기, 0이면 초기값을 안 넘음")
    return "\n".join(lines)
