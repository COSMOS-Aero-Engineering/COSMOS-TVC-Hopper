"""Compare every exported KiCad XML pin/net with the generator's source (#66).

Usage: python kicad/_tools/check_netlist.py exported.xml
The input must come from kicad-cli sch export netlist --format kicadxml.
This checks the generated artifact, not label counts or only the source table.
"""
import argparse
from collections import defaultdict
import xml.etree.ElementTree as ET

from check_imu_nets import load_components, EXPECTED, J6_PIN_NAME


def check(path):
    actual = defaultdict(list)
    root = ET.parse(path).getroot()
    for net in root.findall("./nets/net"):
        nodes = net.findall("node")
        for node in nodes:
            actual[(node.get("ref"), node.get("pin"))].append(
                (net.get("name", "").removeprefix("/"), len(nodes), node.get("pintype", "")))
    expected = {(ref, pin): name for ref, _, _, _, pins in load_components() for pin, name in pins.items()}
    failures = []
    for key in sorted(actual.keys() | expected.keys()):
        name, found = expected.get(key), actual.get(key, [])
        if name == "__NC__":
            ok = len(found) == 1 and found[0][1] == 1 and "no_connect" in found[0][2]
        else:
            ok = name is not None and len(found) == 1 and found[0][0] == name
        if not ok:
            failures.append(f"{key[0]}.{key[1]} expected={name!r} actual={found!r}")
    for line in failures:
        print("FAIL:", line)
    print(f"Checked {len(expected)} pins; mismatches={len(failures)}")
    print("| IMU | J6 pin | Expected | Exported | Result |")
    print("|---|---|---|---|---|")
    for signal, _, name, _ in EXPECTED:
        signal = "WAK" if signal == "WAK/PS0" else signal
        pin = next(k for k, v in J6_PIN_NAME.items() if v == signal)
        found = actual.get(("J6", pin), [])
        value = found[0][0] if len(found) == 1 else "missing/duplicate"
        print(f"| {signal} | {pin} | {name} | {value} | {'PASS' if value == name else 'FAIL'} |")
    return not failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netlist")
    raise SystemExit(0 if check(parser.parse_args().netlist) else 1)
