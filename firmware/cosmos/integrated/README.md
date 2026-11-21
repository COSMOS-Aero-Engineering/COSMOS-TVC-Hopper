# 통합 제어 펌웨어 (무출력)

호스트 SIL(software-in-the-loop)과 Teensy 4.0이 같은 `Controller::step`과 CSV 작성기를 쓴다. Teensy는 SPI IMU와 RC 펄스를 읽고 USB로 명령을 기록한다. DShot과 서보 출력 드라이버는 빌드에 포함하지 않는다.

## 실행

이 폴더에서 `pio run`으로 Teensy용 이미지를 빌드한다. 입력은 `imu_test`의 SPI 핀과 `rc_bench`의 CH1(18), CH5(9)이다. 보드 축 매핑과 수신기 기준값은 실물 확인이 필요하다(#238, #245, #275, #293).

호스트에서 다음 명령을 실행한다(GCC 또는 Clang).

```sh
c++ -std=c++17 -Wall -Wextra -Werror src/control.cpp src/telemetry.cpp sil/main.cpp -o sil-run
c++ -std=c++17 -Wall -Wextra -Werror src/control.cpp sil/policy_check.cpp -o policy-check
./policy-check
python sil/check.py ./sil-run
```

Windows의 x64 Native Tools 명령 프롬프트에서는 다음 명령을 쓴다.

```bat
cl /utf-8 /EHsc /std:c++17 src\control.cpp src\telemetry.cpp sil\main.cpp /Fe:sil-run.exe
cl /utf-8 /EHsc /std:c++17 src\control.cpp sil\policy_check.cpp /Fe:policy-check.exe
policy-check.exe
python sil/check.py sil-run.exe
```

Stage 1 환경을 설치한 파이썬으로 아래 명령을 실행한다. Windows에서는 실행 파일 이름으로 `sil-run.exe`를 준다. 출력 파일은 새 경로를 쓴다.

```sh
python sil/stage1.py ./sil-run episode.csv --seed 0
```

각 10 ms 틱에서 Stage 1 자세와 자이로를 C++에 넣고, C++이 낸 다섯 명령을 다음 물리 스텝에 적용한다. 변화율 제한은 C++에서 한 번만 적용한다. 기본 실행은 초기 자세를 seed로 정하고 기체 상수는 명목값으로 고정한다. SIL 직접 입력은 한 줄이 한 틱이다.

```text
now_ms att_ms qw qx qy qz gyro_ms wx wy wz ch1_ms ch1_us ch5_ms ch5_us arm|disarm|-
```

`*_ms`는 해당 보고의 마지막 수신 시각이다. -1은 아직 받지 않았다는 뜻이다. USB 모니터에서는 `+` 한 글자가 arm 요청이고 `!`는 disarm이다. 같은 틱에 둘 다 들어오면 disarm을 적용한다.

## 제어와 정지 조건

- 부팅은 DISARMED다. 두 센서 보고가 모두 유효하고 CH5가 킬 해제 상태이며 CH1이 1050 µs 이하일 때 새 arm 요청으로 ACTIVE에 들어간다. 첫 틱의 명령은 모두 0이다.
- `levelPd`는 Stage 1의 수평 롤·피치 PD(8, 2)와 베인 부호를 쓴다. CH1은 1000-2000 µs를 0-1로 바꾼다. 후보 정책은 자세 3축, 각속도 3축, 직전 적용 스로틀을 받아 베인 4개와 스로틀 목표를 돌려준다. RL 연결 시 정책의 다섯 번째 출력은 [-1,1]에서 [0,1]로 변환해야 한다(#291).
- 정상 경로에서는 베인을 [-1,1]로 제한하고 스로틀 목표를 CH1 한도 안으로 제한한다. 적용 스로틀은 직전 값에서 초당 최대 ±0.25만큼 변한다(#184). CH1을 내리는 것과 비상정지는 다른 입력이다.
- CH5가 1500 µs 미만이거나, CH1·CH5 수신이 100 ms 이상 끊기거나, 자세·자이로 중 하나가 50 ms 이상 끊기면 ACTIVE에서 FAILSAFE로 간다. MCU가 보고를 읽은 시각을 기준으로 두 종류의 수신 시각을 따로 갱신한다. 수신 시각은 센서 내부 시각과 다르다.
- 유효하지 않은 회전·각속도·정책 값이나 50 ms 이상의 제어 지연도 정지 조건이다. 정지한 틱부터 베인·스로틀 명령이 모두 0이다. FAILSAFE는 신호가 회복돼도 유지된다. disarm으로 해제한 뒤 새 arm 요청이 필요하다. USB 연결을 잃으면 disarm한다.
- 보고 간격(10 ms), 정지 시간, 쿼터니언 제곱 노름 허용 오차(0.02), CH1·CH5 기준은 무출력 검사용 설정이다. 실제 수신기가 송신기 신호를 잃고도 마지막 펄스를 계속 보내면 시간 검사만으로 검출할 수 없다(#275).

## CSV

앞 21개 열은 `sim/sim_stage1/export_episode.py`의 순서를 따른다.

```csv
t_ms,source,mode,phi,theta,psi,qw,qx,qy,qz,wx,wy,wz,servo1,servo2,servo3,servo4,throttle,batt_v,rpm,reward,fsm,reason,dry_run
```

`t_ms`는 호스트의 틱 시각 또는 보드 부팅 후 밀리초다(32비트 순환). 각도는 rad, 바디 각속도는 rad/s다. 자세나 자이로가 무효인 행은 해당 칸을 비운다. 원시 CSV에서는 정지 판정 행을 보존한다. 웹 뷰어는 쿼터니언이 없는 행을 건너뛴다.

`source=SIM`은 호스트, `source=DRY_RUN`은 보드 입력 전용이다. 두 경우 모두 `mode=PID`, `dry_run=1`이다. servo1-4는 정규화한 FWD/LEFT/AFT/RIGHT 명령, throttle은 변화율 제한 뒤의 명령이다. batt_v, rpm, reward는 비운다. `fsm`과 `reason`으로 정지 틱을 찾는다. 보드는 USB를 다시 연결하면 헤더를 다시 보내고 송신 버퍼가 차면 해당 틱의 로그를 건너뛴다.
