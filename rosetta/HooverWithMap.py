from pathlib import Path
from collections import defaultdict

# === FILE FINDER FOR ROSETTA ===
VALID_EXTENSIONS = {".txt", ".json", ".yml"}
ALLOWED_TOP_LEVEL_DIRS = {"common", "events", "localisation"}
SKIP_DIR_NAMES = {"diplo_phrases", "name_lists",}

# === GRAB FILES FROM FULL STELLARIS INSTALL ===
def get_stellaris_path() -> Path:
    return Path("C:/Program Files (x86)/Steam/steamapps/common/Stellaris")

# === YIELD ONE FOLDER'S FILES AT A TIME ===
def iterate_folders(root_folder: Path):
    folder_map = defaultdict(list)

    for path in root_folder.rglob("*"):
        if not path.is_file():
            continue

        try:
            relative_path = path.relative_to(root_folder)
        except ValueError:
            continue

        if not relative_path.parts:
            continue

        top_level = relative_path.parts[0].lower()
        if top_level not in ALLOWED_TOP_LEVEL_DIRS:
            continue

        if any(part.lower() in SKIP_DIR_NAMES for part in relative_path.parts):
            continue

        if path.suffix.lower() not in VALID_EXTENSIONS:
            continue

        if top_level == "localisation" and path.suffix.lower() != ".yml":
            continue

        folder_map[path.parent].append(path)

    for folder, files in folder_map.items():
        yield folder, files
