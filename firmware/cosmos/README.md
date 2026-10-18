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

폴더 3개가 각각 독립된 PlatformIO 프로젝트다. CI(`.github/workflows/ci.yml`의 firmware job)는 세 프로젝트를
모두 `pio run`으로 빌드한다. 복사한 드라이버 파일은 `firmware/reference/SingleRotorUAV/src/`의 같은 이름
파일과 내용이 같다(2026-10-18 `diff`로 확인).

| 폴더 | 내용 | 복사한 드라이버 | 대응 실험 |
|---|---|---|---|
| `imu_test/` | BNO085 자세값(Roll/Pitch/Yaw)을 도 단위로 시리얼에 출력한다. 최종 설계의 SPI 배선(CS=10, MOSI=11, MISO=12, SCK=13, INT=21, RST=20, PS0=22, PS1=3.3V)을 쓴다. 배선표는 `src/imu_test.ino` 첫 부분에 있다 | `BNO080.h/.cpp` | 실험 B(IMU 브링업) |
| `imu_test_i2c/` | BNO085가 살아 있는지 4선 I2C(3V·G·SDA=18·SCL=19)로만 확인하는 브링업 스케치다. I2C 버스를 스캔해서 0x4A나 0x4B에 붙고, 못 찾으면 2초마다 다시 스캔한다. 붙은 뒤에는 `imu_test`와 같은 형식으로 자세값을 출력한다 | `BNO080.h/.cpp` | 실험 B(IMU 브링업)의 I2C 사전 확인(SPI 배선 전), #28 IMU 축·부호 측정 |
| `throttle_serial/` | 시리얼 명령으로 ESC 하나에 DShot600 스로틀을 낸다(ESC 신호선 = 핀 8). `arm` 명령 뒤에만 출력한다. 상한은 DShot 600(27.6 %), 상승 램프는 20 %/s다. ARMED이고 목표 스로틀이 0보다 클 때 3초 넘게 유효한 명령이 없으면 워치독이 즉시 정지하고 DISARM한다. 빈 줄 Enter나 `stop`은 출력을 즉시 0으로 하고 DISARM한다. 다시 출력하려면 `arm`부터 다시 보낸다 | `dshot.h/.cpp` | 실험 C(DShot 모터 제어), 실험 A(추력곡선)·TC-0의 스로틀 소스 |

## 확인 상태 (2026-10-18 기준)

빌드, 실물 업로드, 실물에서 확인한 출력을 스케치마다 따로 적는다. 한 스케치의 실물 확인을 다른 스케치나
다른 배선의 확인으로 넓혀 읽지 않는다. `imu_test_i2c`의 I2C 확인은 `imu_test`의 SPI 배선을 확인한 것이
아니다. `throttle_serial`은 ESC 없이 Teensy에서만 확인했다. 실제 ESC의 DShot 동작은 아직 확인하지 않았다.

| 폴더 | 빌드 | 실물 업로드 기록 | 실물에서 확인한 것 | 아직 확인하지 않은 것 |
|---|---|---|---|---|
| `imu_test/` | 성공 | 없음 | 없음 | SPI 배선의 실물 동작 전체. PR #18은 만능기판 납땜 때 확인한다고 적었다. 핀 표와 01 문서 §2.2의 사람 대조는 #89 |
| `imu_test_i2c/` | 성공 | 2026-10-15, PR #18(작성자 `MINBBBB1201`) | 주소 0x4B에서 BNO085 인식, Roll·Pitch·Yaw 출력(PR #18). 짧은 손 시험에서 Yaw는 돌린 각도보다 작게 변했다(#28 §2) | IMU 축·부호 판정, Game Rotation Vector 비교(#28 §4) |
| `throttle_serial/` | 성공 | 2026-10-15, PR #19(작성자 `MINBBBB1201`). 2026-10-17, `kwon6789`(#24 dry-run 댓글) | ESC·모터 없이 시리얼 명령만 확인: arm 전 거부, 상한 초과 거부, 램프, 3초 워치독 정지, 빈 줄 정지(PR #19, #24 3-7번) | 실제 ESC·모터 반응, 핀 8의 DShot 파형, USB 분리 때 정지(#24 1·2·8번). #24 dry-run의 원시 로그는 아직 main의 `data/`에 없다 |

- 빌드 "성공"은 2026-10-18 서버(Linux x86_64, PlatformIO Core 6.2.0, platform teensy 6.0.0)에서 세 프로젝트
  모두 `pio run`이 `SUCCESS`로 끝난 결과다. CI도 PR마다 같은 빌드를 돌린다. 빌드 성공은 실물 동작을 뜻하지
  않는다.
