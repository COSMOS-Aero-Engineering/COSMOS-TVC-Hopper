"""Read-only USB capture for COSMOS bench sketches. See data/README.md."""
import argparse
import base64
import csv
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

FIELDS = {
    "imu": "t_ms source mode phi theta psi qw qx qy qz",
    "servo": "host_ms source device_ms servo servo_us",
    "rc": "host_ms source device_ms ch1_us ch2_us ch3_us ch4_us ch5_us state throttle_out_us",
    "phase1": "host_ms source device_ms roll_deg servo_us",
    "integrated": ("t_ms source mode phi theta psi qw qx qy qz wx wy wz servo1 servo2 servo3 "
                   "servo4 throttle batt_v rpm reward fsm reason dry_run"),
}
ANGLES = re.compile(r"Roll:\s*(\S+)\s+Pitch:\s*(\S+)\s+Yaw:\s*(\S+)")


def decode_sample(profile, line, host_ms, source):
    if profile == "integrated":
        columns = FIELDS[profile].split()
        if line.startswith("#") or not line:
            return None
        cells = next(csv.reader([line], strict=True))
        if cells == columns:
            return None
        if len(cells) != len(columns):
            raise ValueError("integrated CSV column count")
        row = dict(zip(columns, cells))
        if not 0 <= int(row["t_ms"]) <= 0xffffffff or row["source"] not in {"SIM", "DRY_RUN"}:
            raise ValueError("invalid integrated source or time")
        if row["dry_run"] != "1" or any(v and not math.isfinite(float(v)) for v in cells[3:21]):
            raise ValueError("invalid dry-run row")
        if source == "FIXTURE":
            cells[1] = "FIXTURE"
        return cells
    if profile == "imu":
        match = ANGLES.fullmatch(line)
        if not match:
            if line.startswith("Roll:"):
                raise ValueError("bad IMU row")
            return None
        angles = [math.radians(float(x)) for x in match.groups()]
        if not all(map(math.isfinite, angles)):
            raise ValueError("nonfinite angle")
        cr, cp, cy = (math.cos(x / 2) for x in angles)
        sr, sp, sy = (math.sin(x / 2) for x in angles)
        return [host_ms, source, "MANUAL", *angles,
                cr*cp*cy + sr*sp*sy, sr*cp*cy - cr*sp*sy,
                cr*sp*cy + sr*cp*sy, cr*cp*sy - sr*sp*cy]
    if not line.startswith("D,"):
        return None
    fields = line.split(",")[1:]
    if len(fields) != (8 if profile == "rc" else 3):
        raise ValueError("wrong number of fields")
    ms = int(fields[0])
    if not 0 <= ms <= 0xffffffff:
        raise ValueError("invalid millis")
    if profile == "rc":
        *channels, state, output = fields[1:]
        channels = list(map(int, channels))
        output = int(output)
        if state not in {"OK", "KILL"} or any(v != 0 and not 800 <= v <= 2200 for v in channels):
            raise ValueError("bad receiver row")
        if (state == "KILL" and output != 0) or output != 0 and not 800 <= output <= 2200:
            raise ValueError("bad throttle")
        return [host_ms, source, ms, *channels, state, output]
    us = int(fields[2])
    if us != 0 and not 1000 <= us <= 2000:
        raise ValueError("bad pulse")
    if profile == "phase1":
        roll = float(fields[1])
        if not math.isfinite(roll):
            raise ValueError("bad roll")
        return [host_ms, source, ms, roll, us]
    servo = int(fields[1])
    if servo not in (1, 2):
        raise ValueError("bad servo channel")
    return [host_ms, source, ms, servo, us]


