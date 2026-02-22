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


SCHEMA_VERSION = "1.0.0"
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

KNOWN_EVENT_LINK_KEYS = {"country_event", "ship_event", "planet_event", "fleet_event", "pop_event"}


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
                option_name_keys = extract_option_name_keys(payload.get("option"))

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
                gfx_refs.update(dedup_pictures)

                record = {
                    "id": event_id,
                    "event_type": event_type,
                    "title_key": title_key,
                    "desc_keys": desc_keys,
                    "picture_gfx_candidates": dedup_pictures,
                    "picture_asset_candidates": [
                        resolve_gfx_asset(gfx, sprite_index, texture_to_asset) for gfx in dedup_pictures
                    ],
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
    event_to_events: Dict[str, List[str]],
) -> Dict[str, dict]:
    reverse: Dict[str, dict] = {}

    def ensure(event_id: str) -> dict:
        return reverse.setdefault(
            event_id,
            {"from_anomalies": [], "from_arc_sites": [], "from_events": []},
        )

    for anomaly_id, event_ids in anomaly_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_anomalies"].append(anomaly_id)

    for site_id, event_ids in arc_site_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_arc_sites"].append(site_id)

    for source_event_id, event_ids in event_to_events.items():
        for event_id in event_ids:
            ensure(event_id)["from_events"].append(source_event_id)

    for payload in reverse.values():
        payload["from_anomalies"] = sorted(set(payload["from_anomalies"]))
        payload["from_arc_sites"] = sorted(set(payload["from_arc_sites"]))
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

    anomalies_dir = output_root / "common" / "anomalies"
    arc_sites_dir = output_root / "common" / "archaeological_site_types"
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

    all_loc_keys = set()
    all_loc_keys.update(anomaly_loc_keys)
    all_loc_keys.update(arc_loc_keys)
    all_loc_keys.update(event_loc_keys)

    referenced_gfx = set()
    referenced_gfx.update(anomaly_gfx)
    referenced_gfx.update(arc_gfx)
    referenced_gfx.update(event_gfx)

    if reporter is not None:
        try:
            reporter.set_phase("Forge | Build chains", total=2)
            reporter.set_current_file("event backlink index")
            reporter.advance()
        except Exception:
            pass
    reverse_event_to_sources = build_reverse_event_sources(anomaly_to_events, arc_site_to_events, event_to_events)

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
    write_json(chains_dir / "anomaly_to_events.json", dict(sorted(anomaly_to_events.items())))
    write_json(chains_dir / "arc_site_to_events.json", dict(sorted(arc_site_to_events.items())))
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
                "referenced_gfx": len(referenced_gfx),
                "unresolved_gfx": len(unresolved_gfx),
                "loc_keys": len(all_loc_keys),
            },
            "unresolved_gfx": unresolved_gfx,
            "duplicate_ids": {
                "anomalies": anomaly_dupes,
                "arc_sites": arc_dupes,
                "events": event_dupes,
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
