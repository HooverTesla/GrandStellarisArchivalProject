import json
from pathlib import Path
import sys

sys.setrecursionlimit(10000)  # Boost recursion limit for deep PDX hell

def sanitize(obj, seen=None):
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return "<RECURSION>"
    seen.add(obj_id)

    if isinstance(obj, dict):
        return {sanitize(k, seen): sanitize(v, seen) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(i, seen) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize(i, seen) for i in obj)
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

def export_folder_jsons(loaded_folders: dict, output_root: Path = Path("output/parsed")):
    output_root.mkdir(parents=True, exist_ok=True)

    for folder_name, contents in loaded_folders.items():
        folder_path = output_root / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        for sub_file_name, data in contents.items():
            json_name = Path(sub_file_name).stem + ".json"
            out_file = folder_path / json_name
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(sanitize(data), f, indent=2, ensure_ascii=False)
            print(f"[BOXES] Exported: {out_file}")
