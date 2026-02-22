import re

_COMPARATORS = {"=", "<", ">", "<=", ">=", "!="}


def _coerce_variable_value(raw_value: str):
    value = raw_value.strip()

    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]

    if re.fullmatch(r"-?\d+", value):
        return int(value)

    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)

    return value


def _add_preserving_duplicates(container: dict, key: str, value):
    if key in container:
        existing = container[key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            container[key] = [existing, value]
    else:
        container[key] = value


def _tokenize_pdx(text: str):
    tokens = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch in " \t\r\n":
            i += 1
            continue

        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue

        if ch == '"':
            i += 1
            start = i
            while i < n:
                if text[i] == '"' and text[i - 1] != "\\":
                    break
                i += 1
            tokens.append(text[start:i])
            i += 1
            continue

        if ch in "{}=":
            tokens.append(ch)
            i += 1
            continue

        if ch in "<>!":
            if i + 1 < n and text[i + 1] == "=":
                tokens.append(ch + "=")
                i += 2
            else:
                tokens.append(ch)
                i += 1
            continue

        start = i
        while i < n and text[i] not in " \t\r\n{}=<>!#\"":
            i += 1
        tokens.append(text[start:i])

    return tokens


def _parse_value(tokens, idx):
    if idx >= len(tokens):
        return "", idx
    if tokens[idx] == "{":
        return _parse_block(tokens, idx)
    return tokens[idx], idx + 1


def _parse_block(tokens, idx):
    idx += 1  # consume "{"
    obj = {}
    values = []

    while idx < len(tokens) and tokens[idx] != "}":
        if tokens[idx] == "{":
            nested, idx = _parse_block(tokens, idx)
            values.append(nested)
            continue

        if idx + 1 < len(tokens) and tokens[idx + 1] in _COMPARATORS:
            key = tokens[idx]
            op = tokens[idx + 1]
            idx += 2
            value, idx = _parse_value(tokens, idx)
            stored_key = key if op == "=" else f"{key} {op}"
            _add_preserving_duplicates(obj, stored_key, value)
        else:
            value, idx = _parse_value(tokens, idx)
            values.append(value)

    if idx < len(tokens) and tokens[idx] == "}":
        idx += 1  # consume "}"

    if obj and not values:
        return obj, idx
    if values and not obj:
        return values, idx
    if not obj and not values:
        return {}, idx

    obj["_values"] = values
    return obj, idx

# === PARSE SINGLE PDX BLOCK ===
def parse_pdx_block(lines):
    tokens = _tokenize_pdx("".join(lines))
    current = {}
    idx = 0

    while idx < len(tokens):
        if tokens[idx] == "{":
            _, idx = _parse_block(tokens, idx)
            continue

        if idx + 1 < len(tokens) and tokens[idx + 1] in _COMPARATORS:
            key = tokens[idx]
            op = tokens[idx + 1]
            idx += 2
            value, idx = _parse_value(tokens, idx)
            stored_key = key if op == "=" else f"{key} {op}"
            _add_preserving_duplicates(current, stored_key, value)
        else:
            idx += 1

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
    pending_key = None
    current_block = []
    bracket_level = 0
    file_blocks = {}
    total_blocks = 0
    all_keys = set()

    def finalize_current_block(current_line_index: int):
        nonlocal current_key, current_block, total_blocks

        if current_key is None:
            return

        parsed = parse_pdx_block(current_block)
        parsed["_source_file"] = filepath.name
        parsed["_line_number"] = current_line_index - len(current_block) + 2
        _add_preserving_duplicates(file_blocks, current_key, parsed)

        total_blocks += 1
        current_key = None
        current_block = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # For bracket counting and variable extraction, remove comments.
        bracket_line = stripped
        comment_start = bracket_line.find('#')
        if comment_start != -1:
            bracket_line = bracket_line[:comment_start].rstrip()

        if not bracket_line:
            continue

        if bracket_level == 0 and pending_key is None:
            # Capture top-level variable definitions like @foo = 10 or @foo = 0.25.
            var_match = re.match(r'^(@[\w.:+-]+)\s*=\s*(.+)$', bracket_line)
            if var_match:
                var_name, raw_value = var_match.groups()
                file_variables[var_name] = _coerce_variable_value(raw_value)
                continue

        if bracket_level == 0 and pending_key is not None:
            current_block.append(line)
            if "{" in bracket_line:
                current_key = pending_key
                pending_key = None

            bracket_level += bracket_line.count("{") - bracket_line.count("}")
            if bracket_level == 0 and current_key is not None:
                finalize_current_block(i)
            continue

        if bracket_level == 0 and "=" in bracket_line and "{" in bracket_line:
            current_key = bracket_line.split("=", 1)[0].strip()
            all_keys.add(current_key)
            current_block = [line]
            bracket_level += bracket_line.count("{") - bracket_line.count("}")
            if bracket_level == 0:
                finalize_current_block(i)
            continue

        if bracket_level == 0 and "=" in bracket_line:
            key_candidate, rhs = bracket_line.split("=", 1)
            if rhs.strip() == "":
                pending_key = key_candidate.strip()
                all_keys.add(pending_key)
                current_block = [line]
            continue

        if bracket_level > 0:
            current_block.append(line)
            bracket_level += bracket_line.count("{") - bracket_line.count("}")
            if bracket_level == 0:
                finalize_current_block(i)

    return file_blocks, file_variables, total_blocks, all_keys
