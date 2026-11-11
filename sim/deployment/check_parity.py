"""Compare SB3 predict against a compiled C++ actor on Stage 1 evaluation rollouts."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

from export_actor import load_actor, load_normalization, render_header

HERE = Path(__file__).resolve().parent
STAGE1 = HERE.parent / "sim_stage1"
sys.path.insert(0, str(STAGE1))
from hopper_aviary import HopperAttitudeEnv, OBS_NAMES
from pd_gate import EVAL_SEEDS

BENCH_HEADER = HERE.parents[1] / "firmware/cosmos/policy_bench/include/actor_data.h"
ATOL = 1e-5


def compile_host(directory, compiler):
    compiler = shutil.which(compiler) if compiler else next(
        (path for name in ("c++", "g++", "clang++", "cl") if (path := shutil.which(name))), None)
    if not compiler:
        raise ValueError("No host C++ compiler. Use a VS Developer Prompt or pass --cxx PATH.")
    exe = directory / ("parity.exe" if os.name == "nt" else "parity")
    if Path(compiler).stem.lower() == "cl":
        flags = ["/nologo", "/std:c++17", "/O2", "/EHsc", f"/I{directory}", f"/Fe:{exe}"]
    else:
        flags = ["-std=c++17", "-O2", "-I", str(directory), "-o", str(exe)]
    subprocess.run([compiler, *flags, str(HERE / "host.cpp")], cwd=directory, check=True)
    return exe


def evaluation_rows(env, model, norm, seeds):
    observations, predictions, lengths = [], [], []
    for seed in seeds:
        obs, _ = env.reset(seed=seed)
        start = len(observations)
        while True:
            inputs = norm.normalize_obs(obs) if norm is not None else obs
            action, _ = model.predict(inputs, deterministic=True)
            observations.append(obs.copy())
            predictions.append(action.copy())
            obs, _, terminated, truncated, _ = env.step(action)
            if terminated or truncated:
                break
        lengths.append(len(observations) - start)
    return np.asarray(observations), np.asarray(predictions), lengths


def compare(directory, exe, obs, expected, lengths, seeds):
    raw = directory / "obs.f32"
    result = directory / "actions.f32"
    if not np.isfinite(obs).all() or not np.isfinite(expected).all():
        raise ValueError("Non-finite observation or Python prediction")
    obs.astype(np.float32).tofile(raw)
    subprocess.run([exe, raw, result], check=True)
    if result.stat().st_size != expected.size * 4:
        raise ValueError("C++ returned the wrong number of actions")
    actual = np.fromfile(result, np.float32).reshape(expected.shape)
    if not np.isfinite(actual).all() or np.any(np.abs(actual) > 1):
        raise ValueError("Invalid C++ action")
    error = np.abs(expected - actual)
    row, channel = np.unravel_index(error.argmax(), error.shape)
    ends = np.cumsum(lengths)
    episode = ends.searchsorted(row, side="right")
    step = row - (ends[episode - 1] if episode else 0)
    print(f"seeds={seeds[0]}..{seeds[-1]} observations={len(obs)} action_values={error.size}")
    print(f"max_abs_per_action={error.max(axis=0)}")
    print(f"max_abs={error[row, channel]:.9g} seed={seeds[episode]} step={step} "
          f"action_index={channel} atol={ATOL:g}")
    if error[row, channel] > ATOL:
        raise ValueError("C++ prediction exceeded absolute tolerance")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=STAGE1 / "hopper_attitude_ppo.zip")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--raw-obs", action="store_true", help="model was trained on raw Stage 1 observations")
    group.add_argument("--vecnormalize", type=Path, help="matching trusted VecNormalize.save file")
    parser.add_argument("--episodes", type=int, default=len(EVAL_SEEDS))
    parser.add_argument("--output", type=Path, default=BENCH_HEADER)
    parser.add_argument("--cxx", help="path or name of host C++ compiler")
    args = parser.parse_args()
    if not 1 <= args.episodes <= len(EVAL_SEEDS):
        parser.error(f"--episodes must be in [1,{len(EVAL_SEEDS)}]")
    seeds = EVAL_SEEDS[:args.episodes]
    with closing(HopperAttitudeEnv()) as env, tempfile.TemporaryDirectory() as tmp:
        if OBS_NAMES != ("phi", "theta", "psi", "wx", "wy", "wz", "throttle") or not env.dr["enabled"]:
            raise ValueError("Expected Stage 1 observation order and randomized evaluation")
        model, digest = load_actor(args.model, env)
        norm, normalization_id = load_normalization(args.vecnormalize, args.raw_obs, digest, env.observation_space)
        header = render_header(model, digest, norm, normalization_id)
        print(f"model_sha256={digest} normalization={normalization_id}", flush=True)
        directory = Path(tmp)
        (directory / "actor_data.h").write_text(header, encoding="ascii")
        exe = compile_host(directory, args.cxx)
        obs, actions, lengths = evaluation_rows(env, model, norm, seeds)
        compare(directory, exe, obs, actions, lengths, seeds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as staged:
        staged.write(header.encode("ascii"))
    try:
        os.replace(staged.name, args.output)
    finally:
        Path(staged.name).unlink(missing_ok=True)
    print(f"PASS: exported {args.output}")


if __name__ == "__main__":
    main()
