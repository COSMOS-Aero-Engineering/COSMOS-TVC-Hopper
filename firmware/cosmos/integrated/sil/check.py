"""Run regression scenarios through the compiled SIL executable and its CSV writer."""
import argparse
import csv
import io
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STOP = ("servo1", "servo2", "servo3", "servo4", "throttle")


def snapshot(now, *, attitude=None, gyro=None, ch1=None, ch5=None, op="-",
             q=(1, 0, 0, 0), rates=(0, 0, 0), throttle=1000, kill=1800):
    def stamp(t):
        return now if t is None else t

    return " ".join(map(str, (now, stamp(attitude), *q, stamp(gyro), *rates,
                              stamp(ch1), throttle, stamp(ch5), kill, op)))


def replay(binary, lines):
    data = subprocess.run([binary], input="\n".join(lines) + "\n", capture_output=True,
                          text=True, check=True).stdout
    rows = list(csv.DictReader(io.StringIO(data)))
    assert len(rows) == len(lines)
    for row in rows:
        assert None not in row and None not in row.values()
        assert (row["source"], row["dry_run"], row["mode"]) == ("SIM", "1", "PID")
        assert all(row[c] == "" for c in ("rpm", "batt_v", "reward"))
    return rows


def stopped(row, state, reason):
    assert (row["fsm"], row["reason"]) == (state, reason), row
    assert all(float(row[c]) == 0 for c in STOP), row


def check(binary):
    angle = 0.05
    roll = (math.cos(angle / 2), math.sin(angle / 2), 0, 0)
    lines = [
        snapshot(0, attitude=-1, gyro=-1, ch1=-1, ch5=-1, op="arm"),
        snapshot(10, op="arm", throttle=1051),
        snapshot(20, op="arm"),
        snapshot(30, throttle=2000, q=roll, rates=(0.1, 0.7, 0)),
        snapshot(47, throttle=2000),
        snapshot(60),
        snapshot(70, kill=1499),
        snapshot(80, op="arm"),
        snapshot(90, op="disarm"),
        snapshot(100, op="arm", throttle=1050, kill=1500),
        snapshot(110, throttle=2000),
        snapshot(120, op="disarm", throttle=2000),
    ]
    rows = replay(binary, lines)
    stopped(rows[0], "DISARMED", "RC_INVALID")
    stopped(rows[1], "DISARMED", "ARM_THROTTLE_HIGH")
    stopped(rows[2], "ACTIVE", "OK")
    action = [float(rows[3][key]) for key in STOP[:4]]
    assert all(math.isclose(x, y, abs_tol=1e-6) for x, y in zip(action, [-0.6, 1, -0.6, 1]))
    assert math.isclose(float(rows[3]["phi"]), angle, abs_tol=1e-7)
    yaml = (ROOT / "sim/sim_stage1/params.yaml").read_text(encoding="utf-8")
    rate = float(re.search(r"^throttle_slew_rate:\s*([.\d]+)", yaml, re.M)[1])
    for row, ms in zip(rows[3:6], (10, 27, 14)):
        assert math.isclose(float(row["throttle"]), rate * ms / 1000, abs_tol=1e-8)
    stopped(rows[6], "FAILSAFE", "KILL")
    stopped(rows[7], "FAILSAFE", "KILL")
    stopped(rows[8], "DISARMED", "DISARM")
    stopped(rows[9], "ACTIVE", "OK")
    assert float(rows[10]["throttle"]) > 0
    stopped(rows[11], "DISARMED", "DISARM")

    # Force each failure from a nonzero command. Ages just below each timeout still pass.
    cases = [
        ({"attitude": 51}, "ATTITUDE_INVALID"), ({"gyro": 51}, "GYRO_INVALID"),
        ({"ch1": 1}, "RC_INVALID"), ({"ch5": 1}, "RC_INVALID"),
        ({"q": (0, 0, 0, 0)}, "ATTITUDE_INVALID"),
        ({"kill": 2201}, "RC_INVALID"), ({"throttle": 799}, "RC_INVALID"),
        ({"ch5": -1}, "RC_INVALID"), ({"gyro": -1}, "GYRO_INVALID"),
    ]
    for args, reason in cases:
        rows = replay(binary, [snapshot(80, op="arm"),
                               snapshot(100, throttle=2000, attitude=51, gyro=51, ch1=1, ch5=1),
                               snapshot(101, **args), snapshot(111, op="arm")])
        assert float(rows[1]["throttle"]) > 0
        stopped(rows[2], "FAILSAFE", reason)
        stopped(rows[3], "FAILSAFE", reason)
        if reason == "ATTITUDE_INVALID":
            assert rows[2]["qw"] == ""
        if reason == "GYRO_INVALID":
            assert rows[2]["wx"] == ""

    wrap = 2**32
    rows = replay(binary, [snapshot(wrap - 16, op="arm"), snapshot(wrap - 6, throttle=2000),
                           snapshot(4, attitude=wrap - 6, gyro=wrap - 6, throttle=2000),
                           snapshot(54)])
    assert math.isclose(float(rows[2]["throttle"]), 0.005, abs_tol=1e-8)
    stopped(rows[3], "FAILSAFE", "LOOP_GAP")

    bad = subprocess.run([binary], input="10 invalid\n", text=True, capture_output=True)
    assert bad.returncode == 2 and "line 1" in bad.stderr
    print("SIL passed: arm, PD axes, clipping, bidirectional slew, kill, disarm, "
          "fault latch, input expiration, loop gap, unsigned wrap, CSV and invalid input")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    check(parser.parse_args().binary.resolve())
