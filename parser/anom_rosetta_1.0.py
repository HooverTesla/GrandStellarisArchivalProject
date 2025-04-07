import os
import re
import pandas as pd
from pathlib import Path

# === CONFIGURATION ===
BASE_PATH = Path(__file__).resolve().parent.parent
LOCALISATION_PATH = BASE_PATH / "input" / "localisation"
ANOMALY_PATH = BASE_PATH / "input" / "anomalies"
#OUTPUT
OUTPUT_PATH = BASE_PATH / "output"
# Gets filename without .py
SCRIPT_NAME = Path(__file__).stem

OUTPUT_FILE = OUTPUT_PATH / f"{SCRIPT_NAME}.csv"
OUTPUT_PATH.mkdir(exist_ok=True)

# === BLOCK PARSER (Bracket Balanced) ===
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


# === FIELD PARSING ===
desc_pattern = re.compile(r"desc\s*=\s*\"?([^\s\"]+)\"?")
picture_pattern = re.compile(r"picture\s*=\s*\"?([^\s\"]+)\"?")
level_pattern = re.compile(r"level\s*=\s*(\d+|\@\w+)")
event_patterns = [
    re.compile(r'\b[a-zA-Z][a-zA-Z0-9_]*\.\d+\b'),
]

# === FINAL EXTRACTION ===
parsed_data = []
for anomaly_id, block_text, source_file, file_variables in anomaly_blocks:

    level_match = level_pattern.search(block_text)
    if level_match:
      level_raw = level_match.group(1)
      level = file_variables.get(level_raw, level_raw)
    else:
      level = "ERROR: Missing Level"

    picture_match = picture_pattern.search(block_text)
    picture = picture_match.group(1).strip() if picture_match else None

    found_events = set()
    # TESTING EVENT ID
    # print(f"[DEBUG] ID: {anomaly_id} | Raw Block: {block_text}")
    # ENDTESTING EVENT ID
    for pattern in event_patterns:
        found_events.update(pattern.findall(block_text))

    parsed_data.append({
        "anomaly_id": anomaly_id,
        "level": level,
        "success_event_ids": ", ".join(found_events),
        "source_file": source_file,

    })
    #Debugging - log to terminal
    # print("Block text for", anomaly_id)
    # print(block_text)
    # print("Regex Matches:")
    # print(re.findall(r'\b\w+\.\d+\b', block_text))
    #end Debugging - Log to terminal

# === OUTPUT ===
df = pd.DataFrame(parsed_data)
df.to_csv(OUTPUT_FILE, index=False)
print(f"✅ Exported {len(df)} anomalies to: {OUTPUT_FILE}")
