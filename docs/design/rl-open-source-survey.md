# 오픈소스 RL 환경 조사 (2026-10-15)

우리 기체(EDF 1개 + 제트 베인 4개, 구속 스탠드 자세 제어)를 그대로 넣고 학습할 수 있는 오픈소스 RL 환경은 찾지 못했다. 같은 구성을 시뮬레이션한 프로젝트는 하나 있어서 물리 모델링 교훈을 가져올 수 있고, 같은 계열 프로젝트 두 곳이 RL을 시도했다가 고전 제어로 돌아간 기록이 있다. 결론은 지금의 numpy 환경(`sim/sim_stage1`)을 버리지 말고 물리를 고치는 것이다.

관련 이슈: #21 (Stage 1 환경에서 베인 제어력이 CG 오프셋 랜덤화보다 약 20배 작아 어떤 정책도 안정화 불가)

## 1. 조사 방법과 한계

- 웹 검색 12회로 후보를 모으고, GitHub API로 17개 레포의 존재, 최근 push 날짜, 라이선스를 직접 확인했다.
- 가장 가까운 4곳(tvc-retro-propulsion, PyFlyt, monocopter_flight_controller, SingleRotorUAV)은 README, 문서, 소스 일부를 직접 읽었다. 나머지는 검색 결과와 README 요약 수준이다.
- 외부 프로젝트의 수치는 저자 주장이고 독립 검증하지 않았다. 별이 0~1개인 레포는 개인 프로젝트다.
- Osedo 외(2023) 논문은 출판사 페이지가 인증을 요구해 본문을 읽지 못했다.

## 2. 우리와 가장 가까운 프로젝트

### Jacob19999/tvc-retro-propulsion

<https://github.com/Jacob19999/tvc-retro-propulsion> · MIT · Python, NVIDIA Isaac Sim · 2026-09 활동

