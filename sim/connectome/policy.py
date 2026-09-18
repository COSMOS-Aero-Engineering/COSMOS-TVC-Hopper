"""커넥톰 제약 정책망 — SB3의 특징 추출기(features extractor)로 꽂는 부분.

핵심 아이디어는 한 줄이다:

    커넥톰 = 신경망의 '연결 구조'로 고정 · 가중치 크기만 학습한다.

FlyWire가 알려주는 건 "어느 뉴런이 어느 뉴런에 몇 개의 시냅스로 붙어 있는가"뿐이다.
시냅스 세기·시상수는 측정된 값이 없다. 그래서 커넥톰을 그대로 제어기로 쓸 수는 없고,
연결이 있는 자리에만 파라미터를 두고 그 크기를 강화학습으로 찾는다. 연결이 없는 자리는
학습을 아무리 해도 영원히 0이다 — 이게 "커넥톰 제약"의 정의다.
(flyvis: Lappalainen et al., Nature 2024 / FlyGM: arXiv 2602.17997 이 쓰는 방식과 같다.)

왜 스파이킹(LIF)이 아니라 발화율(rate) 모델인가
-----------------------------------------------
스파이크는 미분이 안 돼서 PPO의 역전파가 붙지 않는다. 전뇌 LIF 모델(Shiu et al.,
Nature 2024)은 "자극을 주고 어디로 퍼지나 보는" 용도지 학습용이 아니다. 우리는 정책을
'학습'시켜야 하므로 미분 가능한 발화율 모델을 쓴다. flyvis가 정확히 같은 선택을 했다.

왜 상태를 매 스텝 리셋하는가 (= RecurrentPPO가 필요 없다)
--------------------------------------------------------
우리 관측 [phi, theta, psi, wx, wy, wz]는 완전관측 마르코프 상태다. 자세와 각속도가 다
보이므로 뉴런에 과거를 기억시킬 이유가 없다. 그래서 매 환경 스텝마다 발화율을 0에서
시작해 n_settle 번 정착시키고 버린다. 덕분에 sb3-contrib의 RecurrentPPO 없이 기본
PPO를 그대로 쓸 수 있고, 학습 안정성도 훨씬 낫다.
(Stage 2에서 위치 구속을 풀어 부분관측이 되면 그때 이 결정을 다시 봐야 한다.)

SB3에 꽂는 법
-------------
    model = PPO("MlpPolicy", env, policy_kwargs=dict(
        features_extractor_class=ConnectomeExtractor,
        features_extractor_kwargs=dict(graph_path="graphs/synthetic.npz"),
        net_arch=dict(pi=[], vf=[64, 64]),
    ))

net_arch의 pi=[] 가 핵심이다. 정책 쪽에는 은닉층을 두지 않아서, 실제로 배포되는 경로가
    관측 -> 커넥톰 -> (하강뉴런 발화율) -> 선형 readout -> 액션
하나로 끝난다. 여기에 MLP를 얹으면 "커넥톰이 제어했다"고 말할 수 없게 된다.
가치망(vf)은 MLP를 그대로 둔다 — 학습에만 쓰이고 기체에 올라가지 않기 때문이다.
(SB3는 기본적으로 특징 추출기를 pi/vf가 공유하므로, 가치 손실의 기울기도 커넥톰
가중치로 흘러든다. 표준 설정이고 문제는 없지만, 알고 있어야 하는 사실이라 적어둔다.)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import ConnectomeGraph  # noqa: E402


def _inverse_softplus(x: torch.Tensor) -> torch.Tensor:
    """softplus(y) = x 가 되는 y. 초기 가중치를 그대로 재현하려고 쓴다."""
    return torch.log(torch.expm1(x.clamp(min=1e-4)))


class ConnectomeExtractor(BaseFeaturesExtractor):
    """관측 -> 커넥톰 발화율 dynamics -> 하강뉴런(DN) 발화율.

    dynamics (오일러 적분):
        I[sensory] = enc(obs_normalized)
        r <- r + alpha * ( -r + relu( W r + I + b ) )      n_settle 번
        features = r[motor] * out_scale

    alpha 를 dt/tau 로 두지 않고 그냥 숫자로 노출한 이유: 처음엔 dt=2ms, tau=20ms 같은
    '생물학적'인 값을 넣었는데, 그러면 환경 한 스텝(10ms) 안에 신호가 감각뉴런에서
    하강뉴런까지 도달조차 못 한다(홉마다 시상수만큼 지연되므로). 실제로 재보니 출력이
    1e-7 이었다. 여기서 하는 계산은 '10ms 동안의 실제 막전위 궤적'이 아니라 '이 배선이
    이 입력에 대해 수렴하는 정상상태'를 읽는 것이므로, 물리 시간 대신 수렴에 필요한
    반복 횟수로 보는 게 맞다 (flyvis 도 정상상태 응답을 이렇게 다룬다). 대신 이건
    근사이고, Stage 2에서 과도응답까지 보려면 이 결정을 다시 봐야 한다.

        W = edge_sign * softplus(w_raw) * gain
            - edge_sign : 학습 안 함 (신경전달물질로 결정, ACh +1 / GABA,Glu -1)
            - w_raw     : 학습함 (연결이 있는 자리에만 존재)
            - gain      : 전역 스케일 하나. 발산 방지용 여유를 학습이 조금씩 조절한다
    """

    def __init__(
        self,
        observation_space: spaces.Box,
        graph_path: str,
        n_settle: int = 20,
        alpha: float = 0.5,
        initial_gain: float = 0.9,
    ):
        g = ConnectomeGraph.load(_resolve(graph_path))
        super().__init__(observation_space, features_dim=int(g.motor_idx.shape[0]))

        self.graph_meta = g.meta
        self.n_nodes = g.n_nodes
        self.n_settle = int(n_settle)
        self.alpha = float(alpha)

        self.register_buffer("ei_pre", torch.as_tensor(g.edge_index[0], dtype=torch.long))
        self.register_buffer("ei_post", torch.as_tensor(g.edge_index[1], dtype=torch.long))
        self.register_buffer("edge_sign", torch.as_tensor(g.edge_sign, dtype=torch.float32))
        self.register_buffer("sensory_idx", torch.as_tensor(g.sensory_idx, dtype=torch.long))
        self.register_buffer("motor_idx", torch.as_tensor(g.motor_idx, dtype=torch.long))

        # 관측 정규화. phi/theta/psi 는 rad(최대 pi)인데 각속도는 최대 50 rad/s 라서,
        # 그대로 넣으면 각속도가 입력 전류를 완전히 지배해 자세각이 거의 안 보인다.
        high = np.asarray(observation_space.high, dtype=np.float32)
        high = np.where(np.isfinite(high) & (high > 0), high, 1.0).astype(np.float32)
        self.register_buffer("obs_scale", torch.as_tensor(high))

        w0 = torch.as_tensor(g.edge_w, dtype=torch.float32)
        self.w_raw = nn.Parameter(_inverse_softplus(w0))
        self.gain_raw = nn.Parameter(_inverse_softplus(torch.tensor(float(initial_gain))))
        self.bias = nn.Parameter(torch.zeros(self.n_nodes))
        self.enc = nn.Linear(int(observation_space.shape[0]), int(g.sensory_idx.shape[0]))

        # 출력 보정 — 이게 없으면 학습이 안 된다.
        #
        # 감각뉴런에서 하강뉴런까지는 여러 홉을 지나는데, 홉마다 가중치(1 미만)가 곱해져서
        # 출력이 아주 작아진다. 합성 CX 그래프에서 실측해보니 DN 발화율이 1e-3 수준이었다.
        # 이 값이 SB3의 선형 액션 헤드로 들어가면 행동 평균이 사실상 0에 붙박이고, 기울기도
        # 같은 비율로 작아져서 PPO가 몇십만 스텝을 돌려도 못 벗어난다.
        #
        # 그래서 초기화 시점에 무작위 관측을 한 번 흘려보고, 출력 RMS가 1이 되는 상수를
        # 버퍼에 저장해 곱한다(LSUV 계열의 데이터 기반 초기화와 같은 발상). 학습되는 값이
        # 아니라 그래프마다 한 번 정해지는 상수라서, 그래프가 커지거나 홉 수가 달라져도
        # 사람이 손으로 스케일을 다시 맞출 필요가 없다. 고정 시드를 써서 재현도 된다.
        self.register_buffer("out_scale", torch.ones(()))
        with torch.no_grad():
            gen = torch.Generator().manual_seed(0)
            probe = (torch.rand(256, int(observation_space.shape[0]), generator=gen) * 2 - 1)
            rms = self._settle(probe * self.obs_scale).pow(2).mean().sqrt()
            self.out_scale.fill_(1.0 / float(rms.clamp(min=1e-12)))

    # -- 학습되는 가중치 ----------------------------------------------------
    def edge_weights(self) -> torch.Tensor:
        return self.edge_sign * F.softplus(self.w_raw) * F.softplus(self.gain_raw)

    def _settle(self, observations: torch.Tensor) -> torch.Tensor:
        """정착 루프를 돌려 하강뉴런 발화율을 낸다 (출력 보정 전)."""
        b = observations.shape[0]
        w = self.edge_weights()

        current = torch.zeros(b, self.n_nodes, device=observations.device,
                              dtype=observations.dtype)
        current.index_copy_(1, self.sensory_idx, self.enc(observations / self.obs_scale))
        current = current + self.bias

        rate = torch.zeros_like(current)
        for _ in range(self.n_settle):
            # 희소 전파: syn[:, post[e]] += rate[:, pre[e]] * w[e]
            syn = torch.zeros_like(rate)
            syn.index_add_(1, self.ei_post, rate.index_select(1, self.ei_pre) * w)
            rate = rate + self.alpha * (-rate + F.relu(syn + current))

        return rate.index_select(1, self.motor_idx)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        return self._settle(observations) * self.out_scale

    # -- 보고용 ------------------------------------------------------------
    def describe(self) -> str:
        deployed = self.w_raw.numel() + self.bias.numel() + sum(
            p.numel() for p in self.enc.parameters()
        ) + 1
        return (
            f"뉴런 {self.n_nodes} · 학습 가중치 {self.w_raw.numel()} · "
            f"정착 {self.n_settle}스텝 · alpha={self.alpha:.3f} · "
            f"기체에 올라갈 파라미터 {deployed}개 (float32 기준 {deployed * 4 / 1024:.0f} KB)"
        )


def _resolve(path: str) -> Path:
    """상대경로는 이 파일 기준으로도 찾아본다.

    학습 스크립트를 sim_stage1/ 에서 돌리든 connectome/ 에서 돌리든 같은 --graph 인자가
    통해야 한다. 안 그러면 "내 PC에선 되는데" 가 바로 생긴다.
    """
    p = Path(path)
    if p.exists():
        return p
    here = Path(__file__).resolve().parent / path
    if here.exists():
        return here
    return p  # 없으면 ConnectomeGraph.load 가 안내 메시지와 함께 죽는다


def make_policy_kwargs(graph_path: str, n_settle: int = 20, vf_arch=(64, 64)) -> dict:
    """PPO(..., policy_kwargs=make_policy_kwargs("graphs/synthetic.npz")) 로 쓴다."""
    return dict(
        features_extractor_class=ConnectomeExtractor,
        features_extractor_kwargs=dict(graph_path=graph_path, n_settle=n_settle),
        net_arch=dict(pi=[], vf=list(vf_arch)),
    )
