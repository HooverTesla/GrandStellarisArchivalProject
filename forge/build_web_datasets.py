#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


SCHEMA_VERSION = "1.1.0"
DATA_ROOT_SUBPATH = Path("data") / "v1"

DEFAULT_LOCALES = [
    "l_english",
    "l_german",
    "l_french",
    "l_spanish",
    "l_simp_chinese",
]

LOCALE_DIR_MAP = {
    "l_english": "english",
    "l_braz_por": "braz_por",
    "l_german": "german",
    "l_french": "french",
    "l_spanish": "spanish",
    "l_polish": "polish",
    "l_russian": "russian",
    "l_simp_chinese": "simp_chinese",
    "l_japanese": "japanese",
    "l_korean": "korean",
}

EVENT_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[0-9]+$")
EVENT_ID_IN_TEXT_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*\.[0-9]+)\b")
GFX_PATTERN = re.compile(r"\bGFX_[A-Za-z0-9_]+\b")
TECH_ID_PATTERN = re.compile(r"^tech_[A-Za-z0-9_]+$")

KNOWN_EVENT_LINK_KEYS = {"country_event", "ship_event", "planet_event", "fleet_event", "pop_event"}


DATABANK_CATEGORY_SPECS = [
    {
        "slug": "precursors",
        "label": "Precursors",
        "sources": ["common/precursor_civilizations/*.json"],
    },
    {
        "slug": "relics",
        "label": "Relics",
        "sources": ["common/relics/*.json"],
    },
    {
        "slug": "leaders",
        "label": "Leaders",
        "sources": ["common/leader_classes/*.json", "common/leader_tiers/*.json"],
    },
    {
        "slug": "species_traits",
        "label": "Species Traits",
        "sources": ["common/traits/*species_traits*.json"],
    },
    {
        "slug": "origins",
        "label": "Origins",
        "sources": ["common/governments/civics/*origins*.json"],
    },
    {
        "slug": "guardians",
        "label": "Guardians",
        "sources": ["common/guardian_*/**/*.json"],
    },
    {
        "slug": "situations",
        "label": "Situations",
        "sources": ["common/situations/*.json"],
    },
    {
        "slug": "civics",
        "label": "Civics",
        "sources": ["common/governments/civics/*civic*.json"],
    },
    {
        "slug": "buildings",
        "label": "Buildings",
        "sources": ["common/buildings/*.json"],
    },
    {
        "slug": "traits",
        "label": "Traits",
        "sources": ["common/traits/*.json"],
    },
    {
        "slug": "ethics",
        "label": "Ethics",
        "sources": ["common/ethics/*.json"],
    },
    {
        "slug": "fallen_empires",
        "label": "Fallen Empires",
        "sources": ["common/fallen_empires/*.json"],
    },
    {
        "slug": "world_types",
        "label": "World Types",
        "sources": ["common/planet_classes/*.json"],
    },
    {
        "slug": "terms",
        "label": "Term Definitions",
        "sources": ["common/game_concepts/*.json"],
    },
    {
        "slug": "event_chains",
        "label": "Event Chains",
        "sources": ["common/event_chains/*.json"],
    },
]


def to_posix(path_like: str | Path) -> str:
    return Path(path_like).as_posix()


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


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


