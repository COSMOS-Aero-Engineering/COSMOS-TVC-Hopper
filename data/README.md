# 실험 로그 수집

저장소 루트에서 보드를 연결한 포트와 실제 업로드한 커밋을 지정한다. 실물 없이 호스트 시험만 할 때는 `FIXTURE`를 쓴다. 수집기는 명령을 보내지 않는다.

```powershell
uv run --no-project --with pyserial==3.5 python data/capture_bench.py capture --port COM5 --source REAL --profile imu --firmware <업로드한커밋> --seconds 30 --retries 2 --output run.jsonl
python data/capture_bench.py convert run.jsonl run-export
```

포트는 장치 관리자에서 확인한다. `run.jsonl`은 새 파일, `run-export`는 새 폴더를 지정한다. 수신한 바이트를 base64로 보존하고 연결·단절·수신 시각을 기록한다. 재접속마다 CSV를 나눈다. 빈 데이터나 포트 열기 실패는 종료 코드 1이다. 전송 도중 잘린 마지막 줄은 원본에 보존하고 CSV 집계에서 제외한다.

- `imu`: I2C/SPI 벤치의 도 단위 Roll/Pitch/Yaw를 ZYX 라디안·쿼터니언으로 변환한다. `001-imu.csv`를 웹 뷰어의 CSV 열기로 재생한다. 시간은 호스트 수신 시각이며 센서의 측정 시각은 알 수 없다. 축 보정은 #238에서 판정한다.
- `servo`, `rc`, `phase1`: 해당 스케치의 D 행을 채널 CSV로 변환한다. 장치의 millis와 호스트 경과 시간을 각각 보존한다. PHASE 1은 #286의 형식이다. 각도 없는 PWM 행을 자세 뷰어에 넣지 않는다.
- `integrated`: #288의 통합 펌웨어 CSV를 받는다. 실보드 입력이어도 출력이 연결되지 않은 행은 펌웨어의 `DRY_RUN` 표기를 유지한다. fixture로 수집하면 `FIXTURE`가 우선한다. 자세가 비어 있는 failsafe 행은 CSV에 남고 웹 자세 뷰어는 그 행을 건너뛴다.

검사: `uv run --no-project --with pyserial==3.5 python data/test_capture_bench.py`. 로컬 TCP 시험 송신기로 서로 다른 두 연결의 원시 바이트·단절·쿼터니언을 대조한다. 포트 동작은 [pySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)에 따른다.

시험 카드(TC-0~TC-7, `docs/design/00-hopper-master-design.md` §11)를 진행할 때마다 여기에 기록.
CSV 하나로 시작해도 됨 — 형식 강제 없음, 아래는 제안.

## 권장 파일명

```
data/YYYY-MM-DD_TC-<번호>_<한줄설명>.csv
예: data/2026-09-19_TC-0_throttle-only.csv
```

## 권장 컬럼 (실험 A류 — 추력 등)

```
timestamp, throttle_pct, thrust_g, current_A, voltage_V, notes
```

## 권장 컬럼 (실험 B/C류 — 자세·제어)

```
timestamp, roll_deg, pitch_deg, yaw_deg, gyro_p, gyro_q, gyro_r, servo1..4_pwm, motor_throttle, notes
```

`sim/sim_stage1/params.yaml`의 PLACEHOLDER 값(Jxx/Jyy/Jzz, CLα/CD0, Kf 등)을 실측값으로 바꿀 때,
그 실측이 나온 원본 로그를 여기 남겨두면 나중에 "이 숫자 어디서 나왔지" 추적 가능.

커밋 태그: `[data]`.
