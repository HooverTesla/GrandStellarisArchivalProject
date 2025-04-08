from pathlib import Path

# === FILE FINDER FOR ROSETTA ===
VALID_EXTENSIONS = {".txt", ".json", ".yml"}
BLACKLIST_DIRS = {".git", ".vscode", "output", "PDX_docs", "__pycache__"}

# === GRAB FILES FROM FOLDER TREE ===
def find_valid_files(root_folder: Path) -> list[Path]:
    found_files = []
    for path in root_folder.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VALID_EXTENSIONS:
            continue
        if any(black in path.parts for black in BLACKLIST_DIRS):
            continue
        found_files.append(path)
    return found_files

# === FILTER LOCALISATION FILES ONLY ===
def filter_localisation_files(files: list[Path]) -> list[Path]:
    return [f for f in files if "/localisation/english/" in f.as_posix() and f.suffix == ".yml"]
