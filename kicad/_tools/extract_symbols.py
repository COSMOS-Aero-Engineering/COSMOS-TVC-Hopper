"""Extract exact top-level symbol S-expr blocks + pin geometry from real KiCad
library files, by balancing parens (no hand-typed geometry, no guessing)."""
import re
import sys

def find_balanced_block(text, start_idx):
    """Given index of the opening '(' , return (block_text, end_idx_exclusive)."""
    depth = 0
    i = start_idx
    in_str = False
    while i < len(text):
        c = text[i]
        if c == '"' and text[i-1] != '\\':
            in_str = not in_str
        elif not in_str:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return text[start_idx:i+1], i + 1
        i += 1
    raise ValueError("unbalanced")

def extract_symbol(filepath, symbol_name):
    text = open(filepath, encoding="utf-8").read()
    # top-level symbol def: (symbol "NAME"   <-- exact name, then whitespace or quote-close
    pat = re.compile(r'\(symbol "' + re.escape(symbol_name) + r'"')
    m = pat.search(text)
    if not m:
        raise ValueError(f"{symbol_name} not found in {filepath}")
    start = m.start()
    block, _ = find_balanced_block(text, start)
    return block

def extract_pins(block):
    """Return {pin_number: (x, y, angle)} from a top-level symbol block."""
    pins = {}
    for m in re.finditer(r'\(pin\s', block):
        pin_block, _ = find_balanced_block(block, m.start())
        at_m = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)', pin_block)
        num_m = re.search(r'\(number\s+"([^"]+)"', pin_block)
        if at_m and num_m:
            pins[num_m.group(1)] = (float(at_m.group(1)), float(at_m.group(2)), float(at_m.group(3)))
    return pins

if __name__ == "__main__":
    import json
    lib_path = sys.argv[1]
    sym_name = sys.argv[2]
    block = extract_symbol(lib_path, sym_name)
    pins = extract_pins(block)
    print(f"=== {sym_name}: {len(pins)} pins ===")
    print(json.dumps(pins, indent=2))
