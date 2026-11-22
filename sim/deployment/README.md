# Stage 1 PPO Actor의 PC 출력 비교

기본 모델은 발표 표에 쓰는 #230 모델 `hopper_attitude_ppo_230.zip`이다([학습 조건](../sim_stage1/ppo-ablation.md)). #230 전 [실패 PPO](../sim_stage1/ppo-diagnosis.md) `hopper_attitude_ppo.zip`도 `--model`로 비교할 수 있다. 통과 기준은 같은 관측에서 정책 출력마다 최대 절대 오차가 `1e-5` 이하인 것이다. 출력 일치는 안정화 성능이나 실기 사용 승인이 아니다.

## PC에서 실행

저장소 루트에서 실행한다. Windows에서는 Visual Studio의 **x64 Native Tools Command Prompt**를 열고 루트로 이동한다. Linux와 macOS에서는 C++17을 지원하는 GCC 또는 Clang을 사용한다.

```text
python ship.py capped 8G -- uv run --frozen --project . python sim/deployment/check_parity.py
```

이 명령은 [평가 코드](../sim_stage1/pd_gate.py)의 seed 0-199로 도메인 랜덤화를 켠 에피소드를 실행한다. 매 스텝에서 SB3의 `model.predict(..., deterministic=True)`가 고른 행동으로 환경을 진행한다. 정규화 모델이면 저장한 통계로 정규화한 관측을 넣는다. 별도로 컴파일한 PC 실행 파일에 같은 원시 관측을 float32로 전달한다. 출력에는 채널별 최대 절대 오차와 최대 오차가 발생한 seed, 스텝, 행동 번호(0부터)가 나온다. 관측·행동에 NaN이나 무한대가 있거나 C++ 출력 길이·행동 범위·오차 검사가 실패하면 오류로 종료한다.

| 모델 | 컴파일러 | 관측 | 출력값 | 최대 절대 오차 |
| --- | --- | --- | --- | --- |
| `hopper_attitude_ppo_230.zip` (`vanes4`) | Linux x64 GCC | 100,000 | 400,000 | `6.55651093e-7` (seed 88, 스텝 12, 베인 2) |
| `hopper_attitude_ppo.zip` (`learned`) | Linux x64 GCC | 99,873 | 499,365 | `4.17232513e-7` (seed 49, 스텝 202, 스로틀) |
| `hopper_attitude_ppo.zip` (`learned`) | Windows x64 MSVC | 99,873 | 499,365 | `4.17232513e-7` (seed 51, 스텝 186, 스로틀) |

빠른 점검에는 `--episodes 2`를 붙인다. 컴파일러를 지정하려면 `--cxx` 뒤에 실행 파일 이름이나 경로를 넣는다. 통과하면 [Teensy 벤치](../../firmware/cosmos/policy_bench/README.md)의 `include/actor_data.h`를 갱신한다. 헤더에는 통과한 seed 수 `kParityEpisodes`와 최대 오차 `kParityMaxAbs`가 들어간다. 벤치의 합성 입력 256개를 PC 빌드로 계산한 체크섬 `kBenchChecksumPc`도 들어간다.

