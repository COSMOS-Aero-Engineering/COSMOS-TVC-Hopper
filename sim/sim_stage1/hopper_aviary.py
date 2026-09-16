"""
PRJ-01 TVC 호퍼 — Stage 1 시뮬레이션 환경 (자세 안정화, 위치 구속)

Week 2 물리 실험의 "구속 스탠드"(M1, 만능조인트로 위치를 고정하고 회전만 자유롭게 두는
테스트 리그)와 1:1로 대응되는 환경. 즉 연습용 CartPole/Pendulum이 아니라, 실제로
우리 기체 구조·좌표계·베인 4개짜리 토크 방정식을 그대로 쓰는 "진짜" 첫 RL 환경.

⚠️ 아직 실험 A(EDF 추력곡선)·구속 스탠드 실측 전이라 params.yaml의 물리 상수
   (Jxx/Jyy/Jzz, CLalpha, CD0, Kf)는 PLACEHOLDER 상태. 지금 단계 목표는:
     "RL 학습 파이프라인이 우리 기체의 실제 상태/액션 구조에 맞춰 정상적으로 도는가"
   를 확인하는 것 — 절대적인 학습 성능 숫자 자체는 아직 의미 없음.
   Week 2에서 실측값이 나오는 대로 params.yaml만 교체하면 이 코드는 그대로 재사용됨.

상태(observation) = [phi, theta, psi, wx, wy, wz]  (자세각 rad, 바디 각속도 rad/s)
액션(action)       = [a1, a2, a3, a4, throttle]     (베인각 -1~1 정규화, 스로틀 0~1)
과제               = 초기 교란에서 수평(phi=theta=0)으로 되돌아와 유지하기
                     → 구속 스탠드 첫 실험(실험 B 이후, 자세 제어 첫 검증)과 같은 목표

도메인 랜덤화: params.yaml의 domain_rand 설정에 따라 매 reset()마다 Jxx/Jyy/Jzz,
베인 모멘트암(l,r), Kf, 무게중심-추력축 오프셋을 그 범위 안에서 무작위로 다시 뽑는다.
지금은 애초에 실측 전 PLACEHOLDER 값들이라 "정확한 한 점"을 맞추는 게 의미가 없고,
"이 근처 분포 전체"에서 버티는 정책을 학습해두는 게 나중에 실측값이 들어왔을 때도,
그리고 실제 기체로 이식할 때도(PID와의 정량 비교 실험, CLAUDE.md 참고) 더 안전하다.
"""
import os
from typing import Optional

import gymnasium as gym
import numpy as np
import yaml
from gymnasium import spaces


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
        self.nominal_r = p["vane_arm_r"]
        self.nominal_Kf = p["Kf"]
        self.CLalpha = p["CLalpha"]
        self.CD0 = p["CD0"]
        self.alpha_max = np.deg2rad(p["alpha_max_deg"])

        self.dr = p.get("domain_rand", {"enabled": False})

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
        # 상태: 자세각(rad) + 바디 각속도(rad/s, 대략적 상한으로 클리핑)
        high = np.array([np.pi, np.pi, np.pi, 50, 50, 50], dtype=np.float32)
        self.observation_space = spaces.Box(low=-high, high=high, dtype=np.float32)

        self.state = np.zeros(6, dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._randomize_episode_params()
        # 완전 수평에서 시작하면 학습할 게 없으므로 초기 교란을 줌
        # (구속 스탠드 실험에서 손으로 살짝 기울여 놓고 시작하는 것과 같은 셋업)
        phi, theta, psi = self.np_random.uniform(-0.3, 0.3, size=3)
        self.state = np.array([phi, theta, psi, 0.0, 0.0, 0.0], dtype=np.float32)
        self.step_count = 0
        return self.state.copy(), {}

    def _randomize_episode_params(self):
        """도메인 랜덤화 — 이번 에피소드에서 쓸 물리 상수를 명목값 주변에서 다시 뽑는다."""
        if not self.dr.get("enabled", False):
            self.Jxx, self.Jyy, self.Jzz = self.nominal_Jxx, self.nominal_Jyy, self.nominal_Jzz
            self.l, self.r = self.nominal_l, self.nominal_r
            self.Kf = self.nominal_Kf
            self.cg_offset_x = 0.0
            self.cg_offset_y = 0.0
            return

        def jitter(nominal, rel_range):
            # nominal * (1 + U(-rel_range, +rel_range))
            return nominal * (1.0 + self.np_random.uniform(-rel_range, rel_range))

        self.Jxx = jitter(self.nominal_Jxx, self.dr.get("Jxx_range", 0.0))
        self.Jyy = jitter(self.nominal_Jyy, self.dr.get("Jyy_range", 0.0))
        self.Jzz = jitter(self.nominal_Jzz, self.dr.get("Jzz_range", 0.0))

        arm_range = self.dr.get("vane_arm_range", 0.0)
        arm_scale = 1.0 + self.np_random.uniform(-arm_range, arm_range)
        self.l = self.nominal_l * arm_scale
        self.r = self.nominal_r * arm_scale

        self.Kf = jitter(self.nominal_Kf, self.dr.get("Kf_range", 0.0))

        # 무게중심-추력축 오프셋 → 추력 방향으로 일정한 잔류 토크(bias)를 만듦
        cg_offset_max_m = self.dr.get("cg_offset_mm", 0.0) / 1000.0
        self.cg_offset_x = self.np_random.uniform(-cg_offset_max_m, cg_offset_max_m)
        self.cg_offset_y = self.np_random.uniform(-cg_offset_max_m, cg_offset_max_m)

    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)
        a1, a2, a3, a4, throttle_norm = action
        alpha = np.array([a1, a2, a3, a4]) * self.alpha_max
        throttle = (throttle_norm + 1.0) / 2.0  # -1~1 -> 0~1

        # 스로틀 -> 추력 (PLACEHOLDER 스케일: omega_t_equiv는 실제 rpm이 아니라
        # throttle을 상대적 회전수로 환산한 임시 값. 실험 A 이후 실제 DShot 값 기준으로 교체)
        omega_t_equiv = throttle * 3000.0
        Ft = self.Kf * omega_t_equiv**2

        # 베인 선형 공력 근사 (modelling-notes-ch3.md §5)
        F1, F2, F3, F4 = self.CLalpha * Ft * alpha

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

        return self.state.copy(), float(reward), terminated, truncated, {}