def normalize_list(value: object) -> List[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def is_event_id(text: object) -> bool:
    return isinstance(text, str) and bool(EVENT_ID_PATTERN.fullmatch(text.strip()))


def extract_desc_keys(value: object) -> List[str]:
    result: List[str] = []

    def visit(item: object) -> None:
        if isinstance(item, str):
            result.append(item)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if isinstance(item, dict):
            if isinstance(item.get("text"), str):
                result.append(item["text"])
            return

    visit(value)
    seen: Set[str] = set()
    ordered: List[str] = []
    for key in result:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def extract_option_name_keys(value: object) -> List[str]:
    result: List[str] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "name" and isinstance(child, str):
                    result.append(child)
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    seen: Set[str] = set()
    ordered: List[str] = []
    for key in result:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for item in values:
        if not isinstance(item, str):
            continue
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def is_tech_id(text: object) -> bool:
    return isinstance(text, str) and bool(TECH_ID_PATTERN.fullmatch(text.strip()))


def is_loc_key_candidate(text: object) -> bool:
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > 160:
        return False
    if " " in stripped or "/" in stripped:
        return False
    if stripped.startswith("@"):
        return False
    return True


def extract_tech_ids_in_value(value: object) -> List[str]:
    found: List[str] = []
    stack: List[object] = [value]
    while stack:
        item = stack.pop()
        if is_tech_id(item):
            found.append(str(item))
            continue
        if isinstance(item, list):
            stack.extend(item)
            continue
        if isinstance(item, dict):
            for child in item.values():
                stack.append(child)
    return dedupe_preserve_order(found)


def _merge_prerequisite_logic(base: dict, extra: dict) -> dict:
    all_of = dedupe_preserve_order(normalize_list(base.get("all_of")) + normalize_list(extra.get("all_of")))
    any_of_raw = normalize_list(base.get("any_of")) + normalize_list(extra.get("any_of"))
    any_of: List[List[str]] = []
    for group in any_of_raw:
        group_ids = dedupe_preserve_order([item for item in normalize_list(group) if is_tech_id(item)])
        if group_ids:
            any_of.append(group_ids)
    return {"all_of": all_of, "any_of": any_of}


def normalize_prerequisite_logic(value: object) -> dict:
    empty = {"all_of": [], "any_of": []}
    if value is None:
        return empty
    if is_tech_id(value):
        return {"all_of": [str(value)], "any_of": []}
    if isinstance(value, list):
        merged = empty
        for item in value:
            merged = _merge_prerequisite_logic(merged, normalize_prerequisite_logic(item))
        return merged
    if not isinstance(value, dict):
        return empty

    merged = empty

    if "_values" in value:
        merged = _merge_prerequisite_logic(
            merged,
            {"all_of": extract_tech_ids_in_value(value.get("_values")), "any_of": []},
        )

    if "AND" in value:
        merged = _merge_prerequisite_logic(merged, normalize_prerequisite_logic(value.get("AND")))

    if "OR" in value:
        options: List[str] = []
        for option in normalize_list(value.get("OR")):
            options.extend(extract_tech_ids_in_value(option))
        option_ids = dedupe_preserve_order(options)
        if option_ids:
            merged = _merge_prerequisite_logic(merged, {"all_of": [], "any_of": [option_ids]})

    recognized = {"_values", "AND", "OR"}
    if not recognized.intersection(value.keys()):
        merged = _merge_prerequisite_logic(
            merged,
            {"all_of": extract_tech_ids_in_value(value), "any_of": []},
        )

    return merged


def classify_event_category(source_file: object, event_type: object) -> str:
    source = str(source_file or "").lower()
    event_type_norm = str(event_type or "").lower()

    if "pre_ftl" in source or "primitive" in source:
        return "pre_ftl"
    if "colony" in source:
        return "colony"
    if event_type_norm == "country_event":
        return "empire"
    if any(token in source for token in ("federation", "diplomatic", "agenda", "council", "empire")):
        return "empire"
    return "misc"


def extract_event_options(option_value: object) -> tuple[List[dict], List[str], Set[str]]:
    options: List[dict] = []
    all_name_keys: List[str] = []
    loc_keys: Set[str] = set()

    for index, option in enumerate(normalize_list(option_value), start=1):
        if not isinstance(option, dict):
            continue
        name_key = option.get("name") if isinstance(option.get("name"), str) else None
        desc_keys = extract_desc_keys(option.get("desc"))
        followups = sorted(collect_followup_event_ids(option))
        tooltip_keys = extract_desc_keys(option.get("custom_tooltip"))

        if name_key:
            all_name_keys.append(name_key)
            if is_loc_key_candidate(name_key):
                loc_keys.add(name_key)
        for key in desc_keys + tooltip_keys:
            if is_loc_key_candidate(key):
                loc_keys.add(key)

        options.append(
            {
                "index": index,
                "name_key": name_key,
                "desc_keys": desc_keys,
                "tooltip_keys": tooltip_keys,
                "followup_event_ids": followups,
            }
        )

    return options, dedupe_preserve_order(all_name_keys), loc_keys


def _extract_first_gfx(value: object) -> Optional[str]:
    stack: List[object] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            match = GFX_PATTERN.search(item)
            if match:
                return match.group(0)
            continue
        if isinstance(item, list):
            stack.extend(item)
            continue
        if isinstance(item, dict):
            for child in item.values():
                stack.append(child)
    return None

def extract_inline_picture_gfx(inline_script: object) -> List[str]:
    result: List[str] = []
    if not isinstance(inline_script, dict):
        return result

    for key, value in inline_script.items():
        if "PICTURE" not in str(key).upper():
            continue
        if isinstance(value, str):
            for gfx in GFX_PATTERN.findall(value):
                result.append(gfx)

    seen: Set[str] = set()
    ordered: List[str] = []
    for gfx in result:
        if gfx not in seen:
            seen.add(gfx)
            ordered.append(gfx)
    return ordered


def collect_event_ids_in_value(value: object, include_raw_strings: bool = False) -> Set[str]:
    event_ids: Set[str] = set()
    stack: List[object] = [value]

    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "anomaly_event":
                    if is_event_id(child):
                        event_ids.add(child)
                    elif isinstance(child, list):
                        for entry in child:
                            if is_event_id(entry):
                                event_ids.add(entry)
                stack.append(child)
            continue

        if isinstance(item, list):
            stack.extend(item)
            continue

        if include_raw_strings and isinstance(item, str):
            for match in EVENT_ID_IN_TEXT_PATTERN.findall(item):
                event_ids.add(match)

    return event_ids


def collect_followup_event_ids(event_payload: dict) -> Set[str]:
    result: Set[str] = set()

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in KNOWN_EVENT_LINK_KEYS and isinstance(child, dict):
                    linked_id = child.get("id")
                    if is_event_id(linked_id):
                        result.add(linked_id)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(event_payload)
    return result


def load_media_indexes(assets_root: Path) -> tuple[Dict[str, dict], Dict[str, str], Dict[str, dict]]:
    index_dir = assets_root / "index"
    sprite_index = read_json(index_dir / "sprite_index.json") if (index_dir / "sprite_index.json").exists() else {}
    reachable_textures = (
        read_json(index_dir / "reachable_textures.json") if (index_dir / "reachable_textures.json").exists() else []
    )
    frame_rects = read_json(index_dir / "frame_rects.json") if (index_dir / "frame_rects.json").exists() else {}

    texture_to_asset: Dict[str, str] = {}
    for row in normalize_list(reachable_textures):
        if not isinstance(row, dict):
            continue
        source_rel = row.get("source_rel")
        conversion = row.get("conversion", {}) if isinstance(row.get("conversion"), dict) else {}
        output_rel = conversion.get("output_rel")
        if isinstance(source_rel, str) and isinstance(output_rel, str):
            texture_to_asset[to_posix(source_rel)] = to_posix(output_rel)

    return sprite_index if isinstance(sprite_index, dict) else {}, texture_to_asset, frame_rects if isinstance(frame_rects, dict) else {}


def resolve_gfx_asset(gfx_id: Optional[str], sprite_index: Dict[str, dict], texture_to_asset: Dict[str, str]) -> Optional[str]:
    if not isinstance(gfx_id, str):
        return None
    sprite = sprite_index.get(gfx_id)
    if not isinstance(sprite, dict):
        return None
    texture_rel = sprite.get("primary_texture")
    if not isinstance(texture_rel, str):
        return None
    return texture_to_asset.get(to_posix(texture_rel))


def parse_anomalies(
    anomalies_dir: Path,
    sprite_index: Dict[str, dict],
    texture_to_asset: Dict[str, str],
    reporter=None,
) -> tuple[Dict[str, dict], Dict[str, List[str]], Set[str], Set[str], List[str]]:
    records: Dict[str, dict] = {}
    chain_map: Dict[str, List[str]] = {}
    loc_keys: Set[str] = set()
    gfx_refs: Set[str] = set()
    duplicates: List[str] = []

    files = sorted(anomalies_dir.glob("*.json"))
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build web entities", total=len(files))
        except Exception:
            pass

    for path in files:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(path))
                reporter.advance()
            except Exception:
                pass
        try:
            root = read_json(path)
        except Exception as exc:
            _emit(f"[web-datasets] Failed anomaly file: {path} | {exc}", reporter=reporter, level="error")
            continue

        if not isinstance(root, dict):
            continue

        for anomaly_id, wrapper in root.items():
            if not isinstance(wrapper, dict):
                continue
            payload = wrapper.get(anomaly_id)
            if not isinstance(payload, dict):
                continue

            desc_keys = extract_desc_keys(payload.get("desc"))
            desc_key = desc_keys[0] if desc_keys else None
            if isinstance(desc_key, str):
                loc_keys.add(desc_key)

            picture_gfx = payload.get("picture") if isinstance(payload.get("picture"), str) else None
            if picture_gfx:
                for gfx in GFX_PATTERN.findall(picture_gfx):
                    gfx_refs.add(gfx)
                picture_gfx = GFX_PATTERN.findall(picture_gfx)[0] if GFX_PATTERN.findall(picture_gfx) else None

            on_success = payload.get("on_success")
            event_ids = set()
            if on_success is not None:
                event_ids.update(collect_event_ids_in_value(on_success, include_raw_strings=True))
            event_ids.update(collect_event_ids_in_value(payload, include_raw_strings=False))

            ordered_event_ids = sorted(event_ids)
            existing_chain = set(chain_map.get(anomaly_id, []))
            existing_chain.update(ordered_event_ids)
            chain_map[anomaly_id] = sorted(existing_chain)

            record = {
                "id": anomaly_id,
                "desc_key": desc_key,
                "level": payload.get("level"),
                "max_once": payload.get("max_once"),
                "max_once_global": payload.get("max_once_global"),
                "picture_gfx": picture_gfx,
                "image_asset": resolve_gfx_asset(picture_gfx, sprite_index, texture_to_asset),
                "event_ids": ordered_event_ids,
                "source_file": wrapper.get("_source_file"),
                "source_line": wrapper.get("_line_number"),
            }

            if anomaly_id in records:
                duplicates.append(anomaly_id)
                existing = records[anomaly_id]
                merged_events = sorted(set(normalize_list(existing.get("event_ids"))) | set(ordered_event_ids))
                existing["event_ids"] = merged_events
                if not existing.get("desc_key"):
                    existing["desc_key"] = desc_key
                if not existing.get("picture_gfx"):
                    existing["picture_gfx"] = picture_gfx
                    existing["image_asset"] = resolve_gfx_asset(picture_gfx, sprite_index, texture_to_asset)
            else:
                records[anomaly_id] = record

    return records, chain_map, loc_keys, gfx_refs, sorted(set(duplicates))


