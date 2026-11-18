"""compare_metrics.py PID 기준 제어기의 단위 검사(#349). tasks.py의 sanity 작업이 돌린다.

    python -m unittest -q test_pid      (sim/sim_stage1 폴더에서)

잡으려는 사고:
    1. PID의 부호나 행동 구조가 pd_gate.pd()와 다르다(ki = 0에서 행동이 달라진다)
    2. 적분값이 에피소드를 넘어 남는다(앞 에피소드가 다음 에피소드 결과를 바꾼다)
    3. 출력이 포화된 채로 적분이 계속 쌓인다(와인드업)
    4. 적분 항이 일정한 외란(CG 오프셋)의 정상오차를 줄이지 못한다
"""
import unittest

import numpy as np

from compare_metrics import PID, evaluate, make_pid
from pd_gate import pd

DT = 0.01


class PIDTest(unittest.TestCase):
    def test_zero_ki_matches_pd(self):
        rng = np.random.default_rng(0)
        ctrl = PID(kp=8.0, kd=2.0, ki=0.0, dt=DT)
        for _ in range(200):
            obs = rng.uniform(-0.5, 0.5, size=7).astype(np.float32)
            np.testing.assert_array_equal(ctrl(obs), pd(obs))

    def test_reset_clears_integral(self):
        ctrl = PID(kp=8.0, kd=2.0, ki=5.0, dt=DT)
        obs = np.array([0.05, -0.05, 0, 0, 0, 0, 1], dtype=np.float32)
        first = ctrl(obs)
        for _ in range(50):
            ctrl(obs)
        self.assertFalse(np.array_equal(ctrl(obs), first))
        ctrl.reset()
        np.testing.assert_array_equal(ctrl(obs), first)

    def test_no_windup_while_saturated(self):
        ctrl = PID(kp=100.0, kd=0.0, ki=5.0, dt=DT)
        obs = np.array([0.5, 0.5, 0, 0, 0, 0, 1], dtype=np.float32)   # 비례 항만으로 포화
        for _ in range(100):
            ctrl(obs)
        self.assertEqual((ctrl.ix, ctrl.iy), (0.0, 0.0))

    def test_evaluate_is_repeatable(self):
        # 같은 PID 객체로 두 번 평가해도 같아야 한다. 적분값이 에피소드 사이에 남으면 다르다
        ctrl = make_pid()
        a = evaluate(ctrl, seeds=range(5))
        b = evaluate(ctrl, seeds=range(5))
        self.assertEqual(a, b)

    def test_integral_removes_offset(self):
        seeds = range(10)
        pd_err = evaluate(pd, seeds=seeds)["steady_err_deg"]
        pid_err = evaluate(PID(kp=8.0, kd=2.0, ki=10.0, dt=DT), seeds=seeds)["steady_err_deg"]
        self.assertLess(pid_err, 0.5 * pd_err)


if __name__ == "__main__":
    unittest.main()
