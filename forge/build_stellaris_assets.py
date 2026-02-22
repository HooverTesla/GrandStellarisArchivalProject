#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import imageio.v2 as imageio
except ImportError:
    imageio = None


DEFAULT_STELLARIS_ROOT = Path("C:/Program Files (x86)/Steam/steamapps/common/Stellaris")
INDEX_DIR_NAME = "index"
STELLARIS_MIRROR_DIR_NAME = "stellaris"

GFX_REFERENCE_PATTERN = re.compile(r"\bGFX_[A-Za-z0-9_]+\b")
TEXTURE_PATH_PATTERN = re.compile(r"\bgfx/[A-Za-z0-9_./-]+\.(?:dds|tga|png|webp)\b", flags=re.IGNORECASE)

SPRITE_BLOCK_TYPES = (
    "spriteType",
    "SpriteType",
    "corneredTileSpriteType",
    "progressbarType",
    "progressbartype",
)


def to_posix(path_like: str | Path) -> str:
    return Path(path_like).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def find_matching_brace(text: str, open_brace_index: int) -> int:
    depth = 0
    for i in range(open_brace_index, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def iter_named_blocks(text: str, names: Iterable[str]) -> Iterable[Tuple[str, str]]:
    pattern = re.compile(
        r"^[ \t]*(?P<name>" + "|".join(re.escape(name) for name in names) + r")\s*=\s*\{",
        flags=re.MULTILINE,
    )
    for match in pattern.finditer(text):
        block_name = match.group("name")
        open_brace = text.find("{", match.start())
        if open_brace < 0:
            continue
        close_brace = find_matching_brace(text, open_brace)
        if close_brace < 0:
            continue
        yield block_name, text[match.start() : close_brace + 1]


def extract_string(block: str, key: str) -> Optional[str]:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\"([^\"]+)\"", block, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_int(block: str, key: str) -> Optional[int]:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\"?(-?\d+)\"?", block, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def extract_key_block(block: str, key: str) -> Optional[str]:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\{{", block, flags=re.IGNORECASE)
    if not match:
        return None
    open_brace = block.find("{", match.start())
    if open_brace < 0:
        return None
    close_brace = find_matching_brace(block, open_brace)
    if close_brace < 0:
        return None
    return block[open_brace + 1 : close_brace]


def extract_token_list(content: str) -> List[str]:
    tokens: List[str] = []
    for quoted, bare in re.findall(r'"([^"]+)"|([A-Za-z0-9_./-]+)', content):
        token = quoted or bare
        if token:
            tokens.append(token)
    return tokens


def extract_xy(content: str) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for axis in ("x", "y"):
        match = re.search(rf"\b{axis}\s*=\s*(-?\d+)", content, flags=re.IGNORECASE)
        if match:
            result[axis] = int(match.group(1))
    return result


def parse_gfx_sprites(
    interface_dir: Path,
    stellaris_root: Path,
    gfx_paths: Optional[List[Path]] = None,
    reporter=None,
) -> Dict[str, dict]:
    sprite_index: Dict[str, dict] = {}
    iter_paths = gfx_paths if gfx_paths is not None else sorted(interface_dir.rglob("*.gfx"))

    for gfx_path in iter_paths:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(gfx_path.relative_to(stellaris_root)))
                reporter.advance()
            except Exception:
                pass
        text = read_text(gfx_path)
        gfx_rel = to_posix(gfx_path.relative_to(stellaris_root))

        for block_type, block in iter_named_blocks(text, SPRITE_BLOCK_TYPES):
            name = extract_string(block, "name")
            if not name or not name.startswith("GFX_"):
                continue

            textures: List[str] = []
            for texture_key in ("textureFile", "texturefile", "textureFile1", "textureFile2"):
                value = extract_string(block, texture_key)
                if value:
                    textures.append(to_posix(value))

            border_size: Optional[Dict[str, int]] = None
            border_raw = extract_key_block(block, "borderSize")
            if border_raw:
                parsed = extract_xy(border_raw)
                if parsed:
                    border_size = parsed

            sprite_index[name] = {
                "name": name,
                "sprite_type": block_type,
                "source_gfx_file": gfx_rel,
                "textures": textures,
                "primary_texture": textures[0] if textures else None,
                "no_of_frames": extract_int(block, "noOfFrames") or 1,
                "default_frame": extract_int(block, "default_frame"),
                "sprite_sheet_sprite_type": extract_string(block, "sprite_sheet_sprite_type"),
                "effect_file": extract_string(block, "effectFile"),
                "border_size": border_size,
            }

    return sprite_index


def resolve_target_guis(
    interface_dir: Path,
    targets: List[str],
    all_gui: bool,
    default_to_anomaly: bool = True,
) -> Tuple[List[Path], List[str]]:
    warnings: List[str] = []

    if all_gui:
        return sorted(interface_dir.rglob("*.gui")), warnings

    if not targets and default_to_anomaly:
        targets = ["anomaly_view.gui"]

    resolved: Set[Path] = set()

    for target in targets:
        is_glob = any(ch in target for ch in "*?[]")
        target_path = Path(target)

        if is_glob:
            matches = sorted(interface_dir.glob(target))
            if not matches:
                warnings.append(f"No gui files matched glob target '{target}'.")
            resolved.update(matches)
            continue

        if target_path.is_absolute():
            if target_path.exists():
                resolved.add(target_path)
            else:
                warnings.append(f"Absolute gui target not found: {target}")
            continue

        direct = interface_dir / target_path
        if direct.exists():
            resolved.add(direct)
            continue

        fallback_matches = list(interface_dir.rglob(target_path.name))
        if not fallback_matches:
            warnings.append(f"Gui target not found: {target}")
        elif len(fallback_matches) == 1:
            resolved.add(fallback_matches[0])
        else:
            warnings.append(
                f"Multiple gui files matched '{target}'. Using all: "
                + ", ".join(to_posix(p.relative_to(interface_dir)) for p in fallback_matches)
            )
            resolved.update(fallback_matches)

    return sorted(resolved), warnings


def parse_gui_references(
    target_guis: List[Path],
    interface_dir: Path,
    stellaris_root: Path,
    reporter=None,
) -> Tuple[dict, Set[str], Set[str]]:
    gui_refs: Dict[str, dict] = {}
    all_sprite_refs: Set[str] = set()
    all_font_refs: Set[str] = set()

    sprite_pattern = re.compile(r"\b(?:spriteType|quadTextureSprite)\s*=\s*\"([^\"]+)\"")
    font_pattern = re.compile(r"\bfont\s*=\s*\"([^\"]+)\"")

    for gui_path in target_guis:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(gui_path.relative_to(stellaris_root)))
                reporter.advance()
            except Exception:
                pass
        text = read_text(gui_path)
        sprite_refs = sorted(set(sprite_pattern.findall(text)))
        font_refs = sorted(set(font_pattern.findall(text)))

        rel = to_posix(gui_path.relative_to(stellaris_root))
        gui_refs[rel] = {
            "sprites": sprite_refs,
            "fonts": font_refs,
        }

        all_sprite_refs.update(sprite_refs)
        all_font_refs.update(font_refs)

    return gui_refs, all_sprite_refs, all_font_refs


def extract_references_from_objects(objects: Iterable[object]) -> Tuple[Set[str], Set[str]]:
    sprite_refs: Set[str] = set()
    texture_refs: Set[str] = set()
    stack: List[object] = list(objects)

    while stack:
        item = stack.pop()

        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(key, str):
                    sprite_refs.update(GFX_REFERENCE_PATTERN.findall(key))
                    texture_refs.update(to_posix(path) for path in TEXTURE_PATH_PATTERN.findall(key))
                stack.append(value)
            continue

        if isinstance(item, list):
            stack.extend(item)
            continue

        if isinstance(item, str):
            sprite_refs.update(GFX_REFERENCE_PATTERN.findall(item))
            texture_refs.update(to_posix(path) for path in TEXTURE_PATH_PATTERN.findall(item))
            continue

    return sprite_refs, texture_refs


def resolve_reachable_sprites(initial: Set[str], sprite_index: Dict[str, dict]) -> Set[str]:
    reachable: Set[str] = set()
    stack = list(initial)

    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)

        sprite = sprite_index.get(current)
        if not sprite:
            continue

        parent = sprite.get("sprite_sheet_sprite_type")
        if parent and parent not in reachable:
            stack.append(parent)

    return reachable


