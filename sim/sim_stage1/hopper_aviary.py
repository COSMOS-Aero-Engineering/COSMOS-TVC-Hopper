"""
PRJ-01 TVC 호퍼 — Stage 1 시뮬레이션 환경 (자세 안정화, 위치 구속)

Week 2 물리 실험의 "구속 스탠드"(M1, 만능조인트로 위치를 고정하고 회전만 자유롭게 두는
테스트 리그)와 1:1로 대응되는 환경. 즉 연습용 CartPole/Pendulum이 아니라, 실제로
우리 기체 구조·좌표계·베인 4개짜리 토크 방정식을 그대로 쓰는 "진짜" 첫 RL 환경.

⚠️ 아직 실험 A(EDF 추력곡선)·구속 스탠드 실측 전이라 params.yaml의 물리 상수
   (Jxx/Jyy/Jzz, CLalpha, vane_geometry, Kf, omega_t_per_throttle, vane_arm_l)는 PLACEHOLDER 상태.
   지금 단계 목표는:
     "RL 학습 파이프라인이 우리 기체의 실제 상태/액션 구조에 맞춰 정상적으로 도는가"
   를 확인하는 것 — 절대적인 학습 성능 숫자 자체는 아직 의미 없음.
   Week 2에서 실측값이 나오는 대로 params.yaml만 교체하면 이 코드는 그대로 재사용됨.

관측(observation)  = [phi, theta, psi, wx, wy, wz, throttle]   (OBS_NAMES)
                     자세각 rad, 바디 각속도 rad/s, 직전 스텝에 실제로 쓴 스로틀 0-1(#186)
액션(action)       = [a1, a2, a3, a4, throttle]     (베인각 -1~1 정규화, 스로틀 0~1)
과제               = 초기 교란에서 수평(phi=theta=0)으로 되돌아와 유지하기
                     → 구속 스탠드 첫 실험(실험 B 이후, 자세 제어 첫 검증)과 같은 목표

EDF 회전자 항(#86): params.yaml의 rotor.enabled를 켜면 회전자 반작용 토크(−I_r·dΩ/dt, z축)와
회전자 자이로 토크(−ω × h, 롤·피치)를 더한다. 기본값은 끔이다. 원논문은 반대로 도는 모터 2개라
이 토크가 상쇄된다고 보고 뺐다(Jacobsen 2021 §3.2). 우리는 EDF 1개라 상쇄되지 않는다.
켜면 추력도 1차 지연을 따르는 회전수 Ω에서 계산한다(Ft ∝ Ω², #122). 끄면 추력은 지연 없이 스로틀을 따른다.
식과 상수 근거는 docs/design/modelling-notes-ch3.md §3의 "EDF 회전자 반작용·자이로 항".

스로틀 변화율 제한(#120): params.yaml의 throttle_slew_rate(1/s)로 스로틀 명령이 한 스텝에 바뀌는 양을
±throttle_slew_rate·dt로 자른다. 회전자 항 스위치와 상관없이 늘 쓴다. 펌웨어도 같은 제한을 쓴다(마스터 설계 §8.1).
제한 뒤 실제로 쓴 스로틀은 step()의 info["throttle"]와 관측 obs[6]에 있다(#186). 제한이 있으면 다음 스텝에 쓸 수
있는 스로틀이 이 값에 달려서, 관측에 없으면 정책이 못 보는 상태가 된다. reset() 직후 obs[6]은 RESET_THROTTLE_OBS(1.0)다.
첫 스텝은 제한하지 않으므로 이 값은 첫 스텝을 제약하지 않는다. 회전자 회전수 Ω(rotor.enabled)는 관측에 넣지 않았다.
실물에서 회전수를 받으려면 ESC 텔레메트리가 필요하고 지금 하드웨어에는 없다(#174, #186 결정).

베인 서보 동특성(#161): params.yaml의 servo.enabled를 켜면 베인각이 명령각을 데드밴드·1차 지연·속도 제한으로 따라간다
(_advance_servo). 기본값은 끔이다. 끄면 베인각은 행동을 받은 스텝에 바로 명령각이 된다. 켜도 실제 베인각은 관측에 없다.
MG90S는 위치 피드백이 없어서 실물에서도 재지 못한다. 상수 근거는 params.yaml servo 블록.

도메인 랜덤화: params.yaml의 domain_rand 설정에 따라 매 reset()마다 Jxx/Jyy/Jzz,
베인 모멘트암(l,r), Kf, 무게중심-추력축 오프셋, 회전자 상수(inertia·omega_max·tau, #121)를
그 범위 안에서 무작위로 다시 뽑는다.
지금은 애초에 실측 전 PLACEHOLDER 값들이라 "정확한 한 점"을 맞추는 게 의미가 없고,
"이 근처 분포 전체"에서 버티는 정책을 학습해두는 게 나중에 실측값이 들어왔을 때도,
그리고 실제 기체로 이식할 때도(PID와의 정량 비교 실험, CLAUDE.md 참고) 더 안전하다.

seed 재현 범위(#98): reset()은 gymnasium의 np_random에서 에피소드 seed 하나만 뽑는다. 초기 자세와
랜덤화하는 값은 이름마다 따로 난수 흐름을 쓴다(EPISODE_STREAMS). 그래서 값을 더하거나 빼거나 뽑는
순서를 바꿔도 같은 seed의 다른 값과 초기 자세는 그대로다. 랜덤화를 꺼도 초기 자세는 같다.
같은 numpy·gymnasium 버전(uv.lock)에서만 보장한다. #98 전 커밋의 로그는 그 커밋에서만 재현된다.
"""
import hashlib
import os
from typing import Optional

