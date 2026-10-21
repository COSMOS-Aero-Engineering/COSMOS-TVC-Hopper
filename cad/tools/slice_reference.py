"""Reference slicing mass only (#223), not a printer-ready job or measured mass.

Use PrusaSlicer 2.9.6 and the checked-in profile. Keep the G-code in a local
output directory. Input STL orientation is retained, support is disabled and
all slicer warnings are saved. Do not send this G-code to a printer.
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "cad/slicing/reference-0.4mm.ini"
PART_ROWS = {
    "top_plate": "top plate (printed)",
    "vane_ring": "vane ring + leg root bosses (printed)",
    "vanes_x4": "4 vanes (printed)",
    "edf_clamp": "EDF clamp (printed)",
    "battery_shelf": "battery shelf (printed)",
    "avionics_shelf": "avionics shelf (printed)",
    "esc_bracket": "ESC bracket (printed)",
    "vane_couplers_x4": "4 couplers (printed)",
}


def sha256(path, text=False):
    data = path.read_bytes()
    if text:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slicer", required=True, type=Path)
    parser.add_argument("--stls", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="Fresh local directory")
    args = parser.parse_args()
    version = subprocess.run([str(args.slicer), "--help"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", check=True)
    version_text = (version.stdout + version.stderr).splitlines()[0].strip()
    if not re.search(r"\b2\.9\.6\b", version_text):
        parser.error(f"Reference profile requires PrusaSlicer 2.9.6: {version_text}")
    args.out.mkdir(parents=True, exist_ok=False)
    result = []
    for name in PART_ROWS:
        stl = args.stls / f"{name}.stl"
        gcode = args.out / f"{name}.gcode"
        command = [str(args.slicer), "--datadir", str(args.out / "settings"),
                   "--load", str(PROFILE), "--export-gcode", "--threads", "2",
                   "--center", "250,250", "--output", str(gcode), str(stl)]
        run = subprocess.run(command, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=600)
        log = run.stdout + run.stderr
        (args.out / f"{name}.log").write_text(log, encoding="utf-8")
        if run.returncode:
            raise SystemExit(f"{name}: slicer failed ({run.returncode}); inspect its log")
        text = gcode.read_text(encoding="utf-8")
        masses = re.findall(r"^; filament used \[g\] = ([0-9.]+)\s*$", text, re.M)
        if len(masses) != 1 or float(masses[0]) <= 0:
            raise SystemExit(f"{name}: missing or invalid filament mass")
        result.append(dict(part=name, mass_g=float(masses[0]), stl_sha256=sha256(stl),
                           warnings=[line.strip() for line in log.splitlines()
                                     if any(word in line.lower() for word in
                                            ("warning", "floating", "loose extrusion", "support"))]))
        print(f"{name}: {masses[0]} g", flush=True)
    with (ROOT / "cad/cg/parts.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for item in result:
        matches = [row for row in rows if row["part"] == PART_ROWS[item["part"]]]
        if len(matches) != 1:
            raise SystemExit(f"Missing or ambiguous mass row: {item['part']}")
        matches[0]["mass_g"] = str(item["mass_g"])
        matches[0]["mass_source"] = "REFERENCE SLICER #223: PrusaSlicer2.9.6 profile; NOT measured; vendor settings unconfirmed"
    with (args.out / "parts-reference.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report = dict(slicer=version_text, profile_sha256=sha256(PROFILE, text=True),
                  text_hash_newlines="LF",
                  source_mass_table_sha256=sha256(ROOT / "cad/cg/parts.csv", text=True),
                  scope="Reference only. Input orientation retained; no support. G-code must not be printed.",
                  parts=result)
    (args.out / "slice-reference.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
