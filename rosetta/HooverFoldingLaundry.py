import re

# === PARSE SINGLE PDX BLOCK ===
def parse_pdx_block(lines, file_variables):
    stack = []
    current = {}
    key = None
    comment_buffer = []

    def finalize(key, value):
        if isinstance(stack[-1], dict):
            stack[-1][key] = value
        elif isinstance(stack[-1], list):
            stack[-1].append(value)

    stack.append(current)

    for line in lines:
        raw_line = line
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            comment_buffer.append(raw_line.strip())
            continue

        if "{" in line:
            if comment_buffer:
                if isinstance(stack[-1], dict):
                    stack[-1].setdefault("_comments", []).extend(comment_buffer)
                comment_buffer = []

            if "=" in line:
                key, _ = line.split("=", 1)
                key = key.strip()
                new = {}
                finalize(key, new)
                stack.append(new)
            else:
                new = {}
                stack.append(new)
        elif "}" in line:
            stack.pop()
        elif "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"')
            finalize(k, v)

            if comment_buffer:
                if isinstance(stack[-1], dict):
                    stack[-1].setdefault("_comments", []).extend(comment_buffer)
                comment_buffer = []

    return current

# === PARSE FULL FILE ===
def parse_pdx_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    file_variables = {}
    current_key = None
    current_block = []
    bracket_level = 0
    file_blocks = {}
    total_blocks = 0
    all_keys = set()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        var_match = re.match(r'(@\w+)\s*=\s*(\d+)', stripped)
        if var_match:
            var_name, var_value = var_match.groups()
            file_variables[var_name] = int(var_value)
            continue

        if bracket_level == 0 and "=" in stripped and "{" in stripped:
            current_key = stripped.split("=")[0].strip()
            all_keys.add(current_key)
            current_block = [line]
            bracket_level += line.count("{") - line.count("}")

        elif bracket_level > 0:
            current_block.append(line)
            bracket_level += line.count("{") - line.count("}")

            if bracket_level == 0:
                parsed = parse_pdx_block(current_block, file_variables)
                parsed["_source_file"] = filepath.name
                parsed["_line_number"] = i - len(current_block)
                file_blocks[current_key] = parsed

                total_blocks += 1
                current_key = None
                current_block = []

    return file_blocks, file_variables, total_blocks, all_keys