def collect_reachable_textures(
    reachable_sprites: Set[str],
    sprite_index: Dict[str, dict],
    stellaris_root: Path,
    direct_texture_refs: Optional[Set[str]] = None,
) -> Dict[str, dict]:
    texture_map: Dict[str, dict] = {}

    for sprite_name in sorted(reachable_sprites):
        sprite = sprite_index.get(sprite_name)
        if not sprite:
            continue

        for texture_rel in sprite.get("textures", []):
            normalized_rel = to_posix(texture_rel)
            source_path = stellaris_root / Path(normalized_rel)
            info = texture_map.setdefault(
                normalized_rel,
                {
                    "source_rel": normalized_rel,
                    "exists": source_path.exists(),
                    "source_size": source_path.stat().st_size if source_path.exists() else None,
                    "referenced_by": [],
                },
            )
            info["referenced_by"].append(sprite_name)

    for info in texture_map.values():
        info["referenced_by"] = sorted(set(info["referenced_by"]))

    if direct_texture_refs:
        for texture_rel in sorted(direct_texture_refs):
            normalized_rel = to_posix(texture_rel.strip().strip('"').strip("'"))
            source_path = stellaris_root / Path(normalized_rel)
            info = texture_map.setdefault(
                normalized_rel,
                {
                    "source_rel": normalized_rel,
                    "exists": source_path.exists(),
                    "source_size": source_path.stat().st_size if source_path.exists() else None,
                    "referenced_by": [],
                },
            )
            info["referenced_by"].append("__direct_reference__")
            info["referenced_by"] = sorted(set(info["referenced_by"]))

    return texture_map


