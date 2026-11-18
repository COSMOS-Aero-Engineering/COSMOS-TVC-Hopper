"""Model invariants and nominal landing gates, run by python tasks.py stage2."""
import csv
import json
from pathlib import Path
import re
import unittest

import mujoco
import numpy as np
from gymnasium.utils.env_checker import check_env

from cad.cg import cg_estimate
from .__main__ import COLUMNS, MISSION_COLUMNS, episode, mission_rows
from .control import LandingPD
from .env import CONTROL_DT, LandingEnv
from .mission import (
    MAX_REF_ACCEL, MAX_REF_SPEED, MISSION_STEPS, PAD_XY, Trajectory, reference_limits, run,
    tilt_limit_deg, zyx_quat,
)
from .model import (
    Airframe, CHORD, GRAVITY, JET_INNER, JET_OUTER, LIFT_SLOPE, MAX_ANGLE, MAX_THRUST, MOTOR_TAU, PARTS,
    PRESSURE_RADIUS, SERVO_RATE, SERVO_TAU, SIDE_GAIN, euler,
)

WEB_CSV = Path(__file__).resolve().parents[2] / "web" / "src" / "csv.js"


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


class ParamsTest(unittest.TestCase):
    def test_constants_match_stage1_params(self):
        """Stage 2 copies these placeholders from sim/sim_stage1/params.yaml. Keep them equal.

        Mass, inertia and the roll/pitch arm are not copied: Stage 2 computes them from the CAD
        parts table (README table), while params.yaml keeps Stage 1 placeholders until #306."""
        import yaml
        p = yaml.safe_load((Path(__file__).resolve().parents[1] / "sim_stage1" / "params.yaml")
                           .read_text(encoding="utf-8"))
        g = p["vane_geometry"]
        np.testing.assert_allclose([JET_INNER, JET_OUTER, CHORD],
                                   np.array([g["inner_r_mm"], g["outer_r_mm"], g["chord_mm"]]) / 1000)
        self.assertEqual(LIFT_SLOPE, p["CLalpha"])
        self.assertAlmostEqual(MAX_ANGLE, np.deg2rad(p["alpha_max_deg"]))
        self.assertAlmostEqual(MAX_THRUST, p["Kf"] * p["omega_t_per_throttle"] ** 2)
        self.assertEqual(SERVO_TAU, p["servo"]["tau"])
        self.assertAlmostEqual(SERVO_RATE, np.deg2rad(p["servo"]["rate_max_dps"]))
        self.assertEqual(MOTOR_TAU, p["rotor"]["tau"])


