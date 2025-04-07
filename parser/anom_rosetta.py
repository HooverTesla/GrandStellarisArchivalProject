import os
import re
import pandas as pd
from pathlib import Path

# === CONFIGURATION ===
BASE_PATH = Path(__file__).resolve().parent.parent
# LOCALISATION_PATH = BASE_PATH / "input" / "localisation"
ANOMALY_PATH = BASE_PATH / "input" / "anomalies"
OUTPUT_PATH = BASE_PATH / "output"
SCRIPT_NAME = Path(__file__).stem  # Gets filename without .py
OUTPUT_FILE = OUTPUT_PATH / f"{SCRIPT_NAME}.csv"
OUTPUT_PATH.mkdir(exist_ok=True)

anomaly_blocks = []
for file in ANOMALY_PATH.glob("*.txt"):
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    file_variables = {}
    current_id = None
    block_lines = []
    bracket_level = 0

    for i, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith("#"):
            continue  # ⬅️ Skip full-line comments
        # find  @foo with the assigned value from the beginning of the file replaces later
        var_match = re.match(r'(@\w+)\s*=\s*(\d+)', line.strip())
        if var_match:
          var_name, var_value = var_match.groups()
          file_variables[var_name] = var_value


        # Detect block start
        if bracket_level == 0 and "=" in line_strip and "{" in line_strip:
            possible_id = line_strip.split("=")[0].strip()
            if re.match(r"^[\w.]+$", possible_id):
                current_id = possible_id
                block_lines = [line]
                bracket_level += line.count("{") - line.count("}")
                continue

        elif bracket_level > 0:
            block_lines.append(line)
            bracket_level += line.count("{") - line.count("}")

            # Block ends when bracket_level returns to 0
            if bracket_level == 0:
                full_block = "".join(block_lines)
                if "level" in full_block:  # keep if level= exists in *any* form
                    anomaly_blocks.append((current_id, full_block, file.name, dict(file_variables)))
                current_id = None
                block_lines = []