def parse_arc_sites(
    arc_sites_dir: Path,
    sprite_index: Dict[str, dict],
    texture_to_asset: Dict[str, str],
    reporter=None,
) -> tuple[Dict[str, dict], Dict[str, List[str]], Set[str], Set[str], List[str]]:
    records: Dict[str, dict] = {}
    chain_map: Dict[str, List[str]] = {}
    loc_keys: Set[str] = set()
    gfx_refs: Set[str] = set()
    duplicates: List[str] = []

    files = sorted(arc_sites_dir.glob("*.json"))
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build web entities", total=max(1, len(files)))
        except Exception:
            pass

    for path in files:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(path))
                reporter.advance()
            except Exception:
                pass
        try:
            root = read_json(path)
        except Exception as exc:
            _emit(f"[web-datasets] Failed arc site file: {path} | {exc}", reporter=reporter, level="error")
            continue

        if not isinstance(root, dict):
            continue

        for site_id, wrapper in root.items():
            if not isinstance(wrapper, dict):
                continue
            payload = wrapper.get(site_id)
            if not isinstance(payload, dict):
                continue

            desc_keys = extract_desc_keys(payload.get("desc"))
            for key in desc_keys:
                loc_keys.add(key)

            picture_gfx = payload.get("picture") if isinstance(payload.get("picture"), str) else None
            if picture_gfx:
                found = GFX_PATTERN.findall(picture_gfx)
                if found:
                    picture_gfx = found[0]
                    gfx_refs.add(picture_gfx)
                else:
                    picture_gfx = None

            stages: List[dict] = []
            stage_event_ids: List[str] = []
            for index, stage in enumerate(normalize_list(payload.get("stage")), start=1):
                if not isinstance(stage, dict):
                    continue
                icon_gfx = stage.get("icon") if isinstance(stage.get("icon"), str) else None
                if icon_gfx:
                    icon_found = GFX_PATTERN.findall(icon_gfx)
                    icon_gfx = icon_found[0] if icon_found else None
                if icon_gfx:
                    gfx_refs.add(icon_gfx)

                event_id = stage.get("event") if is_event_id(stage.get("event")) else None
                if event_id:
                    stage_event_ids.append(event_id)

                stages.append(
                    {
                        "stage_index": index,
                        "difficulty": stage.get("difficulty"),
                        "icon_gfx": icon_gfx,
                        "event_id": event_id,
                    }
                )

            existing_chain = set(chain_map.get(site_id, []))
            existing_chain.update(stage_event_ids)
            chain_map[site_id] = sorted(existing_chain)
            record = {
                "id": site_id,
                "desc_keys": desc_keys,
                "picture_gfx": picture_gfx,
                "image_asset": resolve_gfx_asset(picture_gfx, sprite_index, texture_to_asset),
                "stages": stages,
                "source_file": wrapper.get("_source_file"),
                "source_line": wrapper.get("_line_number"),
            }

            if site_id in records:
                duplicates.append(site_id)
                existing = records[site_id]
                combined: List[dict] = []
                for stage_item in normalize_list(existing.get("stages")) + stages:
                    if not isinstance(stage_item, dict):
                        continue
                    combined.append(stage_item)
                by_index: Dict[int, dict] = {}
                for stage_item in combined:
                    stage_index = int(stage_item.get("stage_index", 0))
                    by_index[stage_index] = stage_item
                existing["stages"] = [by_index[idx] for idx in sorted(by_index) if idx > 0]
            else:
                records[site_id] = record

    return records, chain_map, loc_keys, gfx_refs, sorted(set(duplicates))


