from pathlib import Path
import re
import json


def create_flashCards(entries: dict, flashCards: dict, file_source: str, line_offset: int = 0):
    for key in entries:
        if key.startswith("_"):
            continue  # Skip metadata keys like _source_file or _comments

        # Only track the main keys (e.g., anomaly.54 not anomaly.54.desc.a)
        base_key = key.split(".")[0] if "." in key else key

        if base_key not in flashCards:
            flashCards[base_key] = {
                "_source_file": file_source,
                "_line_number": line_offset
            }

    return flashCards


# Merge key sets from multiple modules (like localisation, anomalies)
def merge_keys_to_flashCards(keys: set, file_source: str, existing_flashCards: dict) -> dict:
    for key in keys:
        # Only keep top-level keys like colony.53, not colony.53.desc or .a
        base_key = key.split(".")[0] if "." in key else key
        if base_key not in existing_flashCards:
            existing_flashCards[base_key] = {"_source_file": file_source}
    return existing_flashCards


# Inject file-scope variables (e.g., @foobar = 6) at top of the flashCards dictionary
def store_variables_in_flashCards(var_dict: dict, flashCards: dict) -> dict:
    flashCards["__variables__"] = var_dict
    return flashCards


# Actually create a file named "flashCards" up one level from this script.
# The file will contain the entire flashCards dictionary in JSON format.

def save_flashCards_to_file(flashCards: dict) -> None:
    # compute path to the parent folder of the script's directory.
    parent_dir = Path(__file__).resolve().parent.parent
    file_path = parent_dir / "flashCards.json"  # the user wants a file named exactly 'flashCards'

    # let's store data as JSON.
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(flashCards, f, indent=2)

    # optional: print a small message for debugging.
    print(f"flashCards data written to {file_path}")