def capture(args):
    import serial
    if "://" in args.port and args.source != "FIXTURE":
        raise ValueError("URL ports require --source FIXTURE")
    if args.retries < 0 or not math.isfinite(args.seconds) or args.seconds < 0:
        raise ValueError("invalid time or retry count")
    start = time.monotonic()
    deadline = start + args.seconds if args.seconds else math.inf
    with args.output.open("x", encoding="utf-8") as out:
        def event(kind, **fields):
            out.write(json.dumps(dict(kind=kind, host_ms=round((time.monotonic()-start)*1000, 3),
                                      **fields), ensure_ascii=False) + "\n")
            out.flush()

        event("meta", version=1, utc=datetime.now(timezone.utc).isoformat(),
              profile=args.profile, source=args.source, firmware=args.firmware)
        try:
            for attempt in range(args.retries + 1):
                if time.monotonic() >= deadline:
                    break
                try:
                    with serial.serial_for_url(args.port, baudrate=115200, timeout=0.25) as port:
                        event("open", segment=attempt + 1)
                        while time.monotonic() < deadline:
                            chunk = port.read_until(b"\n", size=4096)
                            if chunk:
                                event("rx", b64=base64.b64encode(chunk).decode("ascii"))
                    break
                except (OSError, serial.SerialException) as exc:
                    event("lost", error=str(exc))
                    if attempt == args.retries:
                        raise
                    time.sleep(min(1.0, max(0.0, deadline-time.monotonic())))
        except KeyboardInterrupt:
            event("stop", reason="operator")
        else:
            event("stop", reason="duration")


def convert(raw, folder):
    folder.mkdir(parents=True, exist_ok=False)
    writer = handle = None
    profile = source = None
    pending = bytearray()
    dropping = False
    report = {"rows": 0, "bad_lines": 0, "partial_lines": 0, "segments": 0}
    try:
        with raw.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.endswith("\n"):
                    report["incomplete_record"] = True
                    break
                event = json.loads(line)
                kind = event["kind"]
                if kind == "meta":
                    if profile or event["version"] != 1 or event["profile"] not in FIELDS:
                        raise ValueError("invalid capture header")
                    profile, source = event["profile"], event["source"]
                    if source not in {"REAL", "FIXTURE"}:
                        raise ValueError("invalid source")
                elif kind in {"open", "lost", "stop"}:
                    if handle:
                        handle.close()
                        handle = writer = None
                    if pending or dropping:
                        report["partial_lines"] += 1
                    pending.clear()
                    dropping = False
                    if kind == "open":
                        if not profile:
                            raise ValueError("missing capture header")
                        report["segments"] += 1
                        name = f"{report['segments']:03}-{profile}.csv"
                        handle = (folder / name).open("x", encoding="utf-8", newline="")
                        writer = csv.writer(handle)
                        writer.writerow(FIELDS[profile].split())
                        epoch = float(event["host_ms"])
                elif kind == "rx":
                    if writer is None:
                        raise ValueError("data outside connection")
                    chunk = base64.b64decode(event["b64"], validate=True)
                    # capture reads at most one newline, always as the last byte.
                    if b"\n" in chunk[:-1]:
                        raise ValueError("invalid capture chunk")
                    if not dropping:
                        pending.extend(chunk)
                        if len(pending) > 16384:
                            pending.clear()
                            dropping = True
                            report["bad_lines"] += 1
                    if not chunk.endswith(b"\n"):
                        continue
                    if not dropping:
                        try:
                            row = decode_sample(profile, pending.decode("utf-8").strip(),
                                                round(float(event["host_ms"])-epoch, 3), source)
                        except (ValueError, OverflowError, csv.Error):
                            report["bad_lines"] += 1
                        else:
                            if row is not None:
                                writer.writerow(row)
                                report["rows"] += 1
                    pending.clear()
                    dropping = False
                else:
                    raise ValueError(f"unknown event {kind}")
        if pending or dropping:
            report["partial_lines"] += 1
    finally:
        if handle:
            handle.close()
    (folder / "summary.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    if not report["rows"]:
        raise ValueError("no usable rows; check profile and raw log")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    c = subs.add_parser("capture")
    c.add_argument("--port", required=True)
    c.add_argument("--profile", choices=FIELDS, required=True)
    c.add_argument("--source", choices=["REAL", "FIXTURE"], required=True)
    c.add_argument("--firmware", required=True, help="flashed revision or fixture generator")
    c.add_argument("--seconds", type=float, default=0)
    c.add_argument("--retries", type=int, default=0)
    c.add_argument("--output", type=Path, required=True)
    e = subs.add_parser("convert")
    e.add_argument("raw", type=Path)
    e.add_argument("out", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "capture":
            capture(args)
        else:
            print(json.dumps(convert(args.raw, args.out)))
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(1, str(exc)+"\n")


if __name__ == "__main__":
    main()
