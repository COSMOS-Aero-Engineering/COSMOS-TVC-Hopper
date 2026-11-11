# Stage 1 PPO Actor의 PC 출력 비교

저장소의 [실패 PPO](../sim_stage1/ppo-diagnosis.md)는 Python과 C++의 수치 비교에만 쓴다. 통과 기준은 같은 관측에서 다섯 행동의 최대 절대 오차가 각각 `1e-5` 이하인 것이다. 안정화 성능과 실기 사용 승인은 별도다.

## PC에서 실행

저장소 루트에서 실행한다. Windows에서는 Visual Studio의 **x64 Native Tools Command Prompt**를 열고 루트로 이동한다. Linux와 macOS에서는 C++17을 지원하는 GCC 또는 Clang을 사용한다.

```text
python ship.py capped 8G -- uv run --frozen --project . python sim/deployment/check_parity.py
```

이 명령은 [평가 코드](../sim_stage1/pd_gate.py)의 seed 0-199로 도메인 랜덤화를 켠 에피소드를 실행한다. 매 스텝에서 SB3의 `model.predict(obs, deterministic=True)`가 고른 행동으로 환경을 진행한다. 별도로 컴파일한 PC 실행 파일에 같은 원시 관측을 float32로 전달한다. 출력에는 채널별 최대 절대 오차와 최대 오차가 발생한 seed, 스텝, 행동 번호(0부터)가 나온다. 관측·행동에 NaN이나 무한대가 있거나 C++ 출력 길이·행동 범위·오차 검사가 실패하면 오류로 종료한다.

기준 체크포인트를 Windows x64에서 MSVC로 비교했을 때 관측은 99,873개였다. 행동값 499,365개의 최대 절대 오차는 `4.17232513e-7`이었다(seed 51, 스텝 186, 스로틀).

빠른 점검에는 `--episodes 2`를 붙인다. 컴파일러를 지정하려면 `--cxx` 뒤에 실행 파일 이름이나 경로를 넣는다. 통과하면 [Teensy 벤치](../../firmware/cosmos/policy_bench/README.md)의 `include/actor_data.h`를 갱신한다. `--output PATH`로 다른 위치를 지정할 수 있다. 실패하면 기존 헤더가 남으므로 해당 실행의 종료 코드와 모델 해시를 확인한다.

## 추론 계약

- [학습 코드](../sim_stage1/train.py)는 `PPO("MlpPolicy", HopperAttitudeEnv())`와 같은 구성을 사용한다. 현재 체크포인트의 Actor는 float32 `7 → 64 → 64 → 5`다. 처음 두 선형층 뒤에 tanh를 적용한다. 마지막 선형층은 가우시안 평균을 출력한다. 각 평균을 행동 범위로 자른다. Critic과 확률 샘플링은 추론에 쓰지 않는다.
- 관측 순서는 [환경의 OBS_NAMES](../sim_stage1/hopper_aviary.py)를 따른다. 롤·피치·요(rad), 바디 각속도 x·y·z(rad/s), 직전에 변화율 제한을 적용한 스로틀(0-1) 순이다. reset 직후 마지막 값은 1이다.
- 행동은 베인 1-4와 스로틀 순이고 모두 `[-1, 1]`이다. 환경의 `step()`이 베인각 환산, 스로틀의 `(a+1)/2` 변환과 변화율 제한을 맡는다.
- 현재 zip은 관측 정규화를 사용하지 않았다. 도구가 확인하는 SHA-256은 `9fa28231e3a9995d693fd9241397044f0b846c4e005b9c6bd9d8f6324b7a78b2`다. 다른 체크포인트에는 관측 순서와 학습 래퍼를 먼저 확인한다. 같은 단위·순서의 Stage 1 관측과 같은 행동 계약을 사용하는 모델만 비교한다.

다른 모델은 `--model FILE`에 학습 조건을 함께 지정한다. 원시 관측으로 학습했으면 `--raw-obs`, VecNormalize로 학습했으면 `--vecnormalize FILE`에 그 모델과 함께 저장한 통계를 준다. Python은 저장한 `normalize_obs`를 사용한다. C++은 같은 평균·분산·epsilon으로 표준화하고 `±clip_obs`에서 자른 뒤 float32로 변환한다. 보상 정규화는 행동 추론에 쓰지 않는다. 통계 파일은 pickle이므로 출처를 확인한 모델과 파일만 읽는다. 모델 zip만으로 학습 당시 래퍼나 통계 파일의 짝을 복원할 수 없다.

지원 범위는 7차원 Stage 1 Box, FlattenExtractor, 두 개의 Linear/Tanh 은닉층, 선형 행동 헤드, squash를 쓰지 않는 대각 가우시안이다. 구조나 차원이 다르면 내보내기를 중단한다. 내보낸 배열은 PyTorch Linear의 `[출력][입력]` 순서다. 호스트와 MCU는 같은 [actor.hpp](actor.hpp)를 빌드한다.

정규화 회귀 검사는 위와 같은 컴파일러 환경에서 실행한다. 별도로 만든 소형 시험 모델로 관측 정규화, 양쪽 행동 상한·하한, 통계 누락 시 비교 실패를 확인한다.

```text
python ship.py capped 8G -- uv run --frozen --project . python sim/deployment/test_normalization.py
```