import gymnasium as gym
import numpy as np
import yaml
from gymnasium import spaces

# 에피소드마다 뽑는 값의 이름(#98). 이름 하나가 독립 난수 흐름 하나의 키다.
# 새로 랜덤화하는 값은 여기에 이름을 더하고 self._rng("이름")에서 뽑는다.
# 이름을 바꾸면 그 값의 seed별 표본만 바뀐다. 다른 값의 표본은 그대로다.
EPISODE_STREAMS = (
    "initial_attitude",
    "Jxx", "Jyy", "Jzz",
    "vane_arm_l", "vane_arm_r",
    "Kf",
    "cg_offset_x", "cg_offset_y",
    "rotor_inertia", "rotor_omega_max", "rotor_tau",   # #121
)

# 회전자 상수의 랜덤화 분포(#121). 범위는 params.yaml domain_rand의 <이름>_range([아래, 위])에 있다.
# True = 로그 균등(ln 값이 균등. 비율마다 같은 확률), False = 균등.
#   inertia: 범위가 7배(5e-6 - 3.5e-5)라 로그 균등. 명목 1e-5 아래를 뽑을 확률이 36 %다(균등이면 17 %)
#   omega_max: 범위가 1.29배(3100 - 4000)라 두 분포의 차이가 작다. 균등
#   tau: 시상수(척도 값)이고 범위가 5배(0.03 - 0.15)라 로그 균등. 0.06 s 위를 뽑을 확률이 57 %다(균등이면 75 %)
# 근거: Peng et al. 2018(arXiv:1710.06537)은 질량·감쇠·마찰·게인을 로그로, 나머지를 균등으로 뽑았다.
#   OpenAI 2018(arXiv:1808.00177) 표 1도 감쇠·액추에이터 게인을 loguniform으로 뽑았다.
ROTOR_RAND_LOG = {"rotor_inertia": True, "rotor_omega_max": False, "rotor_tau": True}

# 관측 벡터의 이름과 순서(#186). 앞 6개는 물리 상태(self.state), 마지막은 직전 스텝에 실제로 쓴 스로틀(0-1)이다.
# 순서를 바꾸면 학습한 모델과 pd_gate.pd() 같은 obs[:6] 사용처가 조용히 틀린다. 새 값은 끝에 더한다.
OBS_NAMES = ("phi", "theta", "psi", "wx", "wy", "wz", "throttle")
N_STATE = 6               # obs[:N_STATE]가 물리 상태다. 6차원 관측으로 학습한 모델은 이 부분만 받는다
RESET_THROTTLE_OBS = 1.0  # reset() 직후 obs[6]. 첫 스텝은 제한하지 않으므로 값 자체는 동역학에 영향이 없다.
                          # 1.0은 pd_gate.py·yaw_check.py 시나리오 A의 고정 스로틀이다


def stream_id(name: str) -> int:
    """이름 → 32비트 정수 키. 파이썬 hash()는 프로세스마다 값이 달라서(PYTHONHASHSEED) 쓰지 않는다."""
    return int.from_bytes(hashlib.blake2b(name.encode("utf-8"), digest_size=4).digest(), "little")


STREAM_IDS = {name: stream_id(name) for name in EPISODE_STREAMS}
if len(set(STREAM_IDS.values())) != len(STREAM_IDS):
    raise RuntimeError("EPISODE_STREAMS의 두 이름이 같은 32비트 키를 받았다. 둘 중 하나의 이름을 바꿀 것.")


