import re
from pathlib import Path

# === LOCALISATION PARSER ===
def parse_localisation_file(file_path: Path) -> dict:
    entries = {}
    with open(file_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("l_") and line.endswith(":"):
                continue

            # Match key[:optional_digit] "value"
            match = re.match(r'^([^\s:#]+)(?::\d+)?\s+"(.*)"$', line)
            if match:
                key, value = match.groups()
                entries[key] = value
    return entries

# === BASE KEY EXTRACTOR ===
def extract_base_keys(localisation_dict: dict) -> set:
    base_keys = set()
    for full_key in localisation_dict:
        # Keep full localisation keys to avoid collapsing valid identifiers.
        base_keys.add(full_key)

        # Add root id aliases for script link lookups (e.g. anomaly.625.name -> anomaly.625).
        parts = full_key.split(".")
        if len(parts) >= 2:
            base_keys.add(".".join(parts[:2]))

        base_keys.add(full_key.split(":")[0])
    return base_keys
