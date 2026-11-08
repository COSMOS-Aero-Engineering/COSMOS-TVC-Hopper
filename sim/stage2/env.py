"""Headless 6-DOF descent onto a flat pad."""
import gymnasium as gym
import mujoco
import numpy as np

from .model import (
    Airframe, GRAVITY, MAX_ANGLE, MAX_THRUST, MOTOR_TAU, PHYSICS_DT,
    SERVO_RATE, SERVO_TAU,
)

SUBSTEPS = 5
CONTROL_DT = PHYSICS_DT * SUBSTEPS


class LandingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, max_steps=400):
        super().__init__()
        self.airframe = Airframe()
        self.model = self.airframe.engine()
        self.data = mujoco.MjData(self.model)
        self.body = self.model.body("hopper").id
        self.pad_ids = {self.model.geom(f"pad{i}").id for i in range(4)}
        if max_steps < 1:
            raise ValueError("max_steps must be positive.")
        self.max_steps = max_steps
        self.action_space = gym.spaces.Box(-1, 1, shape=(5,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(18,), dtype=np.float32)
        self.done = True

    def observation(self):
        d = self.data
        return np.concatenate((d.qpos[:3], d.qvel[:3], d.qpos[3:7], d.qvel[3:],
                               self.angles, [self.motor])).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        rng = self.np_random
        pos = self.data.qpos
        pos[:2] = rng.uniform(-0.05, 0.05, 2)
        pos[2] = self.airframe.rest_height + rng.uniform(0.45, 0.65)
        rotation = rng.uniform(-0.055, 0.055, 3)
        mujoco.mju_euler2Quat(pos[3:7], rotation, "xyz")
        self.angles = np.zeros(4)
        self.motor = np.sqrt(self.airframe.mass * GRAVITY / MAX_THRUST)
        self.steps = self.stable_steps = 0
        self.max_impact = 0.
        self.touching = set()
        self.done = False
        mujoco.mj_forward(self.model, self.data)
        return self.observation(), {}

    def contact_outcome(self):
        d = self.data
        # Only ground-to-body collisions are enabled in this single-body world.
        touching = {max(c.geom1, c.geom2) for c in d.contact if c.dist <= 0}
        if touching - self.pad_ids:
            return "body_contact"
        rot = d.xmat[self.body].reshape(3, 3)
        new_contacts = touching - self.touching
        self.touching = touching
        for pad in new_contacts:
            arm = d.geom_xpos[pad] - d.xpos[self.body]
            velocity = d.qvel[:3] + np.cross(rot @ d.qvel[3:], arm)
            self.max_impact = max(self.max_impact, -velocity[2])
            if self.max_impact > 0.45 or np.linalg.norm(velocity[:2]) > 0.4:
                return "hard_contact"
        if rot[2, 2] < np.cos(np.deg2rad(45)):
            return "tipped"
        pos = d.qpos[:3]
        if np.linalg.norm(pos[:2]) > 1.5 or pos[2] > 2.5:
            return "out_of_bounds"
        stable = (len(touching) >= 3 and self.motor <= 0.10 and np.linalg.norm(pos[:2]) < 0.20
                  and rot[2, 2] > np.cos(np.deg2rad(8))
                  and np.linalg.norm(d.qvel[:3]) < 0.10 and np.linalg.norm(d.qvel[3:]) < 0.25)
        self.stable_steps = self.stable_steps + 1 if stable else 0
        if self.stable_steps * PHYSICS_DT >= 0.15:
            return "landed"
        return "flying"

    def step(self, action):
        if self.done:
            raise gym.error.ResetNeeded("Call reset() before stepping a new episode.")
        action = np.asarray(action)
        if action.shape != (5,) or not np.isfinite(action).all():
            raise ValueError("Expected five finite controls.")
        action = np.clip(action, -1., 1.)
        target_angles = MAX_ANGLE * action[:4]
        throttle = (1 + action[4]) / 2
        d = self.data
        for _ in range(SUBSTEPS):
            delta = (target_angles - self.angles) * -np.expm1(-PHYSICS_DT / SERVO_TAU)
            self.angles += np.clip(delta, -SERVO_RATE * PHYSICS_DT, SERVO_RATE * PHYSICS_DT)
            self.motor += (throttle - self.motor) * -np.expm1(-PHYSICS_DT / MOTOR_TAU)
            force, torque = self.airframe.wrench(self.motor, self.angles)
            rot = d.xmat[self.body].reshape(3, 3)
            d.xfrc_applied[self.body, :3] = rot @ force
            d.xfrc_applied[self.body, 3:] = rot @ torque
            mujoco.mj_step(self.model, d)
            mujoco.mj_forward(self.model, d)
            outcome = self.contact_outcome()
            if outcome != "flying":
                break
        self.steps += 1
        obs = self.observation()
        height = max(0., obs[2] - self.airframe.rest_height)
        tilt_cost = 1 - d.xmat[self.body, 8]
        reward = -CONTROL_DT * (0.2 + height + np.linalg.norm(obs[:2]) + tilt_cost
                                + 0.1 * np.dot(obs[3:6], obs[3:6]))
        terminated = outcome != "flying"
        truncated = self.steps >= self.max_steps and not terminated
        if terminated:
            reward += 10. if outcome == "landed" else -10.
        if truncated:
            outcome = "time_limit"
            reward -= 5.
        self.done = terminated or truncated
        info = {"outcome": outcome, "pad_count": len(self.touching),
                "impact_m_s": self.max_impact, "time_s": d.time}
        return obs, float(reward), terminated, truncated, info
