from pathlib import Path
import re

def create_index(entries: dict, index: dict, file_source: str, line_offset: int = 0):
    for key in entries:
        if key.startswith("_"):
            continue  # Skip metadata keys like _source_file or _comments

        # Only index the main keys (e.g., anomaly.54 not anomaly.54.desc.a)
        base_key = key.split(".")[0] if "." in key else key

        if base_key not in index:
            index[base_key] = {
                "_source_file": file_source,
                "_line_number": line_offset
            }

    return index

# Merge key sets from multiple modules (like localisation, anomalies)
def merge_keys_to_index(keys: set, file_source: str, existing_index: dict) -> dict:
    for key in keys:
        # Only keep top-level keys like colony.53, not colony.53.desc or .a
        base_key = key.split(".")[0] if "." in key else key
        if base_key not in existing_index:
            existing_index[base_key] = {"_source_file": file_source}
    return existing_index

# Inject file-scope variables (e.g., @foobar = 6) at top of the index
def store_variables_in_index(var_dict: dict, index: dict) -> dict:
    index["__variables__"] = var_dict
    return index
