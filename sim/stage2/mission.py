"""Closed-loop ground mission: take off, hover, move sideways, hover, land.

The mission starts with the pads on the floor and the EDF stopped (LandingEnv
options={"start": "ground"}). A cascaded PD tracks a smooth reference. It reads
either the simulator truth ("truth") or a state estimate built from assumed
sensors ("estimated"): IMU attitude and gyro, a downward range sensor and an
optical-flow sensor. Every sensor constant below is an assumption for this
comparison, not a datasheet or measured value.
"""
from dataclasses import dataclass

import numpy as np

from .control import LandingPD
from .env import CONTROL_DT
from .model import GRAVITY, MAX_THRUST, euler

# Mission shape. Heights are CG heights above the resting CG height.
HOVER_HEIGHT = 0.50     # m
PAD_XY = (0.50, 0.0)    # m, world landing pad center. The start is near the origin.
TOUCHDOWN_CUT = 0.003   # m, same 3 mm throttle cut as LandingPD
LAND_OVERSHOOT = 0.03   # m, the landing reference ends this far below rest height
PHASES = (              # name, duration (s)
    ("takeoff", 3.0),
    ("hover1", 2.0),
    ("translate", 3.0),
    ("hover2", 2.0),
    ("land", 4.0),
)
SETTLE_S = 3.0          # time after the land phase for touchdown and the landed judgment
MISSION_STEPS = int(round((sum(d for _, d in PHASES) + SETTLE_S) / CONTROL_DT))

# Reference limits the mission must respect (checked from the reference itself).
MAX_REF_SPEED = 0.40    # m/s, the env's hard-contact horizontal limit
MAX_REF_ACCEL = 1.0     # m/s^2, LandingPD's horizontal acceleration clip

# Assumed sensors for feedback="estimated".
RANGE_MIN, RANGE_MAX, RANGE_SIGMA = 0.04, 4.0, 0.005   # m
RANGE_POS = np.array([0.06, 0.0, 0.0])                 # m, CAD point on the exhaust plane
FLOW_MIN_RANGE = 0.08                                  # m, flow invalid below this range
FLOW_SIGMA = 0.03                                      # rad/s, flow-rate noise
GYRO_SIGMA, GYRO_BIAS = 0.005, 0.01                    # rad/s noise, per-episode bias bound
TILT_ERROR = np.deg2rad(0.5)                           # per-episode roll/pitch error bound
YAW_WALK = np.deg2rad(0.2)                             # rad/sqrt(s), yaw random walk


def quintic(s):
    """Minimum-jerk blend 0..1 with zero velocity and acceleration at both ends."""
    s = np.clip(s, 0., 1.)
    return 10*s**3 - 15*s**4 + 6*s**5, (30*s**2 - 60*s**3 + 30*s**4), (60*s - 180*s**2 + 120*s**3)


class Trajectory:
    """Reference CG position, velocity and acceleration in world axes (Z up)."""

    def __init__(self, start_xy, rest_height):
        self.start = np.array([start_xy[0], start_xy[1], rest_height])
        self.rest_height = rest_height
        self.bounds = np.cumsum([0.] + [d for _, d in PHASES])
        self.end_time = self.bounds[-1]
        self.target_xy = np.array(PAD_XY)

    def phase(self, t):
        index = int(np.searchsorted(self.bounds, t, side="right")) - 1
        return PHASES[index][0] if index < len(PHASES) else "settle"

    def __call__(self, t):
        pos = self.start.copy()
        vel, acc = np.zeros(3), np.zeros(3)

        def blend(axis, a, b, t0, duration):
            p, v, s2 = quintic((t - t0) / duration)
            inside = t0 <= t <= t0 + duration
            pos[axis] = a + (b - a) * p
            vel[axis] = (b - a) * v / duration if inside else 0.
            acc[axis] = (b - a) * s2 / duration**2 if inside else 0.

        top = self.rest_height + HOVER_HEIGHT
        floor = self.rest_height - LAND_OVERSHOOT
        b = self.bounds
        if t < b[4]:
            blend(2, self.rest_height, top, b[0], PHASES[0][1])
        else:
            blend(2, top, floor, b[4], PHASES[4][1])
        for axis in (0, 1):
            blend(axis, self.start[axis], self.target_xy[axis], b[2], PHASES[2][1])
        return pos, vel, acc


