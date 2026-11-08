"""Nominal cascaded PD for a near-upright descent toward the pad center."""
import numpy as np

from .model import GRAVITY, MAX_ANGLE, MAX_THRUST, SIDE_GAIN, euler


class LandingPD:
    def __init__(self, airframe):
        self.body = airframe
        # Small-angle allocation at unit thrust. Include the CAD offset between
        # exhaust axis and CG, even in level hover with neutral vane commands.
        self.allocate = np.linalg.pinv(airframe.side_moments.T * (SIDE_GAIN * MAX_ANGLE))

    def __call__(self, obs):
        body = self.body
        position, velocity = obs[:3], obs[3:6]
        roll, pitch, yaw = euler(obs[6:10])
        height = position[2] - body.rest_height
        if height < 0.003:
            return np.array([0, 0, 0, 0, -1], dtype=np.float32)
        descent = -np.clip(0.13 + 0.7 * height, 0.13, 0.38)
        accel_z = 4. * (descent - velocity[2])
        thrust = body.mass * (GRAVITY + accel_z) / max(0.5, np.cos(roll) * np.cos(pitch))
        thrust = np.clip(thrust, 0.1, MAX_THRUST)
        accel_xy = np.clip(-2 * position[:2] - 2.4 * velocity[:2], -1., 1.)
        c, s = np.cos(yaw), np.sin(yaw)
        target_roll = (s * accel_xy[0] - c * accel_xy[1]) / GRAVITY
        target_pitch = (c * accel_xy[0] + s * accel_xy[1]) / GRAVITY
        attitude_error = np.array([target_roll - roll, target_pitch - pitch, -yaw])
        torque = body.inertia @ (28 * attitude_error - 8 * obs[10:13])
        trim = np.cross(-body.cg, [0, 0, 1])
        commands = self.allocate @ (torque / thrust - trim)
        return np.r_[np.clip(commands, -1, 1), 2 * np.sqrt(thrust / MAX_THRUST) - 1].astype(np.float32)
