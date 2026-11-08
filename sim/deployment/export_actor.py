"""Export the deterministic Stage 1 actor parameters for actor.hpp."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import pickle

import numpy as np
from gymnasium.spaces import Box
from stable_baselines3 import PPO
from stable_baselines3.common.distributions import DiagGaussianDistribution
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.torch_layers import FlattenExtractor, MlpExtractor
from stable_baselines3.common.vec_env import VecNormalize
from torch import float32, nn

# train.py trained this tracked zip on the raw HopperAttitudeEnv.
RAW_FIXTURE = "9fa28231e3a9995d693fd9241397044f0b846c4e005b9c6bd9d8f6324b7a78b2"


def load_actor(path, env):
    data = Path(path).read_bytes()
    model = PPO.load(BytesIO(data), device="cpu")
    policy = model.policy
    if not (type(policy) is ActorCriticPolicy and
            type(policy.pi_features_extractor) is FlattenExtractor and
            type(policy.mlp_extractor) is MlpExtractor and
            type(policy.action_dist) is DiagGaussianDistribution and not policy.squash_output):
        raise ValueError("Expected SB3 MlpPolicy, FlattenExtractor and unsquashed diagonal Gaussian")
    if not (isinstance(model.observation_space, Box) and
            model.observation_space == env.observation_space and model.observation_space.shape == (7,) and
            model.observation_space.dtype == np.float32 and model.action_space == env.action_space and
            model.action_space.shape == (5,) and model.action_space.dtype == np.float32 and
            np.all(model.action_space.low == -1) and np.all(model.action_space.high == 1)):
        raise ValueError("Expected the Stage 1 float32 observation Box and 5 actions in [-1,1]")
    return model, sha256(data).hexdigest()


def load_normalization(path, raw, model_hash, observation_space):
    if path is None:
        if not raw and model_hash != RAW_FIXTURE:
            raise ValueError("Unknown model: declare --raw-obs or supply its --vecnormalize FILE")
        return None, "raw"
    if model_hash == RAW_FIXTURE:
        raise ValueError("The tracked checkpoint was trained on raw observations")
    # VecNormalize.save pickles the wrapper without its environment. normalize_obs
    # uses only these frozen statistics; no vectorized rollout or rewards are needed.
    data = Path(path).read_bytes()
    norm = pickle.loads(data)
    if type(norm) is not VecNormalize or not norm.norm_obs or norm.observation_space != observation_space:
        raise ValueError("Expected VecNormalize with observation normalization on the Stage 1 Box")
    norm.training = False
    norm.norm_reward = False
    rms = norm.obs_rms
    if (rms.mean.shape != (7,) or rms.var.shape != (7,) or
            not np.isfinite(rms.mean).all() or not np.isfinite(rms.var).all() or
            np.any(rms.var < 0) or not np.isfinite(norm.epsilon) or norm.epsilon <= 0 or
            not np.isfinite(norm.clip_obs) or norm.clip_obs <= 0):
        raise ValueError("Invalid frozen observation statistics")
    return norm, sha256(data).hexdigest()


def cpp_array(name, values):
    """Nine significant digits round-trip each binary32 parameter."""
    def literal(value):
        return f"{value:.8e}f"

    if values.ndim == 1:
        body = ", ".join(map(literal, values))
    else:
        body = ",\n".join("    {" + ", ".join(map(literal, row)) + "}" for row in values)
    dims = "".join(f"[{n}]" for n in values.shape)
    return f"constexpr float {name}{dims} = {{\n{body}\n}};"


def normalizer_cpp(norm):
    if norm is None:
        return "inline float normalize(std::size_t, float x) { return x; }"
    def doubles(values):
        return ", ".join(format(x, ".17g") for x in values)
    mean = doubles(norm.obs_rms.mean)
    std = doubles(np.sqrt(norm.obs_rms.var + norm.epsilon))
    return f"""inline float normalize(std::size_t i, float x) {{
    static constexpr double mean[kInputs] = {{{mean}}};
    static constexpr double stddev[kInputs] = {{{std}}};
    constexpr double limit = {norm.clip_obs:.17g};
    double z = (static_cast<double>(x) - mean[i]) / stddev[i];
    if (z < -limit) z = -limit;
    if (z > limit) z = limit;
    return static_cast<float>(z);
}}"""


def render_header(model, model_hash, norm, normalization_id):
    policy = model.policy
    hidden = list(policy.mlp_extractor.policy_net)
    if list(map(type, hidden)) != [nn.Linear, nn.Tanh, nn.Linear, nn.Tanh]:
        raise ValueError("Expected two Linear + Tanh hidden layers")
    layers = [hidden[0], hidden[2], policy.action_net]
    if any(type(layer) is not nn.Linear or layer.bias is None for layer in layers):
        raise ValueError("Expected three biased Linear layers")
    widths = [layers[0].in_features] + [layer.out_features for layer in layers]
    if widths[0] != 7 or widths[-1] != 5 or [l.in_features for l in layers] != widths[:-1]:
        raise ValueError("Actor layer widths do not match the Stage 1 contract")
    lines = ["// Generated by export_actor.py; inference parity fixture.",
             "#pragma once", "#include <cstddef>", "namespace actor {",
             f'constexpr char kModelHash[] = "{model_hash}";',
             f'constexpr char kNormalization[] = "{normalization_id}";']
    for name, width in zip(["Inputs", "Hidden1", "Hidden2", "Outputs"], widths):
        lines.append(f"constexpr std::size_t k{name} = {width};")
    lines.append(normalizer_cpp(norm))
    for i, layer in enumerate(layers, 1):
        for prefix, param in [("w", layer.weight), ("b", layer.bias)]:
            if param.dtype != float32:
                raise ValueError("Only float32 actor parameters are supported")
            values = param.detach().cpu().numpy()
            if not np.isfinite(values).all():
                raise ValueError("Non-finite actor parameter")
            lines.append(cpp_array(f"{prefix}{i}", values))
    return "\n".join(lines + ["}  // namespace actor", ""])