@dataclass
class State:
    position: np.ndarray
    velocity: np.ndarray
    quat: np.ndarray
    rates: np.ndarray


def truth_state(obs):
    return State(obs[:3].astype(float), obs[3:6].astype(float), obs[6:10].astype(float),
                 obs[10:13].astype(float))


def rotation(quat):
    w, x, y, z = quat
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
        [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
        [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)],
    ])


def zyx_quat(roll, pitch, yaw):
    cr, sr = np.cos(roll / 2), np.sin(roll / 2)
    cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
    cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
    return np.array([cr*cp*cy + sr*sp*sy, sr*cp*cy - cr*sp*sy,
                     cr*sp*cy + sr*cp*sy, cr*cp*sy - sr*sp*cy])


class Estimator:
    """IMU + downward range + optical flow. Position is integrated flow, so it drifts."""

    def __init__(self, airframe, rng, start_xy):
        self.body = airframe
        self.rng = rng
        self.gyro_bias = rng.uniform(-GYRO_BIAS, GYRO_BIAS, 3)
        self.tilt_error = rng.uniform(-TILT_ERROR, TILT_ERROR, 2)
        self.yaw_error = 0.
        # Range sensor point relative to the CG, in body axes.
        self.sensor = RANGE_POS - airframe.cg
        # The estimator starts where the vehicle is told it starts.
        self.position = np.array([start_xy[0], start_xy[1], airframe.rest_height])
        self.velocity = np.zeros(3)
        self.range_valid = self.flow_valid = False

    def measure_range(self, obs):
        rot = rotation(obs[6:10])
        point = obs[:3] + rot @ self.sensor
        down = rot @ [0, 0, -1.]
        if down[2] >= -1e-6:
            return None
        distance = point[2] / -down[2] + self.rng.normal(0, RANGE_SIGMA)
        return distance if RANGE_MIN <= distance <= RANGE_MAX else None

    def __call__(self, obs):
        roll, pitch, yaw = euler(obs[6:10])
        self.yaw_error += self.rng.normal(0, YAW_WALK * np.sqrt(CONTROL_DT))
        quat = zyx_quat(roll + self.tilt_error[0], pitch + self.tilt_error[1], yaw + self.yaw_error)
        rates = obs[10:13] + self.gyro_bias + self.rng.normal(0, GYRO_SIGMA, 3)
        rot = rotation(quat)

        # Height: alpha-beta filter on the tilt-corrected range. Below the
        # minimum range the filter predicts with the last vertical velocity.
        distance = self.measure_range(obs)
        self.range_valid = distance is not None
        z_pred = self.position[2] + self.velocity[2] * CONTROL_DT
        if self.range_valid:
            down = rot @ [0, 0, -1.]
            z_meas = distance * -down[2] - (rot @ self.sensor)[2]
            residual = z_meas - z_pred
            self.position[2] = z_pred + 0.5 * residual
            self.velocity[2] += 0.2 * residual / CONTROL_DT
        else:
            self.position[2] = max(z_pred, self.body.rest_height)
            if self.position[2] <= self.body.rest_height:
                self.velocity[2] = 0.

        # Horizontal velocity: flow rate (rad/s) times range, in body axes,
        # rotated to world with the estimated attitude. Gyro compensation
        # leaves the gyro error in the measurement.
        self.flow_valid = self.range_valid and distance >= FLOW_MIN_RANGE
        if self.flow_valid:
            true_rot = rotation(obs[6:10])
            v_body = true_rot.T @ obs[3:6]
            noise = self.rng.normal(0, FLOW_SIGMA, 2) * distance
            rate_error = (rates - obs[10:13])[[1, 0]] * [1, -1] * distance
            v_xy = v_body[:2] + noise + rate_error
            world = rot @ np.r_[v_xy, v_body[2]]
            self.velocity[:2] = 0.7 * self.velocity[:2] + 0.3 * world[:2]
        elif not self.range_valid or distance < FLOW_MIN_RANGE:
            # On or near the floor: assume the pads hold the vehicle still.
            self.velocity[:2] *= 0.5
        self.position[:2] += self.velocity[:2] * CONTROL_DT
        return State(self.position.copy(), self.velocity.copy(), quat, rates)


