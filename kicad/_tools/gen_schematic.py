"""Generate cosmos-avionics.kicad_sch from real KiCad library symbols.

Ground truth for file syntax/pin geometry was read directly from KiCad 10's
own bundled Arduino_Mega template and symbol libraries (extract_symbols.py) -
nothing here is guessed from memory.

Net list mirrors docs/design/01-avionics-integration-final.md SS2 (Teensy pin
map) and SS3 (power tree). This is a documentation-grade schematic capture
(generic connector symbols standing in for Teensy/BNO085/ESC/etc, since none
of those have official KiCad symbols) - not a fabrication-ready PCB source.
"""
import argparse
import math
import os
import re
import uuid as uuidlib
from pathlib import Path

from extract_symbols import extract_symbol, extract_pins

PROJECT_NAME = "cosmos-avionics"
ROOT_UUID = "b6a2f001-0000-4000-8000-000000000000"  # fixed so file is reproducible

HERE = Path(__file__).resolve().parent        # kicad/_tools
REPO_ROOT = HERE.parents[1]                   # repository root
DEFAULT_OUT = REPO_ROOT / "kicad" / "cosmos-avionics" / f"{PROJECT_NAME}.kicad_sch"


def u():
    return str(uuidlib.uuid4())


# ---------- library symbols needed (file path is resolved at run time) ----------
LIB_FILES = {
    "Connector_Generic": "Connector_Generic.kicad_sym",
    "Device": "Device.kicad_sym",
    "Switch": "Switch.kicad_sym",
}

LIB_SYMBOLS = {
    "Connector_Generic:Conn_01x01": "Conn_01x01",
    "Connector_Generic:Conn_01x03": "Conn_01x03",
    "Connector_Generic:Conn_01x04": "Conn_01x04",
    "Connector_Generic:Conn_01x05": "Conn_01x05",
    "Connector_Generic:Conn_01x06": "Conn_01x06",
    "Connector_Generic:Conn_01x07": "Conn_01x07",
    "Connector_Generic:Conn_01x08": "Conn_01x08",
    "Connector_Generic:Conn_01x10": "Conn_01x10",
    "Device:C": "C",
    "Device:Battery": "Battery",
    "Switch:SW_SPST": "SW_SPST",
}


def _kicad_version_key(path):
    """Sort key that orders KiCad version folders numerically: 9.0 before 10.0."""
    m = re.search(r"KiCad[/\\]([0-9]+(?:\.[0-9]+)*)", str(path))
    return tuple(int(part) for part in m.group(1).split(".")) if m else (0,)


def _has_libraries(path):
    return all((path / f).is_file() for f in LIB_FILES.values())


def _symbol_dir_candidates():
    """Yield places KiCad's bundled symbol libraries might live, best first."""
    # 1. KiCad's own environment variables. An explicit KICAD_SYMBOL_DIR wins,
    #    then the versioned names (KICAD10_SYMBOL_DIR, KICAD9_SYMBOL_DIR, ...)
    #    from the newest major version down. Compare versions as numbers: a plain
    #    string sort puts KICAD9 before KICAD10.
    unversioned = os.environ.get("KICAD_SYMBOL_DIR")
    if unversioned:
        yield Path(unversioned)
    versioned = [n for n in os.environ if re.fullmatch(r"KICAD\d+_SYMBOL_DIR", n)]
    for name in sorted(versioned, key=lambda n: int(re.search(r"\d+", n).group()),
                       reverse=True):
        value = os.environ.get(name)
        if value:
            yield Path(value)
    # 2. Common install locations, newest KiCad version first.
    if os.name == "nt":
        for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles"),
                     os.environ.get("ProgramFiles(x86)")):
            if not base:
                continue
            for pattern in ("Programs/KiCad/*/share/kicad/symbols",
                            "KiCad/*/share/kicad/symbols"):
                yield from sorted(Path(base).glob(pattern),
                                  key=_kicad_version_key, reverse=True)
    else:
        for fixed in ("/usr/share/kicad/symbols", "/usr/local/share/kicad/symbols",
                      "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"):
            yield Path(fixed)
        yield from sorted(
            Path("/Applications").glob("KiCad*/KiCad.app/Contents/SharedSupport/symbols"),
            key=_kicad_version_key, reverse=True,
        )


