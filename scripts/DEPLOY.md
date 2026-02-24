# Deployment Workflow

This project deploys a generated `dist/` package, not the full source tree.

## Recommended For This Machine

Use WSL deploy (works even though Windows PowerShell does not have `rsync` in PATH):

```powershell
.\scripts\deploy-wsl.ps1 -Build -DryRun
.\scripts\deploy-wsl.ps1 -Build
```

## Build Dist Package

```powershell
.\scripts\build-dist.ps1
```

Included in `dist/`:

- `webUI/`
- `assets/data/v1/`
- `assets/stellaris/`
- `stellaris-tech-tree/assets/`
- `stellaris-tech-tree/phoenix-4.0.10/`

## Deploy (Dry Run)

```powershell
.\scripts\deploy.ps1 `
  -Build `
  -DryRun `
  -SshTarget "u2075-ntm9pzojpmo6@gcam1274.siteground.biz" `
  -Port 18765 `
  -SshKeyPath "C:\Users\Brand\.ssh\siteground_ssh" `
  -RemotePath "/home/customer/www/stellaris.hoovertesla.com/public_html"
```

## Deploy (Live)

```powershell
.\scripts\deploy.ps1 `
  -Build `
  -SshTarget "u2075-ntm9pzojpmo6@gcam1274.siteground.biz" `
  -Port 18765 `
  -SshKeyPath "C:\Users\Brand\.ssh\siteground_ssh" `
  -RemotePath "/home/customer/www/stellaris.hoovertesla.com/public_html"
```

## Requirements

- `ssh` in PATH
- `rsync` in PATH (extension-only integrations are not enough for this script)

If `rsync` is missing on Windows, run deploy from WSL or Git Bash with `rsync` installed.
