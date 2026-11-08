"""Host tests. The TCP peer supplies synthetic USB bytes through pySerial."""
import argparse
import base64
import csv
import json
import math
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from capture_bench import capture, convert, decode_sample


class BenchCapture(unittest.TestCase):
    def test_two_connections_and_web_csv(self):
        with tempfile.TemporaryDirectory() as tmp, socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            listener.settimeout(8)
            raw = Path(tmp) / "capture.jsonl"
            def events():
                if not raw.exists():
                    return []
                return [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines(keepends=True)
                        if line.endswith("\n")]

            def wait_for(predicate):
                until = time.monotonic() + 6
                while time.monotonic() < until:
                    if predicate(events()):
                        return
                    time.sleep(0.02)
                raise AssertionError("capture did not flush expected event")

            def peer():
                received = b""
                for i, session in enumerate((b"Roll: 90\tPitch: 0\tYaw: 0\r\nRoll:", b"Roll: 0\tPitch: 0\tYaw: 0\n"), 1):
                    with listener.accept()[0] as client:
                        wait_for(lambda log: sum(e["kind"] == "open" for e in log) == i)
                        client.sendall(session)
                        received += session
                        wait_for(lambda log: b"".join(base64.b64decode(e["b64"]) for e in log
                                                      if e["kind"] == "rx") == received)
            worker = threading.Thread(target=peer, daemon=True)
            worker.start()
            args = argparse.Namespace(port=f"socket://127.0.0.1:{listener.getsockname()[1]}",
                profile="imu", source="FIXTURE", firmware="host-test", seconds=8, retries=1, output=raw)
            # Second unplug is an error after both segments have been flushed.
            import serial
            with self.assertRaises(serial.SerialException):
                capture(args)
            worker.join(1)
            self.assertFalse(worker.is_alive())
            rx = [base64.b64decode(e["b64"]) for e in map(json.loads, raw.read_text().splitlines())
                  if e["kind"] == "rx"]
            self.assertEqual(b"".join(rx), b"Roll: 90\tPitch: 0\tYaw: 0\r\nRoll:Roll: 0\tPitch: 0\tYaw: 0\n")
            out = Path(tmp) / "export"
            report = convert(raw, out)
            self.assertEqual([report[k] for k in ("rows","segments","partial_lines")], [2,2,1])
            with (out/"001-imu.csv").open() as f:
                row, = csv.DictReader(f)
            self.assertEqual(row["source"], "FIXTURE")
            self.assertAlmostEqual(float(row["qx"]), math.sin(math.pi/4))
            self.assertAlmostEqual(float(row["phi"]), math.pi/2)
            with self.assertRaises(FileExistsError):
                convert(raw, out)

    def test_no_fabricated_attitude(self):
        self.assertEqual(decode_sample("servo","D,20,1,0",2,"REAL"), [2,"REAL",20,1,0])
        self.assertEqual(decode_sample("phase1","D,101,2.5,1500",5,"REAL"), [5,"REAL",101,2.5,1500])
        self.assertEqual(decode_sample("rc","D,20,0,0,0,0,0,KILL,0",1,"REAL")[-2:], ["KILL",0])
        with self.assertRaises(ValueError):
            decode_sample("rc","D,20,0,0,0,0,0,KILL,1000",1,"REAL")
        with self.assertRaises(ValueError):
            decode_sample("imu","Roll: nan Pitch: 2 Yaw: 3",1,"REAL")

    def test_dry_run_does_not_become_flight_data(self):
        line = "1,DRY_RUN,PID,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,,,,DISARMED,OK,1"
        self.assertEqual(decode_sample("integrated",line,10,"REAL")[1], "DRY_RUN")
        self.assertEqual(decode_sample("integrated",line,10,"FIXTURE")[1], "FIXTURE")
        with self.assertRaises(ValueError):
            decode_sample("integrated",line.replace("DRY_RUN","REAL"),10,"REAL")


if __name__ == "__main__":
    unittest.main()
