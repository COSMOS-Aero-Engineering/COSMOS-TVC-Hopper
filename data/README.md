# data/ — 실험 로그 (아직 비어 있음)

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