def parse_events(
    events_dir: Path,
    sprite_index: Dict[str, dict],
    texture_to_asset: Dict[str, str],
    reporter=None,
) -> tuple[Dict[str, dict], Dict[str, List[str]], Set[str], Set[str], List[str]]:
    records: Dict[str, dict] = {}
    event_to_events: Dict[str, Set[str]] = defaultdict(set)
    loc_keys: Set[str] = set()
    gfx_refs: Set[str] = set()
    duplicates: List[str] = []

    files = sorted(events_dir.glob("*.json"))
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build web entities", total=max(1, len(files)))
        except Exception:
            pass

    for path in files:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(path))
                reporter.advance()
            except Exception:
                pass
        try:
            root = read_json(path)
        except Exception as exc:
            _emit(f"[web-datasets] Failed event file: {path} | {exc}", reporter=reporter, level="error")
            continue

        if not isinstance(root, dict):
            continue

        for event_type, entries in root.items():
            if not isinstance(event_type, str) or event_type.startswith("_"):
                continue

            for entry in normalize_list(entries):
                if not isinstance(entry, dict):
                    continue
                payload = entry.get(event_type)
                if not isinstance(payload, dict):
                    continue

                event_id = payload.get("id")
                if not is_event_id(event_id):
                    continue

                title_key = payload.get("title") if isinstance(payload.get("title"), str) else None
                desc_keys = extract_desc_keys(payload.get("desc"))
                options, option_name_keys, option_loc_keys = extract_event_options(payload.get("option"))
                event_category = classify_event_category(entry.get("_source_file"), event_type)

                picture_candidates: List[str] = []
                direct_picture = payload.get("picture")
                if isinstance(direct_picture, str):
                    picture_candidates.extend(GFX_PATTERN.findall(direct_picture))

                picture_candidates.extend(extract_inline_picture_gfx(payload.get("inline_script")))
                dedup_pictures: List[str] = []
                seen_pictures: Set[str] = set()
                for pic in picture_candidates:
                    if pic not in seen_pictures:
                        seen_pictures.add(pic)
                        dedup_pictures.append(pic)

                followups = collect_followup_event_ids(payload)
                event_to_events[event_id].update(followups)

                if title_key:
                    loc_keys.add(title_key)
                for key in desc_keys:
                    loc_keys.add(key)
                for key in option_name_keys:
                    loc_keys.add(key)
                loc_keys.update(option_loc_keys)
                gfx_refs.update(dedup_pictures)

                record = {
                    "id": event_id,
                    "event_type": event_type,
                    "event_category": event_category,
                    "title_key": title_key,
                    "desc_keys": desc_keys,
                    "picture_gfx_candidates": dedup_pictures,
                    "picture_asset_candidates": [
                        resolve_gfx_asset(gfx, sprite_index, texture_to_asset) for gfx in dedup_pictures
                    ],
                    "options": options,
                    "option_name_keys": option_name_keys,
                    "followup_event_ids": sorted(followups),
                    "source_file": entry.get("_source_file"),
                    "source_line": entry.get("_line_number"),
                }

                if event_id in records:
                    duplicates.append(event_id)
                    existing = records[event_id]
                    existing["desc_keys"] = sorted(set(normalize_list(existing.get("desc_keys"))) | set(desc_keys))
                    existing["option_name_keys"] = sorted(
                        set(normalize_list(existing.get("option_name_keys"))) | set(option_name_keys)
                    )
                    existing_options = normalize_list(existing.get("options"))
                    merged_options: List[dict] = []
                    option_by_index: Dict[int, dict] = {}
                    for opt in existing_options + options:
                        if not isinstance(opt, dict):
                            continue
                        idx = int(opt.get("index", 0))
                        if idx <= 0:
                            continue
                        option_by_index[idx] = opt
                    for idx in sorted(option_by_index):
                        merged_options.append(option_by_index[idx])
                    existing["options"] = merged_options
                    existing["followup_event_ids"] = sorted(
                        set(normalize_list(existing.get("followup_event_ids"))) | set(followups)
                    )
                    existing["picture_gfx_candidates"] = sorted(
                        set(normalize_list(existing.get("picture_gfx_candidates"))) | set(dedup_pictures)
                    )
                    existing["picture_asset_candidates"] = [
                        resolve_gfx_asset(gfx, sprite_index, texture_to_asset)
                        for gfx in normalize_list(existing.get("picture_gfx_candidates"))
                    ]
                    if not existing.get("event_category"):
                        existing["event_category"] = event_category
                    if existing.get("title_key") is None:
                        existing["title_key"] = title_key
                else:
                    records[event_id] = record

    event_to_events_out = {key: sorted(values) for key, values in sorted(event_to_events.items())}
    for event_id, record in records.items():
        if event_id in event_to_events_out:
            record["followup_event_ids"] = event_to_events_out[event_id]
        else:
            event_to_events_out[event_id] = []
            record["followup_event_ids"] = []

    event_to_events_out = dict(sorted(event_to_events_out.items()))

    return records, event_to_events_out, loc_keys, gfx_refs, sorted(set(duplicates))


