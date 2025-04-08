# HooverWithWhip – The bossy master Rosetta module
from HooverWithMap import get_stellaris_path, iterate_folders
from HooverHearingVoices import parse_localisation_file, extract_base_keys
from HooverFoldingLaundry import parse_pdx_file
from HooverWithFlashCards import create_index, merge_keys_to_index, store_variables_in_index
from HooverWithBoxes import export_folder_jsons

# === WHIP-ONLY COORDINATOR ===
def run_rosetta():
    print("[WHIP] Starting Rosetta runtime")
    stellaris_path = get_stellaris_path()
    print(f"[WHIP] Using Stellaris path: {stellaris_path}")

    all_files = []
    for folder, files in iterate_folders(stellaris_path):
        print(f"[WHIP] Found folder: {folder} with {len(files)} file(s)")
        all_files.extend(files)

    print(f"[WHIP] Total files gathered: {len(all_files)}")

    # === Localisation phase ===
    loc_files = [f for f in all_files if "/localisation/english/" in f.as_posix() and f.suffix == ".yml"]
    print(f"[WHIP] Localisation files detected: {len(loc_files)}")

    loaded_folders = {}
    index = {}
    all_variables = {}

    for loc_file in loc_files:
        print(f"[WHIP] Parsing localisation file: {loc_file}")
        entries = parse_localisation_file(loc_file)
        base_keys = extract_base_keys(entries)
        folder_name = loc_file.parent.name
        loaded_folders.setdefault(folder_name, {})[loc_file.name] = entries
        index = merge_keys_to_index(base_keys, loc_file.name, index)

    # === Game data phase ===
    data_files = [f for f in all_files if f not in loc_files]
    print(f"[WHIP] Non-localisation files to process: {len(data_files)}")

    for file in data_files:
        print(f"[WHIP] Parsing data file: {file}")
        file_blocks, file_vars, _, keys = parse_pdx_file(file)
        folder_name = file.parent.name
        loaded_folders.setdefault(folder_name, {})[file.name] = file_blocks
        index = create_index(file_blocks, index, file.name)
        index = merge_keys_to_index(keys, file.name, index)
        index = store_variables_in_index(file_vars, index)
        all_variables.update(file_vars)

    print("[WHIP] Parsing complete. Exporting folder JSONs.")
    export_folder_jsons(loaded_folders)

    print("[WHIP] Export complete. Returning data structure.")
    return {
        "loaded": loaded_folders,
        "index": index,
        "variables": all_variables
    }

if __name__ == "__main__":
    result = run_rosetta()
    print("[WHIP] Rosetta returned:")
    print(result)