def find_symbols_dir(override):
    """Return the directory that holds KiCad's bundled .kicad_sym files."""
    if override:
        path = Path(override)
        if not _has_libraries(path):
            raise SystemExit(
                f"--kicad-symbols does not hold KiCad's symbol libraries: {path}\n"
                f"  expected files: {', '.join(sorted(LIB_FILES.values()))}"
            )
        return path
    for candidate in _symbol_dir_candidates():
        try:
            if _has_libraries(candidate):
                return candidate
        except OSError:
            continue
    raise SystemExit(
        "KiCad's symbol libraries were not found. Pass --kicad-symbols <dir>, or set\n"
        "KICAD_SYMBOL_DIR (or KICAD10_SYMBOL_DIR). Usual place on Windows:\n"
        r"  %LOCALAPPDATA%\Programs\KiCad\<version>\share\kicad\symbols"
    )


def build_lib_sources(symbols_dir):
    """Map lib_id -> (symbol library file, symbol name) for the parts we embed."""
    sources = {}
    for lib_id, symbol in LIB_SYMBOLS.items():
        lib = lib_id.split(":")[0]
        sources[lib_id] = (str(Path(symbols_dir) / LIB_FILES[lib]), symbol)
    return sources

# ---------- components: (ref, lib_id, value, position(x,y mm), {pin: net_or_None}) ----------
NC = "__NC__"
COMPONENTS = [
    ("J1", "Connector_Generic:Conn_01x04", "Teensy D2-D5 (Vane Servo Out)", (25, 25),
     {"1": "SERVO1_FWD", "2": "SERVO2_LEFT", "3": "SERVO3_AFT", "4": "SERVO4_RIGHT"}),
    ("J2", "Connector_Generic:Conn_01x05", "Teensy D18,19,23,1,9 (RC In, PWM)", (25, 65),
     {"1": "RC_CH1_3V3", "2": "RC_CH2_3V3", "3": "RC_CH3_3V3", "4": "RC_CH4_3V3", "5": "RC_CH5_3V3"}),
    ("J3", "Connector_Generic:Conn_01x07", "Teensy D10-13,20-22 (IMU SPI)", (25, 105),
     {"1": "IMU_CS", "2": "IMU_MOSI", "3": "IMU_MISO", "4": "IMU_SCK",
      "5": "IMU_RST", "6": "IMU_INT", "7": "IMU_WAK"}),
    ("J4", "Connector_Generic:Conn_01x01", "Teensy D8 (DShot to ESC)", (25, 150),
     {"1": "DSHOT"}),
    ("J5", "Connector_Generic:Conn_01x03", "Teensy Power (3V3,VIN,GND)", (25, 168),
     {"1": "+3V3", "2": NC, "3": "GND"}),

    ("J6", "Connector_Generic:Conn_01x10", "BNO085 IMU (CS,SCK,MOSI,MISO,INT,RST,WAK,PS1,VIN,GND)", (95, 105),
     {"1": "IMU_CS", "2": "IMU_SCK", "3": "IMU_MOSI", "4": "IMU_MISO", "5": "IMU_INT",
      "6": "IMU_RST", "7": "IMU_WAK", "8": "+3V3", "9": "+3V3", "10": "GND"}),

    ("U1", "Connector_Generic:Conn_01x06", "Level Shifter #1 (RC CH1,CH2)", (95, 45),
     {"1": "RC_CH1_5V", "2": "RC_CH1_3V3", "3": "RC_CH2_5V", "4": "RC_CH2_3V3",
      "5": "+5V", "6": "+3V3"}),
    ("U2", "Connector_Generic:Conn_01x08", "Level Shifter #2 (RC CH3,CH4,CH5)", (95, 65),
     {"1": "RC_CH3_5V", "2": "RC_CH3_3V3", "3": "RC_CH4_5V", "4": "RC_CH4_3V3",
      "5": "RC_CH5_5V", "6": "RC_CH5_3V3", "7": "+5V", "8": "+3V3"}),

    ("J7", "Connector_Generic:Conn_01x07", "RC RX FS-iA6B (CH1-5,+5V,GND)", (155, 55),
     {"1": "RC_CH1_5V", "2": "RC_CH2_5V", "3": "RC_CH3_5V", "4": "RC_CH4_5V",
      "5": "RC_CH5_5V", "6": "+5V", "7": "GND"}),

    ("S1", "Connector_Generic:Conn_01x03", "MG90S Servo FWD (Sig,5V,GND)", (155, 105),
     {"1": "SERVO1_FWD", "2": "+5V", "3": "GND"}),
    ("S2", "Connector_Generic:Conn_01x03", "MG90S Servo LEFT (Sig,5V,GND)", (155, 118),
     {"1": "SERVO2_LEFT", "2": "+5V", "3": "GND"}),
    ("S3", "Connector_Generic:Conn_01x03", "MG90S Servo AFT (Sig,5V,GND)", (155, 131),
     {"1": "SERVO3_AFT", "2": "+5V", "3": "GND"}),
    ("S4", "Connector_Generic:Conn_01x03", "MG90S Servo RIGHT (Sig,5V,GND)", (155, 144),
     {"1": "SERVO4_RIGHT", "2": "+5V", "3": "GND"}),

    ("ESC1", "Connector_Generic:Conn_01x07", "ESC 60A DShot (Sig,GND,Batt+,Batt-,PhA,PhB,PhC)", (95, 150),
     {"1": "DSHOT", "2": "GND", "3": "+BATT", "4": "GND",
      "5": "MOTOR_A", "6": "MOTOR_B", "7": "MOTOR_C"}),
    ("M1", "Connector_Generic:Conn_01x03", "64mm EDF Motor (3-phase)", (155, 165),
     {"1": "MOTOR_A", "2": "MOTOR_B", "3": "MOTOR_C"}),

    ("U3", "Connector_Generic:Conn_01x03", "UBEC 5V/5A (IN,OUT,GND)", (205, 150),
     {"1": "+BATT", "2": "+5V", "3": "GND"}),
    ("C1", "Device:C", "470uF/35V (ESC input)", (115, 175),
     {"1": "+BATT", "2": "GND"}),
    ("C2", "Device:C", "470uF (UBEC output)", (225, 150),
     {"1": "+5V", "2": "GND"}),

    ("SW1", "Switch:SW_SPST", "Physical kill switch (>=80A)", (205, 180),
     {"1": "BATT_RAW", "2": "+BATT"}),
    ("BT1", "Device:Battery", "4S LiPo 1300mAh 75C", (205, 200),
     {"1": "BATT_RAW", "2": "GND"}),
]