def parse_astral_rifts(
    rifts_dir: Path,
    reporter=None,
) -> tuple[Dict[str, dict], Dict[str, List[str]], Set[str], Set[str], List[str]]:
    records: Dict[str, dict] = {}
    chain_map: Dict[str, List[str]] = {}
    loc_keys: Set[str] = set()
    gfx_refs: Set[str] = set()
    duplicates: List[str] = []

    files = sorted(rifts_dir.glob("*.json"))
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build web entities", total=max(1, len(files)))
        except Exception:
            pass

    for path in files:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(path))
                reporter.advance()
            except Exception:
                pass
        try:
            root = read_json(path)
        except Exception as exc:
            _emit(f"[web-datasets] Failed astral rift file: {path} | {exc}", reporter=reporter, level="error")
            continue

        if not isinstance(root, dict):
            continue

        for rift_id, wrapper in root.items():
            if not isinstance(wrapper, dict):
                continue
            payload = wrapper.get(rift_id)
            if not isinstance(payload, dict):
                continue

            name_key = payload.get("name") if isinstance(payload.get("name"), str) else None
            if is_loc_key_candidate(name_key):
                loc_keys.add(str(name_key))

            event_id = payload.get("event") if is_event_id(payload.get("event")) else None
            event_ids = [event_id] if event_id else []
            chain_map[rift_id] = list(event_ids)

            flags = [str(item) for item in normalize_list(payload.get("flags")) if isinstance(item, str)]
            relic_rewards = sorted(flag for flag in flags if flag.startswith("r_"))

            record = {
                "id": rift_id,
                "name_key": name_key,
                "event_id": event_id,
                "event_ids": event_ids,
                "flags": flags,
                "relic_rewards": relic_rewards,
                "is_randomized": str(payload.get("randomized", "yes")).lower() != "no",
                "source_file": wrapper.get("_source_file"),
                "source_line": wrapper.get("_line_number"),
            }

            if rift_id in records:
                duplicates.append(rift_id)
                existing = records[rift_id]
                existing["event_ids"] = dedupe_preserve_order(
                    normalize_list(existing.get("event_ids")) + event_ids,
                )
                existing["flags"] = dedupe_preserve_order(
                    normalize_list(existing.get("flags")) + flags,
                )
                existing["relic_rewards"] = dedupe_preserve_order(
                    normalize_list(existing.get("relic_rewards")) + relic_rewards,
                )
                if existing.get("name_key") is None:
                    existing["name_key"] = name_key
            else:
                records[rift_id] = record

    return records, chain_map, loc_keys, gfx_refs, sorted(set(duplicates))


def _infer_bioship_mode(payload: dict) -> str:
    potential = payload.get("potential")
    if isinstance(potential, dict):
        uses_bio = potential.get("country_uses_bio_ships")
        if isinstance(uses_bio, str):
            if uses_bio.lower() == "yes":
                return "bio_only"
            if uses_bio.lower() == "no":
                return "non_bio_only"
    return "any"


def parse_technologies(
    technology_dir: Path,
    reporter=None,
) -> tuple[Dict[str, dict], Set[str], List[str]]:
    records: Dict[str, dict] = {}
    loc_keys: Set[str] = set()
    duplicates: List[str] = []
    postreq_map: Dict[str, Set[str]] = defaultdict(set)

    files = sorted(technology_dir.glob("*.json"))
    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build web entities", total=max(1, len(files)))
        except Exception:
            pass

    for path in files:
        if reporter is not None:
            try:
                reporter.set_current_file(to_posix(path))
                reporter.advance()
            except Exception:
                pass
        try:
            root = read_json(path)
        except Exception as exc:
            _emit(f"[web-datasets] Failed technology file: {path} | {exc}", reporter=reporter, level="error")
            continue

        if not isinstance(root, dict):
            continue

        for tech_id, wrapper in root.items():
            if not isinstance(wrapper, dict):
                continue
            payload = wrapper.get(tech_id)
            if not isinstance(payload, dict):
                continue
            if not is_tech_id(tech_id):
                continue

            prerequisite_logic = normalize_prerequisite_logic(payload.get("prerequisites"))
            flat_prereqs = dedupe_preserve_order(
                normalize_list(prerequisite_logic.get("all_of"))
                + [item for group in normalize_list(prerequisite_logic.get("any_of")) for item in normalize_list(group)],
            )
            for prereq in flat_prereqs:
                postreq_map[prereq].add(tech_id)

            area = payload.get("area") if isinstance(payload.get("area"), str) else None
            tier_raw = payload.get("tier")
            try:
                tier = int(float(str(tier_raw)))
            except Exception:
                tier = 0
            category = payload.get("category")
            category_list = [str(item) for item in normalize_list(category) if isinstance(item, str)]

            tech_record = {
                "id": tech_id,
                "name_key": tech_id,
                "desc_key": f"{tech_id}_desc",
                "area": area,
                "tier": tier,
                "category": category_list,
                "bioship_mode": _infer_bioship_mode(payload),
                "prerequisites_flat": flat_prereqs,
                "prerequisite_logic": prerequisite_logic,
                "source_file": wrapper.get("_source_file"),
                "source_line": wrapper.get("_line_number"),
            }

            loc_keys.add(tech_id)
            loc_keys.add(f"{tech_id}_desc")

            if tech_id in records:
                duplicates.append(tech_id)
                existing = records[tech_id]
                existing["prerequisites_flat"] = dedupe_preserve_order(
                    normalize_list(existing.get("prerequisites_flat")) + flat_prereqs,
                )
                existing["category"] = dedupe_preserve_order(
                    normalize_list(existing.get("category")) + category_list,
                )
                existing["prerequisite_logic"] = _merge_prerequisite_logic(
                    existing.get("prerequisite_logic", {"all_of": [], "any_of": []}),
                    prerequisite_logic,
                )
                if existing.get("area") is None:
                    existing["area"] = area
                if int(existing.get("tier", 0)) <= 0 and tier > 0:
                    existing["tier"] = tier
            else:
                records[tech_id] = tech_record

    for tech_id, record in records.items():
        record["postrequisites"] = sorted(postreq_map.get(tech_id, set()))

    return dict(sorted(records.items())), loc_keys, sorted(set(duplicates))


