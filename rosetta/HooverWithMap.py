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
        # if "/licenses/" in path.as_posix():
        #     continue
        if path.suffix.lower() not in VALID_EXTENSIONS:
            continue

        folder_map[path.parent].append(path)

    for folder, files in folder_map.items():
        yield folder, files
