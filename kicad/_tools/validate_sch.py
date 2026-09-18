"""Self-check for cosmos-avionics.kicad_sch since kicad-cli's headless ERC is
blocked on this machine (Windows Controlled Folder Access won't let kicad-cli
create its config dir under Documents - see kicad/README.md). Not a
replacement for real ERC, but catches the structural mistakes a hand-built
generator is most likely to make.
"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else \
    "C:/Users/mimin/Desktop/cosmos-tvc-hopper/kicad/cosmos-avionics/cosmos-avionics.kicad_sch"
text = open(path, encoding="utf-8").read()

errors = []
warnings = []

# 1. Paren balance (excluding parens inside quoted strings)
depth = 0
in_str = False
for i, c in enumerate(text):
    if c == '"' and text[i - 1] != '\\':
        in_str = not in_str
    elif not in_str:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0:
                errors.append(f"unbalanced ')' at char {i}")
if depth != 0:
    errors.append(f"file ends with paren depth {depth} (should be 0)")

# 2. every (lib_id "X:Y") used by a placed symbol must exist in lib_symbols
declared = set(re.findall(r'\(symbol "([A-Za-z0-9_]+:[A-Za-z0-9_]+)"', text))
used = set(re.findall(r'\(lib_id "([^"]+)"\)', text))
missing = used - declared
if missing:
    errors.append(f"lib_id used but not declared in lib_symbols: {missing}")

# 3. UUID uniqueness
uuids = re.findall(r'\(uuid "([0-9a-fA-F-]{36})"\)', text)
dupes = {x for x in uuids if uuids.count(x) > 1}
if dupes:
    errors.append(f"duplicate UUIDs: {dupes}")

# 4. every placed instance's pin count matches its lib symbol's declared pin count
# (rough check: count "(pin "" (uuid" occurrences per instance block vs number
# blocks in the matching lib_symbols entry)
lib_pin_counts = {}
for m in re.finditer(r'\(symbol "([A-Za-z0-9_]+:[A-Za-z0-9_]+)"', text):
    name = m.group(1)
    # crude: count (number "N" within next 4000 chars (enough for these small parts)
    seg = text[m.start():m.start() + 6000]
    lib_pin_counts[name] = len(re.findall(r'\(number "\d+"', seg))

inst_blocks = re.findall(
    r'\(symbol\s+\(lib_id "([^"]+)"\).*?\(instances', text, re.S)
for lib_id in inst_blocks:
    pass  # per-instance pin count check would need per-block slicing; skipped for now

# 5. net summary: each label text -> count of occurrences (labels sharing a
#    name are the same net on a flat sheet). Flag nets with fewer than 2 pins
#    (i.e. only one connection - almost certainly a mistake unless it's a
#    deliberately single-ended test point).
labels = re.findall(r'\(label "([^"]+)"', text)
from collections import Counter
net_counts = Counter(labels)
singletons = [n for n, c in net_counts.items() if c < 2]
if singletons:
    warnings.append(f"nets with only 1 connection (check intentional): {singletons}")

no_connects = len(re.findall(r"\(no_connect", text))

print(f"parens balanced: {'OK' if not any('paren' in e for e in errors) else 'FAIL'}")
print(f"lib_id references all declared: {'OK' if not missing else 'FAIL -> ' + str(missing)}")
print(f"UUIDs unique: {'OK' if not dupes else 'FAIL'}")
n_wires = len(re.findall(r"\(wire", text))
print(f"components placed: {len(inst_blocks)}")
print(f"wires: {n_wires}")
print(f"labels: {len(labels)}  distinct nets: {len(net_counts)}")
print(f"no_connect markers: {no_connects}")
print()
print("Net -> pin count:")
for n, c in sorted(net_counts.items()):
    print(f"  {n:20s} {c}")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(" -", e)
if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(" -", w)

sys.exit(1 if errors else 0)
