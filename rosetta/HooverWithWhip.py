# HooverWithWhip - The bossy master Rosetta module
from pathlib import Path
import sys

from HooverWithMap import get_stellaris_path, iterate_folders
from HooverHearingVoices import parse_localisation_file, extract_base_keys
from HooverFoldingLaundry import parse_pdx_file
from HooverWithFlashCards import (
    create_flashCards,
    merge_keys_to_flashCards,
    save_flashCards_to_file,
    store_variables_in_flashCards,
)
from HooverWithBoxes import export_folder_jsons


def _emit(message: str, reporter=None, level: str = "note") -> None:
    if reporter is None:
        print(message)
        return

    try:
        if level == "error":
            reporter.error(message)
        elif level == "warn":
            reporter.warn(message)
        else:
            reporter.note(message)
    except Exception:
        print(message)


def _run_forge_asset_pipeline(data_loaded_files: dict, stellaris_path: Path, reporter=None) -> None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from forge.build_stellaris_assets import extract_references_from_objects, run_asset_pipeline
    except Exception as exc:
        _emit(f"[WHIP] Asset pipeline unavailable: {exc}", reporter=reporter, level="error")
        return

    sprite_refs, texture_refs = extract_references_from_objects(data_loaded_files.values())
    _emit(
        f"[WHIP] Rosetta image refs gathered: "
        f"{len(sprite_refs)} sprite refs, {len(texture_refs)} direct texture refs",
        reporter=reporter,
    )

    if not sprite_refs and not texture_refs:
        _emit("[WHIP] No Rosetta image references found. Skipping Forge asset build.", reporter=reporter, level="warn")
        return

    summary = run_asset_pipeline(
        stellaris_root=stellaris_path,
        assets_dir=project_root / "assets",
        target_gui=[],
        all_gui=False,
        additional_sprite_refs=sprite_refs,
        additional_texture_refs=texture_refs,
        dry_run=False,
        webp_quality=90,
        default_gui_targets=False,
        reporter=reporter,
    )
    _emit(
        f"[WHIP] Forge asset build complete: "
        f"{summary['texture_count']} textures, {summary['reachable_sprite_count']} reachable sprites",
        reporter=reporter,
    )


# === WHIP-ONLY COORDINATOR ===
def run_rosetta(reporter=None):
    _emit("[WHIP] Starting Rosetta runtime", reporter=reporter)
    stellaris_path = get_stellaris_path()
    _emit(f"[WHIP] Using Stellaris path: {stellaris_path}", reporter=reporter)

    all_files = []
    folder_batches = list(iterate_folders(stellaris_path))
    if reporter is not None:
        try:
            reporter.set_phase("Rosetta | Discover folders", total=len(folder_batches))
        except Exception:
            pass

    for folder, files in folder_batches:
        if reporter is not None:
            try:
                reporter.set_current_file(folder.as_posix())
                reporter.advance()
            except Exception:
                pass
        all_files.extend(files)

    _emit(f"[WHIP] Total files gathered: {len(all_files)}", reporter=reporter)

    # === Localisation phase ===
    loc_files = [
        f
        for f in all_files
        if f.suffix.lower() == ".yml" and f.relative_to(stellaris_path).parts[0].lower() == "localisation"
    ]
    _emit(f"[WHIP] Localisation files detected: {len(loc_files)}", reporter=reporter)

    loaded_files = {}
    data_loaded_files = {}
    flashCards = {}
    if reporter is not None:
        try:
            reporter.set_phase("Rosetta | Parse localisation", total=len(loc_files))
        except Exception:
            pass
    for loc_file in sorted(loc_files):
        relative_path = loc_file.relative_to(stellaris_path).as_posix()
        if reporter is not None:
            try:
                reporter.set_current_file(relative_path)
            except Exception:
                pass
        try:
            entries = parse_localisation_file(loc_file)
            base_keys = extract_base_keys(entries)
            loaded_files[relative_path] = entries
            flashCards = merge_keys_to_flashCards(base_keys, relative_path, flashCards)
        except Exception as exc:
            _emit(f"[WHIP] Localisation parse failed: {relative_path} | {exc}", reporter=reporter, level="error")
        finally:
            if reporter is not None:
                try:
                    reporter.advance()
                except Exception:
                    pass

    # === Game data phase ===
    data_files = [f for f in all_files if f not in loc_files]
    _emit(f"[WHIP] Non-localisation files to process: {len(data_files)}", reporter=reporter)
    if reporter is not None:
        try:
            reporter.set_phase("Rosetta | Parse game data", total=len(data_files))
        except Exception:
            pass

    for file in sorted(data_files):
        relative_path = file.relative_to(stellaris_path).as_posix()
        if reporter is not None:
            try:
                reporter.set_current_file(relative_path)
            except Exception:
                pass
        try:
            file_blocks, file_vars, _, keys = parse_pdx_file(file)
            loaded_files[relative_path] = file_blocks
            data_loaded_files[relative_path] = file_blocks
            flashCards = create_flashCards(file_blocks, flashCards, relative_path)
            flashCards = merge_keys_to_flashCards(keys, relative_path, flashCards)
            flashCards = store_variables_in_flashCards(file_vars, relative_path, flashCards)
        except Exception as exc:
            _emit(f"[WHIP] Data parse failed: {relative_path} | {exc}", reporter=reporter, level="error")
        finally:
            if reporter is not None:
                try:
                    reporter.advance()
                except Exception:
                    pass

    _emit("[WHIP] Parsing complete. Exporting folder JSONs.", reporter=reporter)
    if reporter is not None:
        try:
            reporter.set_phase("Rosetta | Export + flashcards", total=2)
            reporter.set_current_file("output/*.json export")
        except Exception:
            pass
    export_folder_jsons(loaded_files)
    if reporter is not None:
        try:
            reporter.advance()
            reporter.set_current_file("flashCards.json")
        except Exception:
            pass

    save_flashCards_to_file(flashCards)
    if reporter is not None:
        try:
            reporter.advance()
        except Exception:
            pass

    _emit("[WHIP] Handing Rosetta image references to Forge.", reporter=reporter)
    _run_forge_asset_pipeline(data_loaded_files, stellaris_path, reporter=reporter)


# if __name__ == "__main__":
#     result = run_rosetta()
#     print("[WHIP] Rosetta returned:")
#     # print(result)