- 업로드 방법별 실물 확인 상태는 아래 "빌드·업로드"에 있다.
- 기록: 2026-09-19 PlatformIO로 처음 빌드했을 때 `imu_test`가 컴파일되지 않았다. 인자 없는 `BNO080 imu;`를
  썼는데 `BNO080.h`에는 핀 4개를 받는 생성자만 있었다(#11에서 고침). 지금 `imu_test`는 SPI 핀 4개를 생성자에
  넘긴다(#13). `imu_test_i2c`는 `BNO080 imu(255, 255, 255, 255)`를 쓴다. 생성자는 핀 번호를 저장만 하고,
  CS·WAK·RST 핀을 쓰는 코드는 `beginSPI()`와 SPI 분기에만 있다(`BNO080.cpp`). 그래서 I2C 경로에서 `255`는
  자리만 채운다.

## 빌드·업로드 (PlatformIO)

```bash
cd firmware/cosmos/imu_test_i2c    # 또는 imu_test, throttle_serial
pio run                            # 컴파일만
pio run -t upload                  # Teensy에 업로드
pio run -e teensy40_cli -t upload  # macOS에서 Teensy에 업로드 (#91)
pio device monitor -b 115200       # 시리얼 모니터
```

macOS에서 `pio run -t upload`가 `Unable find Teensy Loader.`로 실패한 사례가 있다(#91). 기본 업로드 방식
`teensy-gui`는 Teensy Loader 앱과 연결해야 하기 때문이다. 그래서 각 `platformio.ini`에 업로드 방식만
`teensy-cli`로 바꾼 env `teensy40_cli`를 두었다. env를 지정하지 않은 명령은 `default_envs = teensy40`이라
예전처럼 `teensy40` env만 처리한다. Windows용 명령 `pio run -t upload`와 CI의 `pio run`도 env를 지정하지 않으므로
계속 `teensy40`을 쓴다.
`teensy_loader_cli`의 macOS 실행 파일은 x86_64 전용이라 Apple Silicon Mac에서는 Rosetta 2가 필요할 것으로
보인다(확인 필요).

업로드 방법별 실물 확인 상태(2026-10-18 기준):

- macOS, `pio run -e teensy40_cli -t upload`: 실물 업로드 기록이 없다. #126에서 확인한다. 이슈와 PR에 남은
  macOS 실물 업로드 기록은 2026-10-17 `kwon6789`가 `teensy_loader_cli`를 직접 실행한 것뿐이다(#91 본문,
  #24 dry-run 댓글).
- Windows, `pio run -t upload`(기본 env `teensy40`, `teensy-gui`): PR #125가 `default_envs`와 `teensy40_cli`를
  더한 뒤의 실물 업로드 기록이 없다. #127에서 확인한다.

VSCode PlatformIO 익스텐션 쓰면 왼쪽 개미 아이콘(PlatformIO 사이드바)에서 같은 동작을 버튼으로 — 이번에
SW팀이 오늘 설치한 그 익스텐션.

## 다음 단계

1. **`imu_test_i2c`로 IMU 축·부호 판정**(#28 §4). 5개 자세를 Rotation Vector와 Game Rotation Vector로 각각
   재고 "일치 / 축 매핑 필요 / 확인 필요" 중 하나로 판정한다.
2. **`imu_test` SPI 실물 확인.** SPI 배선을 납땜한 뒤 업로드해서 자세값이 나오는지 본다. 핀 대조는 #89.
3. `throttle_serial` — **반드시 EDF 팬 분리한 채로 먼저 확인**, 그다음 추력 스탠드에 고정해서 실험 A. 실제
   ESC 시험 항목은 #24에 있다. ESC·EDF에 배터리 전원을 넣기 전에 지도교사 서명과 부장 입회를 확인한다
   (#24, `AGENTS.md` §안전 원칙).
4. 통합 펌웨어(전체 제어 루프) 만들 때 `imu_test`(SPI)와 `throttle_serial`의 초기화·배선 코드를 재사용 — 가장
   먼저 고칠 곳은 `src/control.cpp`의 프로펄전 믹서(원본은 모터 2개 전제, 우리는 EDF 1개라 오히려 단순해짐).
5. 자이로 정차 보정 필요해지면(`docs/design/00-hopper-master-design.md` §6.7) `dshot.cpp`의 RPM
   텔레메트리 읽는 부분부터 확인.

커밋 태그: `[fw]`.
