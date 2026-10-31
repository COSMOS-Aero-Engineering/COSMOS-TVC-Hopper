"""비교군들을 같은 자로 재는 평가 코드.

AGENTS.md가 정한 지표 그대로다: **복원시간 · 오버슈트 · 정상상태오차**. 여기에 RL 비교에서만
의미가 있는 것 두 개(추락률, 평균보상)를 더했다.

가장 중요한 설계: **모든 비교군이 완전히 같은 초기조건을 본다.** 에피소드 k는 어느 정책을
평가하든 env.reset(seed=eval_seed_base + k) 로 시작한다. 도메인 랜덤화(관성·모멘트암·Kf·
무게중심 오프셋)도 그 시드에서 나오므로, 정책 A가 유독 쉬운 기체를 뽑아서 이기는 일이
생기지 않는다. 이걸 안 맞추면 시드 운으로 순위가 뒤집힌다 — RL 비교에서 제일 흔한 사고다.

기울기는 롤·피치를 합친 크기 hypot(phi, theta)다(요는 따로 본다). 지표 정의와 교재 정의의 차이는
episode_metrics()의 설명과 sim/sim_stage1/compare_metrics.py에 있다(#266).
"""
from __future__ import annotations

import numpy as np

# 복원 판정 각도. 이보다 작아진 뒤 끝까지 유지되면 "복원됐다"고 본다.
SETTLE_DEG = 2.0
EVAL_SEED_BASE = 10_000


def episode_metrics(xy, dt: float) -> dict:
    """에피소드 하나의 롤·피치 기록 xy(rad, 모양 (스텝 수 + 1, 2), 0행은 reset 직후)로 지표를 계산한다.

    run_episodes()가 에피소드마다 부른다. 실제 에피소드 없이 손으로 만든 기록으로 검사할 수 있게
    따로 둔다(check.py 6번).

    돌려주는 값:
      overshoot        (최대 기울기 - 초기 기울기) / 초기 기울기. 기울기는 크기(hypot)라서 0을 지나
                       반대쪽으로 넘어간 것은 보지 못한다. 이 값은 "처음보다 더 기울어진 정도"다.
      overshoot_cross  초기 기울기 방향 u0 = xy[0]/|xy[0]|에 기록을 투영한 e(t) = xy(t)·u0에서
                       max(0, -min e(t)) / |xy[0]|. 0을 지나 반대쪽으로 넘어간 최대 크기를 초기 오프셋으로
                       나눈 값이다. 교재의 최대 오버슈트(목표값을 넘어간 최대 크기 / 응답의 변화 크기)를
                       초기 오프셋에서 0으로 돌아오는 응답에 맞춘 것이다(#266).
      steady_err_deg   마지막 20 % 구간의 평균 기울기(deg).
      settle_s         SETTLE_DEG 아래로 내려가서 끝까지 유지된 첫 시점(s). 끝까지 못 내려오면 기록 길이.
      censored         끝까지 SETTLE_DEG 아래로 못 내려왔으면 True.
    """
    xy = np.asarray(xy, dtype=float)
    trace = np.hypot(xy[:, 0], xy[:, 1])
    tilt0 = trace[0]

    # 오버슈트: 시작보다 얼마나 더 나빠졌나. 0이면 한 번도 초기 기울기를 안 넘었다는 뜻.
    overshoot = float(max(0.0, trace[1:].max() - tilt0) / max(tilt0, 1e-9))

    # 0을 지나 반대쪽으로 넘어간 크기. 초기 기울기가 0이면 방향이 없으므로 0으로 둔다.
    if tilt0 > 1e-9:
        e = xy[1:] @ (xy[0] / tilt0)
        overshoot_cross = float(max(0.0, -e.min()) / tilt0)
    else:
        overshoot_cross = 0.0

    # 정상상태오차: 마지막 20% 구간의 평균 기울기 (deg)
    tail = trace[max(1, int(len(trace) * 0.8)):]
    steady_err_deg = float(np.rad2deg(tail.mean()))

    # 복원시간: 임계값 아래로 내려가서 '끝까지' 유지된 첫 시점
    thresh = np.deg2rad(SETTLE_DEG)
    above = np.flatnonzero(trace > thresh)
    censored = False
    if above.size == 0:
        settle_s = 0.0
    elif above[-1] >= len(trace) - 1:
        # 끝까지 못 내려왔다. 에피소드 길이로 기록하되 몇 번인지 따로 센다 —
        # 이걸 그냥 평균에 섞으면 "복원 못 한 정책"이 "느린 정책"으로 보인다.
        settle_s = float(len(trace) - 1) * dt
        censored = True
    else:
        settle_s = float(above[-1] + 1) * dt

    return {"overshoot": overshoot, "overshoot_cross": overshoot_cross,
            "steady_err_deg": steady_err_deg, "settle_s": settle_s, "censored": censored}


def run_episodes(policy, env, episodes: int = 30, seed_base: int = EVAL_SEED_BASE) -> dict:
    per_episode, rewards = [], []
    crashes = 0

    for k in range(episodes):
        obs, _ = env.reset(seed=seed_base + k)
        xy = [obs[:2]]
        total = 0.0

        while True:
            action, _ = policy.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            total += reward
            xy.append(obs[:2])
            if terminated or truncated:
                break

        rewards.append(total)
        if terminated:
            crashes += 1
        per_episode.append(episode_metrics(np.asarray(xy), env.dt))

    def mean(key):
        return float(np.mean([m[key] for m in per_episode]))

    return {
        "episodes": episodes,
        "mean_reward": float(np.mean(rewards)),
        "settle_s": mean("settle_s"),
        "settle_censored": sum(m["censored"] for m in per_episode),
        "overshoot": mean("overshoot"),
        "overshoot_cross": mean("overshoot_cross"),
        "steady_err_deg": mean("steady_err_deg"),
        "crash_rate": crashes / episodes,
    }


def format_table(results: dict) -> str:
    """{이름: 지표dict} 를 사람이 읽는 표로."""
    head = (f"{'비교군':<22}{'평균보상':>10}{'복원(s)':>10}{'미복원':>8}"
            f"{'오버슈트':>10}{'정상오차(deg)':>14}{'추락률':>8}")
    lines = [head, "-" * len(head)]
    for name, m in results.items():
        # 시드 평균을 거치면 정수 항목도 float이 되므로 표시 형식을 하나로 맞춘다
        # (PD는 30, RL은 30.0 으로 찍혀서 서로 다른 값처럼 보였다).
        lines.append(
            f"{name:<22}{m['mean_reward']:>10.1f}{m['settle_s']:>10.2f}"
            f"{m['settle_censored']:>8.0f}{m['overshoot']:>10.2f}"
            f"{m['steady_err_deg']:>14.2f}{m['crash_rate']:>8.0%}"
        )
    lines.append("")
    lines.append(f"* 복원 판정 기준 {SETTLE_DEG}도 · '미복원' 은 끝까지 그 아래로 못 내려온 에피소드 수")
    lines.append("* 오버슈트 = (최대 기울기 - 초기 기울기) / 초기 기울기, 0이면 초기값을 안 넘음")
    return "\n".join(lines)
