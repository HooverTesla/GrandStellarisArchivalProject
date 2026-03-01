param(
  [string]$OutDir = "dist",
  [switch]$KeepExisting
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$outPath = Join-Path $repoRoot $OutDir

if ((Test-Path $outPath) -and -not $KeepExisting) {
  Remove-Item -Path $outPath -Recurse -Force
}

New-Item -Path $outPath -ItemType Directory -Force | Out-Null

$includeMap = @(
  @{ Source = "ProjectLogo_tech_galactic_archivism.ico"; Dest = "ProjectLogo_tech_galactic_archivism.ico" },
  @{ Source = "webUI"; Dest = "webUI" },
  @{ Source = "assets/data/v1"; Dest = "assets/data/v1" },
  @{ Source = "assets/stellaris"; Dest = "assets/stellaris" },
  @{ Source = "stellaris-tech-tree/assets"; Dest = "stellaris-tech-tree/assets" },
  @{ Source = "stellaris-tech-tree/phoenix-4.0.10"; Dest = "stellaris-tech-tree/phoenix-4.0.10" }
)

foreach ($item in $includeMap) {
  $sourcePath = Join-Path $repoRoot $item.Source
  if (-not (Test-Path $sourcePath)) {
    throw "Missing required path: $sourcePath"
  }

  $destPath = Join-Path $outPath $item.Dest
  $destParent = Split-Path -Parent $destPath
  New-Item -Path $destParent -ItemType Directory -Force | Out-Null
  Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
  Write-Host ("Included: {0}" -f $item.Source)
}

$buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
$buildVersion = (Get-Date).ToString("yyyyMMddHHmmss")
$manifest = @(
  "Grand Stellaris Archive deploy package",
  "Build time: $buildTime",
  "",
  "Included paths:"
) + ($includeMap | ForEach-Object { "- $($_.Dest)" })

$manifestPath = Join-Path $outPath "deploy-manifest.txt"
Set-Content -Path $manifestPath -Value $manifest -Encoding UTF8

$rootIndex = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grand Stellaris Archive</title>
  <meta http-equiv="refresh" content="0; url=./webUI/index.html">
</head>
<body>
  <p>Redirecting to <a href="./webUI/index.html">webUI/index.html</a>...</p>
  <script>
    window.location.replace("./webUI/index.html");
  </script>
</body>
</html>
"@
Set-Content -Path (Join-Path $outPath "index.html") -Value $rootIndex -Encoding UTF8

$webUiPath = Join-Path $outPath "webUI"
if (Test-Path $webUiPath) {
  $webUiFiles = Get-ChildItem -Path $webUiPath -Recurse -File | Where-Object {
    $_.Extension -in @(".html", ".js", ".css")
  }
  foreach ($file in $webUiFiles) {
    $content = Get-Content -Path $file.FullName -Raw
    if ($content.Contains("__BUILD_VERSION__")) {
      $content = $content.Replace("__BUILD_VERSION__", $buildVersion)
      Set-Content -Path $file.FullName -Value $content -Encoding UTF8
    }
  }
}

$apacheNoCache = @'
<IfModule mod_headers.c>
  Header always set Cache-Control "no-store, no-cache, must-revalidate, max-age=0"
  Header always set Pragma "no-cache"
  Header always set Expires "0"
</IfModule>
'@
Set-Content -Path (Join-Path $outPath ".htaccess") -Value $apacheNoCache -Encoding UTF8

$totalBytes = (Get-ChildItem -Path $outPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
if (-not $totalBytes) {
  $totalBytes = 0
}

Write-Host ("Build complete: {0}" -f $outPath)
Write-Host ("Package size: {0:N2} MB" -f ($totalBytes / 1MB))
