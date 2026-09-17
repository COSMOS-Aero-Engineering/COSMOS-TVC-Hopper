# firmware/cosmos/ — 우리 팀의 Teensy 펌웨어

`firmware/reference/SingleRotorUAV/`(SolidGeek 원본 vendor-copy, 손대지 않음)에서 필요한 드라이버를
그대로 복사해 쓰는 단위 테스트 스케치들 + (나중에) 전체 통합 펌웨어.

## 현재 있는 것

| 폴더 | 내용 | 대응 실험 |
|---|---|---|
| `imu_test/` | BNO085 자세값(Roll/Pitch/Yaw) 시리얼 출력. `BNO080.h/.cpp`는 원본 vendor-copy에서 복사 | 실험 B(IMU 브링업) |
| `throttle_serial/` | 시리얼로 0~100 입력하면 그 %로 DShot 스로틀. `dshot.h/.cpp`는 원본에서 복사, 2초 무입력 시 자동 0% 페일세이프 포함 | 실험 C(DShot 모터제어), 실험 A(추력곡선)의 스로틀 소스 |

두 스케치 다 **아직 Teensy 4.0 실물 업로드 전** (핀헤더 미납땜, 2026-09-17 기준 `AGENTS.md` 참고).

## 다음 단계

1. 핀헤더 납땜 → 업로드 → `imu_test`로 축 방향·부호 확인.
2. `throttle_serial` — **반드시 EDF 팬 분리한 채로 먼저 확인**, 그다음 추력 스탠드에 고정해서 실험 A.
3. 통합 펌웨어(전체 제어 루프) 만들 때 이 두 스케치의 초기화·배선 코드를 재사용 — 가장 먼저 고칠 곳은
   `src/control.cpp`의 프로펄전 믹서(원본은 모터 2개 전제, 우리는 EDF 1개라 오히려 단순해짐).
4. 자이로 정차 보정 필요해지면(`docs/design/00-hopper-master-design.md` §6.7) `dshot.cpp`의 RPM
   텔레메트리 읽는 부분부터 확인.

커밋 태그: `[fw]`.
