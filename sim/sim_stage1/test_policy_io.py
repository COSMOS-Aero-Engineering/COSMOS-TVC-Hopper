"""policy_io.py 행동 구조와 ppo_ablation.py 종료 비용의 단위 검사(#230). tasks.py의 sanity 작업이 돌린다.

    python -m unittest -q test_policy_io      (sim/sim_stage1 폴더에서)

잡으려는 사고:
    1. 믹서의 롤·피치·요 요구가 다른 축 토크를 만든다(부호나 베인 순서가 틀림)
    2. 고정 스로틀 행동이 스로틀 100 %가 아니다(지름길이 다시 열린다)
    3. json이 없는 #230 전 모델을 다른 행동 구조로 읽는다
    4. 종료 비용이 "남은 스텝 동안 같은 보상"의 할인 합과 다르다
"""
import unittest
from pathlib import Path

import numpy as np

from hopper_aviary import HopperAttitudeEnv
from policy_io import ACTIONS, ActionAdapter, read_meta, sidecar, to_env_action

HERE = Path(__file__).resolve().parent


def torque_signs(action5):
    """hopper_aviary.py step()의 토크 식에서 베인 부분만(l = r = CL·Ft = 1)."""
    a1, a2, a3, a4 = action5[:4]
    return np.array([a1 + a3, -(a2 + a4), a1 - a2 - a3 + a4])


class MixerTest(unittest.TestCase):
    def test_each_axis_makes_only_its_torque(self):
        for axis in range(3):
            u = np.zeros(3)
            u[axis] = 0.5
            tau = torque_signs(to_env_action("mixer3", u))
            others = [i for i in range(3) if i != axis]
            self.assertTrue(np.allclose(tau[others], 0.0), f"축 {axis}: {tau}")
            self.assertNotEqual(tau[axis], 0.0)

    def test_roll_pitch_sign_matches_pd(self):
        # pd_gate.pd()는 [ux, uy, ux, uy]를 낸다. 같은 요구면 믹서 출력도 같아야 한다
        np.testing.assert_allclose(to_env_action("mixer3", [0.3, -0.2, 0.0])[:4], [0.3, -0.2, 0.3, -0.2], rtol=1e-6)

    def test_output_is_clipped(self):
        self.assertLessEqual(np.abs(to_env_action("mixer3", [1.0, 1.0, 1.0])[:4]).max(), 1.0)


class FixedThrottleTest(unittest.TestCase):
    def test_fixed_kinds_send_full_throttle(self):
        env = HopperAttitudeEnv()
        for kind, n in (("vanes4", 4), ("mixer3", 3)):
            wrapped = ActionAdapter(env, kind)
            self.assertEqual(wrapped.action_space.shape, (n,))
            wrapped.reset(seed=0)
            _, _, _, _, info = wrapped.step(-np.ones(n, dtype=np.float32))
            self.assertEqual(info["throttle"], 1.0, kind)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            to_env_action("bogus", [0.0])
        self.assertEqual(ACTIONS, ("learned", "vanes4", "mixer3"))


class MetaTest(unittest.TestCase):
    def test_legacy_model_without_json_is_learned(self):
        legacy = HERE / "hopper_attitude_ppo.zip"
        self.assertFalse(sidecar(legacy, ".json").exists())
        self.assertEqual(read_meta(legacy), {"action": "learned", "vecnormalize": False})

    def test_sidecar_names(self):
        self.assertEqual(sidecar("a/b.zip", ".vecnormalize.pkl"), Path("a/b.vecnormalize.pkl"))


class CrashCostTest(unittest.TestCase):
    def test_cost_equals_discounted_tail(self):
        from ppo_ablation import GAMMA, CrashCost

        env = CrashCost(HopperAttitudeEnv())
        base = env.unwrapped
        env.reset(seed=0)
        # 피치 59.9°, 큰 각속도에서 한 스텝이면 넘어진다
        base.state = np.array([0.0, np.deg2rad(59.9), 0.0, 0.0, 20.0, 0.0], dtype=np.float32)
        base.step_count = 100
        raw = HopperAttitudeEnv()
        raw.reset(seed=0)
        raw.state, raw.step_count = base.state.copy(), 100
        action = np.array([0, 0, 0, 0, 1.0], dtype=np.float32)
        _, r_raw, term_raw, _, _ = raw.step(action)
        _, r, term, _, _ = env.step(action)
        self.assertTrue(term and term_raw)
        n = base.max_steps - base.step_count
        expected = r_raw + sum(r_raw * GAMMA ** k for k in range(1, n + 1))
        self.assertAlmostEqual(r, expected, places=9)


if __name__ == "__main__":
    unittest.main()