class TrackingPD(LandingPD):
    """LandingPD's attitude and allocation loop with a position/velocity reference."""

    KP_XY, KD_XY = 2.0, 2.4
    KP_Z, KD_Z = 6.0, 4.5
    MAX_ACCEL_XY = 1.0

    def command(self, state, ref_pos, ref_vel, ref_acc, cut):
        body = self.body
        if cut:
            return np.array([0, 0, 0, 0, -1], dtype=np.float32), {"thrust_sat": False, "vane_sat": False}
        roll, pitch, yaw = euler(state.quat)
        error = ref_pos - state.position
        rate_error = ref_vel - state.velocity
        accel_z = ref_acc[2] + self.KP_Z * error[2] + self.KD_Z * rate_error[2]
        raw_thrust = body.mass * (GRAVITY + accel_z) / max(0.5, np.cos(roll) * np.cos(pitch))
        thrust = np.clip(raw_thrust, 0.1, MAX_THRUST)
        accel_xy = np.clip(ref_acc[:2] + self.KP_XY * error[:2] + self.KD_XY * rate_error[:2],
                           -self.MAX_ACCEL_XY, self.MAX_ACCEL_XY)
        c, s = np.cos(yaw), np.sin(yaw)
        target_roll = (s * accel_xy[0] - c * accel_xy[1]) / GRAVITY
        target_pitch = (c * accel_xy[0] + s * accel_xy[1]) / GRAVITY
        attitude_error = np.array([target_roll - roll, target_pitch - pitch, -yaw])
        torque = body.inertia @ (28 * attitude_error - 8 * state.rates)
        trim = np.cross(-body.cg, [0, 0, 1])
        commands = self.allocate @ (torque / thrust - trim)
        limits = {"thrust_sat": bool(raw_thrust > MAX_THRUST), "vane_sat": bool(np.any(np.abs(commands) > 1))}
        action = np.r_[np.clip(commands, -1, 1), 2 * np.sqrt(thrust / MAX_THRUST) - 1]
        return action.astype(np.float32), limits