- 구성: 90 mm EDF(약 45 N) 1개, 서보 베인 4개(±15°), IMU BNO085. 우리보다 크고 착륙(위치 제어)까지 목표로 한다.
- RL(Transformer-PPO)로 시작했다가 2026-09-28에 학습 코드를 레포에서 빼고 볼록최적화 유도(SOCP) + LQR로 바꿨다. 학습 코드는 git 기록에 남아 있다.
- `simulation/isaac/docs/physics_review_2026-09-29.md`, `physics-audit-2026-09-27.md`에서 가져올 교훈:
  - **베인 측력 상한.** 베인마다 양력을 따로 더한 모델이 물리적으로 가능한 측력의 약 8.5배를 냈고, 제트 운동량 유량으로 상한을 두는 coupled-jet 모델로 고쳤다. 우리는 반대로 과소 추정 상태(#21)라서, `CLalpha`를 고칠 때 이 상한으로 과대 추정이 아닌지 확인한다.
  - **베인 제어력 규모.** 호버 회전수에서 베인이 약 0.35 N·m를 낸다. 체급이 달라 직접 비교는 못 하지만 우리 환경의 축당 1.5 mN·m와는 한두 자릿수 차이가 난다.
  - **회전자 자이로·스풀 반작용.** 스로틀을 바꿀 때마다 회전자 각운동량 교환으로 기체가 요 방향으로 돌고, 베인의 요 제어력(약 0.3 N·m)이 이를 감당하기 어렵다고 기록했다. 우리 TC-2.5(자이로 커플링 관찰)가 같은 위험을 본다.
  - **서보 모델.** 각도 제한 0.262 rad, 데드밴드 0.017 rad(약 1°), 1차 지연 0.05 s. 데드밴드 역보상만으로 1 Hz 코닝 진동이 호버 각속도 RMS 15 → 1.5 °/s로 줄었다고 한다.
  - **IMU 모델.** 바이어스, 드리프트, 저역통과, 출력 주기, 지연을 넣은 측정 체인을 따로 둔다.
- 쓰기 어려운 점: Isaac Sim은 NVIDIA GPU와 무거운 설치가 필요하다. 코드를 가져오기보다 모델 구조와 수치 범위를 참고한다.

## 3. 프레임워크 후보

### PyFlyt (`03-control-pipeline-design.md` §8-1 확인 결과)

<https://github.com/jjshoots/PyFlyt> · 별 264 · MIT · PyBullet, Gymnasium API

- `PyFlyt/core/drones/rocket.py`의 `Rocket`은 부스터, 2축 짐벌(1차 지연, 각도 제한), 핀 4개(`LiftingSurface`)로 구성된다.
- `PyFlyt/core/abstractions/lifting_surfaces.py`의 `LiftingSurfaces.state_update()`는 각 면의 공기 속도를 **링크 자체의 속도에서 바람장(`wind_field`)을 뺀 값**으로 계산한다. EDF 배기 제트 속도는 들어가지 않는다.
- 따라서 **기본 부품만으로는 제트 베인을 표현할 수 없다.** 제자리 호버(기체 속도 0)에서 베인 힘이 0이 된다. §8-1의 답은 "포크 없이 그대로는 안 된다"이다.
- 대안은 두 가지다. (1) 우리 코드 안에서 `LiftingSurface`를 대신하는 제트 베인 부품을 만들어 조합한다(PyFlyt 자체를 고치지 않으므로 포크는 아니다). (2) 바람장 콜백으로 베인 위치에 제트 속도를 흘려 넣는 방법도 이론상 되지만 기체 다른 부분에도 같은 바람이 적용돼 권장하지 않는다.
- Stage 2(자유 비행)에서 쓰려면 (1)을 기준으로 검토한다.

### gym-pybullet-drones

<https://github.com/utiasDSL/gym-pybullet-drones> · 별 2.1k · MIT · 쿼드콥터 전용. 기존 기각 판단(대칭 믹싱 하드코딩)을 유지한다.

## 4. 실패 기록과 학술 사례

| 출처 | 내용 | 우리에게 주는 의미 |
|---|---|---|
| [jasonangelov/monocopter_flight_controller](https://github.com/jasonangelov/monocopter_flight_controller) | EDF + 짐벌 시험대에서 RL을 시도했다가 실패. 요 회전과 기울기를 동시에 못 잡았고 학습 효율이 낮았으며 실물로 옮겨지지 않았다고 기록. 고전 제어로 전환 | 요 회전과 실물 미이식이 실패 원인. 우리도 회전자 반작용과 서보 지연을 모델에 넣기 전에는 RL 결과를 믿기 어렵다 |
| tvc-retro-propulsion (2절) | RL에서 SOCP + LQR로 전환 | 같은 기체 계열에서 두 번째 사례 |
| Osedo, Wada, Hisada (2023), ROBOMECH Journal, [doi:10.1186/s40648-023-00260-0](https://doi.org/10.1186/s40648-023-00260-0) | 추력편향 UAV 피치 한 축을 도메인 랜덤화 RL로 제어. 실제 편차가 랜덤화 범위를 넘으면 성능 저하 | 구속 스탠드 Stage 1과 가장 비슷한 사례. 랜덤화 범위는 실측 편차를 덮되 제어 가능한 범위 안이어야 한다(#21과 같은 문제) |
| arXiv 2504.07694 (가변피치 MAV sim-to-real) | 추력 응답 지연을 시뮬레이션에 넣은 것이 실물 이식의 핵심 | 모터 1차 지연(`03` 문서에서 생략된 항목)을 넣을 근거 |

## 5. 참고 레포 (RL 없음, 부품 참고용)

| 레포 | 라이선스 | 참고할 부분 |
|---|---|---|
| [AxelBoularot/6DDL_TVC](https://github.com/AxelBoularot/6DDL_TVC) | MIT | 서보 지연, 백래시, 끝단 제한 모델. 실제 비행 로그와 비교 |
| [UrosKukovic/TVC_Self_Landing_Rocket](https://github.com/UrosKukovic/TVC_Self_Landing_Rocket) | 명시 안 됨 | EDF + 노즐 짐벌 TVC, 캐스케이드 PID로 실제 비행 |
| [SolidGeek/SingleRotorUAV](https://github.com/SolidGeek/SingleRotorUAV) | MIT | 우리 펌웨어 원본. [Jacobsen (2021) 석사논문](https://vbn.aau.dk/ws/files/421577367/Master_Thesis_Emil_Jacobsen_v5.pdf)의 하드웨어 |
| [taherfattahi/ppo-rocket-landing](https://github.com/taherfattahi/ppo-rocket-landing) | MIT | PPO 학습 코드 예제(2D 착륙) |
| [Raiqueeee/SpaceX-Falcon9-Landing](https://github.com/Raiqueeee/SpaceX-Falcon9-Landing) | MIT | MuJoCo 6자유도 로켓 PPO와 고전 제어 비교 구성 |
| [abritten/dRehmFlight-Monocopter](https://github.com/abritten/dRehmFlight-Monocopter) | GPL-3.0 | 베인 모노콥터 하드웨어. 코드는 복사하지 않는다 |
| [TVC-Hopper/tvc-hopper](https://github.com/TVC-Hopper/tvc-hopper) | GPL-3.0 | Simulink 기반 TVC 호퍼 비행 소프트웨어. 코드는 복사하지 않는다 |

MIT 레포는 출처를 밝히면 코드를 가져올 수 있다. GPL 레포의 코드를 섞으면 우리 코드도 GPL 의무가 생기므로 구조와 수치만 참고한다.

## 6. 권장 순서

1. #21의 두 버그(`CLalpha` 기하 인자, `vane_arm_l`)를 고친다. 베인 측력 합이 제트 운동량 유량 × sin(편향각)을 넘지 않는지 확인한다.
2. **RL 학습 전 합격 기준**: 도메인 랜덤화를 켠 상태에서 PD가 안정화해야 한다(#21 재현 스크립트).
3. 환경에 서보 지연·데드밴드·속도 제한, 모터 1차 지연, 회전자 자이로·스풀 반작용 토크를 추가한다. 값은 실험 A와 TC-2.5 데이터로 정한다.
4. 그 다음에 PPO를 다시 학습하고 PD와 같은 조건에서 비교한다.
5. Stage 2는 PyFlyt + 직접 만든 제트 베인 부품을 1순위로 검토한다.
