import os
import re
import csv
import yaml

# Always base paths off where the script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ANOMALY_TXT_FOLDER = os.path.join(BASE_DIR, "../data_raw/")
LOCALIZATION_FOLDER = os.path.join(BASE_DIR, "../localisation/")
OUTPUT_CSV = os.path.join(BASE_DIR, "../csv_output/anomalies_parsed.csv")

# Load all localization .yml files
def load_localization(folder):
    localization = {}
    for filename in os.listdir(folder):
        if filename.endswith(".yml"):
            with open(os.path.join(folder, filename), 'r', encoding='utf-8-sig') as f:
                try:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        localization.update(data.get("l_english", {}))
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    return localization

# Parse anomaly .txt files
def parse_anomalies(folder, localization_dict):
    anomalies = []
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            with open(os.path.join(folder, filename), 'r', encoding='utf-8') as f:
                content = f.read()

            matches = re.finditer(r'(\w+)\s*=\s*\{([^{}]*\{[^{}]*\}[^{}]*|[^{}]*)\}', content, re.DOTALL)
            for match in matches:
                data = {}
                data['id'] = match.group(1)
                block = match.group(2)

                level = re.search(r'level\s*=\s*(\d+)', block)
                data['level'] = level.group(1) if level else ""

                pic = re.search(r'picture\s*=\s*(\w+)', block)
                data['picture'] = pic.group(1) if pic else ""

                desc = re.search(r'desc\s*=\s*"?(.*?)"?$', block, re.MULTILINE)
                if desc:
                    key = desc.group(1).strip()
                    data['desc_key'] = key
                    data['description'] = localization_dict.get(key, f"Missing: {key}")
                else:
                    data['desc_key'] = ""
                    data['description'] = ""

                anomalies.append(data)
    return anomalies

# Export to CSV
def export_to_csv(data, output_file):
    keys = ['id', 'level', 'picture', 'desc_key', 'description']
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

if __name__ == "__main__":
    loc = load_localization(LOCALIZATION_FOLDER)
    parsed = parse_anomalies(ANOMALY_TXT_FOLDER, loc)
    export_to_csv(parsed, OUTPUT_CSV)
    print(f"Exported {len(parsed)} anomalies to {OUTPUT_CSV}")