STUB_LEN = 5.08  # mm, one grid unit beyond the pin's own length


def load_libs(sources):
    cache = {}
    for lib_id, (path, name) in sources.items():
        block = extract_symbol(path, name)
        pins = extract_pins(block)
        lib, sym = lib_id.split(":")
        # rename the top-level id to "Lib:Name" the way eeschema embeds it
        block = re.sub(r'^\(symbol "' + re.escape(sym) + '"',
                        f'(symbol "{lib_id}"', block, count=1)
        cache[lib_id] = {"block": block, "pins": pins}
    return cache


def emit_lib_symbols(cache, sources):
    out = ["\t(lib_symbols"]
    for lib_id in sources:
        # indent each line of the block by one extra tab
        block = cache[lib_id]["block"]
        indented = "\n".join(("\t\t" + line if line else line) for line in block.split("\n"))
        out.append(indented)
    out.append("\t)")
    return "\n".join(out)


def pin_world_pos(comp_pos, pin_local):
    x, y, ang = pin_local
    return (comp_pos[0] + x, comp_pos[1] + y, ang)


def emit_component_instance(ref, lib_id, value, pos, pins_by_num):
    x, y = pos
    lines = []
    lines.append("\t(symbol")
    lines.append(f'\t\t(lib_id "{lib_id}")')
    lines.append(f"\t\t(at {x} {y} 0)")
    lines.append("\t\t(unit 1)")
    lines.append("\t\t(exclude_from_sim no)")
    lines.append("\t\t(in_bom yes)")
    lines.append("\t\t(on_board yes)")
    lines.append("\t\t(dnp no)")
    inst_uuid = u()
    lines.append(f'\t\t(uuid "{inst_uuid}")')
    lines.append(f'\t\t(property "Reference" "{ref}"')
    lines.append(f"\t\t\t(at {x} {y - 4} 0)")
    lines.append("\t\t\t(effects (font (size 1.27 1.27)))")
    lines.append("\t\t)")
    lines.append(f'\t\t(property "Value" "{value}"')
    lines.append(f"\t\t\t(at {x} {y + 4} 0)")
    lines.append("\t\t\t(effects (font (size 1.0 1.0)))")
    lines.append("\t\t)")
    lines.append('\t\t(property "Footprint" ""')
    lines.append(f"\t\t\t(at {x} {y} 0)")
    lines.append("\t\t\t(effects (font (size 1.27 1.27)) (hide yes))")
    lines.append("\t\t)")
    for n in sorted(pins_by_num.keys(), key=lambda s: int(s)):
        lines.append(f'\t\t(pin "{n}" (uuid "{u()}"))')
    lines.append("\t\t(instances")
    lines.append(f'\t\t\t(project "{PROJECT_NAME}"')
    lines.append(f'\t\t\t\t(path "/{ROOT_UUID}"')
    lines.append(f'\t\t\t\t\t(reference "{ref}")')
    lines.append("\t\t\t\t\t(unit 1)")
    lines.append("\t\t\t\t)")
    lines.append("\t\t\t)")
    lines.append("\t\t)")
    lines.append("\t)")
    return "\n".join(lines), inst_uuid


