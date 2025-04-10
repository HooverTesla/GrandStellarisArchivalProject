import re
from collections import deque

# === PARSE SINGLE PDX BLOCK ===
def parse_pdx_block(lines, file_variables):
    stack = []
    current = {}
    key = None
    comment_buffer = []

    def finalize(k, val):
        if isinstance(stack[-1], dict):
            stack[-1][k] = val
        elif isinstance(stack[-1], list):
            stack[-1].append(val)

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
            # Attach any pending comments to the current object
            if comment_buffer:
                if isinstance(stack[-1], dict):
                    stack[-1].setdefault("_comments", []).extend(comment_buffer)
                comment_buffer = []

            if "=" in line:
                k, _ = line.split("=", 1)
                k = k.strip()
                new = {}
                finalize(k, new)
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
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="cp1252") as f:
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

        # Check for variable definitions like @some_var = 10
        var_match = re.match(r'(@\w+)\s*=\s*(\d+)', stripped)
        if var_match:
            var_name, var_value = var_match.groups()
            file_variables[var_name] = int(var_value)
            continue

        # For bracket counting, remove anything after '#' in this line
        bracket_line = stripped
        comment_start = bracket_line.find('#')
        if comment_start != -1:
            bracket_line = bracket_line[:comment_start].rstrip()

        if bracket_level == 0 and "=" in bracket_line and "{" in bracket_line:
            current_key = bracket_line.split("=", 1)[0].strip()
            all_keys.add(current_key)
            current_block = [line]  # store full line (with comments) for block parser
            bracket_level += bracket_line.count("{") - bracket_line.count("}")

        elif bracket_level > 0:
            current_block.append(line)  # store full line (with comments)
            bracket_level += bracket_line.count("{") - bracket_line.count("}")

            if bracket_level == 0:
                parsed = parse_pdx_block(current_block, file_variables)
                parsed["_source_file"] = filepath.name
                parsed["_line_number"] = i - len(current_block)
                file_blocks[current_key] = parsed

                total_blocks += 1
                current_key = None
                current_block = []

    return file_blocks, file_variables, total_blocks, all_keys
