import json
from pathlib import Path
import traceback
import shutil
import os
import stat
import time

# No recursion limit override; we're assuming sane data now

def _handle_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def _clear_output_root(output_root: Path):
    for attempt in range(3):
        try:
            shutil.rmtree(output_root, onexc=_handle_remove_readonly)
            return True
        except PermissionError as e:
            if attempt == 2:
                print(f"[BOXES] Warning: could not fully clear {output_root}: {e}")
                return False
            time.sleep(0.3)
    return False

def export_folder_jsons(loaded_files: dict, output_root: Path = Path("output")):
    if output_root.exists() and any(output_root.iterdir()):
        _clear_output_root(output_root)

    output_root.mkdir(parents=True, exist_ok=True)

    for relative_source_path, file_data in loaded_files.items():
        try:
            source_path = Path(relative_source_path)
            out_file = output_root / source_path.with_suffix(".json")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(file_data, f, indent=2, ensure_ascii=False)
            # print(f"[BOXES] Exported: {out_file}")
        except Exception as e:
            print(f"[BOXES] Failed to export {relative_source_path}: {e}")
            traceback.print_exc()
