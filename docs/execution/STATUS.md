# 현재 상태

`AGENTS.md`에서 옮긴 날짜별 상태 기록이다(#38). 상태가 바뀌면 이 파일을 고친다.

## 현재 상태 (2026-10-16)

**된 것 (확인 범위 포함)**
- CAD 정본 `cad/hopper_params.scad`, 외주용 STL 9종 export(9/18, 검증 `echo()` 통과). STL은 `.gitignore` 대상이라 저장소에는 없다.
- Teensy 업로드 성공(10/15). 안 되던 원인은 **충전 전용 USB 케이블**이었다. BNO085를 4선 I2C로 0x4B에서 인식하고 자세값 출력 확인(`firmware/cosmos/imu_test_i2c`). SPI 스케치(`imu_test`)는 빌드만 확인.
- DShot 벤치 펌웨어(`throttle_serial`): arm 게이트, 상한 DShot 600, 램프, 워치독, 비상정지. **ESC 없이 Teensy에서만 확인**(#19). 실물 시험은 #24.
- Stage 1 시뮬레이션(`sim/sim_stage1`)과 PPO 파이프라인, 에피소드를 웹 CSV로 내보내는 `export_episode.py`(#23).
- KiCad 회로도 생성(20부품, 30넷). ERC 첫 실행(10/17, 오류 4개·경고 129개). 같은 날 넷리스트 대조로 생성기 핀 좌표 Y축 반전 결함을 찾음(#66).
- 웹 뷰어 뼈대 `web/`(Vite + Three.js, 빌드 통과, 10/16). 축 변환은 판정 전.

**막혀 있는 것**
1. **실험 A(EDF 추력곡선) 미실시.** `Kf`(추력 상수)가 잠정값 `1.1e-6`(10 N 역산)이다.
2. **시뮬레이션 베인 제어력 버그(#21).** main에서는 도메인 랜덤화를 켜면 어떤 정책도 1초 안에 넘어진다. **PR #35**가 CL을 논문 식 3.16으로 다시 계산하고 `vane_arm_l`을 0.104 m로 바꿔 합격 판정(PD 넘어짐 0 %)을 받았다. 리뷰와 머지가 남았다. 머지 전에는 **RL 결과를 성능으로 해석하지 않는다.** 머지 뒤에도 CL·팔 길이는 추정값이다. 남은 일: [`docs/tasks/27-sim-vane-authority.md`](../tasks/27-sim-vane-authority.md).
3. **3D프린트 외주 미발주**(10/14 기준). 조립 일정 전체가 여기에 걸려 있다.
4. **IMU Yaw**가 돌린 만큼 안 변한다. 스케치가 지자기를 쓰는 Rotation Vector 모드인데 설계는 자력계를 안 쓰기로 했다. Game Rotation Vector로 비교 예정(#28).
