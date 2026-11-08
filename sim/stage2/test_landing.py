"""Model invariants and nominal landing gates, run by python tasks.py stage2."""
import csv
import unittest

import mujoco
import numpy as np
from gymnasium.utils.env_checker import check_env

from cad.cg import cg_estimate
from .__main__ import COLUMNS, episode
from .control import LandingPD
from .env import CONTROL_DT, LandingEnv
from .model import Airframe, GRAVITY, MAX_ANGLE, MAX_THRUST, PARTS, PRESSURE_RADIUS, SIDE_GAIN


class ModelTest(unittest.TestCase):
    def test_cad_to_engine(self):
        body = Airframe()
        with PARTS.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            for key in ("mass_g", "x", "y", "z", "p1", "p2", "p3"):
                row[key] = float(row[key])
        mass, cg, diagonal = cg_estimate.props(rows)
        np.testing.assert_allclose([body.mass, *body.cg], [mass, *cg])
        np.testing.assert_allclose(body.inertia.diagonal(), diagonal)
        engine = body.engine()
        principal = np.zeros(9)
        mujoco.mju_quat2Mat(principal, engine.body_iquat[1])
        rotation = principal.reshape(3, 3)
        np.testing.assert_allclose(rotation @ np.diag(engine.body_inertia[1]) @ rotation.T,
                                   body.inertia, atol=1e-8)

    def test_four_jet_sectors(self):
        body = Airframe()
        neutral = np.zeros(4)
        force, moment = body.wrench(1., neutral)
        np.testing.assert_allclose(force, [0, 0, MAX_THRUST])
        np.testing.assert_allclose(moment, np.cross(-body.cg, force), atol=1e-12)
        # Positive servos follow the web viewer's hinge convention. Compare
        # each isolated vane to the neutral moment, referred to the CAD origin.
        for i, yaw_sign in enumerate([1, -1, -1, 1]):
            angles = neutral.copy()
            angles[i] = MAX_ANGLE
            force, moment = body.wrench(0., angles)
            np.testing.assert_array_equal(np.r_[force, moment], 0.)
            force, moment = body.wrench(1., angles)
            lateral = MAX_THRUST * SIDE_GAIN * MAX_ANGLE
            expected_xy = [0, lateral] if i % 2 == 0 else [lateral, 0]
            np.testing.assert_allclose(force[:2], expected_xy)
            moment_at_exit = moment + np.cross(body.cg, force)
            self.assertAlmostEqual(moment_at_exit[2], yaw_sign * PRESSURE_RADIUS * lateral)
            self.assertLess(np.linalg.norm(force), MAX_THRUST)
        # Mirrored pairs produce pure roll/pitch increments at first order.
        for i, expected in [(0, [1, 0, 0]), (1, [0, -1, 0])]:
            angles = neutral.copy()
            angles[i::2] = MAX_ANGLE
            _, plus = body.wrench(1., angles)
            _, minus = body.wrench(1., -angles)
            change = plus - minus
            # CG lateral offset adds a small yaw couple, tested above.
            np.testing.assert_array_equal(np.sign(change[:2]), expected[:2])


class LandingTest(unittest.TestCase):
    def test_seed_and_gym_api(self):
        env = LandingEnv()
        check_env(env, skip_render_check=True)
        def trace(seed):
            obs, _ = env.reset(seed=seed)
            return np.vstack([obs, *(env.step(np.zeros(5))[0] for _ in range(5))])
        np.testing.assert_array_equal(trace(21), trace(21))
        self.assertFalse(np.array_equal(trace(21), trace(22)))

    def test_gravity_and_tilted_thrust(self):
        env = LandingEnv()
        env.reset(seed=1)
        env.motor = 0.
        obs, *_ = env.step([0, 0, 0, 0, -1])
        np.testing.assert_allclose(obs[3:6], [0, 0, -GRAVITY * CONTROL_DT], atol=1e-6)
        env.reset(seed=1)
        angle = 0.15
        env.data.qpos[3:] = [np.cos(angle/2), 0, np.sin(angle/2), 0]
        mujoco.mj_forward(env.model, env.data)
        obs, *_ = env.step([0, 0, 0, 0, 2 * env.motor - 1])
        self.assertAlmostEqual(obs[3], GRAVITY * np.sin(angle) * CONTROL_DT, delta=0.001)
        self.assertLess(obs[5], 0)

    def test_controlled_landing_and_replay(self):
        env = LandingEnv()
        rows, result = episode(env, LandingPD(env.airframe), 2, "PID")
        self.assertEqual(result["outcome"], "landed")
        self.assertGreaterEqual(result["pad_count"], 3)
        self.assertGreater(result["impact_m_s"], 0.)
        self.assertLessEqual(result["impact_m_s"], 0.45)
        self.assertEqual(len(rows), env.steps + 1)
        self.assertTrue(all(len(r) == len(COLUMNS) for r in rows))
        np.testing.assert_allclose([np.linalg.norm(r[6:10]) for r in rows], 1., atol=1e-6)
        self.assertTrue(np.all(np.diff([r[0] for r in rows]) > 0))
        self.assertEqual(rows[-1][0], round(1000 * result["time_s"]))

    def test_drop_and_timeout_are_distinct(self):
        env = LandingEnv()
        _, result = episode(env, lambda obs: [0, 0, 0, 0, -1], 2, "MANUAL")
        self.assertEqual(result["outcome"], "hard_contact")
        self.assertGreater(result["impact_m_s"], 0.45)
        env = LandingEnv(max_steps=1)
        env.reset(seed=3)
        _, _, terminated, truncated, info = env.step([0] * 5)
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertEqual(info["outcome"], "time_limit")


if __name__ == "__main__":
    unittest.main()
