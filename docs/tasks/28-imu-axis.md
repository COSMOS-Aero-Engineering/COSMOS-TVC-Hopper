# #28 IMU 축·부호 확인 (김시우)

## 지금 상태

- Teensy와 BNO085를 4선 I2C(3V·G·18·19)로 연결해 주소 0x4B에서 Roll·Pitch·Yaw가 나온다(10/15, `firmware/cosmos/imu_test_i2c`).
- 손 시험에서 Roll·Pitch는 잘 변했지만 Yaw는 돌린 만큼 안 변했다(약 −20~−70°).
- 원인 후보를 찾았다. 스케치는 `enableRotationVector`를 쓰는데, 이 모드는 **지자기(나침반)** 를 섞는다. 그런데 설계는 처음부터 **자력계를 안 쓰기로** 했다(01 문서 §7.5-4, 마스터 §12 리스크: "자력계 미사용으로 회피"). 자력계를 빼는 모드는 `enableGameRotationVector`다. 라이브러리에 이미 있다(`src/BNO080.h` 152행).

## 용어

- **Roll / Pitch / Yaw:** X축(FWD) / Y축(LEFT) / Z축(위) 둘레의 회전.
- **오른손 법칙:** 오른손 엄지를 축 방향으로 두면 나머지 손가락이 감기는 방향이 + 회전이다.
- **Rotation Vector vs Game Rotation Vector:** 앞의 것은 자이로+가속도+지자기, 뒤의 것은 지자기를 뺀 것. 뒤의 것은 Yaw가 천천히 흐를 수 있지만 노트북·모터 자기장에 흔들리지 않는다.
- **축 매핑:** IMU 축과 기체 축이 다를 때 펌웨어에서 부호나 축을 바꿔 맞추는 표.

## 기대 부호 (시뮬레이션 정의 기준)

01 문서 §1 좌표계(+X=FWD, +Y=LEFT, +Z=위)에 오른손 법칙을 적용한 값이다. 시뮬레이션 `hopper_aviary.py`와 웹 뷰어 예제 `web/public/samples/axis-test.csv`도 같은 정의를 쓴다.

| # | 자세 (3초 정지 후 읽기) | 기대 변화 |
|---|---|---|
| 1 | 평평하게 정지 | 0 근처 (Yaw는 시작값 기록) |
| 2 | FWD 쪽을 약 30° 아래로 | Pitch **+** 약 30, 나머지 거의 그대로 |
| 3 | LEFT 쪽을 약 30° 아래로 | Roll **−** 약 30 |
| 4 | 위에서 볼 때 반시계 90° | Yaw **+** 약 90 |
| 5 | 위에서 볼 때 시계 90° | Yaw **−** 약 90 |

IMU 출력이 위 부호와 반대여도 일관되면 "축 매핑 필요"로 판정하고 표를 남긴다. 부호 정의 자체는 김준원(#27)과 한 번 더 맞춘다.

## 첫 30분

1. 모듈 위에 FWD 화살표와 LEFT 화살표를 펜으로 그린다. 모듈 실크의 X 화살표를 FWD로 둔다(01 문서 §7.5-2).
2. 업로드하고 값이 나오는지 본다. PowerShell에서는 `&&` 대신 `;`.
   ```bash
   cd firmware/cosmos/imu_test_i2c; pio run -t upload
   pio device monitor --filter time --filter log2file
   ```
   `log2file`은 화면에 나온 줄을 이 폴더의 `logs/device-monitor-날짜-시각.log`로 저장한다(Git에는 안 올라감). `time`은 각 줄 앞에 시각을 붙인다.
3. 노트북에서 30 cm 이상 떨어진 평평한 책상에서 위 표 1~5를 측정한다.

정상 결과: 2번에서 Pitch만, 3번에서 Roll만 크게 변한다.

## 이어서 할 일

1. **Yaw 비교:** 같은 측정을 `enableRotationVector(50)` 대신 `enableGameRotationVector(50)`으로 한 번 더 한다(`src/main.cpp` 37행 한 줄). 두 결과를 나란히 적고 어느 쪽이 90°에 가까운지 판정한다. Game 모드로 바꾸는 게 맞으면 그 변경을 PR에 포함한다.
2. **기록:** `logs/`의 로그 파일을 `data/20261024-IMU-axis-01.log`처럼 옮기고, 표(측정값, 기대 부호, 결과)는 PR 본문에 쓴다.
3. **판정:** "일치 / 축 매핑 필요 / 확인 필요" 중 하나. 매핑이 필요하면 "IMU Roll = −기체 Roll"처럼 적는다.
4. **이민우와 교차 확인:** 펌웨어 핀 정의와 회로도 핀이 같은지 본다(#26의 `check_imu_nets.py` 표).
5. **그다음:** 권재후와 DShot 실물 시험(#24). 착수 문서는 [28-dshot-bench.md](28-dshot-bench.md).

## 확인 못 한 것

- Game Rotation Vector로 바꾸면 Yaw가 90°에 가깝게 나오는지는 아직 아무도 실물로 보지 않았다.
- 위 기대 부호는 좌표계 정의에서 유도한 것이다. BNO085 라이브러리의 오일러 변환 부호는 실측으로만 확인할 수 있다.
