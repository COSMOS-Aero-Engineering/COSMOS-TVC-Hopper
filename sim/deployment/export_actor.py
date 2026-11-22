"""Export the deterministic Stage 1 actor parameters for actor.hpp."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import pickle
import sys

import numpy as np
from gymnasium.spaces import Box
from stable_baselines3 import PPO
from stable_baselines3.common.distributions import DiagGaussianDistribution
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.torch_layers import FlattenExtractor, MlpExtractor
from stable_baselines3.common.vec_env import VecNormalize
from torch import float32, nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim_stage1"))
from policy_io import FIXED_THROTTLE_NORM, ActionAdapter, read_meta, sidecar  # noqa: E402
from hopper_aviary import OBS_NAMES  # noqa: E402

# Tracked zip trained on the raw HopperAttitudeEnv.
# and the #230 presentation model (4 vanes, throttle fixed at 1.0; see its .json).
RAW_FIXTURES = {
    "0a40036028c119f0f12b4ec580f1956244599d9790e6bf877ee9d319da92f1b2": "hopper_attitude_ppo_230.zip",
}
# Policy output layouts the C++ actor reproduces. mixer3 needs the policy_io.MIXER
# step after the network, which actor.hpp does not implement.
SUPPORTED_ACTIONS = ("learned", "vanes4")


def load_actor(path, env):
    """Return (model, sha256, action kind, declared VecNormalize).

    The kind and VecNormalize flag come from the model's .json (policy_io). The flag is
    None when there is no .json; then the caller must declare the observation contract.
    A .json with "vecnormalize": false declares raw observations, as in policy_io.load_policy.
    """
    meta = read_meta(path)
    declared = None
    if sidecar(path, ".json").exists():
        declared = meta.get("vecnormalize", False)
        if not isinstance(declared, bool):
            raise ValueError(f"Model json 'vecnormalize' must be true or false, got {declared!r}")
    if "action" not in meta:
        raise ValueError("Model json has no 'action' layout")
    kind = meta["action"]
    if kind not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported action layout {kind!r}; supported: {SUPPORTED_ACTIONS}")
    data = Path(path).read_bytes()
    model = PPO.load(BytesIO(data), device="cpu")
    policy = model.policy
    if not (type(policy) is ActorCriticPolicy and
            type(policy.pi_features_extractor) is FlattenExtractor and
            type(policy.mlp_extractor) is MlpExtractor and
            type(policy.action_dist) is DiagGaussianDistribution and not policy.squash_output):
        raise ValueError("Expected SB3 MlpPolicy, FlattenExtractor and unsquashed diagonal Gaussian")
    outputs = ActionAdapter.SIZES[kind]
    if not (isinstance(model.observation_space, Box) and
            model.observation_space == env.observation_space and model.observation_space.shape == (len(OBS_NAMES),) and
            model.observation_space.dtype == np.float32 and isinstance(model.action_space, Box) and
            model.action_space.shape == (outputs,) and model.action_space.dtype == np.float32 and
            np.all(model.action_space.low == -1) and np.all(model.action_space.high == 1)):
        raise ValueError(f"Expected the Stage 1 float32 observation Box and {outputs} actions "
                         f"in [-1,1] for action layout {kind!r}")
    model_hash = sha256(data).hexdigest()
    if declared and model_hash in RAW_FIXTURES:
        raise ValueError("Model json says VecNormalize, but this tracked zip was trained on raw observations")
    return model, model_hash, kind, declared


def load_normalization(path, raw, model_hash, observation_space, declared=None, model_path=None):
    """declared: the .json vecnormalize flag from load_actor, or None without a .json.

    When the .json declares VecNormalize, the statistics are <model>.vecnormalize.pkl next to
    the model (policy_io.load_policy reads the same file). --vecnormalize may only name it.
    """
    if declared is True and model_path is not None:
        own = sidecar(model_path, ".vecnormalize.pkl")
        if path is None:
            path = own
        elif Path(path).resolve() != own.resolve():
            raise ValueError(f"Model json says VecNormalize; its statistics are {own.name}, not {Path(path).name}")
    if declared is True and path is None:
        raise ValueError("Model json says VecNormalize: supply its --vecnormalize FILE")
    if declared is False and path is not None:
        raise ValueError("Model json says raw observations: drop --vecnormalize")
    if path is None:
        if not raw and declared is not False and model_hash not in RAW_FIXTURES:
            raise ValueError("Unknown model: declare --raw-obs or supply its --vecnormalize FILE")
        return None, "raw"
    if model_hash in RAW_FIXTURES:
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
    if (rms.mean.shape != (len(OBS_NAMES),) or rms.var.shape != (len(OBS_NAMES),) or
            not np.isfinite(rms.mean).all() or not np.isfinite(rms.var).all() or
            np.any(rms.var < 0) or not np.isfinite(norm.epsilon) or norm.epsilon <= 0 or
            not np.isfinite(norm.clip_obs) or norm.clip_obs <= 0):
        raise ValueError("Invalid frozen observation statistics")
    return norm, sha256(data).hexdigest()


def cpp_float(value):
    """Nine significant digits round-trip a binary32 value."""
    return f"{value:.8e}f"


def cpp_array(name, values):
    if values.ndim == 1:
        body = ", ".join(map(cpp_float, values))
    else:
        body = ",\n".join("    {" + ", ".join(map(cpp_float, row)) + "}" for row in values)
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


def render_header(model, model_hash, norm, normalization_id, kind):
    policy = model.policy
    hidden = list(policy.mlp_extractor.policy_net)
    if list(map(type, hidden)) != [nn.Linear, nn.Tanh, nn.Linear, nn.Tanh]:
        raise ValueError("Expected two Linear + Tanh hidden layers")
    layers = [hidden[0], hidden[2], policy.action_net]
    if any(type(layer) is not nn.Linear or layer.bias is None for layer in layers):
        raise ValueError("Expected three biased Linear layers")
    widths = [layers[0].in_features] + [layer.out_features for layer in layers]
    if (kind not in SUPPORTED_ACTIONS or widths[0] != 7 or widths[-1] != ActionAdapter.SIZES[kind] or
            [l.in_features for l in layers] != widths[:-1]):
        raise ValueError("Actor layer widths do not match the Stage 1 contract")
    lines = ["// Generated by export_actor.py; inference parity fixture.",
             "#pragma once", "#include <cstddef>", "namespace actor {",
             f'constexpr char kModelHash[] = "{model_hash}";',
             f'constexpr char kNormalization[] = "{normalization_id}";',
             f'constexpr char kActionLayout[] = "{kind}";']
    if kind == "vanes4":
        # policy_io.to_env_action: env action = [vane1..4, kFixedThrottleNorm].
        lines.append(f"constexpr float kFixedThrottleNorm = {cpp_float(FIXED_THROTTLE_NORM)};")
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
