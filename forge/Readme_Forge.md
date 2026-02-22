### Forge is the information handler.

## Asset Pipeline

`forge/build_stellaris_assets.py` builds a repeatable UI asset mirror for the site.

What it does:
- Parses Stellaris `interface/*.gfx` sprite definitions.
- Parses selected `interface/*.gui` files for referenced sprites and fonts.
- Accepts direct Rosetta-extracted references (for event/anomaly/arc-site/etc image keys).
- Resolves reachable textures (including sprite-sheet aliases).
- Converts textures to WebP under the project `assets/` folder.
- Emits metadata indexes under `assets/index/`:
  - `sprite_index.json`
  - `gui_refs.json`
  - `reachable_textures.json`
  - `frame_rects.json`
  - `font_map.json`

Default paths:
- Stellaris root: `C:/Program Files (x86)/Steam/steamapps/common/Stellaris`
- Output assets dir: `./assets`

## Usage

Target a specific GUI (recommended for smaller output):

```powershell
python forge/build_stellaris_assets.py --target-gui anomaly_view.gui
```

Target multiple GUIs:

```powershell
python forge/build_stellaris_assets.py --target-gui anomaly_view.gui --target-gui mapicons.gui
```

Process all GUI files (largest output):

```powershell
python forge/build_stellaris_assets.py --all-gui
```

Dry run (metadata only, no conversion/copy):

```powershell
python forge/build_stellaris_assets.py --target-gui anomaly_view.gui --dry-run
```

Use a custom Stellaris install path:

```powershell
python forge/build_stellaris_assets.py --stellaris-root "D:/SteamLibrary/steamapps/common/Stellaris" --target-gui anomaly_view.gui
```

## Rosetta Integration

`rosetta/HooverWithWhip.py` now calls Forge automatically at the end of Rosetta runtime.

Workflow:
- Rosetta parses game files as before.
- Rosetta extracts image refs from parsed game data (for example `GFX_evt_*`, `icon`, `picture`, embedded `origin_icon:GFX_*`, and direct `gfx/...` texture paths).
- Forge resolves and converts those references into `assets/stellaris/...`.

Run Rosetta normally:

```powershell
python rosetta/RunRosetta.py
```

## Web Dataset Stage

`forge/build_web_datasets.py` builds static-site-friendly datasets in:

- `assets/data/v1/entities/*.json`
- `assets/data/v1/chains/*.json`
- `assets/data/v1/media/*.json`
- `assets/data/v1/i18n/<locale>/narrative.json`
- `assets/data/v1/manifest.json`

Default locales:
- `l_english`
- `l_german`
- `l_french`
- `l_spanish`
- `l_simp_chinese`

Run directly:

```powershell
python forge/build_web_datasets.py --output-root output --assets-root assets
```

Custom locale set:

```powershell
python forge/build_web_datasets.py --locale l_english --locale l_japanese
```