def _iter_wrapped_records(root: object) -> Iterable[tuple[str, dict, dict]]:
    if not isinstance(root, dict):
        return
    for entry_id, wrapper in root.items():
        if not isinstance(wrapper, dict):
            continue
        payload = wrapper.get(entry_id)
        if not isinstance(payload, dict):
            continue
        yield entry_id, payload, wrapper


def _find_databank_name_key(entry_id: str, payload: dict) -> str:
    candidates: List[str] = []
    for key in ("name", "title"):
        value = payload.get(key)
        if isinstance(value, str):
            candidates.append(value)
    candidates.append(entry_id)
    for candidate in candidates:
        if is_loc_key_candidate(candidate):
            return candidate
    return entry_id


def _find_databank_desc_key(payload: dict) -> Optional[str]:
    for key in ("description", "desc", "effect_desc", "tooltip"):
        value = payload.get(key)
        if isinstance(value, str) and is_loc_key_candidate(value):
            return value
        values = extract_desc_keys(value)
        for item in values:
            if is_loc_key_candidate(item):
                return item
    return None


def parse_databank_categories(
    output_root: Path,
    sprite_index: Dict[str, dict],
    texture_to_asset: Dict[str, str],
    reporter=None,
) -> tuple[Dict[str, List[dict]], List[dict], Set[str], Set[str]]:
    datasets: Dict[str, List[dict]] = {}
    index_rows: List[dict] = []
    loc_keys: Set[str] = set()
    gfx_refs: Set[str] = set()

    for spec in DATABANK_CATEGORY_SPECS:
        slug = spec["slug"]
        label = spec["label"]
        file_paths: List[Path] = []
        for pattern in spec["sources"]:
            file_paths.extend(sorted(output_root.glob(pattern)))
        file_paths = sorted(set(file_paths))

        entries: List[dict] = []
        if reporter is not None:
            try:
                reporter.set_phase("Forge | Build web entities", total=max(1, len(file_paths)))
            except Exception:
                pass

        for path in file_paths:
            if reporter is not None:
                try:
                    reporter.set_current_file(to_posix(path))
                    reporter.advance()
                except Exception:
                    pass
            try:
                root = read_json(path)
            except Exception as exc:
                _emit(f"[web-datasets] Failed databank file: {path} | {exc}", reporter=reporter, level="warn")
                continue

            for entry_id, payload, wrapper in _iter_wrapped_records(root):
                name_key = _find_databank_name_key(entry_id, payload)
                desc_key = _find_databank_desc_key(payload)
                if is_loc_key_candidate(name_key):
                    loc_keys.add(name_key)
                if is_loc_key_candidate(desc_key):
                    loc_keys.add(str(desc_key))

                gfx_id = _extract_first_gfx(
                    payload.get("picture")
                    or payload.get("portrait")
                    or payload.get("icon")
                    or payload.get("complete_icon")
                )
                if gfx_id:
                    gfx_refs.add(gfx_id)

                tags = dedupe_preserve_order(
                    [str(item) for item in normalize_list(payload.get("tags")) if isinstance(item, str)]
                    + [str(item) for item in normalize_list(payload.get("category")) if isinstance(item, str)],
                )

                entries.append(
                    {
                        "id": entry_id,
                        "name_key": name_key,
                        "desc_key": desc_key,
                        "tags": tags,
                        "gfx_id": gfx_id,
                        "image_asset": resolve_gfx_asset(gfx_id, sprite_index, texture_to_asset),
                        "icon_token": payload.get("icon") if isinstance(payload.get("icon"), str) else None,
                        "source_file": wrapper.get("_source_file"),
                        "source_line": wrapper.get("_line_number"),
                        "source_dataset": to_posix(path.relative_to(output_root)),
                    }
                )

        dedup_map: Dict[str, dict] = {}
        for item in entries:
            dedup_map[item["id"]] = item
        ordered_entries = [dedup_map[key] for key in sorted(dedup_map.keys())]
        datasets[slug] = ordered_entries
        index_rows.append(
            {
                "slug": slug,
                "label": label,
                "available": len(file_paths) > 0,
                "entry_count": len(ordered_entries),
                "source_patterns": spec["sources"],
            }
        )

    return datasets, index_rows, loc_keys, gfx_refs


