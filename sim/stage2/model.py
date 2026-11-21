"""Stage 2 rigid body and jet model. SI units, CAD axes (+X forward, +Y left)."""
import csv
from pathlib import Path

import mujoco
import numpy as np

from cad.cg import cg_estimate

PARTS = Path(cg_estimate.__file__).with_name("parts.csv")
GRAVITY = 9.81
MAX_THRUST = 9.9  # N, provisional 1.1e-6 * 3000**2 (experiment A pending)
MAX_ANGLE = np.deg2rad(10)
SERVO_RATE = np.deg2rad(600)
SERVO_TAU = 0.05
MOTOR_TAU = 0.05
JET_INNER, JET_OUTER, CHORD = 0.004, 0.032, 0.025
LIFT_SLOPE = 1.637
SIDE_GAIN = LIFT_SLOPE * (JET_OUTER - JET_INNER) * CHORD / (2 * np.pi * JET_OUTER**2)
PRESSURE_RADIUS = (JET_INNER + JET_OUTER) / 2
PIVOT_Z = cg_estimate.VANE_PIVOT_Z_MM / 1000
PAD_BOTTOM = -0.148  # foot_z - foot_pad_h in hopper_params.scad: -140 - 8 mm
PAD_RADIUS = 0.008
RADIAL = np.array([[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]])
SIDE_DIRECTION = np.array([[0, 1, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0]])
PHYSICS_DT = 0.004


def mass_properties():
    """Use the CAD mass discretization, including products of inertia about the CG."""
    with PARTS.open(encoding="utf-8", newline="") as stream:
        cloud = []
        for row in csv.DictReader(stream):
            for key in ("mass_g", "x", "y", "z", "p1", "p2", "p3"):
                row[key] = float(row[key])
            cloud.extend(cg_estimate.points(row))
    points = np.array(cloud)
    weights = points[:, 0]
    cg = np.average(points[:, 1:], axis=0, weights=weights)
    offsets = points[:, 1:] - cg
    second = (offsets.T * weights) @ offsets
    return weights.sum(), cg, np.trace(second) * np.eye(3) - second


def vector(values):
    return " ".join(str(float(v)) for v in values)


class Airframe:
    def __init__(self):
        self.mass, self.cg, self.inertia = mass_properties()
        self.vane_arms = RADIAL * PRESSURE_RADIUS + [0, 0, PIVOT_Z] - self.cg
        self.side_moments = np.cross(self.vane_arms, SIDE_DIRECTION)
        pad_xy = 0.180 * np.array([[1, 1], [-1, 1], [-1, -1], [1, -1]]) / np.sqrt(2)
        self.pad_centers = np.column_stack((pad_xy, np.full(4, PAD_BOTTOM + PAD_RADIUS))) - self.cg
        self.rest_height = self.cg[2] - PAD_BOTTOM

    def engine(self):
        # Body origin is CG, axes are CAD axes. MuJoCo rotates the inertial frame
        # internally to diagonalize fullinertia. Keep the CAD body frame for all loads.
        inertia = self.inertia
        six = inertia[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]]
        pads = "\n".join(
            f'<geom name="pad{i}" type="sphere" size="{PAD_RADIUS}" pos="{vector(p)}"/>'
            for i, p in enumerate(self.pad_centers)
        )
        shell = vector(np.array([0, 0, 0.046]) - self.cg)
        return mujoco.MjModel.from_xml_string(f"""
        <mujoco>
          <option timestep="{PHYSICS_DT}" gravity="0 0 -{GRAVITY}" integrator="implicitfast"/>
          <default><geom friction="0.7 0.005 0.0001" solref="0.016 1"/></default>
          <worldbody>
            <geom name="floor" type="plane" size="3 3 0.1"/>
            <body name="hopper">
              <freejoint/>
              <inertial pos="0 0 0" mass="{self.mass}" fullinertia="{vector(six)}"/>
              <geom name="housing" type="cylinder" size="0.036 0.046" pos="{shell}"/>
              {pads}
            </body>
          </worldbody>
        </mujoco>""")

    def wrench(self, motor, angles):
        """Equal jet sectors. Lateral loads act at the four centers of pressure."""
        thrust = MAX_THRUST * motor**2
        sector = thrust / 4
        limit = sector * np.sin(MAX_ANGLE)
        side = np.clip(thrust * SIDE_GAIN * angles, -limit, limit)
        # Turning a sector consumes axial momentum. The undeflected sectors
        # sum to a single EDF load along the exhaust axis.
        axial = np.sqrt(np.maximum(0, sector**2 - side**2))
        force = side @ SIDE_DIRECTION
        force[2] = axial.sum()
        # Each sector's axial load also acts at its own center of pressure.
        moment = side @ self.side_moments + axial @ np.cross(self.vane_arms, [0, 0, 1])
        return force, moment


def euler(quat):
    w, x, y, z = quat
    return np.array([
        np.arctan2(2 * (w*x + y*z), 1 - 2 * (x*x + y*y)),
        np.arcsin(np.clip(2 * (w*y - z*x), -1, 1)),
        np.arctan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z)),
    ])
