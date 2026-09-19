# firmware/cosmos/ — 우리 팀의 Teensy 펌웨어

`firmware/reference/SingleRotorUAV/`(SolidGeek 원본 vendor-copy, 손대지 않음)에서 필요한 드라이버를
그대로 복사해 쓰는 단위 테스트 스케치들 + (나중에) 전체 통합 펌웨어.

**2026-09-19: Arduino IDE → PlatformIO(VSCode) 전환 완료.** SW팀 개발환경이 오늘부로 PlatformIO
기준으로 바뀌었다 — 버전 고정(`platformio.ini`의 `lib_deps`), CI 연동 가능(`pio run`은 커맨드라인),
`sim/`(Python)과 같은 VSCode에서 작업 가능해서. 각 폴더가 이제 **독립된 PlatformIO 프로젝트**다
(`platformio.ini` + `src/`) — Arduino IDE의 "스케치 폴더 안 .h/.cpp만 같이 컴파일" 제약이 없어져서
드라이버 파일을 여러 폴더에 복사해둘 필요가 원래는 없지만, 지금은 vendor-copy 추적성 유지 목적으로
그대로 두고 있다(나중에 `lib/`로 통합 검토 가능).

## 현재 있는 것

| 폴더 | 내용 | 대응 실험 |
|---|---|---|
| `imu_test/` | BNO085 자세값(Roll/Pitch/Yaw) 시리얼 출력. `BNO080.h/.cpp`는 원본 vendor-copy에서 복사 | 실험 B(IMU 브링업) |
| `throttle_serial/` | 시리얼로 0~100 입력하면 그 %로 DShot 스로틀. `dshot.h/.cpp`는 원본에서 복사, 2초 무입력 시 자동 0% 페일세이프 포함 | 실험 C(DShot 모터제어), 실험 A(추력곡선)의 스로틀 소스 |

**둘 다 `pio run`으로 컴파일 검증 완료(2026-09-19)** — 이번에 처음 실제로 빌드해봤고,
`imu_test.ino`에서 진짜 버그를 하나 잡았다: `BNO080 imu;`가 인자 없는 생성자를 호출하는데
`BNO080.h`엔 4-인자 생성자(`CSPin,WAKPin,INTPin,RSTPin`, SPI용)만 있어서 **컴파일 자체가 안 됐다**
(Arduino IDE로도 마찬가지였을 것 — 이전엔 아무도 실제로 빌드해본 적이 없어서 몰랐던 것뿐).
`BNO080(255,255,255,255)`로 고침 — I2C(`.begin()`) 경로는 이 4개 인자를 안 쓰므로(생성자가
멤버변수에 저장만 함, `BNO080.cpp` 확인) 플레이스홀더로 안전. **여전히 Teensy 4.0 실물 업로드는 아직**
(컴파일 성공 ≠ 실물에서 동작 확인).

## 빌드·업로드 (PlatformIO)

```bash
cd firmware/cosmos/imu_test        # 또는 throttle_serial
pio run                            # 컴파일만
pio run -t upload                  # Teensy에 업로드
pio device monitor -b 115200       # 시리얼 모니터
```

VSCode PlatformIO 익스텐션 쓰면 왼쪽 개미 아이콘(PlatformIO 사이드바)에서 같은 동작을 버튼으로 — 이번에
SW팀이 오늘 설치한 그 익스텐션.

## 다음 단계

1. **`imu_test` 실물 업로드** → 축 방향·부호 확인(실험 B). 컴파일은 이미 통과했으니 이제 손에 있는
   Teensy에 `pio run -t upload`만 하면 됨.
2. `throttle_serial` — **반드시 EDF 팬 분리한 채로 먼저 확인**, 그다음 추력 스탠드에 고정해서 실험 A.
3. 통합 펌웨어(전체 제어 루프) 만들 때 이 두 스케치의 초기화·배선 코드를 재사용 — 가장 먼저 고칠 곳은
   `src/control.cpp`의 프로펄전 믹서(원본은 모터 2개 전제, 우리는 EDF 1개라 오히려 단순해짐).
4. 자이로 정차 보정 필요해지면(`docs/design/00-hopper-master-design.md` §6.7) `dshot.cpp`의 RPM
   텔레메트리 읽는 부분부터 확인.

커밋 태그: `[fw]`.