def should_skip_conversion(source_path: Path, output_path: Path) -> bool:
    if not output_path.exists():
        return False
    try:
        return output_path.stat().st_mtime >= source_path.stat().st_mtime and output_path.stat().st_size > 0
    except OSError:
        return False


def convert_image_to_webp(source_path: Path, output_path: Path, quality: int) -> None:
    if Image is None:
        raise RuntimeError("Pillow is not installed. Install pillow to enable image conversion.")

    ext = source_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if ext == ".dds":
        if imageio is None:
            raise RuntimeError("imageio is not installed. Install imageio to convert DDS textures.")
        arr = imageio.imread(source_path)
        if hasattr(arr, "astype"):
            arr = arr.astype("uint8")
        image = Image.fromarray(arr)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        image.save(output_path, format="WEBP", quality=quality, method=6)
        return

    with Image.open(source_path) as image:
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        image.save(output_path, format="WEBP", quality=quality, method=6)


def convert_or_copy_texture(
    source_rel: str,
    stellaris_root: Path,
    assets_dir: Path,
    quality: int,
    dry_run: bool,
) -> dict:
    source_path = stellaris_root / Path(source_rel)
    output_base = assets_dir / STELLARIS_MIRROR_DIR_NAME / Path(source_rel)
    webp_output = output_base.with_suffix(".webp")

    result = {
        "source_rel": source_rel,
        "exists": source_path.exists(),
        "output_rel": None,
        "status": None,
        "error": None,
    }

    if not source_path.exists():
        result["status"] = "missing"
        return result

    if dry_run:
        result["output_rel"] = to_posix(webp_output.relative_to(assets_dir))
        result["status"] = "planned"
        return result

    try:
        if should_skip_conversion(source_path, webp_output):
            result["output_rel"] = to_posix(webp_output.relative_to(assets_dir))
            result["status"] = "skipped_up_to_date"
            return result

        convert_image_to_webp(source_path, webp_output, quality=quality)
        result["output_rel"] = to_posix(webp_output.relative_to(assets_dir))
        result["status"] = "converted"
        return result
    except Exception as exc:
        fallback_output = assets_dir / STELLARIS_MIRROR_DIR_NAME / Path(source_rel)
        fallback_output.parent.mkdir(parents=True, exist_ok=True)

        if should_skip_conversion(source_path, fallback_output):
            result["output_rel"] = to_posix(fallback_output.relative_to(assets_dir))
            result["status"] = "copied_up_to_date"
            result["error"] = str(exc)
            return result

        try:
            shutil.copy2(source_path, fallback_output)
            result["output_rel"] = to_posix(fallback_output.relative_to(assets_dir))
            result["status"] = "copied_original"
            result["error"] = str(exc)
            return result
        except Exception as copy_exc:
            result["status"] = "failed"
            result["error"] = f"{exc} | copy fallback failed: {copy_exc}"
            return result