이 비교는 PC 빌드만 확인한다. Teensy 빌드(`-std=gnu++17 -O2`)는 곱셈·덧셈을 합칠 수 있고(`vfma`) 다른 `tanhf`를 쓴다. 그래서 보드 출력이 PC와 조금 다를 수 있다. 보드에서는 벤치의 `checksum`과 `checksum_pc`를 비교한다(#292). `--episodes 2`로 만든 헤더도 덮어쓰므로 벤치에 쓰기 전에 전체 seed로 다시 실행한다. `--output PATH`로 다른 위치를 지정할 수 있다. 실패하면 기존 헤더가 남으므로 해당 실행의 종료 코드와 모델 해시를 확인한다.

## 추론 계약

- [학습 코드](../sim_stage1/ppo_ablation.py)는 SB3 `PPO("MlpPolicy", ...)` 기본 신경망을 쓴다. Actor는 float32 `7 → 64 → 64 → N`이다. N은 행동 구조에 따라 정해진다. 처음 두 선형층 뒤에 tanh를 적용한다. 마지막 선형층은 가우시안 평균을 출력한다. 각 평균을 행동 범위로 자른다. Critic과 확률 샘플링은 추론에 쓰지 않는다.
- 관측 순서는 [환경의 OBS_NAMES](../sim_stage1/hopper_aviary.py)를 따른다. 롤·피치·요(rad), 바디 각속도 x·y·z(rad/s), 직전에 변화율 제한을 적용한 스로틀(0-1) 순이다. reset 직후 마지막 값은 1이다.
- 행동 구조는 모델 zip 옆 `.json`의 `action`이다([policy_io.py](../sim_stage1/policy_io.py)). `.json`이 없으면 `learned`로 읽는다. 생성 헤더의 `kActionLayout`이 이 값이다.
  - `learned`(N=5): 베인 1-4와 스로틀 순이다.
  - `vanes4`(N=4): 베인 1-4만 낸다. 호출하는 쪽이 스로틀 `kFixedThrottleNorm`(1.0)을 다섯 번째 값으로 붙인다. `policy_io.to_env_action()`과 같다.
  - `mixer3`는 신경망 뒤에 믹서 계산이 필요하다. `actor.hpp`에 이 계산이 없어서 내보내기를 중단한다.
- 정책 출력은 모두 `[-1, 1]`이다. 환경의 `step()`이 베인각 환산, 스로틀의 `(a+1)/2` 변환과 변화율 제한을 맡는다.
- 저장소의 두 zip은 관측 정규화를 쓰지 않았다. 도구는 SHA-256으로 두 zip을 알아본다: `hopper_attitude_ppo_230.zip` `0c0f2162ac12e5d60c52d2cf8b2273a6df0591502d3608593b8feae7f827daea`, `hopper_attitude_ppo.zip` `9fa28231e3a9995d693fd9241397044f0b846c4e005b9c6bd9d8f6324b7a78b2`. 다른 체크포인트에는 관측 순서와 학습 래퍼를 먼저 확인한다. 같은 단위·순서의 Stage 1 관측과 같은 행동 계약을 사용하는 모델만 비교한다.

다른 모델은 `--model FILE`에 학습 조건을 함께 지정한다. 원시 관측으로 학습했으면 `--raw-obs`, VecNormalize로 학습했으면 `--vecnormalize FILE`에 그 모델과 함께 저장한 통계를 준다. Python은 저장한 `normalize_obs`를 사용한다. C++은 같은 평균·분산·epsilon으로 표준화하고 `±clip_obs`에서 자른 뒤 float32로 변환한다. 보상 정규화는 행동 추론에 쓰지 않는다. 통계 파일은 pickle이므로 출처를 확인한 모델과 파일만 읽는다. 모델 zip만으로 학습 당시 래퍼나 통계 파일의 짝을 복원할 수 없다.

지원 범위는 8차원 Stage 1 Box(#347 전에는 7차원), 행동 구조 `learned`·`vanes4`, FlattenExtractor, 두 개의 Linear/Tanh 은닉층, 선형 행동 헤드, squash를 쓰지 않는 대각 가우시안이다. 구조나 차원이 다르면 내보내기를 중단한다. 내보낸 배열은 PyTorch Linear의 `[출력][입력]` 순서다. 호스트와 MCU는 같은 [actor.hpp](actor.hpp)를 빌드한다.

정규화 회귀 검사는 위와 같은 컴파일러 환경에서 실행한다. 별도로 만든 소형 시험 모델로 관측 정규화, 양쪽 행동 상한·하한, 통계 누락 시 비교 실패를 확인한다. `vanes4` 헤더 내용과, `mixer3`·출력 차원이 다른 `.json`을 거부하는지도 확인한다.

```text
python ship.py capped 8G -- uv run --frozen --project . python sim/deployment/test_normalization.py
```
