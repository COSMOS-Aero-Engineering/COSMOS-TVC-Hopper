# sim/ — 시뮬레이션 · 강화학습

Stage 1 환경 구현 완료 (2026-09-14), PPO 1회 학습 성공. **더 이상 gym-pybullet-drones 안 씀** —
이유는 `AGENTS.md`의 "소프트웨어 스택" §2 참고(모터 1개+베인 4개 구조를 넣으려면 라이브러리 내부를
포크 수준으로 새로 써야 해서, 순수 `gymnasium.Env`를 직접 구현하는 쪽으로 결정).

## 현재 있는 것 (`sim/sim_stage1/`)

| 파일 | 내용 |
|---|---|
| `hopper_aviary.py` | **`HopperAttitudeEnv`** — 위치 구속(만능조인트) 상태에서 자세만 제어하는 Stage 1 환경. 뉴턴-오일러 강체 회전방정식(자이로스코픽 교차항 포함) + ZYX 오일러각 운동학을 numpy로 직접 적분. `docs/design/references/`의 논문 3장(Modelling)을 그대로 코드화한 것 |
| `params.yaml` | 물리 상수. **CLalpha/CD0/Kf/mass/Jxx·Jyy·Jzz는 전부 PLACEHOLDER** — 실험 A(EDF 추력곡선) + 조립 후 실측 전까지는 의미 없는 값. `vane_arm_l/r`만 `cad/hopper_params.scad` 실측 기반이라 PLACEHOLDER 아님 |
| `sanity_check.py` | 환경이 안 깨졌는지 빠르게 확인(무작위 액션 20스텝) |
| `train.py` | PPO(stable-baselines3) 학습 스크립트 |
| `hopper_attitude_ppo.zip` | 학습된 모델 1회분 — PLACEHOLDER 물리값 기준이라 **성능 숫자 자체는 의미 없음**, 파이프라인이 도는지 확인용 |

## 관측 / 행동 (실제 구현 기준 — 이전 계획의 12/4차원 문서와 다름, 이게 현재 정답)

```
관측 obs (6): [phi, theta, psi, wx, wy, wz]   — 자세각(rad) + 바디 각속도(rad/s)
행동 act (5): [a1, a2, a3, a4, throttle]       — 베인 4개 각도(-1~1) + 스로틀(-1~1, 내부에서 0~1 변환)
과제: 초기 교란(±0.3rad)에서 수평(phi=theta=0)으로 복귀·유지
```

- 도메인 랜덤화: `params.yaml`의 `domain_rand` 블록 — Jxx/Jyy/Jzz ±30%, 베인 모멘트암 ±15%, Kf ±20%,
  무게중심-추력축 오프셋 ±3mm를 매 `reset()`마다 무작위 재추출.
- PLACEHOLDER 값을 실측치로 바꿀 때: **`params.yaml`만 교체, `hopper_aviary.py`는 안 건드림**
  (일부러 그렇게 분리해둔 것).

## 실행

저장소 루트에서 실행한다. 가상환경을 따로 활성화할 필요 없다 — uv가 `uv.lock`에 맞춰 알아서 맞춰준다.

```bash
python tasks.py sanity   # 환경 정상 동작 확인 (20스텝)
python tasks.py check    # CI와 같은 검사 — PR 올리기 전에
python tasks.py train    # PPO 학습 (200k 스텝)
```

처음이라면 `python tasks.py setup`을 한 번 먼저. 설치 방법은 루트 [`README.md`](../README.md)의 부원 퀵스타트.

## 다음 단계

- **실험 A(EDF 추력곡선) → `params.yaml`의 Kf·CLalpha·CD0 실측값 반영.**
- 조립 후 질량·관성 실측 → mass/Jxx/Jyy/Jzz 반영.
- Stage 2(전체 6DOF, 위치 자유) — 실험 A 데이터 확보 후 착수.
- baseline 제어(PID/LQR)가 실기에서 서기 전엔 이 학습 결과를 실기에 올리지 않음 (CLAUDE.md/AGENTS.md 원칙).

## 선행 (완료됨, 2026-09-13)

- `test_cartpole.py`, `test_pendulum.py`(레포 루트) — SB3 공식 퀵스타트로 워크플로 익히기. CartPole/Pendulum 둘 다 실행 성공.