def vane_geometry(p: dict) -> dict:
    """베인 잠김 구간 하나(params.yaml의 vane_geometry)에서 요 팔 r, 잠긴 면적 A_fin, 종횡비 AR,
    배기 단면적 A_duct를 계산한다(#98, #117).

    잠김 구간은 반경 inner_r-outer_r, 시위는 chord다. 축방향 유속이 이 구간에서 균일하다고 본다.
      r      = (inner_r + outer_r) / 2       z축 → 베인 압력중심 반경(m). 요 토크 팔이다
      A_fin  = (outer_r - inner_r) · chord   베인 1장이 제트에 잠긴 면적(m^2)
      AR     = (outer_r - inner_r) / chord   종횡비. params.yaml의 CLalpha 주석에서 쓴다
      A_duct = π · outer_r²                  배기 단면적(m^2). 제트 반지름 outer_r인 원 전체다(#117 결정 (a)).
                                             꼬리 원뿔(허브) 단면은 빼지 않는다
    mm 값을 1e3, 1e6으로 나눠서 m, m^2로 바꾼다. 곱하기(1e-3) 대신 나누기를 쓰면 명목값이
    소수 리터럴 0.018, 7.0e-4와 비트 단위로 같다.
    """
    for old, since in (("A_fin", "#98"), ("vane_arm_r", "#98"), ("A_duct", "#117")):
        if old in p:
            raise ValueError(f"params.yaml에서 {old} 줄을 지울 것. 이 값은 vane_geometry에서 계산한다({since}). "
                             "두 줄을 같이 두면 두 출처가 어긋날 수 있다.")
    g = p["vane_geometry"]
    inner, outer, chord = float(g["inner_r_mm"]), float(g["outer_r_mm"]), float(g["chord_mm"])
    if not (0.0 <= inner < outer and chord > 0.0):
        raise ValueError(f"vane_geometry가 잘못됐다: 0 ≤ inner_r_mm({inner}) < outer_r_mm({outer}), "
                         f"chord_mm({chord}) > 0 이어야 한다.")
    span = outer - inner
    return {"r": (inner + outer) / 2.0 / 1e3, "A_fin": span * chord / 1e6, "AR": span / chord,
            "A_duct": np.pi * outer**2 / 1e6}


def vane_lift_gain(p: dict) -> float:
    """베인 1장의 측력/추력 비율 기울기 CL(1/rad). F = Ft · CL · alpha (논문 식 3.16).

    CL = CLalpha · A_fin / (2 · A_duct). A_fin과 A_duct는 vane_geometry()에서 계산한다.
    한 축 베인 2장의 최대 측력 2·CL·alpha_max·Ft가
    제트 운동량 상한 Ft·sin(alpha_max)를 넘으면 과대 추정이므로 ValueError를 낸다
    (docs/design/rl-open-source-survey.md §2).
    """
    g = vane_geometry(p)
    CL = p["CLalpha"] * g["A_fin"] / (2.0 * g["A_duct"])
    alpha_max = np.deg2rad(p["alpha_max_deg"])
    if 2.0 * CL * alpha_max > np.sin(alpha_max):
        raise ValueError(
            f"베인 측력 과대 추정: 축당 2·CL·alpha_max = {2.0 * CL * alpha_max:.4f}·Ft > "
            f"sin(alpha_max) = {np.sin(alpha_max):.4f}·Ft. params.yaml의 CLalpha/vane_geometry를 확인할 것."
        )
    return float(CL)


G = 9.81   # m/s². 호버 스로틀 계산에만 쓴다. Stage 1 자세 동역학은 위치를 구속해서 중력을 쓰지 않는다


def hover_throttle(mass: float, Kf: float, omega_t_per_throttle: float) -> float:
    """추력이 무게와 같아지는 스로틀(0-1)을 계산한다(#204). 호버 스로틀의 정본은 이 함수 하나다.

    환경의 추력 식 Ft = Kf·(u·omega_t_per_throttle)²에서 Ft = mass·G를 u로 푼다:
      u = sqrt(mass·G / (Kf·omega_t_per_throttle²))
    params.yaml 명목값(0.735 kg, Kf 1.1e-6, 3000)이면 최대 추력 9.9 N이고 u = 0.853이다.
    u가 1을 넘으면 최대 추력이 무게보다 작아서 기체가 뜨지 못한다. 이때는 ValueError를 낸다.
    """
    u = float(np.sqrt(mass * G / (Kf * omega_t_per_throttle ** 2)))
    if not 0.0 < u <= 1.0:
        raise ValueError(f"호버 스로틀 {u:.3f}: 0보다 크고 1 이하여야 한다. 최대 추력 "
                         f"{Kf * omega_t_per_throttle ** 2:.2f} N, 무게 {mass * G:.2f} N. "
                         "params.yaml의 mass·Kf·omega_t_per_throttle을 확인할 것.")
    return u


