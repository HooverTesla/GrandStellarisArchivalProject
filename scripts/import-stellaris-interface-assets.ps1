param(
  [string]$InterfaceRoot = "C:\Program Files (x86)\Steam\steamapps\common\Stellaris\gfx\interface"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path

$buttonsSource = Join-Path $InterfaceRoot "buttons"
$buttonsTarget = Join-Path $repoRoot "assets/stellaris/gfx/interface/buttons"
$homeSource = Join-Path $InterfaceRoot "game_setup/gamesetup_player_empire_unknown.dds"
$homeTarget = Join-Path $repoRoot "assets/stellaris/gfx/interface/game_setup/gamesetup_player_empire_unknown.webp"

if (-not (Test-Path $buttonsSource)) {
  throw "Buttons source path not found: $buttonsSource"
}
if (-not (Test-Path $homeSource)) {
  throw "Home icon source path not found: $homeSource"
}

New-Item -ItemType Directory -Force -Path $buttonsTarget | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $homeTarget) | Out-Null

@'
import os
import sys
from PIL import Image

buttons_source = sys.argv[1]
buttons_target = sys.argv[2]
home_source = sys.argv[3]
home_target = sys.argv[4]

converted = 0
failed = []

for entry in os.listdir(buttons_source):
    if not entry.lower().endswith(".dds"):
        continue
    src = os.path.join(buttons_source, entry)
    dst = os.path.join(buttons_target, os.path.splitext(entry)[0] + ".webp")
    try:
        with Image.open(src) as img:
            img.save(dst, format="WEBP")
        converted += 1
    except Exception as exc:
        failed.append((src, str(exc)))

with Image.open(home_source) as img:
    img.save(home_target, format="WEBP")

print(f"converted_buttons={converted}")
print(f"home_icon={home_target}")
if failed:
    print("failed_files:")
    for src, msg in failed:
        print(f"{src} :: {msg}")
'@ | python - $buttonsSource $buttonsTarget $homeSource $homeTarget

Write-Host "Import complete."
