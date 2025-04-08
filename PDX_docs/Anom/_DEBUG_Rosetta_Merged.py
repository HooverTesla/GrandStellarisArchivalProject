from pathlib import Path
from collections import defaultdict

# === FILE FINDER FOR ROSETTA ===
VALID_EXTENSIONS = {".txt", ".json", ".yml"}

# === GRAB FILES FROM FULL STELLARIS INSTALL ===
def get_stellaris_path() -> Path:
    return Path("C:/Program Files (x86)/Steam/steamapps/common/Stellaris")

# === YIELD ONE FOLDER'S FILES AT A TIME ===
def iterate_folders(root_folder: Path):
    folder_map = defaultdict(list)

    for path in root_folder.rglob("*"):
        if not path.is_file():
            continue

        if "/localisation/" in path.as_posix():
            if "/localisation/english/" in path.as_posix() and path.suffix == ".yml":
                folder_map[path.parent].append(path)
            continue  # Skip all other localisation files entirely

        if path.suffix.lower() not in VALID_EXTENSIONS:
            continue

        folder_map[path.parent].append(path)

    for folder, files in folder_map.items():
        yield folder, files


import re
from pathlib import Path

# === LOCALISATION PARSER ===
def parse_localisation_file(file_path: Path) -> dict:
    entries = {}
    with open(file_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("l_english:"):
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
        parts = full_key.split(".")
        if len(parts) >= 2:
            base_keys.add(".".join(parts[:2]))
        else:
            base_keys.add(full_key.split(":")[0])
    return base_keys


import re

# === PARSE SINGLE PDX BLOCK ===
def parse_pdx_block(lines, file_variables):
    stack = []
    current = {}
    key = None
    comment_buffer = []

    def finalize(key, value):
        if isinstance(stack[-1], dict):
            stack[-1][key] = value
        elif isinstance(stack[-1], list):
            stack[-1].append(value)

    stack.append(current)

    for line in lines:
        raw_line = line
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            comment_buffer.append(raw_line.strip())
            continue

        if "{" in line:
            if comment_buffer:
                if isinstance(stack[-1], dict):
                    stack[-1].setdefault("_comments", []).extend(comment_buffer)
                comment_buffer = []

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
            finalize(k, v)

            if comment_buffer:
                if isinstance(stack[-1], dict):
                    stack[-1].setdefault("_comments", []).extend(comment_buffer)
                comment_buffer = []

    return current

# === PARSE FULL FILE ===
def parse_pdx_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    file_variables = {}
    current_key = None
    current_block = []
    bracket_level = 0
    file_blocks = {}
    total_blocks = 0
    all_keys = set()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        var_match = re.match(r'(@\w+)\s*=\s*(\d+)', stripped)
        if var_match:
            var_name, var_value = var_match.groups()
            file_variables[var_name] = int(var_value)
            continue

        if bracket_level == 0 and "=" in stripped and "{" in stripped:
            current_key = stripped.split("=")[0].strip()
            all_keys.add(current_key)
            current_block = [line]
            bracket_level += line.count("{") - line.count("}")

        elif bracket_level > 0:
            current_block.append(line)
            bracket_level += line.count("{") - line.count("}")

            if bracket_level == 0:
                parsed = parse_pdx_block(current_block, file_variables)
                parsed["_source_file"] = filepath.name
                parsed["_line_number"] = i - len(current_block)
                file_blocks[current_key] = parsed

                total_blocks += 1
                current_key = None
                current_block = []

    return file_blocks, file_variables, total_blocks, all_keys


from pathlib import Path
import re

def create_index(entries: dict, index: dict, file_source: str, line_offset: int = 0):
    for key in entries:
        if key.startswith("_"):
            continue  # Skip metadata keys like _source_file or _comments

        # Only index the main keys (e.g., anomaly.54 not anomaly.54.desc.a)
        base_key = key.split(".")[0] if "." in key else key

        if base_key not in index:
            index[base_key] = {
                "_source_file": file_source,
                "_line_number": line_offset
            }

    return index

# Merge key sets from multiple modules (like localisation, anomalies)
def merge_keys_to_index(keys: set, file_source: str, existing_index: dict) -> dict:
    for key in keys:
        # Only keep top-level keys like colony.53, not colony.53.desc or .a
        base_key = key.split(".")[0] if "." in key else key
        if base_key not in existing_index:
            existing_index[base_key] = {"_source_file": file_source}
    return existing_index

# Inject file-scope variables (e.g., @foobar = 6) at top of the index
def store_variables_in_index(var_dict: dict, index: dict) -> dict:
    index["__variables__"] = var_dict
    return index


# HooverWithWhip – The bossy master Rosetta module
from HooverWithMap import find_valid_files, filter_localisation_files, get_stellaris_path
from HooverHearingVoices import parse_localisation_file, extract_base_keys
from HooverFoldingLaundry import parse_pdx_file
from HooverWithFlashCards import create_index, merge_keys_to_index, store_variables_in_index

# === WHIP-ONLY COORDINATOR ===
def run_rosetta():
    loaded_folders = {}
    index = {}
    all_variables = {}

    stellaris_path = get_stellaris_path()
    all_files = find_valid_files(stellaris_path)
    loc_files = filter_localisation_files(all_files)

    for loc_file in loc_files:
        entries = parse_localisation_file(loc_file)
        base_keys = extract_base_keys(entries)
        folder_name = loc_file.parent.name
        loaded_folders.setdefault(folder_name, {})[loc_file.name] = entries
        index = merge_keys_to_index(base_keys, loc_file.name, index)

    for file in all_files:
        file_blocks, file_vars, _, keys = parse_pdx_file(file)
        folder_name = file.parent.name
        loaded_folders.setdefault(folder_name, {})[file.name] = file_blocks
        index = create_index(file_blocks, index, file.name)
        index = merge_keys_to_index(keys, file.name, index)
        index = store_variables_in_index(file_vars, index)
        all_variables.update(file_vars)

    return {
        "loaded": loaded_folders,
        "index": index,
        "variables": all_variables
    }
