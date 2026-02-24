param(
  [Parameter(Mandatory = $true)]
  [string]$SshTarget,

  [Parameter(Mandatory = $true)]
  [string]$RemotePath,

  [int]$Port = 22,
  [string]$DistDir = "dist",
  [string]$SshKeyPath = "",
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

if (-not (Get-Command rsync -ErrorAction SilentlyContinue)) {
  throw "rsync is required for deployment. Install rsync (or run from WSL/Git Bash with rsync available)."
}

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
  throw "ssh command not found in PATH."
}

$remotePath = $RemotePath.Trim()
if (-not $remotePath -or $remotePath -eq "/") {
  throw "RemotePath must be a specific directory, not empty or '/'."
}

$sourcePath = (Resolve-Path $distPath).Path
$sshParts = @("ssh", "-p", "$Port")
if ($SshKeyPath) {
  $resolvedKeyPath = (Resolve-Path $SshKeyPath).Path
  $sshParts += @("-i", "`"$resolvedKeyPath`"")
}
$sshCommand = [string]::Join(" ", $sshParts)
$destination = "$SshTarget`:$remotePath/"

$args = @(
  "-az",
  "--delete",
  "--human-readable",
  "--itemize-changes",
  "--progress",
  "-e", $sshCommand
)

if ($DryRun) {
  $args += "--dry-run"
}

$args += "$sourcePath/"
$args += $destination

Write-Host ("Deploying {0} -> {1}" -f $sourcePath, $destination)
if ($DryRun) {
  Write-Host "Dry run enabled; no files will be changed."
}

& rsync @args
if ($LASTEXITCODE -ne 0) {
  throw "Deploy failed with rsync exit code $LASTEXITCODE."
}

Write-Host "Deploy completed successfully."
