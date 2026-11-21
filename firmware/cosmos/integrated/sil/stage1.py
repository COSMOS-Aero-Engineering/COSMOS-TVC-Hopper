"""Feed Stage 1 attitude and body rates to the C++ SIL process each tick."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

from check import ROOT, snapshot

sys.path.insert(0, str(ROOT / "sim/sim_stage1"))
from export_episode import euler_zyx_to_quat
from hopper_aviary import HopperAttitudeEnv


def run(binary, output, seed):
    env = HopperAttitudeEnv(dt=0.01)
    env.dr["enabled"] = False
    # The C++ controller owns slew, including unconditional zero on disarm.
    env.throttle_slew_rate = None
    obs, _ = env.reset(seed=seed)
    with subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True, bufsize=1) as sil, output.open("x", encoding="utf-8") as log:
        try:
            header = sil.stdout.readline()
            log.write(header)
            reader = csv.DictReader(sil.stdout, fieldnames=header.strip().split(","))
            for step in range(env.max_steps):
                now = round(step * env.dt * 1000)
                request = snapshot(now, q=euler_zyx_to_quat(*obs[:3]), rates=obs[3:6],
                                   throttle=1000 if step == 0 else 2000,
                                   op="arm" if step == 0 else "-")
                sil.stdin.write(request + "\n")
                sil.stdin.flush()
                row = next(reader)
                if row["fsm"] != "ACTIVE" or row["source"] != "SIM":
                    raise ValueError(f"unexpected SIL state at {now} ms: {row}")
                log.write(",".join(row.values()) + "\n")
                action = [float(row[f"servo{i}"]) for i in range(1, 5)]
                applied = float(row["throttle"])
                obs, _, terminated, truncated, info = env.step([*action, 2 * applied - 1])
                if abs(info["throttle"] - applied) > 1e-6:
                    raise ValueError("Stage 1 used a different throttle from SIL")
                if terminated or truncated:
                    break
        finally:
            sil.stdin.close()
        if sil.wait() != 0:
            raise RuntimeError("SIL failed")
    print(f"Stage 1 SIL seed={seed}, ticks={step + 1}, terminated={terminated}, "
          f"truncated={truncated}, final roll/pitch (rad)={obs[:2]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path, help="new SIL CSV path")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    run(args.binary.resolve(), args.output, args.seed)
