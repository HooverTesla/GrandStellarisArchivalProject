param(
  [string]$SshTarget = "u2075-ntm9pzojpmo6@gcam1274.siteground.biz",
  [string]$RemotePath = "/home/customer/www/stellaris.hoovertesla.com/public_html",
  [int]$Port = 18765,
  [string]$DistDir = "dist",
  [string]$SshKeyPath = "$env:USERPROFILE\.ssh\siteground_ssh",
  [switch]$Build,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$buildScript = Join-Path $scriptRoot "build-dist.ps1"

if ($Build) {
  & $buildScript -OutDir $DistDir
}

$distPath = Join-Path $repoRoot $DistDir
if (-not (Test-Path $distPath)) {
  throw "Dist directory not found: $distPath. Run build first or use -Build."
}
if (-not (Test-Path $SshKeyPath)) {
  throw "SSH key not found: $SshKeyPath"
}

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
  throw "wsl command not found in PATH."
}

function Convert-ToWslPath([string]$PathValue) {
  $resolved = (Resolve-Path $PathValue).Path
  if ($resolved -match '^([A-Za-z]):\\(.*)$') {
    $drive = $matches[1].ToLower()
    $rest = $matches[2] -replace '\\', '/'
    return "/mnt/$drive/$rest"
  }
  return $resolved
}

$repoWslPath = Convert-ToWslPath $repoRoot
$keyWslPath = Convert-ToWslPath $SshKeyPath

$dryRunArg = ""
if ($DryRun) {
  $dryRunArg = "--dry-run"
}

$remoteDest = "${SshTarget}:$RemotePath/"
$bashCommands = @(
  "set -euo pipefail",
  "mkdir -p ~/.ssh",
  "chmod 700 ~/.ssh",
  "cp '$keyWslPath' ~/.ssh/siteground_ssh",
  "chmod 600 ~/.ssh/siteground_ssh",
  "cd '$repoWslPath'",
  "rsync -az --delete --human-readable --itemize-changes --progress $dryRunArg -e 'ssh -p $Port -i ~/.ssh/siteground_ssh -o IdentitiesOnly=yes' './$DistDir/' '$remoteDest'"
)
$bashScript = ($bashCommands -join "; ")

Write-Host ("Deploying ./{0}/ -> {1}:{2}" -f $DistDir, $SshTarget, $RemotePath)
if ($DryRun) {
  Write-Host "Dry run enabled; no files will be changed."
}

wsl -e bash -lc "$bashScript"
if ($LASTEXITCODE -ne 0) {
  throw "WSL deploy failed with exit code $LASTEXITCODE."
}

Write-Host "Deploy completed successfully."
