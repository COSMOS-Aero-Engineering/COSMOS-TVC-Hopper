# params.yaml 출처 대장

`params.yaml`의 키 34개마다 현재 값, 출처 상태, 근거, 실측 이슈를 한 표에 모았다(#255). 2026-10-31 기준으로 실측값은 하나도 없다. 실측 결과가 들어오면 아래 "실측 결과가 들어오면"의 순서로 고칠 줄을 찾는다.

이 표는 값의 정본이 아니다. 값의 정본은 [`params.yaml`](params.yaml)이다. 두 곳이 다르면 `params.yaml`이 맞고, 이 표를 고친다.

## 출처 상태

| 상태 | 뜻 |
|---|---|
| 실측 | 우리 실물을 재서 얻은 값. `data/`에 원시 기록이 있다 |
| 데이터시트 | 제조사 사양이나 판매 사양. 우리 실물에서 재지 않았다 |
| 설계값 | CAD 변수나 설계 문서에서 정한 치수. 만든 실물에서 재지 않았다 |
| 추정 | 계산, 역산, 공개 자료, 가정으로 잡은 값 |
| 설정 | 물리 상수가 아니라 시뮬레이션의 스위치, 랜덤화 폭, 제어 설계값. 실물에서 잴 대상이 아니다 |

"실측 이슈" 열에는 그 값을 실측할 이슈 번호를 적는다. 상태가 `설정`인 키는 잴 대상이 없어서 `해당 없음`과 이유를 적는다. 관련 결정 이슈가 있으면 함께 적는다.

줄 번호는 2026-10-31 main(`3d704ba`) 기준이다. 줄은 밀릴 수 있으니 키 이름으로 찾는다.

## 대장

### 질량 특성

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `mass` | 0.735 | kg | 추정 | `params.yaml:6`. 01 문서 §8.1 AUW 추정. 자세 동역학은 안 쓰고 `hover_throttle()`만 쓴다(#204) | #239(구매 부품), #219(프린트 부품), #261(조립 전체) |
| `Jxx` | 0.005 | kg·m² | 추정 | `params.yaml:7` | #262 |
| `Jyy` | 0.005 | kg·m² | 추정 | `params.yaml:8`. 좌우 대칭 가정으로 `Jxx`와 같게 둠 | #262 |
| `Jzz` | 0.002 | kg·m² | 추정 | `params.yaml:9` | #262 |
| `vane_arm_l` | 0.104 | m | 추정 | `params.yaml:12-16`. 계산 CG 68 mm(01 문서 §8.4) − 피벗 z −36 mm(`cad/hopper_params.scad`의 `vane_pivot_z`) | #261 |

같은 키의 최신 CAD 계산값이 다르다. 2026-10-31에 `python3 cad/cg/cg_estimate.py`를 실행한 결과는 총질량 778 g, l 119.8 mm, Jxx 0.00763, Jyy 0.00612, Jzz 0.00300 kg·m²다. 프린트 부품 질량이 하한 시나리오라서 이 계산도 실측이 아니다. 실측 전에 값을 바꿀지는 #268에서 정한다.

### 베인 형상 (`vane_geometry`)

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `vane_geometry.inner_r_mm` | 4.0 | mm | 설계값 | `params.yaml:30`. `cad/hopper_params.scad`의 `vane_inner_r` | #265. 허브 반지름이 이 값보다 크면 #118 결과로 다시 정한다 |
| `vane_geometry.outer_r_mm` | 32.0 | mm | 추정 | `params.yaml:31-32`. 64 mm급 EDF 공칭 지름의 절반 | #118 |
| `vane_geometry.chord_mm` | 25.0 | mm | 설계값 | `params.yaml:33`. `cad/hopper_params.scad`의 `vane_chord` | #265 |

요 팔 r, 잠긴 면적 A_fin, 종횡비 AR, 배기 단면적 A_duct는 키가 아니다. `hopper_aviary.py`의 `vane_geometry()`가 위 세 값에서 계산한다(`params.yaml:18-28`).

### 베인 공력

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `CLalpha` | 1.637 | 1/rad | 추정 | `params.yaml:40-47`. 논문 부록 B.3의 2D 기울기 6.194/rad에 Helmbold 저종횡비 보정(AR 1.12) | #263(TC-2 회귀) |
| `CD0` | 0.001054 | 무차원 | 추정 | `params.yaml:55`. 원저자 MATLAB의 뭉쳐진 값 | 해당 없음: 동역학 코드가 읽지 않는다(`hopper_aviary.py:191`에서 저장만). 쓰기 시작하면 #263의 TC-2 데이터로 정한다 |
| `alpha_max_deg` | 10 | deg | 추정 | `params.yaml:56`. 논문의 선형 근사 범위. 행동 −1-1을 베인각으로 바꾸는 배율이기도 하다 | #263(선형 범위). 하드스톱 각도는 #246 |

### 베인 서보 (`servo`)

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `servo.enabled` | false | - | 설정 | `params.yaml:68` | 해당 없음: 스위치. 켤지는 #203에서 정한다 |
| `servo.tau` | 0.05 | s | 추정 | `params.yaml:69-70`. tvc-retro-propulsion 추정값. 03 문서 §5의 20-60 ms 안 | #202 |
| `servo.rate_max_dps` | 600.0 | deg/s | 데이터시트 | `params.yaml:71-73`. TowerPro MG90S 0.10 s/60°(4.8 V, 무부하) | #202(부하 속도) |
| `servo.deadband_deg` | 0.45 | deg | 데이터시트 | `params.yaml:74-75`. Waveshare MG90S 5 µs × 가정 0.09°/µs | #202(데드밴드), #243(°/µs, SG90 기준) |

### 추력과 스로틀

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `Kf` | 1.1e-6 | N/(임의 단위)² | 추정 | `params.yaml:77-84`. 100 % 스로틀 정적 추력 10 N에서 역산 | #244(실험 A) |
| `omega_t_per_throttle` | 3000.0 | 임의 단위 | 추정 | `params.yaml:85-92`. `Kf`와 짝이다. 100 % 스로틀 Ft = Kf · 3000² = 9.9 N | #244. `Kf`와 함께 바꾼다 |
| `throttle_slew_rate` | 0.25 | 1/s | 설정 | `params.yaml:94-105`. #120 요 측정과 #185 고도 확인에서 고른 제어 설계값 | 해당 없음: 제어 설계값. 펌웨어도 같은 값을 쓴다(#184) |

### 도메인 랜덤화 (`domain_rand`)

`params.yaml:107-110`대로 이 블록은 실측 뒤에도 그대로 둔다. 범위는 명목값을 품어야 한다(`hopper_aviary.py`가 회전자 범위를 검사한다).

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `domain_rand.enabled` | true | - | 설정 | `params.yaml:112` | 해당 없음: 스위치 |
| `domain_rand.Jxx_range` | 0.3 | 비율(±) | 설정 | `params.yaml:113` | 해당 없음: 랜덤화 폭. #262 결과를 보고 폭을 다시 볼 수 있다 |
| `domain_rand.Jyy_range` | 0.3 | 비율(±) | 설정 | `params.yaml:114` | 해당 없음: 랜덤화 폭 |
| `domain_rand.Jzz_range` | 0.3 | 비율(±) | 설정 | `params.yaml:115` | 해당 없음: 랜덤화 폭 |
| `domain_rand.vane_arm_range` | 0.15 | 비율(±) | 설정 | `params.yaml:116`. CG 높이 오차 근사 | 해당 없음: 랜덤화 폭. #261 결과를 보고 폭을 다시 볼 수 있다 |
| `domain_rand.vane_arm_r_range` | 0.25 | 비율(±) | 설정 | `params.yaml:117`. 허브 차폐로 압력중심이 바깥으로 갈 가능성을 덮는다(#34) | 해당 없음: 랜덤화 폭. #118 결과를 보고 폭을 다시 볼 수 있다 |
| `domain_rand.Kf_range` | 0.2 | 비율(±) | 설정 | `params.yaml:118`. 모터 개체차·배터리 전압 편차 근사 | 해당 없음: 랜덤화 폭 |
| `domain_rand.cg_offset_mm` | 3.0 | mm(축당) | 설정 | `params.yaml:119-121`. 01 문서 §8.2 횡 CG 목표 ≤ 3 mm | 해당 없음: 랜덤화 폭. 실제 횡 CG 편차는 #261이 잰다 |
| `domain_rand.rotor_inertia_range` | [5.0e-6, 3.5e-5] | kg·m² | 설정 | `params.yaml:126`. `modelling-notes-ch3.md` §3의 추정 범위 | 해당 없음: 랜덤화 폭. 명목값은 #119 |
| `domain_rand.rotor_omega_max_range` | [3100.0, 4000.0] | rad/s | 설정 | `params.yaml:127` | 해당 없음: 랜덤화 폭. 명목값은 #119 |
| `domain_rand.rotor_tau_range` | [0.03, 0.15] | s | 설정 | `params.yaml:128` | 해당 없음: 랜덤화 폭. 명목값은 #264 |

### EDF 회전자 (`rotor`)

| 키 | 값 | 단위 | 상태 | 근거 | 실측 이슈 |
|---|---|---|---|---|---|
| `rotor.enabled` | false | - | 설정 | `params.yaml:142` | 해당 없음: 스위치 |
| `rotor.inertia` | 1.0e-5 | kg·m² | 추정 | `params.yaml:143`. 임펠러와 모터 캔 추정(`modelling-notes-ch3.md` §3) | #119 |
| `rotor.omega_max` | 3800.0 | rad/s | 추정 | `params.yaml:144-145`. KV × 4S 전압 × 부하율 | #119 |
| `rotor.tau` | 0.05 | s | 추정 | `params.yaml:146-147`. 가정 | #264 |
| `rotor.spin_dir` | 1 | - | 추정 | `params.yaml:148-149`. 모른다. 제품마다 다르다 | #119(TC-0) |

## 실측 결과가 들어오면

실측 이슈가 닫히거나 결과 댓글이 오면 그 이슈 번호(예: `#244`)로 이 문서를 검색해서 "실측 이슈" 열에 그 번호가 있는 행을 모두 찾는다. 행마다 첫 열의 키를 `params.yaml`에서 열고 값과 같은 블록의 주석을 고친다. 주석의 PLACEHOLDER 표시와 "실측 필요" 문구도 지운다. 같이 바뀌는 키를 확인한다: `vane_geometry`를 바꾸면 `CLalpha`를 `params.yaml:43`의 식으로 다시 계산하고, `Kf`를 바꾸면 `omega_t_per_throttle`도 함께 본다. 그다음 이 표의 값, 상태(`실측`), 근거(`data/` 파일 경로)를 고친다. PLACEHOLDER 목록이 있는 `sim/README.md`의 `params.yaml` 행과 `hopper_aviary.py` 첫 docstring도 맞춘다. 마지막으로 `python tasks.py check`를 돌려 통과를 확인한다.

`params.yaml`에 키를 더하거나 지우면 이 표에도 행을 더하거나 지운다. 이 일을 검사로 막는 작업은 #267이다.
