from pathlib import Path
import json


def _record_source(flash_card_entry: dict, file_source: str, line_offset: int = 0) -> None:
    sources = flash_card_entry.setdefault("__sources__", [])
    source_info = {"_source_file": file_source, "_line_number": line_offset}
    if source_info not in sources:
        sources.append(source_info)


def create_flashCards(entries: dict, flashCards: dict, file_source: str, line_offset: int = 0):
    for key in entries:
        if key.startswith("_"):
            continue  # Skip metadata keys like _source_file or _comments

        flashCards.setdefault(key, {})
        _record_source(flashCards[key], file_source, line_offset)

    return flashCards


# Merge key sets from multiple modules (like localisation, anomalies)
def merge_keys_to_flashCards(keys: set, file_source: str, existing_flashCards: dict) -> dict:
    for key in keys:
        existing_flashCards.setdefault(key, {})
        _record_source(existing_flashCards[key], file_source)
    return existing_flashCards


# Inject file-scope variables (e.g., @foobar = 6) at top of the flashCards dictionary
def store_variables_in_flashCards(var_dict: dict, file_source: str, flashCards: dict) -> dict:
    if not var_dict:
        return flashCards

    variables = flashCards.setdefault("__variables__", {})
    by_file = variables.setdefault("__by_file__", {})
    definitions = variables.setdefault("__definitions__", {})
    global_first = variables.setdefault("__global_first__", {})
    global_latest = variables.setdefault("__global_latest__", {})

    by_file[file_source] = var_dict

    for var_name, var_value in var_dict.items():
        definitions.setdefault(var_name, []).append(
            {"_source_file": file_source, "value": var_value}
        )
        global_first.setdefault(var_name, var_value)
        global_latest[var_name] = var_value

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
