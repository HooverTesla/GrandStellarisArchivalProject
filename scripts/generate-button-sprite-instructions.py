from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path("assets/stellaris/gfx/interface/buttons")
OUT = Path("assets/data/v1/media/button_sprite_instructions.json")
SPRITE_INDEX = Path("assets/index/sprite_index.json")


def detect_strip_frames(width: int, height: int) -> int:
    if height <= 0:
        return 1
    if width % height != 0:
        return 1
    frames = width // height
    if 1 < frames <= 8:
        return frames
    return 1


def load_sprite_frame_overrides() -> dict[str, int]:
    if not SPRITE_INDEX.exists():
        return {}
    payload = json.loads(SPRITE_INDEX.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}

    overrides: dict[str, int] = {}
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        texture = str(entry.get("primary_texture") or "").replace("\\", "/").lower()
        if "/buttons/" not in texture or not texture.endswith(".dds"):
            continue
        stem = Path(texture).stem
        frames = int(entry.get("no_of_frames") or 1)
        if frames > 1:
            overrides[stem] = frames
    return overrides


def build_entry(path: Path, sprite_frame_overrides: dict[str, int]) -> dict:
    with Image.open(path) as image:
        width, height = image.size

    frames = int(sprite_frame_overrides.get(path.stem) or detect_strip_frames(width, height))
    if (
        frames == 1
        and path.stem.startswith("topbar_")
        and width % 3 == 0
        and (width // 3) >= max(16, int(height * 0.6))
    ):
        # Some topbar sprites are 3-state strips even though frame width != frame height.
        frames = 3
    if frames < 1:
        frames = 1
    frame_width = width // frames if frames > 0 else width
    states = {}
    if frames >= 3:
        states = {
            "normal": 0,
            "hover": 1,
            "pressed": 2,
        }

    return {
        "file": path.name,
        "asset_path": str(path).replace("\\", "/"),
        "layout": "horizontal_strip" if frames > 1 else "single",
        "sheet": {
            "width": width,
            "height": height,
        },
        "frames": {
            "count": frames,
            "frame_width": frame_width,
            "frame_height": height,
            "axis": "x",
        },
        "states": states,
    }


def main() -> None:
    if not ROOT.exists():
        raise SystemExit(f"Buttons folder not found: {ROOT}")

    data = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Generated from Stellaris sprite metadata when available, with image-dimension fallback.",
        "entries": {},
    }
    sprite_frame_overrides = load_sprite_frame_overrides()

    for path in sorted(ROOT.glob("*.webp"), key=lambda p: p.name.lower()):
        data["entries"][path.stem] = build_entry(path, sprite_frame_overrides)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(data['entries'])} entries)")


if __name__ == "__main__":
    main()
