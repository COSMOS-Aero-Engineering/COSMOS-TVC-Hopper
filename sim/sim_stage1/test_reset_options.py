"""hopper_aviary.py reset(options=...)의 단위 검사(#276). tasks.py의 sanity 작업이 돌린다.

    python -m unittest -q test_reset_options      (sim/sim_stage1 폴더에서)

compare_metrics.py의 TC-3 조건은 이 옵션에 기대므로 여기서 잡으려는 사고는 셋이다.
    1. 옵션을 줬는데 기울기가 10°가 아니거나 요 오프셋이 남는다
    2. 옵션이 같은 seed의 랜덤화된 기체를 바꿔서 두 조건의 비교가 다른 기체끼리의 비교가 된다
    3. 오타 난 키나 범위 밖 값이 조용히 기본 분포로 돌아간다
"""
import unittest

import numpy as np

from hopper_aviary import CRASH_DEG, N_STATE, HopperAttitudeEnv

TILT_DEG = 10.0
SEEDS = range(200)   # compare_metrics.py의 평가 seed(pd_gate.EVAL_SEEDS)와 같다


def airframe(env):
    """reset()이 에피소드마다 다시 뽑는 기체 값."""
    return np.array([env.Jxx, env.Jyy, env.Jzz, env.l, env.r, env.Kf, env.cg_offset_x, env.cg_offset_y,
                     env.rotor_inertia, env.rotor_omega_max, env.rotor_tau])


class ResetOptionTest(unittest.TestCase):
    def setUp(self):
        self.env = HopperAttitudeEnv()

    def test_tilt_is_fixed_and_yaw_is_zero(self):
        for seed in SEEDS:
            obs, _ = self.env.reset(seed=seed, options={"initial_tilt_deg": TILT_DEG})
            # obs는 float32다. 10° = 0.1745 rad에서 float32 반올림 오차는 1e-7 rad 수준이다
            self.assertAlmostEqual(np.degrees(np.hypot(obs[0], obs[1])), TILT_DEG, places=4, msg=f"seed {seed}")
            self.assertEqual(obs[2], 0.0, msg=f"seed {seed}: 요 오프셋이 남았다")
            np.testing.assert_array_equal(obs[3:N_STATE], 0.0)

    def test_direction_covers_all_quadrants(self):
        quadrants = set()
        for seed in SEEDS:
            obs, _ = self.env.reset(seed=seed, options={"initial_tilt_deg": TILT_DEG})
            quadrants.add((bool(obs[0] > 0), bool(obs[1] > 0)))
        self.assertEqual(len(quadrants), 4, "기울기 방향이 seed에 따라 바뀌지 않는다")

    def test_same_seed_same_airframe_and_attitude(self):
        for seed in SEEDS:
            default_obs, _ = self.env.reset(seed=seed)
            default_airframe = airframe(self.env)
            tilt_obs, _ = self.env.reset(seed=seed, options={"initial_tilt_deg": TILT_DEG})
            np.testing.assert_array_equal(airframe(self.env), default_airframe, err_msg=f"seed {seed}")
            again_obs, _ = self.env.reset(seed=seed, options={"initial_tilt_deg": TILT_DEG})
            np.testing.assert_array_equal(again_obs, tilt_obs, err_msg=f"seed {seed}: 같은 seed인데 다르다")
            none_obs, _ = self.env.reset(seed=seed, options=None)
            np.testing.assert_array_equal(none_obs, default_obs, err_msg=f"seed {seed}: options=None이 기본과 다르다")

    def test_bad_options_raise(self):
        bad = [
            {"initial_tilt": TILT_DEG},       # 오타
            {"initial_tilt_deg": 0.0},
            {"initial_tilt_deg": -5.0},
            {"initial_tilt_deg": CRASH_DEG},
            {"initial_tilt_deg": float("nan")},
            {"initial_tilt_deg": "10"},
            {"initial_tilt_deg": True},
            [("initial_tilt_deg", TILT_DEG)],
        ]
        for options in bad:
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.env.reset(seed=0, options=options)


if __name__ == "__main__":
    unittest.main()