def probe_image_size(source_path: Path) -> Optional[Tuple[int, int]]:
    if not source_path.exists():
        return None

    ext = source_path.suffix.lower()
    try:
        if ext == ".dds":
            if imageio is None:
                return None
            arr = imageio.imread(source_path)
            if hasattr(arr, "shape") and len(arr.shape) >= 2:
                return int(arr.shape[1]), int(arr.shape[0])
            return None

        if Image is None:
            return None

        with Image.open(source_path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None


def build_frame_rects(
    reachable_sprites: Set[str],
    sprite_index: Dict[str, dict],
    stellaris_root: Path,
) -> Dict[str, dict]:
    frame_rects: Dict[str, dict] = {}

    for sprite_name in sorted(reachable_sprites):
        sprite = sprite_index.get(sprite_name)
        if not sprite:
            continue

        frame_count = int(sprite.get("no_of_frames") or 1)
        if frame_count <= 1:
            continue

        texture_rel = sprite.get("primary_texture")
        if not texture_rel:
            continue

        source_path = stellaris_root / Path(texture_rel)
        size = probe_image_size(source_path)
        if not size:
            continue

        width, height = size
        frame_width = width // frame_count
        if frame_width <= 0:
            continue

        divisible = (width % frame_count) == 0
        rects = []
        for index in range(frame_count):
            rects.append(
                {
                    "frame_index": index + 1,
                    "x": index * frame_width,
                    "y": 0,
                    "width": frame_width,
                    "height": height,
                }
            )

        frame_rects[sprite_name] = {
            "texture_rel": to_posix(texture_rel),
            "frame_count": frame_count,
            "layout_assumption": "horizontal_strip",
            "exact_division": divisible,
            "texture_size": {"width": width, "height": height},
            "frames": rects,
        }

    return frame_rects


def parse_fonts_asset(fonts_asset_path: Path) -> Dict[str, dict]:
    if not fonts_asset_path.exists():
        return {}

    text = read_text(fonts_asset_path)
    fonts: Dict[str, dict] = {}

    for _, block in iter_named_blocks(text, ["font"]):
        name = extract_string(block, "name")
        if not name:
            continue

        styles: Dict[str, str] = {}
        for _, style_block in iter_named_blocks(block, ["fontstyle"]):
            style_name = extract_string(style_block, "style") or "regular"
            style_file = extract_string(style_block, "file")
            if style_file:
                styles[style_name] = to_posix(style_file)

        fonts[name] = {
            "name": name,
            "styles": styles,
        }

    return fonts


def parse_bitmap_fonts(interface_fonts_gfx_path: Path) -> Tuple[Dict[str, dict], List[dict]]:
    if not interface_fonts_gfx_path.exists():
        return {}, []

    text = read_text(interface_fonts_gfx_path)
    bitmap_fonts: Dict[str, dict] = {}
    overrides: List[dict] = []

    for _, block in iter_named_blocks(text, ["bitmapfont"]):
        name = extract_string(block, "name")
        if not name:
            continue

        fontfiles: List[str] = []
        fontfiles_block = extract_key_block(block, "fontfiles")
        if fontfiles_block:
            fontfiles = [to_posix(token) for token in extract_token_list(fontfiles_block)]

        path_value = extract_string(block, "path")

        bitmap_fonts[name] = {
            "name": name,
            "fontfiles": fontfiles,
            "path": to_posix(path_value) if path_value else None,
        }

    for _, block in iter_named_blocks(text, ["bitmapfont_override"]):
        name = extract_string(block, "name")
        if not name:
            continue

        languages_block = extract_key_block(block, "languages")
        languages = extract_token_list(languages_block) if languages_block else []

        overrides.append(
            {
                "name": name,
                "ttf_font": extract_string(block, "ttf_font"),
                "ttf_size": extract_int(block, "ttf_size"),
                "languages": languages,
            }
        )

    return bitmap_fonts, overrides


def resolve_bitmap_files(bitmap_entry: dict, stellaris_root: Path) -> List[str]:
    resolved: List[str] = []
    candidates: List[Path] = []

    for base in bitmap_entry.get("fontfiles", []):
        base_path = stellaris_root / Path(base)
        candidates.extend([base_path.with_suffix(".fnt"), base_path.with_suffix(".dds"), base_path.with_suffix(".tga")])

    path_value = bitmap_entry.get("path")
    if path_value:
        base_path = stellaris_root / Path(path_value)
        candidates.extend([base_path.with_suffix(".fnt"), base_path.with_suffix(".dds"), base_path.with_suffix(".tga")])

    seen: Set[str] = set()
    for candidate in candidates:
        if candidate.exists():
            rel = to_posix(candidate.relative_to(stellaris_root))
            if rel not in seen:
                seen.add(rel)
                resolved.append(rel)

    return resolved


def build_font_map(
    gui_fonts: Set[str],
    bitmap_fonts: Dict[str, dict],
    overrides: List[dict],
    ttf_fonts: Dict[str, dict],
    stellaris_root: Path,
) -> Dict[str, dict]:
    by_name: Dict[str, List[dict]] = {}
    for override in overrides:
        by_name.setdefault(override["name"], []).append(override)

    gui_font_map: Dict[str, dict] = {}
    for gui_font in sorted(gui_fonts):
        entry: Dict[str, object] = {
            "font_id": gui_font,
            "bitmap_font_defined": gui_font in bitmap_fonts,
            "bitmap_sources": [],
            "ttf_overrides": [],
        }

        bitmap_entry = bitmap_fonts.get(gui_font)
        if bitmap_entry:
            entry["bitmap_sources"] = resolve_bitmap_files(bitmap_entry, stellaris_root)

        override_entries = by_name.get(gui_font, [])
        ttf_override_payload = []
        for override in override_entries:
            ttf_name = override.get("ttf_font")
            ttf_entry = ttf_fonts.get(ttf_name, {}) if ttf_name else {}
            ttf_override_payload.append(
                {
                    "ttf_font": ttf_name,
                    "ttf_size": override.get("ttf_size"),
                    "languages": override.get("languages", []),
                    "ttf_styles": ttf_entry.get("styles", {}),
                }
            )

        entry["ttf_overrides"] = ttf_override_payload
        gui_font_map[gui_font] = entry

    return {
        "gui_font_map": gui_font_map,
        "ttf_fonts": ttf_fonts,
    }


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


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


def run_asset_pipeline(
    *,
    stellaris_root: Path,
    assets_dir: Path,
    target_gui: Optional[List[str]] = None,
    all_gui: bool = False,
    additional_sprite_refs: Optional[Set[str]] = None,
    additional_texture_refs: Optional[Set[str]] = None,
    dry_run: bool = False,
    webp_quality: int = 90,
    default_gui_targets: bool = True,
    reporter=None,
) -> dict:
    interface_dir = stellaris_root / "interface"
    fonts_asset_path = stellaris_root / "fonts" / "fonts.asset"
    interface_fonts_gfx_path = interface_dir / "fonts.gfx"
    index_dir = assets_dir / INDEX_DIR_NAME

    if not interface_dir.exists():
        raise SystemExit(f"Stellaris interface directory not found: {interface_dir}")

    gui_targets = target_gui or []
    target_guis, target_warnings = resolve_target_guis(
        interface_dir=interface_dir,
        targets=gui_targets,
        all_gui=all_gui,
        default_to_anomaly=default_gui_targets,
    )

    _emit(f"[forge-assets] Stellaris root: {stellaris_root}", reporter=reporter)
    _emit(f"[forge-assets] Assets output: {assets_dir}", reporter=reporter)
    _emit(f"[forge-assets] Target gui count: {len(target_guis)}", reporter=reporter)
    for warning in target_warnings:
        _emit(f"[forge-assets] warning: {warning}", reporter=reporter, level="warn")

    gfx_paths = sorted(interface_dir.rglob("*.gfx"))
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Parse GFX", total=len(gfx_paths))
        except Exception:
            pass

    sprite_index = parse_gfx_sprites(interface_dir, stellaris_root, gfx_paths=gfx_paths, reporter=reporter)
    _emit(f"[forge-assets] Parsed sprite definitions: {len(sprite_index)}", reporter=reporter)

    gui_refs: Dict[str, dict] = {}
    gui_sprite_refs: Set[str] = set()
    font_refs: Set[str] = set()
    if target_guis:
        if reporter is not None:
            try:
                reporter.set_phase("Forge | Parse GUI refs", total=len(target_guis))
            except Exception:
                pass
        gui_refs, gui_sprite_refs, font_refs = parse_gui_references(
            target_guis,
            interface_dir,
            stellaris_root,
            reporter=reporter,
        )

    all_sprite_refs = set(gui_sprite_refs)
    if additional_sprite_refs:
        all_sprite_refs.update(additional_sprite_refs)

    all_texture_refs = set(additional_texture_refs or set())

    if not all_sprite_refs and not all_texture_refs:
        raise SystemExit(
            "No sprite or texture references provided. "
            "Pass --target-gui/--all-gui or provide additional references."
        )

    reachable_sprites = resolve_reachable_sprites(all_sprite_refs, sprite_index)
    missing_sprites = sorted(name for name in reachable_sprites if name not in sprite_index)
    _emit(
        f"[forge-assets] Referenced sprites: {len(all_sprite_refs)} | Reachable sprites: {len(reachable_sprites)}",
        reporter=reporter,
    )

    texture_map = collect_reachable_textures(
        reachable_sprites=reachable_sprites,
        sprite_index=sprite_index,
        stellaris_root=stellaris_root,
        direct_texture_refs=all_texture_refs,
    )
    _emit(f"[forge-assets] Reachable textures: {len(texture_map)}", reporter=reporter)

    conversion_results: Dict[str, dict] = {}
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Convert textures", total=len(texture_map))
        except Exception:
            pass
    for texture_rel in sorted(texture_map):
        if reporter is not None:
            try:
                reporter.set_current_file(texture_rel)
                reporter.advance()
            except Exception:
                pass
        conversion_results[texture_rel] = convert_or_copy_texture(
            source_rel=texture_rel,
            stellaris_root=stellaris_root,
            assets_dir=assets_dir,
            quality=webp_quality,
            dry_run=dry_run,
        )
        status = conversion_results[texture_rel].get("status")
        if status in {"missing", "failed", "copied_original"}:
            _emit(
                f"[forge-assets] texture status {status}: {texture_rel}",
                reporter=reporter,
                level="warn" if status != "failed" else "error",
            )

    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build metadata", total=3)
            reporter.set_current_file("frame_rects")
            reporter.advance()
        except Exception:
            pass
    frame_rects = build_frame_rects(reachable_sprites, sprite_index, stellaris_root)
    _emit(f"[forge-assets] Frame metadata entries: {len(frame_rects)}", reporter=reporter)

    if reporter is not None:
        try:
            reporter.set_current_file("font_map")
            reporter.advance()
        except Exception:
            pass
    ttf_fonts = parse_fonts_asset(fonts_asset_path)
    bitmap_fonts, bitmap_overrides = parse_bitmap_fonts(interface_fonts_gfx_path)
    font_map = build_font_map(font_refs, bitmap_fonts, bitmap_overrides, ttf_fonts, stellaris_root)

    sprite_index_out = {name: sprite_index[name] for name in sorted(sprite_index)}
    gui_refs_out = {
        "targets": [to_posix(path.relative_to(stellaris_root)) for path in target_guis],
        "refs_by_gui": gui_refs,
        "missing_sprites": missing_sprites,
        "additional_sprite_ref_count": len(additional_sprite_refs or set()),
        "additional_texture_ref_count": len(additional_texture_refs or set()),
    }

    reachable_textures_out = []
    for texture_rel in sorted(texture_map):
        row = dict(texture_map[texture_rel])
        row["conversion"] = conversion_results.get(texture_rel, {})
        reachable_textures_out.append(row)

    if reporter is not None:
        try:
            reporter.set_current_file("index JSON")
            reporter.advance()
        except Exception:
            pass
    write_json(index_dir / "sprite_index.json", sprite_index_out)
    write_json(index_dir / "gui_refs.json", gui_refs_out)
    write_json(index_dir / "reachable_textures.json", reachable_textures_out)
    write_json(index_dir / "frame_rects.json", frame_rects)
    write_json(index_dir / "font_map.json", font_map)

    status_counts: Dict[str, int] = {}
    for result in conversion_results.values():
        status = result.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    _emit("[forge-assets] Conversion status summary:", reporter=reporter)
    for status in sorted(status_counts):
        _emit(f"  - {status}: {status_counts[status]}", reporter=reporter)

    _emit(f"[forge-assets] Wrote index files to: {index_dir}", reporter=reporter)
    if not dry_run:
        _emit(
            f"[forge-assets] Wrote texture outputs under: {assets_dir / STELLARIS_MIRROR_DIR_NAME}",
            reporter=reporter,
        )

    return {
        "target_gui_count": len(target_guis),
        "sprite_ref_count": len(all_sprite_refs),
        "reachable_sprite_count": len(reachable_sprites),
        "texture_count": len(texture_map),
        "missing_sprite_count": len(missing_sprites),
        "status_counts": status_counts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Forge asset pipeline for Stellaris GUI/GFX references -> project assets mirror."
    )
    parser.add_argument(
        "--stellaris-root",
        type=Path,
        default=DEFAULT_STELLARIS_ROOT,
        help="Path to Stellaris install root.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("assets"),
        help="Project assets output directory (default: ./assets).",
    )
    parser.add_argument(
        "--target-gui",
        action="append",
        default=[],
        help="Target .gui file under interface/ (repeatable). Supports glob patterns.",
    )
    parser.add_argument(
        "--all-gui",
        action="store_true",
        help="Process all interface .gui files instead of specific targets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build metadata only and skip copying/conversion.",
    )
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=90,
        help="WebP quality for converted textures (default: 90).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    run_asset_pipeline(
        stellaris_root=args.stellaris_root,
        assets_dir=args.assets_dir,
        target_gui=args.target_gui,
        all_gui=args.all_gui,
        dry_run=args.dry_run,
        webp_quality=args.webp_quality,
        default_gui_targets=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
