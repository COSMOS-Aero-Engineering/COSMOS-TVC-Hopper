# Teensy 4.0 Actor 벤치

이 벤치는 USB 시리얼로 추론 비용을 기록한다. IMU, 모터, ESC, 서보를 연결하지 않는다. 구동 핀을 설정하거나 제어 루프를 호출하는 코드가 없다. 현재 가중치는 실패 PPO의 수치 비교용이다.

먼저 [PC 비교 명령](../../../sim/deployment/README.md)을 저장소 루트에서 실행한다. 성공하면 이 프로젝트의 `include/actor_data.h`에 검증한 가중치와 체크포인트·정규화 식별자가 생긴다. 생성 헤더는 Git에서 제외한다. 같은 루트에서 다음 명령으로 빌드한다.

```text
pio run -d firmware/cosmos/policy_bench
```

PlatformIO가 Teensy 4.0용 ELF와 HEX를 만든다. 링크 단계의 FLASH, RAM1, RAM2 행은 스케치 전체의 정적 메모리 사용량이다. 이 작업은 빌드까지만 수행하며 실물 업로드는 금지한다.

기준 PPO를 `platformio/teensy@6.0.0`으로 빌드한 ELF에서 Actor 가중치와 편향은 19,988 B, 중간 계산 버퍼는 540 B였다. 스케치 전체의 FLASH는 코드 37,836 B, 데이터 25,544 B, 헤더 8,296 B였다. RAM1 변수는 26,944 B, RAM2 변수는 12,416 B였다.

별도로 승인된 보드 단독 시험에서는 USB 시리얼(115200)에 다음 필드가 나온다. 각 표본에서 합성 자세 관측을 바꾸고, `micros()`로 Actor 호출 전후를 잰다. 입력 설정, 체크섬과 시리얼 출력은 이 구간 밖에 있다.

| 필드 | 의미 |
| --- | --- |
| `model`, `normalization` | 체크포인트 SHA-256과 원시 관측 표시(`raw`) 또는 정규화 파일 SHA-256 |
| `n`, `mean_us`, `max_us` | 256회 호출의 평균과 최대 경과 시간(µs). 타이머 읽기 비용과 인터럽트 지연이 포함될 수 있다. |
| `parameter_bytes`, `workspace_bytes` | Actor 가중치·편향 바이트 수와 정적으로 할당한 중간 계산 버퍼 크기. 전체 RAM·스택 사용량은 별도다. |
| `checksum` | 이번 묶음에서 나온 다섯 행동의 합을 모든 표본에 걸쳐 누적한 값 |

실제 보드에서 걸리는 시간은 빌드로 측정할 수 없다. 후속 측정은 [#292](https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper/issues/292)에 기록한다.