def load_locale_catalog(output_root: Path, locale_code: str, reporter=None) -> Dict[str, str]:
    locale_dir_name = LOCALE_DIR_MAP.get(locale_code)
    if not locale_dir_name:
        _emit(f"[web-datasets] Unsupported locale code: {locale_code}", reporter=reporter, level="warn")
        return {}

    locale_dir = output_root / "localisation" / locale_dir_name
    if not locale_dir.exists():
        _emit(f"[web-datasets] Locale directory missing: {locale_dir}", reporter=reporter, level="warn")
        return {}

    merged: Dict[str, str] = {}
    for path in sorted(locale_dir.glob("*.json")):
        try:
            data = read_json(path)
        except Exception as exc:
            _emit(f"[web-datasets] Failed localisation file: {path} | {exc}", reporter=reporter, level="warn")
            continue
        if not isinstance(data, dict):
            continue
        for key, value in data.items():
            if isinstance(key, str) and isinstance(value, str):
                merged[key] = value
    return merged


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_gfx_map(
    referenced_gfx: Set[str],
    sprite_index: Dict[str, dict],
    texture_to_asset: Dict[str, str],
) -> tuple[Dict[str, dict], List[str]]:
    gfx_map: Dict[str, dict] = {}
    unresolved: List[str] = []

    for gfx_id in sorted(referenced_gfx):
        sprite = sprite_index.get(gfx_id)
        image_asset = resolve_gfx_asset(gfx_id, sprite_index, texture_to_asset)
        entry = {
            "gfx_id": gfx_id,
            "resolved": image_asset is not None,
            "image_asset": image_asset,
            "primary_texture": sprite.get("primary_texture") if isinstance(sprite, dict) else None,
            "no_of_frames": sprite.get("no_of_frames") if isinstance(sprite, dict) else None,
            "default_frame": sprite.get("default_frame") if isinstance(sprite, dict) else None,
            "source_gfx_file": sprite.get("source_gfx_file") if isinstance(sprite, dict) else None,
        }
        if image_asset is None:
            unresolved.append(gfx_id)
        gfx_map[gfx_id] = entry

    return gfx_map, unresolved


def build_reverse_event_sources(
    anomaly_to_events: Dict[str, List[str]],
    arc_site_to_events: Dict[str, List[str]],
    astral_rift_to_events: Dict[str, List[str]],
    event_to_events: Dict[str, List[str]],
) -> Dict[str, dict]:
    reverse: Dict[str, dict] = {}

    def ensure(event_id: str) -> dict:
        return reverse.setdefault(
            event_id,
            {"from_anomalies": [], "from_arc_sites": [], "from_astral_rifts": [], "from_events": []},
        )

    for anomaly_id, event_ids in anomaly_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_anomalies"].append(anomaly_id)

    for site_id, event_ids in arc_site_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_arc_sites"].append(site_id)

    for rift_id, event_ids in astral_rift_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_astral_rifts"].append(rift_id)

    for source_event_id, event_ids in event_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_events"].append(source_event_id)

    for payload in reverse.values():
        payload["from_anomalies"] = sorted(set(payload["from_anomalies"]))
        payload["from_arc_sites"] = sorted(set(payload["from_arc_sites"]))
        payload["from_astral_rifts"] = sorted(set(payload["from_astral_rifts"]))
        payload["from_events"] = sorted(set(payload["from_events"]))

    return dict(sorted(reverse.items()))