class CliTest(unittest.TestCase):
    def test_train_and_replay_ppo(self):
        import sys
        import tempfile
        from unittest import mock
        from .__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "ppo.zip"
            with mock.patch.object(sys, "argv", ["stage2", "train", "--steps", "256", "--seed", "5",
                                                 "--model", str(model)]):
                main()
            self.assertTrue(model.exists())
            out = Path(tmp) / "csv"
            with mock.patch.object(sys, "argv", ["stage2", "evaluate", "--policy", "ppo", "--model", str(model),
                                                 "--episodes", "1", "--seed", "1000", "--out", str(out)]):
                main()
            with (out / "stage2-ppo-s1000.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(rows[0], COLUMNS)
            self.assertEqual(rows[1][2], "RL")


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


def web_columns(name):
    """Column list `name` from web/src/csv.js, so the test follows the viewer's parser."""
    match = re.search(rf"{name} = \[([^\]]*)\]", WEB_CSV.read_text(encoding="utf-8"))
    return re.findall(r"'([^']+)'", match.group(1))


class MissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = LandingEnv(max_steps=MISSION_STEPS)
        cls.truth = [run(cls.env, seed, "truth") for seed in (0, 1)]
        cls.estimated = [run(cls.env, seed, "estimated") for seed in (0, 1)]

    def test_reference_is_smooth_and_inside_limits(self):
        rest = self.env.airframe.rest_height
        trajectory = Trajectory([0.01, -0.02], rest)
        speed, accel = reference_limits(trajectory)
        self.assertLessEqual(speed, MAX_REF_SPEED)
        self.assertLessEqual(accel, MAX_REF_ACCEL)
        np.testing.assert_allclose(trajectory(0.)[0], [0.01, -0.02, rest])
        end, end_vel, _ = trajectory(trajectory.end_time)
        np.testing.assert_allclose(end[:2], PAD_XY)
        self.assertLess(end[2], rest)
        np.testing.assert_allclose(end_vel, 0., atol=1e-12)
        times = np.arange(0., trajectory.end_time, 0.001)
        jumps = np.abs(np.diff([trajectory(t)[0] for t in times], axis=0))
        self.assertLess(jumps.max(), MAX_REF_SPEED * 0.001 + 1e-9)

    def test_ground_start_is_not_a_landing(self):
        env = LandingEnv(max_steps=20)
        obs, _ = env.reset(seed=4, options={"start": "ground"})
        self.assertEqual(env.motor, 0.)
        self.assertAlmostEqual(obs[2], env.airframe.rest_height)
        for _ in range(20):
            _, _, terminated, truncated, info = env.step([0, 0, 0, 0, -1])
            self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertFalse(info["airborne"])
        self.assertGreaterEqual(info["pad_count"], 3)
        with self.assertRaises(ValueError):
            env.reset(seed=0, options={"start": "orbit"})

    def test_truth_feedback_mission(self):
        for _, result in self.truth:
            self.assertEqual(result["outcome"], "landed", result)
            self.assertTrue(result["airborne"])
            self.assertLess(result["touchdown_xy_error_m"], 0.05)
            self.assertLessEqual(result["impact_m_s"], 0.45)
            self.assertLess(result["max_tilt_deg"], tilt_limit_deg() + 2)
            self.assertEqual(result["thrust_sat_fraction"], 0.)
            for name, phase in result["phases"].items():
                self.assertLess(phase["pos_rms_m"], 0.06, name)
                self.assertEqual(phase["est_pos_rms_m"], 0.)

    def test_estimated_feedback_mission(self):
        (_, seed0), (_, seed1) = self.estimated
        self.assertEqual(seed0["outcome"], "landed", seed0)
        self.assertLess(seed0["touchdown_xy_error_m"], 0.20)
        # Known failure (README, #409): range noise (sigma 5 mm) cuts the EDF at 2.2 mm
        # estimated height while the true height is 12.9 mm, and the drop is a hard contact.
        self.assertEqual(seed1["outcome"], "hard_contact", seed1)
        self.assertIsNone(seed1["touchdown_xy_error_m"])
        for _, result in self.estimated:
            # The flow-integrated position drifts away from the truth.
            self.assertGreater(result["phases"]["hover2"]["est_pos_rms_m"], 0.)
            # The range sensor sits on the exhaust plane, 148 mm above the floor at rest.
            # That is above RANGE_MIN and FLOW_MIN_RANGE, so both stay valid on the floor too.
            self.assertEqual(result["range_valid_fraction"], 1.)
            self.assertEqual(result["flow_valid_fraction"], 1.)
            json.dumps(result)

    def test_throttle_cut_latches(self):
        for records, _ in self.truth + self.estimated:
            throttle = [r["action"][4] for r in records]
            first = next(i for i, (r, a) in enumerate(zip(records, throttle))
                         if a == -1 and r["phase"] in ("land", "settle"))
            self.assertTrue(all(a == -1 for a in throttle[first:]))

    def test_mission_csv_matches_web_contract(self):
        env = LandingEnv(max_steps=MISSION_STEPS)
        records, result = run(env, 0, "truth")
        # The CLI writes the final row from env.observation() after the last step.
        rows = mission_rows(records, env.observation(), result["time_s"])
        self.assertEqual(MISSION_COLUMNS[:len(COLUMNS)], COLUMNS)
        required, numeric = web_columns("REQUIRED"), web_columns("NUMERIC")
        self.assertTrue(set(required) <= set(numeric) <= set(MISSION_COLUMNS))
        at = {name: i for i, name in enumerate(MISSION_COLUMNS)}
        rest = self.env.airframe.rest_height
        for r in rows:
            self.assertEqual(len(r), len(MISSION_COLUMNS))
            for name in required:
                self.assertTrue(np.isfinite(float(r[at[name]])), name)
            q = np.array([r[at[c]] for c in ("qw", "qx", "qy", "qz")], dtype=float)
            angles = np.array([r[at[c]] for c in ("phi", "theta", "psi")], dtype=float)
            # phi/theta/psi are the ZYX Euler angles of the same body-to-world quaternion.
            # The observation stores float32 quaternions, so compare to 1e-6.
            np.testing.assert_allclose(angles, euler(q), atol=1e-6)
            rebuilt = zyx_quat(*angles)
            self.assertGreater(abs(np.dot(rebuilt, q)), 1 - 1e-6)
        # World frame: Z up from the floor, CG position. Start on the floor, end on the pad.
        first = rows[0]
        self.assertAlmostEqual(first[at["pz"]], rest, places=6)
        self.assertEqual(first[at["phase"]], "takeoff")
        np.testing.assert_allclose([rows[-2][at["px"]], rows[-2][at["py"]]], PAD_XY, atol=0.05)
        top = max(r[at["pz"]] for r in rows[:-1])
        self.assertGreater(top, rest + 0.4)


class PpoBudgetTest(unittest.TestCase):
    def test_timeout_variant_and_outcome_counts(self):
        from .ppo_budget import EVAL_SEEDS, OUTCOMES, evaluate_policy, make_env
        env = make_env("timeout10")
        env.unwrapped.max_steps = 1
        env.reset(seed=3)
        _, reward, _, truncated, info = env.step(np.zeros(5))
        base = LandingEnv(max_steps=1)
        base.reset(seed=3)
        _, base_reward, *_ = base.step(np.zeros(5))
        self.assertTrue(truncated)
        self.assertEqual(info["outcome"], "time_limit")
        self.assertAlmostEqual(reward, base_reward - 5.)
        row = evaluate_policy(LandingPD(base.airframe), list(EVAL_SEEDS)[:2])
        self.assertEqual(row["landed"], 2)
        self.assertEqual(sum(row[k] for k in OUTCOMES), row["episodes"])


if __name__ == "__main__":
    unittest.main()