def emit_wire(p1, p2):
    return (
        "\t(wire\n"
        f"\t\t(pts (xy {p1[0]:.3f} {p1[1]:.3f}) (xy {p2[0]:.3f} {p2[1]:.3f}))\n"
        "\t\t(stroke (width 0) (type solid))\n"
        f'\t\t(uuid "{u()}")\n'
        "\t)"
    )


def emit_label(text, pos, angle):
    justify = "left" if math.cos(math.radians(angle)) >= 0 else "right"
    return (
        f'\t(label "{text}"\n'
        f"\t\t(at {pos[0]:.3f} {pos[1]:.3f} {angle:g})\n"
        f"\t\t(effects (font (size 1.27 1.27)) (justify {justify} bottom))\n"
        f'\t\t(uuid "{u()}")\n'
        "\t)"
    )


def emit_no_connect(pos):
    return f'\t(no_connect (at {pos[0]:.3f} {pos[1]:.3f}) (uuid "{u()}"))'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kicad-symbols", metavar="DIR",
                        help="KiCad symbol library directory (default: auto-detect)")
    parser.add_argument("--out", metavar="FILE", default=str(DEFAULT_OUT),
                        help="output .kicad_sch (default: %(default)s)")
    args = parser.parse_args()

    sources = build_lib_sources(find_symbols_dir(args.kicad_symbols))
    cache = load_libs(sources)
    parts = []
    wires = []
    labels = []
    ncs = []

    for ref, lib_id, value, pos, pinmap in COMPONENTS:
        inst_text, _ = emit_component_instance(ref, lib_id, value, pos, pinmap)
        parts.append(inst_text)
        pin_geo = cache[lib_id]["pins"]
        for pin_num, net in pinmap.items():
            local = pin_geo[pin_num]
            wx, wy, wang = pin_world_pos(pos, local)
            if net == NC:
                ncs.append(emit_no_connect((wx, wy)))
                continue
            # stub extends AWAY from the symbol body: opposite of the pin's own angle
            dx = -math.cos(math.radians(wang))
            dy = -math.sin(math.radians(wang))
            ex, ey = wx + dx * STUB_LEN, wy + dy * STUB_LEN
            wires.append(emit_wire((wx, wy), (ex, ey)))
            labels.append(emit_label(net, (ex, ey), wang))

    lib_symbols_block = emit_lib_symbols(cache, sources)

    doc = []
    doc.append("(kicad_sch")
    doc.append("\t(version 20250114)")
    doc.append('\t(generator "cosmos-schematic-generator")')
    doc.append('\t(generator_version "1.0")')
    doc.append(f'\t(uuid "{ROOT_UUID}")')
    doc.append('\t(paper "A3")')
    doc.append("\t(title_block")
    doc.append('\t\t(title "COSMOS TVC Hopper - Avionics Schematic (rev C.1 capture)")')
    doc.append('\t\t(date "2026-09-18")')
    doc.append('\t\t(rev "C.1")')
    doc.append('\t\t(company "COSMOS Aero Engineering")')
    doc.append('\t\t(comment 1 "Source: docs/design/01-avionics-integration-final.md SS2 (pin map), SS3 (power tree)")')
    doc.append('\t\t(comment 2 "Generic Connector_Generic symbols stand in for Teensy 4.0 / BNO085 / ESC / UBEC / level shifters - none have official KiCad parts yet")')
    doc.append("\t)")
    doc.append(lib_symbols_block)
    doc.extend(parts)
    doc.extend(wires)
    doc.extend(labels)
    doc.extend(ncs)
    doc.append("\t(sheet_instances")
    doc.append('\t\t(path "/"')
    doc.append('\t\t\t(page "1")')
    doc.append("\t\t)")
    doc.append("\t)")
    doc.append(")")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(doc) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"{len(parts)} components, {len(wires)} wires, {len(labels)} labels, {len(ncs)} NC markers")


if __name__ == "__main__":
    main()
