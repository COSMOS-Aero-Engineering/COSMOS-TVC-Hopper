# sim/ — 시뮬레이션 · 강화학습

Stage 1 환경 구현 완료 (2026-09-14), PPO 1회 학습 성공. **더 이상 gym-pybullet-drones 안 씀** —
이유는 `AGENTS.md`의 "소프트웨어 스택" §2 참고(모터 1개+베인 4개 구조를 넣으려면 라이브러리 내부를
포크 수준으로 새로 써야 해서, 순수 `gymnasium.Env`를 직접 구현하는 쪽으로 결정).

> ⚠️ **여기 있는 Stage 1은 파이프라인 검증용 PoC다 — 최종 목표가 아니다.** numpy 직접적분이라
> 빠르고 의존성이 없지만 물리 신뢰도가 낮다(공력 lumped 근사, 서보 동특성 없음, 충돌 없음). 3D
> 물리엔진 기반 Stage 2로 넘어가는 계획(후보 비교·검증 상태 포함)은
> [`../docs/design/03-control-pipeline-design.md`](../docs/design/03-control-pipeline-design.md) §2가
> 정본. 이 Stage 1은 버리지 않고 앞으로도 빠른 스모크테스트용으로 계속 쓴다(§2 참고).

## 현재 있는 것 (`sim/sim_stage1/`)

| 파일 | 내용 |
|---|---|
| `hopper_aviary.py` | **`HopperAttitudeEnv`** — 위치 구속(만능조인트) 상태에서 자세만 제어하는 Stage 1 환경. 뉴턴-오일러 강체 회전방정식(자이로스코픽 교차항 포함) + ZYX 오일러각 운동학을 numpy로 직접 적분. `docs/design/references/`의 논문 3장(Modelling)을 그대로 코드화한 것 |
| `params.yaml` | 물리 상수. **CLalpha/A_fin/A_duct/CD0/Kf/mass/Jxx·Jyy·Jzz/vane_arm_l은 PLACEHOLDER** — 실험 A(EDF 추력곡선)·TC-2·조립 후 실측 전까지는 추정값. 각 값의 계산 근거는 파일 주석에 있다(#27) |
| `pd_gate.py` | **RL 학습 전 합격 기준**(#27): 도메인 랜덤화 켠 상태에서 PD(kp=8, kd=2)가 평가 seed 0~199에서 넘어짐 ≤ 5 %, 최종 기울기 중앙값 ≤ 5°인지. `--model`로 PPO도 같은 seed로 비교. `tasks.py check`가 매번 돌린다 |
| `yaw_check.py` | **요 축 검사**(#65): `pd_gate.py`의 PD는 요 토크가 늘 0이라 요 경로를 못 본다. ① 베인 위치·힘 방향의 외적으로 손계산한 토크와 환경의 한 스텝 Δω를 비교한다(부호, 크기, 롤·피치 누설, 상수는 `params.yaml`에서 읽음). ② 요 PD를 섞으면 평가 seed 0-199에서 마지막 \|ψ\| ≤ 1°인지 본다. `tasks.py check`가 매번 돌린다 |
| `sanity_check.py` | 환경이 안 깨졌는지 빠르게 확인(무작위 액션 20스텝) |
| `train.py` | PPO(stable-baselines3) 학습 스크립트. 학습 seed 10000(평가 seed 0~199와 분리) |
| `export_episode.py` | 에피소드 1회를 웹 대시보드 CSV 형식(`docs/design/02-web-dashboard-design.md` §4)으로 `episode_logs/`에 저장. 정책 `pd`(기준 PD)·`zero`·`ppo`, 옆에 시드·물리 상수·결과를 담은 `.meta.json`. 실물 시험 로그와 같은 3D 뷰어로 재생하기 위한 것 |
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

에피소드를 3D 뷰어용 CSV로 남기려면 `sim/sim_stage1/`에서:

```bash
python export_episode.py --policy pd --no-dr --seed 0     # 랜덤화 끈 PD 1회
python export_episode.py --policy ppo --episodes 5        # 학습 모델 5회 (stable-baselines3 필요)
```

결과는 `sim/sim_stage1/episode_logs/`(git 제외)에 쌓인다. 같은 시드와 커밋이면 같은 파일이 다시 나온다.

처음이라면 `python tasks.py setup`을 한 번 먼저. 설치 방법은 루트 [`README.md`](../README.md)의 부원 퀵스타트.

## 다음 단계

- **실험 A(EDF 추력곡선) → `params.yaml`의 Kf 실측값 반영. TC-2(베인각별 복원 모멘트) → CL 실측 회귀로 CLalpha·A_fin·A_duct 추정값 교체.**
- #26 CAD 무게중심 추정·조립 후 CG 실측 → `vane_arm_l` 교체. 바꾼 뒤 `python pd_gate.py`로 합격 기준을 다시 확인.
- 조립 후 질량·관성 실측 → mass/Jxx/Jyy/Jzz 반영.
- Stage 2(전체 6DOF, 위치 자유) — 실험 A 데이터 확보 후 착수.
- baseline 제어(PID/LQR)가 실기에서 서기 전엔 이 학습 결과를 실기에 올리지 않음 (CLAUDE.md/AGENTS.md 원칙).

## 선행 (완료됨, 2026-09-13)

- `test_cartpole.py`, `test_pendulum.py`(레포 루트) — SB3 공식 퀵스타트로 워크플로 익히기. CartPole/Pendulum 둘 다 실행 성공.
