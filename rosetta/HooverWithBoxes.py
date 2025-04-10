import json
from pathlib import Path
import sys
import traceback

# No recursion limit override; we're assuming sane data now

def export_folder_jsons(loaded_folders: dict, output_root: Path = Path("output")):
    output_root.mkdir(parents=True, exist_ok=True)

    for folder_path_obj, contents in loaded_folders.items():
        for file_name, file_data in contents.items():
            json_name = Path(file_name).stem + ".json"
            out_file = output_root / json_name
            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    import sys
                    sys.setrecursionlimit(10000)  # Increase as needed
                    json.dump(file_data, f, indent=2, ensure_ascii=False)
                print(f"[BOXES] Exported: {out_file}")
            except Exception as e:
                print(f"[BOXES] Failed to export {out_file}: {e}")
                traceback.print_exc()
