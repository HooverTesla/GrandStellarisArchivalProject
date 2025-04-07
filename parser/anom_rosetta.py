import os
import re
import json
from pathlib import Path

# === CONFIGURATION ===
BASE_PATH = Path(__file__).resolve().parent.parent
LOCALISATION_PATH = BASE_PATH / "input" / "localisation"
ANOMALY_PATH = BASE_PATH / "input" / "anomalies"
#OUTPUT
OUTPUT_PATH = BASE_PATH / "output"
# Gets filename without .py
SCRIPT_NAME = Path(__file__).stem
#CREATE JSON
OUTPUT_FILE = OUTPUT_PATH / f"{SCRIPT_NAME}.json"
OUTPUT_PATH.mkdir(exist_ok=True)

def parse_pdx_block(lines):
    stack = []
    current = {}
    key = None

    def finalize(key, value):
        if isinstance(stack[-1], dict):
            stack[-1][key] = value
        elif isinstance(stack[-1], list):
            stack[-1].append(value)

    stack.append(current)

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Open new block
        if "{" in line:
            if "=" in line:
                key, _ = line.split("=", 1)
                key = key.strip()
                new = {}
                finalize(key, new)
                stack.append(new)
            else:
                new = {}
                stack.append(new)
        elif "}" in line:
            stack.pop()
        elif "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"')
            if v.isdigit():
                v = int(v)
            finalize(k, v)

    return current

# === EXTRACTION ===
all_data = {}
total_blocks = 0

for file in ANOMALY_PATH.glob("*.txt"):
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_key = None
    current_block = []
    bracket_level = 0
    file_blocks = {}

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if bracket_level == 0 and "=" in stripped and "{" in stripped:
            current_key = stripped.split("=")[0].strip()
            current_block = [line]
            bracket_level += line.count("{") - line.count("}")
        elif bracket_level > 0:
            current_block.append(line)
            bracket_level += line.count("{") - line.count("}")
            if bracket_level == 0:
                file_blocks[current_key] = parse_pdx_block(current_block)
                total_blocks += 1
                current_key = None
                current_block = []

    all_data[file.name] = file_blocks
# === OUTPUT ===
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    json.dump(all_data, out, indent=2)

print(f"Exported {total_blocks} Anomalies to: {OUTPUT_FILE}")