def run_web_dataset_builder(
    *,
    output_root: Path,
    assets_root: Path,
    locales: Optional[List[str]] = None,
    reporter=None,
) -> dict:
    locales = locales or list(DEFAULT_LOCALES)
    data_root = assets_root / DATA_ROOT_SUBPATH
    entities_dir = data_root / "entities"
    chains_dir = data_root / "chains"
    media_dir = data_root / "media"
    i18n_dir = data_root / "i18n"
    databank_dir = entities_dir / "databank"

    anomalies_dir = output_root / "common" / "anomalies"
    arc_sites_dir = output_root / "common" / "archaeological_site_types"
    astral_rifts_dir = output_root / "common" / "astral_rifts"
    technology_dir = output_root / "common" / "technology"
    events_dir = output_root / "events"

    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build web entities", total=1)
            reporter.set_current_file("load media index")
            reporter.advance()
        except Exception:
            pass
    sprite_index, texture_to_asset, frame_rects = load_media_indexes(assets_root)

    anomalies, anomaly_to_events, anomaly_loc_keys, anomaly_gfx, anomaly_dupes = parse_anomalies(
        anomalies_dir,
        sprite_index,
        texture_to_asset,
        reporter=reporter,
    )
    arc_sites, arc_site_to_events, arc_loc_keys, arc_gfx, arc_dupes = parse_arc_sites(
        arc_sites_dir,
        sprite_index,
        texture_to_asset,
        reporter=reporter,
    )
    events, event_to_events, event_loc_keys, event_gfx, event_dupes = parse_events(
        events_dir,
        sprite_index,
        texture_to_asset,
        reporter=reporter,
    )
    astral_rifts, astral_rift_to_events, astral_loc_keys, astral_gfx, astral_dupes = parse_astral_rifts(
        astral_rifts_dir,
        reporter=reporter,
    )
    tech_prerequisites, tech_loc_keys, tech_dupes = parse_technologies(
        technology_dir,
        reporter=reporter,
    )
    databank_datasets, databank_index, databank_loc_keys, databank_gfx = parse_databank_categories(
        output_root,
        sprite_index,
        texture_to_asset,
        reporter=reporter,
    )

    all_loc_keys = set()
    all_loc_keys.update(anomaly_loc_keys)
    all_loc_keys.update(arc_loc_keys)
    all_loc_keys.update(event_loc_keys)
    all_loc_keys.update(astral_loc_keys)
    all_loc_keys.update(tech_loc_keys)
    all_loc_keys.update(databank_loc_keys)

    referenced_gfx = set()
    referenced_gfx.update(anomaly_gfx)
    referenced_gfx.update(arc_gfx)
    referenced_gfx.update(event_gfx)
    referenced_gfx.update(astral_gfx)
    referenced_gfx.update(databank_gfx)

    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build chains", total=2)
            reporter.set_current_file("event backlink index")
            reporter.advance()
        except Exception:
            pass
    reverse_event_to_sources = build_reverse_event_sources(
        anomaly_to_events,
        arc_site_to_events,
        astral_rift_to_events,
        event_to_events,
    )

    if reporter is not None:
        try:
            reporter.set_current_file("media map")
            reporter.advance()
        except Exception:
            pass
    gfx_map, unresolved_gfx = build_gfx_map(referenced_gfx, sprite_index, texture_to_asset)

    filtered_frame_rects = {key: value for key, value in frame_rects.items() if key in referenced_gfx}

    write_json(entities_dir / "anomalies.json", dict(sorted(anomalies.items())))
    write_json(entities_dir / "events.json", dict(sorted(events.items())))
    write_json(entities_dir / "arc_sites.json", dict(sorted(arc_sites.items())))
    write_json(entities_dir / "astral_rifts.json", dict(sorted(astral_rifts.items())))
    write_json(entities_dir / "tech_prerequisites.json", dict(sorted(tech_prerequisites.items())))
    write_json(entities_dir / "databank_index.json", databank_index)
    for category in databank_index:
        slug = category.get("slug")
        if not isinstance(slug, str):
            continue
        write_json(databank_dir / f"{slug}.json", databank_datasets.get(slug, []))
    write_json(chains_dir / "anomaly_to_events.json", dict(sorted(anomaly_to_events.items())))
    write_json(chains_dir / "arc_site_to_events.json", dict(sorted(arc_site_to_events.items())))
    write_json(chains_dir / "astral_rift_to_events.json", dict(sorted(astral_rift_to_events.items())))
    write_json(chains_dir / "event_to_events.json", dict(sorted(event_to_events.items())))
    write_json(chains_dir / "reverse_event_to_sources.json", reverse_event_to_sources)
    write_json(media_dir / "gfx_map.json", gfx_map)
    write_json(media_dir / "frame_rects.json", dict(sorted(filtered_frame_rects.items())))

    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build i18n packs", total=len(locales))
        except Exception:
            pass

    locale_missing_counts: Dict[str, int] = {}
    english_catalog: Dict[str, str] = {}
    for locale_code in locales:
        if reporter is not None:
            try:
                reporter.set_current_file(locale_code)
                reporter.advance()
            except Exception:
                pass

        catalog = load_locale_catalog(output_root, locale_code, reporter=reporter)
        if locale_code == "l_english":
            english_catalog = catalog

        filtered = {key: catalog[key] for key in sorted(all_loc_keys) if key in catalog}
        missing = len(all_loc_keys) - len(filtered)
        locale_missing_counts[locale_code] = missing
        write_json(i18n_dir / locale_code / "narrative.json", filtered)

    english_missing_keys = sorted([key for key in all_loc_keys if key not in english_catalog])

    if reporter is not None:
        try:
            reporter.set_phase("Forge | Write manifest", total=1)
            reporter.set_current_file("manifest.json")
            reporter.advance()
        except Exception:
            pass

    dataset_files = sorted(
        path for path in data_root.rglob("*.json") if path.name.lower() != "manifest.json"
    )

    dataset_manifest: Dict[str, dict] = {}
    for file_path in dataset_files:
        rel = to_posix(file_path.relative_to(data_root))
        dataset_manifest[rel] = {
            "path": rel,
            "bytes": file_path.stat().st_size,
            "sha256": compute_sha256(file_path),
        }

    build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "build_id": build_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "default_locale": "l_english",
        "locales": locales,
        "datasets": dataset_manifest,
        "diagnostics": {
            "counts": {
                "anomalies": len(anomalies),
                "arc_sites": len(arc_sites),
                "events": len(events),
                "astral_rifts": len(astral_rifts),
                "tech_prerequisites": len(tech_prerequisites),
                "databank_categories": len(databank_index),
                "referenced_gfx": len(referenced_gfx),
                "unresolved_gfx": len(unresolved_gfx),
                "loc_keys": len(all_loc_keys),
            },
            "unresolved_gfx": unresolved_gfx,
            "duplicate_ids": {
                "anomalies": anomaly_dupes,
                "arc_sites": arc_dupes,
                "events": event_dupes,
                "astral_rifts": astral_dupes,
                "tech_prerequisites": tech_dupes,
            },
            "locale_missing_counts": locale_missing_counts,
            "english_missing_keys": english_missing_keys,
        },
    }
    write_json(data_root / "manifest.json", manifest)

    summary = {
        "build_id": build_id,
        "counts": manifest["diagnostics"]["counts"],
        "locales": locales,
        "output_root": to_posix(data_root),
    }
    _emit(f"[web-datasets] Built web datasets at {data_root}", reporter=reporter)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build web-friendly datasets from Rosetta + Forge outputs.")
    parser.add_argument("--output-root", type=Path, default=Path("output"), help="Rosetta output root.")
    parser.add_argument("--assets-root", type=Path, default=Path("assets"), help="Assets root.")
    parser.add_argument(
        "--locale",
        action="append",
        dest="locales",
        default=[],
        help="Locale code to include (repeatable). Default: top 4 + English.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    locales = args.locales if args.locales else list(DEFAULT_LOCALES)
    run_web_dataset_builder(
        output_root=args.output_root,
        assets_root=args.assets_root,
        locales=locales,
        reporter=None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
