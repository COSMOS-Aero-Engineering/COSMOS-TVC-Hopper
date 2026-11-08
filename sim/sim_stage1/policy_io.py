"""PPO 행동 구조와 모델 파일 읽기(#230). 학습(ppo_ablation.py)과 평가(pd_gate.py, compare_metrics.py)가 같이 쓴다.

행동 구조(ACTIONS). 환경(HopperAttitudeEnv)의 행동은 늘 [a1, a2, a3, a4, throttle_norm] 5개다.
정책 출력을 이 5개로 바꾸는 방법만 다르다.
  learned  정책이 5개를 그대로 낸다. 스로틀도 정책이 정한다. #230 전 train.py와 같다
  vanes4   정책이 베인 4개만 낸다. 스로틀은 1.0(100 %)으로 고정한다. pd_gate.pd()와 같은 스로틀이다
  mixer3   정책이 롤·피치·요 요구 [u_r, u_p, u_y] 3개를 낸다. 스로틀은 1.0으로 고정한다. MIXER로 베인 4개에 나눈다

믹서(MIXER). 토크 식은 hopper_aviary.py step()의
  tau_x = (F1 + F3)·l,  tau_y = -(F2 + F4)·l,  tau_z = (F1 - F2 - F3 + F4)·r
이다. 롤 요구는 베인 1·3, 피치 요구는 베인 2·4에 같은 부호로 준다. pd_gate.pd()의 [ux, uy, ux, uy]와 같은 부호 규약이다.
요 요구는 a1 - a2 - a3 + a4 = 4·u_y가 되게 준다. 결과를 베인마다 [-1, 1]로 자른다. 자르면 축끼리 섞일 수 있다.
  a1 = u_r + u_y,  a2 = u_p - u_y,  a3 = u_r - u_y,  a4 = u_p + u_y

모델 파일. <이름>.zip 옆에 <이름>.json(행동 구조, 학습 조건)과, 관측 정규화를 썼으면 <이름>.vecnormalize.pkl을 둔다.
json이 없으면 #230 전 모델(learned, 정규화 없음)로 읽는다. 저장소의 hopper_attitude_ppo.zip이 그렇다.
VecNormalize 통계는 SB3 문서대로 VecNormalize.load()로 읽고 training=False로 둔다(평가 중 통계를 바꾸지 않는다).
"""
import json
from pathlib import Path

import gymnasium as gym
import numpy as np

from hopper_aviary import HopperAttitudeEnv

ACTIONS = ("learned", "vanes4", "mixer3")
FIXED_THROTTLE_NORM = 1.0   # 정규화 스로틀 1.0 = 스로틀 100 %. pd_gate.pd()와 같다
MIXER = np.array([[1.0, 0.0, 1.0],     # a1 = u_r + u_y
                  [0.0, 1.0, -1.0],    # a2 = u_p - u_y
                  [1.0, 0.0, -1.0],    # a3 = u_r - u_y
                  [0.0, 1.0, 1.0]])    # a4 = u_p + u_y


def to_env_action(kind, action):
    """정책 출력 → 환경 행동 5개(float32)."""
    a = np.asarray(action, dtype=np.float64)
    if kind == "learned":
        return a.astype(np.float32)
    if kind == "vanes4":
        vanes = a
    elif kind == "mixer3":
        vanes = np.clip(MIXER @ a, -1.0, 1.0)
    else:
        raise ValueError(f"행동 구조 {kind!r}가 없다. 받는 값: {ACTIONS}")
    return np.append(vanes, FIXED_THROTTLE_NORM).astype(np.float32)


class ActionAdapter(gym.ActionWrapper):
    """정책 행동 공간을 kind에 맞게 바꾼다. learned이면 환경 행동 공간 그대로다."""

    SIZES = {"learned": 5, "vanes4": 4, "mixer3": 3}

    def __init__(self, env, kind):
        super().__init__(env)
        if kind not in ACTIONS:
            raise ValueError(f"행동 구조 {kind!r}가 없다. 받는 값: {ACTIONS}")
        self.kind = kind
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(self.SIZES[kind],), dtype=np.float32)

    def action(self, action):
        return to_env_action(self.kind, action)


def sidecar(model_path, suffix):
    """<이름>.zip → <이름><suffix>. 예: ppo.zip → ppo.json"""
    p = Path(model_path)
    return p.with_name(p.stem + suffix) if p.suffix == ".zip" else p.with_name(p.name + suffix)


def read_meta(model_path):
    """모델 옆 json을 읽는다. 없으면 #230 전 모델의 값."""
    path = sidecar(model_path, ".json")
    if not path.exists():
        return {"action": "learned", "vecnormalize": False}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_policy(model_path):
    """모델 파일 → 관측(환경 7차원) → 환경 행동 5개 함수. 결정적 행동(deterministic=True)을 쓴다."""
    from stable_baselines3 import PPO

    meta = read_meta(model_path)
    kind = meta["action"]
    model = PPO.load(str(model_path), device="cpu")
    n_model = int(model.observation_space.shape[0])
    n_env = int(HopperAttitudeEnv().observation_space.shape[0])
    if n_model != n_env:
        raise ValueError(f"모델 관측 {n_model}차원, 환경 관측 {n_env}차원: 차원이 같아야 한다. "
                         "python train.py로 다시 학습하거나 그 모델을 만든 커밋에서 평가할 것.")
    n_act = int(model.action_space.shape[0])
    if n_act != ActionAdapter.SIZES[kind]:
        raise ValueError(f"모델 행동 {n_act}차원인데 json의 행동 구조 {kind!r}는 {ActionAdapter.SIZES[kind]}차원이다.")

    normalize = None
    if meta.get("vecnormalize"):
        from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
        stats = sidecar(model_path, ".vecnormalize.pkl")
        if not stats.exists():
            raise FileNotFoundError(f"json이 관측 정규화를 쓴다고 하는데 통계 파일이 없다: {stats}")
        vn = VecNormalize.load(str(stats), DummyVecEnv([lambda: ActionAdapter(HopperAttitudeEnv(), kind)]))
        vn.training = False
        vn.norm_reward = False
        normalize = vn.normalize_obs

    def act(obs):
        o = obs if normalize is None else normalize(np.asarray(obs, dtype=np.float32)[None])[0]
        return to_env_action(kind, model.predict(o, deterministic=True)[0])

    return act
