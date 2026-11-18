"""Regression: a saved wrapper changes the inputs even if the actor zip loads alone.

ActionLayoutTest checks that the exporter reads the policy_io .json beside the zip and
refuses layouts the C++ actor does not reproduce.
"""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from check_parity import HopperAttitudeEnv, compare, compile_host
from export_actor import load_actor, load_normalization, render_header
from policy_io import ActionAdapter


class NormalizedActorTest(unittest.TestCase):
    def test_frozen_stats_and_clipped_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            wrapper = VecNormalize(DummyVecEnv([HopperAttitudeEnv]), clip_obs=0.5)
            try:
                wrapper.seed(123)
                wrapper.reset()
                for _ in range(4):
                    wrapper.step(np.zeros((1, 5), dtype=np.float32))
                model = PPO("MlpPolicy", wrapper, seed=42, device="cpu")
                # Force both action bounds and keep three outputs sensitive to observations.
                with torch.no_grad():
                    model.policy.action_net.bias[:2].copy_(torch.tensor([-2., 2.]))
                model.save(directory / "model.zip")
                wrapper.save(directory / "stats.pkl")
                space = wrapper.observation_space
            finally:
                wrapper.close()
            with HopperAttitudeEnv() as env:
                model, digest, kind, _ = load_actor(directory / "model.zip", env)
                with self.assertRaisesRegex(ValueError, "declare --raw-obs"):
                    load_normalization(None, False, digest, env.observation_space)
            norm, norm_id = load_normalization(directory / "stats.pkl", False, digest, space)
            raw = np.array([[0, 0, 0, 0, 0, 0, 1], [1, -1, 0.5, 2, -4, 3, 0]], dtype=np.float32)
            normalized = norm.normalize_obs(raw)
            self.assertEqual(np.max(np.abs(normalized)), 0.5)
            expected = model.predict(normalized, deterministic=True)[0]
            np.testing.assert_equal(expected[:, :2], [[-1, 1], [-1, 1]])
            header = render_header(model, digest, norm, norm_id, kind)
            (directory / "actor_data.h").write_text(header, encoding="ascii")
            exe = compile_host(directory, None)
            compare(directory, exe, raw, expected, [len(raw)], [0])
            # Omitting normalization on the reference side must fail the parity gate.
            with self.assertRaisesRegex(ValueError, "absolute tolerance"):
                compare(directory, exe, raw, model.predict(raw, deterministic=True)[0], [len(raw)], [0])


class ActionLayoutTest(unittest.TestCase):
    def save_vanes4(self, directory, layout):
        with ActionAdapter(HopperAttitudeEnv(), "vanes4") as env:
            PPO("MlpPolicy", env, seed=0, device="cpu").save(directory / "model.zip")
        (directory / "model.json").write_text(json.dumps({"action": layout, "vecnormalize": False}))

    def test_vanes4_header_declares_layout_and_throttle(self):
        with tempfile.TemporaryDirectory() as tmp, HopperAttitudeEnv() as env:
            directory = Path(tmp)
            self.save_vanes4(directory, "vanes4")
            model, digest, kind, declared = load_actor(directory / "model.zip", env)
            self.assertEqual((kind, declared), ("vanes4", False))
            header = render_header(model, digest, None, "raw", kind)
            self.assertIn("constexpr std::size_t kOutputs = 4;", header)
            self.assertIn('constexpr char kActionLayout[] = "vanes4";', header)
            self.assertIn("constexpr float kFixedThrottleNorm = 1.00000000e+00f;", header)

    def test_json_normalization_must_match_arguments(self):
        with tempfile.TemporaryDirectory() as tmp, HopperAttitudeEnv() as env:
            directory = Path(tmp)
            self.save_vanes4(directory, "vanes4")
            meta = json.loads((directory / "model.json").read_text())
            meta["vecnormalize"] = True
            (directory / "model.json").write_text(json.dumps(meta))
            _, digest, _, declared = load_actor(directory / "model.zip", env)
            self.assertIs(declared, True)
            # --raw-obs on a VecNormalize model would make both sides skip normalization and pass.
            with self.assertRaisesRegex(ValueError, "supply its --vecnormalize"):
                load_normalization(None, True, digest, env.observation_space, declared)
            with self.assertRaisesRegex(ValueError, "drop --vecnormalize"):
                load_normalization(directory / "stats.pkl", False, digest, env.observation_space, False)

    def test_rejects_unsupported_or_mismatched_layout(self):
        with tempfile.TemporaryDirectory() as tmp, HopperAttitudeEnv() as env:
            directory = Path(tmp)
            self.save_vanes4(directory, "mixer3")
            with self.assertRaisesRegex(ValueError, "Unsupported action layout"):
                load_actor(directory / "model.zip", env)
            self.save_vanes4(directory, "learned")
            with self.assertRaisesRegex(ValueError, "5 actions"):
                load_actor(directory / "model.zip", env)


if __name__ == "__main__":
    unittest.main()
