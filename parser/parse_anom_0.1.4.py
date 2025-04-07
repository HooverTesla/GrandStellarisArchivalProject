import os
import re
import pandas as pd
from pathlib import Path

# === CONFIGURATION ===
BASE_PATH = Path(__file__).resolve().parent.parent
LOCALISATION_PATH = BASE_PATH / "input" / "localisation"
ANOMALY_PATH = BASE_PATH / "input" / "anomalies"
OUTPUT_PATH = BASE_PATH / "output"
OUTPUT_PATH.mkdir(exist_ok=True)

# === LOCALISATION LOADER ===
localisation_data = {}
localisation_source = {}

for loc_file in LOCALISATION_PATH.glob("*.yml"):
    try:
        with open(loc_file, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line and "\"" in line:
                    try:
                        key_part, value = line.strip().split(":", 1)
                        key = key_part.strip()
                        text = value.strip().split("\"", 1)[1].rsplit("\"", 1)[0]
                        localisation_data[key] = text
                        localisation_source[key] = loc_file.name
                    except Exception:
                        continue
    except Exception as e:
        print(f"Error reading {loc_file.name}: {e}")

# === BLOCK PARSER ===
anomaly_blocks = []
for file in ANOMALY_PATH.glob("*.txt"):
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_id = None
    block = []
    inside_block = False

    for line in lines:
        line_strip = line.strip()
        if not inside_block and "_category" in line_strip and "=" in line_strip and "{" in line_strip:
            current_id = line_strip.split("=")[0].strip()
            block = [line]
            inside_block = True
            continue

        if inside_block:
            block.append(line)
            if "}" in line_strip:
                anomaly_blocks.append((current_id, "".join(block), file.name))
                inside_block = False
                current_id = None
                block = []

# === FIELD PARSING ===
desc_pattern = re.compile(r"desc\s*=\s*\"?([^\s\"]+)\"?")
picture_pattern = re.compile(r"picture\s*=\s*\"?([^\s\"]+)\"?")
level_pattern = re.compile(r"level\s*=\s*(\d+|\@\w+)")

# Catch all forms of event references
event_patterns = [
    re.compile(r'anomaly_event\s*=\s*["\']?([\w]+\.\d+)'),
    re.compile(r'\d+\s*=\s*(anomaly\.\d+)'),
    re.compile(r'add_event\s*=\s*([\w]+\.\d+)'),
    re.compile(r'add_special_project\s*=\s*([\w]+\.\d+)'),
]

def resolve_localised(key_base):
    key_base = key_base.strip().strip("\"")
    for suffix in [":0", ":1", ""]:
        full_key = key_base + suffix
        if full_key in localisation_data:
            return localisation_data[full_key], localisation_source.get(full_key)
    return f"[Missing] {key_base}", None

# === FINAL EXTRACTION ===
parsed_data = []
skipped_files = set()
for anomaly_id, block_text, source_file in anomaly_blocks:
    level_match = level_pattern.search(block_text)
    level = level_match.group(1) if level_match else "ERROR: Missing Level"

    desc_key = None
    desc_match = desc_pattern.search(block_text)
    if desc_match:
        desc_key = desc_match.group(1).strip()
    else:
        desc_key = f"{anomaly_id}_desc"

    name_key = anomaly_id

    name, name_file = resolve_localised(name_key)
    desc, desc_file = resolve_localised(desc_key)

    localisation_source_file = name_file or desc_file

    picture_match = picture_pattern.search(block_text)
    picture = picture_match.group(1).strip() if picture_match else None

    found_events = set()
    for pattern in event_patterns:
        found_events.update(pattern.findall(block_text))

    parsed_data.append({
        "anomaly_id": anomaly_id,
        "name": name,
        "desc": desc,
        "level": level,
        "image": picture,
        "success_event_ids": list(found_events),
        "source_file": source_file,
        "localisation_source_file": localisation_source_file,
    })

# === OUTPUT ===
df = pd.DataFrame(parsed_data)
df.to_csv(OUTPUT_PATH / "anomalies_v0.1.4_basic_parsed.csv", index=False)
print(f"✅ Exported {len(df)} anomalies to: output/anomalies_v0.1.4_basic_parsed.csv")