class HopperAttitudeEnv(gym.Env):
    """Stage 1: 위치 구속(만능조인트) 상태에서 자세(roll/pitch/yaw)만 제어하는 환경."""

    metadata = {"render_modes": []}

    def __init__(self, params_path: Optional[str] = None, dt: float = 0.01, max_steps: int = 500):
        super().__init__()
        if params_path is None:
            params_path = os.path.join(os.path.dirname(__file__), "params.yaml")
        with open(params_path, "r", encoding="utf-8") as f:
            p = yaml.safe_load(f)

        self.mass = p["mass"]
        # 이 아래는 "명목값(nominal)" — 실제로 매 에피소드에 쓰는 값은 reset()에서
        # domain_rand 범위 안에서 다시 뽑은 self.Jxx/self.Jyy/... 로 덮어씀
        self.nominal_Jxx, self.nominal_Jyy, self.nominal_Jzz = p["Jxx"], p["Jyy"], p["Jzz"]
        self.nominal_l = p["vane_arm_l"]
        self.nominal_r = vane_geometry(p)["r"]
        self.nominal_Kf = p["Kf"]
        self.omega_t_per_throttle = p["omega_t_per_throttle"]   # 랜덤화하지 않는다
        # 스로틀 변화율 제한(#120). 스로틀(0-1)이 1초에 바뀔 수 있는 최댓값(1/s). null이면 제한하지 않는다.
        # 키가 없으면 KeyError를 낸다. 제한이 조용히 꺼지지 않게 하려고 기본값을 두지 않았다.
        rate = p["throttle_slew_rate"]
        self.throttle_slew_rate = None if rate is None else float(rate)
        if self.throttle_slew_rate is not None and not self.throttle_slew_rate > 0:
            raise ValueError(f"throttle_slew_rate = {rate}: 0보다 커야 한다. 제한을 끄려면 null로 둔다.")
        self.throttle_applied = None   # 직전 스텝에 실제로 쓴 스로틀(0-1). 에피소드 첫 step()에서 정한다
        self.CL = vane_lift_gain(p)
        self.CD0 = p["CD0"]
        self.alpha_max = np.deg2rad(p["alpha_max_deg"])

        # 베인 서보 동특성(#161). 블록이 없으면 끈다. step()은 servo_enabled가 참일 때만 _advance_servo()를 부른다.
        servo = p.get("servo", {})
        self.servo_enabled = bool(servo.get("enabled", False))
        self.servo_tau = float(servo.get("tau", 0.0))                              # s
        self.servo_rate_max = np.deg2rad(float(servo.get("rate_max_dps", np.inf)))  # rad/s
        self.servo_deadband = np.deg2rad(float(servo.get("deadband_deg", 0.0)))     # rad
        if self.servo_tau < 0 or self.servo_deadband < 0 or not self.servo_rate_max > 0:
            raise ValueError("servo.tau와 servo.deadband_deg는 0 이상, servo.rate_max_dps는 0보다 커야 한다.")
        self.vane_alpha = np.zeros(4)   # rad, 실제 베인각 4개. servo_enabled일 때만 쓴다. reset()이 중립(0)으로 둔다

        self.dr = p.get("domain_rand", {"enabled": False})

        # EDF 회전자(#86). 상수는 늘 읽는다. step()은 rotor_enabled가 참일 때만 회전자 토크를 넣는다.
        # yaw_check.py는 스위치와 상관없이 rotor_enabled를 바꿔서 끈 경우와 켠 경우를 비교한다.
        # inertia·omega_max·tau는 명목값이다. 랜덤화를 켜면 reset()이 에피소드마다 다시 뽑는다(#121). spin_dir는 뽑지 않는다.
        rotor = p.get("rotor", {})
        self.rotor_enabled = bool(rotor.get("enabled", False))
        self.nominal_rotor_inertia = float(rotor.get("inertia", 0.0))      # kg·m²
        self.nominal_rotor_omega_max = float(rotor.get("omega_max", 0.0))  # rad/s, 스로틀 100 %
        self.nominal_rotor_tau = float(rotor.get("tau", 0.0))              # s
        self.rotor_spin_dir = int(rotor.get("spin_dir", 1))
        if self.rotor_spin_dir not in (1, -1):
            raise ValueError(f"rotor.spin_dir = {self.rotor_spin_dir}: +1 또는 -1이어야 한다.")
        if min(self.nominal_rotor_inertia, self.nominal_rotor_omega_max, self.nominal_rotor_tau) < 0:
            raise ValueError("rotor.inertia, rotor.omega_max, rotor.tau는 0 이상이어야 한다.")
        if self.rotor_enabled and not (self.nominal_rotor_inertia > 0 and self.nominal_rotor_omega_max > 0):
            raise ValueError("rotor.enabled가 true인데 rotor.inertia나 rotor.omega_max가 0이다.")
        self.rotor_inertia = self.nominal_rotor_inertia      # 이번 에피소드 값. reset()이 정한다
        self.rotor_omega_max = self.nominal_rotor_omega_max
        self.rotor_tau = self.nominal_rotor_tau
        self.rotor_ranges = self._rotor_ranges()
        self.rotor_omega = None   # rad/s, 회전자 회전수. 에피소드 첫 step()에서 정한다

        self.dt = dt
        self.max_steps = max_steps
        self.step_count = 0

        # 액션: 베인 4개 각도 + 스로틀, 전부 -1~1로 대칭 정규화
        # (SB3 권장사항 — 비대칭 [0,1] 스로틀은 PPO 기본 가우시안 정책과 궁합이 안 좋음.
        #  스로틀은 step()에서 -1~1 -> 0~1로 내부 변환해서 씀)
        self.action_space = spaces.Box(
            low=np.array([-1, -1, -1, -1, -1], dtype=np.float32),
            high=np.array([1, 1, 1, 1, 1], dtype=np.float32),
            dtype=np.float32,
        )
        # 관측: 자세각(rad) + 바디 각속도(rad/s, 대략적 상한) + 제한 뒤 스로틀(0-1, #186). 순서는 OBS_NAMES
        high = np.array([np.pi, np.pi, np.pi, 50, 50, 50, 1], dtype=np.float32)
        low = np.array([-np.pi, -np.pi, -np.pi, -50, -50, -50, 0], dtype=np.float32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)

        self.state = np.zeros(6, dtype=np.float32)
        self.episode_seed = None  # reset()이 정한다. 이번 에피소드의 모든 난수 흐름이 여기서 나온다

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # np_random에서는 에피소드 seed 하나만 뽑는다(#98). seed 없이 reset()해도 다음 에피소드가
        # 결정적으로 이어지고, 값을 더하거나 빼도 np_random을 쓰는 횟수(1회)는 그대로다.
        self.episode_seed = int(self.np_random.integers(2**64, dtype=np.uint64))
        self._randomize_episode_params()
        # 완전 수평에서 시작하면 학습할 게 없으므로 초기 교란을 줌
        # (구속 스탠드 실험에서 손으로 살짝 기울여 놓고 시작하는 것과 같은 셋업)
        phi, theta, psi = self._rng("initial_attitude").uniform(-0.3, 0.3, size=3)
        self.state = np.array([phi, theta, psi, 0.0, 0.0, 0.0], dtype=np.float32)
        self.step_count = 0
        self.throttle_applied = None
        self.vane_alpha = np.zeros(4)
        return self._obs(), {}

    def _obs(self):
        """관측 벡터(OBS_NAMES 순서, float32). 물리 상태 self.state 뒤에 직전 스텝의 제한 뒤 스로틀을 붙인다(#186)."""
        throttle = RESET_THROTTLE_OBS if self.throttle_applied is None else self.throttle_applied
        return np.append(self.state, np.float32(throttle)).astype(np.float32)

    def _rng(self, name):
        """이번 에피소드에서 name 값만 쓰는 난수 생성기(#98).

        numpy 병렬 난수 문서의 권장대로 흐름 키를 바뀌지 않는 seed 앞에 둔 정수 열
        [키, 에피소드 seed]로 SeedSequence를 만든다. 키는 늘 32비트 한 워드라 (키, seed) 쌍이 겹치지 않는다.
        비트 생성기는 PCG64로 고정한다. default_rng는 기본 비트 생성기가 바뀔 수 있다(numpy 호환성 정책).
        """
        if name not in STREAM_IDS:
            raise KeyError(f"난수 흐름 {name!r}가 없다. EPISODE_STREAMS에 이름을 먼저 더할 것.")
        seq = np.random.SeedSequence([STREAM_IDS[name], self.episode_seed])
        return np.random.Generator(np.random.PCG64(seq))

    def _rotor_ranges(self):
        """params.yaml domain_rand의 회전자 상수 범위를 읽고 검사한다(#121). {이름: (아래, 위)}.

        범위 키가 없으면 그 값은 명목값으로 둔다. 랜덤화를 켜면 범위는 명목값을 품어야 한다. 실측 뒤 명목값만 고치고
        범위를 그대로 두면 랜덤화가 명목값을 한 번도 뽑지 않는 어긋남이 생기기 때문이다.
        랜덤화를 끄면 범위를 쓰지 않으므로 검사하지 않는다. 그래서 domain_rand.enabled가 false이면
        rotor.tau = 0(지연 없음)도 범위를 고치지 않고 쓸 수 있다.
        """
        ranges = {}
        check = bool(self.dr.get("enabled", False))
        for name in ROTOR_RAND_LOG:
            bounds = self.dr.get(f"{name}_range")
            if bounds is None:
                continue
            lo, hi = (float(b) for b in bounds)
            nominal = getattr(self, f"nominal_{name}")
            if check and not (0.0 < lo <= nominal <= hi):
                raise ValueError(f"domain_rand.{name}_range = [{lo:g}, {hi:g}]: 0 < 아래 ≤ 명목값({nominal:g}) ≤ 위 "
                                 f"이어야 한다. params.yaml의 rotor 명목값과 범위를 함께 고칠 것. "
                                 f"이 값을 랜덤화하지 않으려면 domain_rand.{name}_range 줄을 지운다.")
            ranges[name] = (lo, hi)
        return ranges

    def _randomize_episode_params(self):
        """도메인 랜덤화 — 이번 에피소드에서 쓸 물리 상수를 명목값 주변에서 다시 뽑는다."""
        if not self.dr.get("enabled", False):
            self.Jxx, self.Jyy, self.Jzz = self.nominal_Jxx, self.nominal_Jyy, self.nominal_Jzz
            self.l, self.r = self.nominal_l, self.nominal_r
            self.Kf = self.nominal_Kf
            self.cg_offset_x = 0.0
            self.cg_offset_y = 0.0
            self.rotor_inertia = self.nominal_rotor_inertia
            self.rotor_omega_max = self.nominal_rotor_omega_max
            self.rotor_tau = self.nominal_rotor_tau
            return

        def jitter(name, nominal, rel_range):
            # nominal * (1 + U(-rel_range, +rel_range)), name 값의 난수 흐름에서 뽑는다
            return nominal * (1.0 + self._rng(name).uniform(-rel_range, rel_range))

        self.Jxx = jitter("Jxx", self.nominal_Jxx, self.dr.get("Jxx_range", 0.0))
        self.Jyy = jitter("Jyy", self.nominal_Jyy, self.dr.get("Jyy_range", 0.0))
        self.Jzz = jitter("Jzz", self.nominal_Jzz, self.dr.get("Jzz_range", 0.0))

        # l(무게중심 → 베인 피벗 세로 거리)과 r(z축 → 베인 압력중심 반경)은 다른 치수라 따로 흔든다(#34).
        # vane_arm_r_range가 없으면 예전처럼 vane_arm_range를 쓴다.
        arm_range = self.dr.get("vane_arm_range", 0.0)
        self.l = jitter("vane_arm_l", self.nominal_l, arm_range)
        self.r = jitter("vane_arm_r", self.nominal_r, self.dr.get("vane_arm_r_range", arm_range))

        self.Kf = jitter("Kf", self.nominal_Kf, self.dr.get("Kf_range", 0.0))

        # 무게중심-추력축 오프셋 → 추력 방향으로 일정한 잔류 토크(bias)를 만듦
        cg_offset_max_m = self.dr.get("cg_offset_mm", 0.0) / 1000.0
        self.cg_offset_x = self._rng("cg_offset_x").uniform(-cg_offset_max_m, cg_offset_max_m)
        self.cg_offset_y = self._rng("cg_offset_y").uniform(-cg_offset_max_m, cg_offset_max_m)

        # 회전자 상수(#121): [아래, 위] 범위에서 값마다 자기 난수 흐름으로 뽑는다. 분포는 ROTOR_RAND_LOG.
        # rotor.enabled가 꺼져 있어도 뽑는다. 흐름이 따로라 다른 값의 표본은 바뀌지 않고, 끄면 쓰지 않는다.
        for name, nominal in (("rotor_inertia", self.nominal_rotor_inertia),
                              ("rotor_omega_max", self.nominal_rotor_omega_max),
                              ("rotor_tau", self.nominal_rotor_tau)):
            if name not in self.rotor_ranges:
                value = nominal
            elif ROTOR_RAND_LOG[name]:
                lo, hi = self.rotor_ranges[name]
                value = float(np.exp(self._rng(name).uniform(np.log(lo), np.log(hi))))
            else:
                value = float(self._rng(name).uniform(*self.rotor_ranges[name]))
            setattr(self, name, value)

    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)
        a1, a2, a3, a4, throttle_norm = action
        alpha = np.array([a1, a2, a3, a4]) * self.alpha_max
        if self.servo_enabled:
            alpha = self._advance_servo(alpha)   # 서보 동특성(#161). 끄면 명령각을 그대로 쓴다
        throttle = self._limit_throttle((throttle_norm + 1.0) / 2.0)  # -1~1 -> 0~1, 그다음 변화율 제한(#120)

        # 회전자 항을 켜면(#86) 회전수 Ω가 스로틀을 1차 지연으로 따라가고, 추력도 이 Ω에서 계산한다(#122).
        # 추력에 쓰는 유효 스로틀 = Ω / omega_max. 끄면 지금처럼 스로틀을 그대로 쓴다.
        if self.rotor_enabled:
            rotor_omega0, rotor_omega1 = self._advance_rotor(throttle)
            thrust_throttle = rotor_omega1 / self.rotor_omega_max
        else:
            thrust_throttle = throttle

        # 스로틀 -> 추력 (PLACEHOLDER 스케일: omega_t_equiv는 실제 rpm이 아니라
        # throttle을 상대적 회전수로 환산한 임시 값. 환산 상수는 params.yaml의 omega_t_per_throttle.
        # 실험 A 이후 실제 DShot 값 기준으로 교체)
        omega_t_equiv = thrust_throttle * self.omega_t_per_throttle
        Ft = self.Kf * omega_t_equiv**2

        # 베인 선형 공력 근사 (modelling-notes-ch3.md §2.2, 식 3.16)
        F1, F2, F3, F4 = self.CL * Ft * alpha

        phi, theta, psi, wx, wy, wz = self.state

        tau_x = (F1 + F3) * self.l
        tau_y = -(F2 + F4) * self.l
        tau_z = (F1 - F2 - F3 + F4) * self.r

        # 무게중심-추력축 오프셋(도메인 랜덤화) → 추력 Ft에 비례하는 잔류 토크
        tau_x += self.cg_offset_y * Ft
        tau_y += -self.cg_offset_x * Ft

        wx_dot = (tau_x + (self.Jyy - self.Jzz) * wy * wz) / self.Jxx
        wy_dot = (tau_y + (self.Jzz - self.Jxx) * wx * wz) / self.Jyy
        wz_dot = (tau_z + (self.Jxx - self.Jyy) * wx * wy) / self.Jzz

        # 오일러각 운동학 (ZYX), 짐벌락(theta=±90도) 근처 특이점만 방어
        cos_theta = np.cos(theta)
        cos_theta = np.sign(cos_theta) * max(abs(cos_theta), 1e-3)
        phi_dot = wx + wy * np.sin(phi) * np.tan(theta) + wz * np.cos(phi) * np.tan(theta)
        theta_dot = wy * np.cos(phi) - wz * np.sin(phi)
        psi_dot = (wy * np.sin(phi) + wz * np.cos(phi)) / cos_theta

        # 오일러 적분 (dt=0.01s로 작게 잡아 안정성 확보; 필요시 RK4로 교체 가능)
        phi += phi_dot * self.dt
        theta += theta_dot * self.dt
        psi += psi_dot * self.dt
        if self.rotor_enabled:
            wx, wy, wz = self._integrate_with_rotor(rotor_omega0, rotor_omega1, wx, wy, wz, wx_dot, wy_dot, wz_dot)
        else:
            wx += wx_dot * self.dt
            wy += wy_dot * self.dt
            wz += wz_dot * self.dt

        self.state = np.array([phi, theta, psi, wx, wy, wz], dtype=np.float32)
        self.step_count += 1

        # 보상: 수평 유지(주 목표) + 각속도 억제 + 액션 과다사용 페널티(부드러운 제어 유도)
        reward = (
            -(phi**2 + theta**2 + 0.1 * psi**2)
            - 0.01 * (wx**2 + wy**2 + wz**2)
            - 0.001 * float(np.sum(np.square(action)))
        )

        crashed = abs(phi) > np.deg2rad(60) or abs(theta) > np.deg2rad(60)
        terminated = bool(crashed)
        truncated = self.step_count >= self.max_steps

        return self._obs(), float(reward), terminated, truncated, {"throttle": float(throttle)}

    def _limit_throttle(self, throttle_cmd):
        """스로틀 변화율 제한(#120). 이번 스텝에 실제로 쓸 스로틀(0-1)을 돌려준다.

        직전 스텝의 스로틀에서 ±throttle_slew_rate·dt 안으로 자른다. 올릴 때와 내릴 때 같은 제한이다.
        에피소드 첫 스텝은 자르지 않는다. 회전자와 같은 가정이다: 팬이 이미 그 스로틀로 돌고 있었다.
        명령이 그대로면 min(max(x, x − d), x + d) = x라서 스로틀을 고정한 결과는 제한이 없을 때와 비트 단위로 같다.
        """
        if self.step_count == 0 or self.throttle_applied is None or self.throttle_slew_rate is None:
            throttle = throttle_cmd
        else:
            d = self.throttle_slew_rate * self.dt
            throttle = min(max(throttle_cmd, self.throttle_applied - d), self.throttle_applied + d)
        self.throttle_applied = throttle
        return throttle

    def _advance_servo(self, alpha_cmd):
        """베인 서보 4개를 한 스텝(dt) 진행하고 스텝 끝 베인각(rad, 4벡터)을 돌려준다(#161). step()이 servo_enabled일 때만 부른다.

        모델은 tvc-retro-propulsion simulation/isaac/tvc_env/dynamics/actuator_servo.py(MIT, 커밋 971e24d)와 같은 꼴이다.
          1. 데드밴드: |α_cmd − α0| < deadband인 베인은 이 스텝에 움직이지 않는다. 데드밴드는 상태가 아니라 오차에 건다
          2. 1차 지연: 명령이 스텝 동안 일정하다고 보고 해석해로 진행한다. α1 = α_cmd + (α0 − α_cmd)·e^(−dt/tau).
             참고 구현은 전진 오일러(α0 + dt·e/tau)다. 해석해는 dt가 tau에 가까워도 명령각을 넘지 않는다(회전자와 같은 방법)
          3. 속도 제한: |α1 − α0| ≤ rate_max·dt
          4. 각도 제한: |α1| ≤ alpha_max. 명령각이 이미 이 안이라 지금은 걸리지 않는다
        에피소드 첫 스텝의 α0는 reset()이 둔 중립(0)이다.
        """
        a0 = self.vane_alpha
        target = np.where(np.abs(alpha_cmd - a0) < self.servo_deadband, a0, alpha_cmd)
        decay = np.exp(-self.dt / self.servo_tau) if self.servo_tau > 0 else 0.0
        d = self.servo_rate_max * self.dt
        a1 = np.clip(target + (a0 - target) * decay, a0 - d, a0 + d)
        self.vane_alpha = np.clip(a1, -self.alpha_max, self.alpha_max)
        return self.vane_alpha

    def _advance_rotor(self, throttle):
        """회전자 회전수 Ω를 한 스텝(dt) 진행하고 (스텝 시작 Ω0, 스텝 끝 Ω1)을 rad/s로 돌려준다(#86, #122).
        step()이 rotor_enabled일 때만 부른다.

        Ω는 목표 omega_max·throttle을 시상수 tau의 1차 지연으로 따라간다(가정, Jacobsen 2021 식 3.8 꼴).
        스텝 동안 목표가 일정하다고 보고 1차 지연의 해석해로 진행한다: Ω1 = Ωc + (Ω0 − Ωc)·e^(−dt/tau).
        에피소드 첫 스텝에서는 회전자가 이미 그 스로틀로 돌고 있었다고 둔다(가정). 구속 스탠드 시험은
        팬을 돌린 상태에서 자세 교란을 주기 때문이다. 그래서 첫 스텝의 반작용은 0이다.
        step()은 Ω1로 추력을 계산한다(#122). 그래서 tau = 0이면 추력이 회전자 항을 끈 경우와 같아진다.
        """
        omega_cmd = self.rotor_omega_max * float(throttle)
        if self.step_count == 0 or self.rotor_omega is None:
            self.rotor_omega = omega_cmd
        omega0 = self.rotor_omega
        decay = np.exp(-self.dt / self.rotor_tau) if self.rotor_tau > 0 else 0.0
        omega1 = omega_cmd + (omega0 - omega_cmd) * decay
        self.rotor_omega = omega1
        return omega0, omega1

    def _integrate_with_rotor(self, omega0, omega1, wx, wy, wz, wx_dot, wy_dot, wz_dot):
        """회전자 항을 넣어 바디 각속도를 한 스텝(dt) 적분한다(#86). step()이 rotor_enabled일 때만 부른다.

        식: 회전자를 품은 강체(gyrostat)의 각운동량 식
            J·ω̇ = τ − ω × (J·ω) − ω × h − dh/dt,   h = s·I_r·Ω·e_z
        반작용 휠 위성 식(Shahraki & Lessard 2024, arXiv:2409.19936 식 4b·4c)과 같은 꼴이다.
        τ와 ω × (J·ω) 항은 step()이 이미 wx_dot·wy_dot·wz_dot에 넣었다. 여기서는 회전자 항 두 개만 더한다.

        회전수 Ω0, Ω1: 이 스텝의 시작과 끝 회전수(rad/s). _advance_rotor()가 계산한다.
        반작용(z축): τz = −s·I_r·(Ω1 − Ω0)/dt. 이 스텝에서 회전자가 얻은 각운동량만큼 바디가 잃는다.
          베인 토크가 0이면 Jzz·ωz + s·I_r·Ω가 매 스텝 그대로다.
        자이로(x·y축): τx = −h·ωy, τy = +h·ωx. 이 항만 사다리꼴(중점) 규칙으로 적분한다.
          전진 오일러로 적분하면 스텝마다 회전 에너지가 (1 + (h·dt/J)²)배로 커져서 물리에 없는 발산이
          생긴다(명목값에서 5초 뒤 각속도 약 4.2배). tvc-retro-propulsion의 rotor_reaction.py도 같은 이유로
          중점 규칙을 쓴다. 사다리꼴 규칙은 자이로 항만 있을 때 ½·ωᵀJω를 그대로 지킨다.
          h는 이 스텝의 평균 회전수 (Ω0 + Ω1)/2로 계산한다.
        """
        s = self.rotor_spin_dir
        wz_new = wz + wz_dot * self.dt - s * self.rotor_inertia * (omega1 - omega0) / self.Jzz

        # 사다리꼴: Jxx·(wx1 − wx0) = dt·τx − a·(wy0 + wy1),  Jyy·(wy1 − wy0) = dt·τy + a·(wx0 + wx1),  a = h·dt/2
        h = s * self.rotor_inertia * 0.5 * (omega0 + omega1)
        a = 0.5 * self.dt * h
        bx = self.Jxx * (wx + wx_dot * self.dt) - a * wy
        by = self.Jyy * (wy + wy_dot * self.dt) + a * wx
        det = self.Jxx * self.Jyy + a * a
        wx_new = (self.Jyy * bx - a * by) / det
        wy_new = (self.Jxx * by + a * bx) / det
        return wx_new, wy_new, wz_new