def run(env, seed, feedback="truth"):
    """Run one mission. Returns per-step records and a summary dict."""
    if feedback not in ("truth", "estimated"):
        raise ValueError("feedback must be 'truth' or 'estimated'.")
    if env.max_steps < MISSION_STEPS:
        raise ValueError(f"LandingEnv(max_steps>={MISSION_STEPS}) is needed for the mission.")
    obs, _ = env.reset(seed=seed, options={"start": "ground", "pad_xy": PAD_XY})
    trajectory = Trajectory(obs[:2], env.airframe.rest_height)
    # A separate sensor-noise stream, so truth and estimated runs share the same env draws.
    estimator = Estimator(env.airframe, np.random.default_rng([seed % 2**32, 2]), obs[:2])
    controller = TrackingPD(env.airframe)
    records = []
    landing_started = False
    while True:
        t = env.data.time
        ref_pos, ref_vel, ref_acc = trajectory(t)
        phase = trajectory.phase(t)
        state = truth_state(obs) if feedback == "truth" else estimator(obs)
        landing_started |= phase in ("land", "settle")
        # Cut at the 3 mm height, or once the landing reference has ended below the floor.
        # The env lands only with the EDF ratio <= 0.10, and the PD thrust floor (0.1 N) is
        # a ratio of 0.1005, so a missed height cut (range noise) must not hold thrust forever.
        cut = landing_started and (state.position[2] - env.airframe.rest_height < TOUCHDOWN_CUT
                                   or phase == "settle")
        action, limits = controller.command(state, ref_pos, ref_vel, ref_acc, cut)
        next_obs, reward, terminated, truncated, info = env.step(action)
        records.append({
            "t": t, "phase": phase, "obs": obs, "action": action, "reward": reward,
            "ref_pos": ref_pos, "ref_vel": ref_vel, "est_pos": state.position, "est_vel": state.velocity,
            "range_valid": estimator.range_valid if feedback == "estimated" else True,
            "flow_valid": estimator.flow_valid if feedback == "estimated" else True,
            **limits,
        })
        obs = next_obs
        if terminated or truncated:
            break
    return records, summarize(records, obs, info, trajectory, env, seed, feedback)


def summarize(records, final_obs, info, trajectory, env, seed, feedback):
    phases = {}
    for name, _ in PHASES:
        rows = [r for r in records if r["phase"] == name]
        if not rows:
            phases[name] = None
            continue
        pos_err = np.array([np.linalg.norm(r["obs"][:3] - r["ref_pos"]) for r in rows])
        vel_err = np.array([np.linalg.norm(r["obs"][3:6] - r["ref_vel"]) for r in rows])
        est_err = np.array([np.linalg.norm(r["est_pos"] - r["obs"][:3]) for r in rows])
        phases[name] = {
            "pos_rms_m": float(np.sqrt(np.mean(pos_err**2))), "pos_max_m": float(pos_err.max()),
            "vel_rms_m_s": float(np.sqrt(np.mean(vel_err**2))), "vel_max_m_s": float(vel_err.max()),
            "est_pos_rms_m": float(np.sqrt(np.mean(est_err**2))),
        }
    tilt = [np.degrees(np.arccos(np.clip(rotation(r["obs"][6:10])[2, 2], -1, 1))) for r in records]
    touchdown = np.linalg.norm(final_obs[:2] - trajectory.target_xy)
    return {
        "seed": seed, "feedback": feedback, "outcome": info["outcome"], "airborne": info["airborne"],
        "time_s": info["time_s"], "steps": len(records), "impact_m_s": info["impact_m_s"],
        "pad_count": info["pad_count"],
        "touchdown_xy_error_m": float(touchdown),
        "max_tilt_deg": float(max(tilt)),
        "thrust_sat_fraction": float(np.mean([r["thrust_sat"] for r in records])),
        "vane_sat_fraction": float(np.mean([r["vane_sat"] for r in records])),
        "range_valid_fraction": float(np.mean([r["range_valid"] for r in records])),
        "flow_valid_fraction": float(np.mean([r["flow_valid"] for r in records])),
        "phases": phases,
    }


def reference_limits(trajectory, dt=CONTROL_DT):
    """Largest reference speed and acceleration over the whole mission."""
    times = np.arange(0., trajectory.end_time + dt, dt)
    samples = [trajectory(t) for t in times]
    speed = max(np.linalg.norm(v) for _, v, _ in samples)
    accel = max(np.linalg.norm(a) for _, _, a in samples)
    return float(speed), float(accel)


def tilt_limit_deg():
    """Largest commanded tilt from the horizontal acceleration clip."""
    return float(np.degrees(np.arctan(np.hypot(1, 1) * TrackingPD.MAX_ACCEL_XY / GRAVITY)))


__all__ = ["MISSION_STEPS", "PHASES", "Trajectory", "TrackingPD", "Estimator", "run",
           "reference_limits", "tilt_limit_deg"]
