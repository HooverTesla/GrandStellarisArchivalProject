# GrandStellarisArchivalProject
A Stellaris Companion Tool. Imagine if you could make a research agreement the the Curators *but they could also break the fourth wall to give game advice* ~~Totally not lowkey rebuilding the wiki from scratch~~

Will be viewable and accessable at stellaris.HooverTesla.com

## Live Deploy (Current Standard)

The live site deploys with `rsync` from the generated `dist/` package.

### Runtime content included in deploy

- `webUI/`
- `assets/data/v1/`
- `assets/stellaris/`
- `stellaris-tech-tree/assets/`
- `stellaris-tech-tree/phoenix-4.0.10/`
- root `index.html` (auto-generated redirect to `webUI/index.html`)

### Local deploy requirements (Windows + WSL)

- WSL installed
- WSL packages:
  - `sudo apt update && sudo apt install -y rsync openssh-client`
- SSH key at `C:\Users\Brand\.ssh\siteground_ssh`

### Local deploy commands (from repo root in VS Code PowerShell)

- Dry run:
  - `.\scripts\deploy-wsl.ps1 -Build -DryRun`
- Live deploy:
  - `.\scripts\deploy-wsl.ps1 -Build`

### Important behavior

- Deploy uses `rsync --delete`.
- Anything in remote `public_html` that is not in `dist/` will be removed.

## Auto Deploy On Git Push

GitHub Actions is configured to auto-deploy on push to branch `Live`.

Workflow file:

- `.github/workflows/deploy-live.yml`

Required GitHub repository secrets:

- `SG_SSH_PRIVATE_KEY`: private key content for deploy user
- `SG_SSH_TARGET`: SSH target like `user@example.com`
- `SG_REMOTE_PATH`: remote path like `/home/customer/www/<domain>/public_html`
- `SG_SSH_PORT`: SSH port (for SiteGround this is custom, example `18765`)

How it works:

1. Checks out repo (with submodules).
2. Builds `dist/` via `scripts/build-dist.ps1`.
3. Deploys `dist/` to the server using `rsync --delete`.

Safety note:

- Keep deploy secrets only in GitHub Secrets, never in code.


***********************************************************
************************ DEV NOTES ************************
***********************************************************

Just wanted to make sure you read the README before breaking shit and whining about it.
## **Rosetta -> Scraper/Grabber/Extractor**
  -> Translates PDX nonsense to a nice clean ~~CSV~~ JSON file-Hence Rosetta stone reference
  -> Also beware that PDX puts @foo = 3 shit at the top of files then calls the var later so this will just apply the variable then export the whole number instead of @ foo for the value.
## **Forge -> Processor**
  -> Processes the Raw input(ores) into workable tools, like variables and modifiers
  -> Will probably[^1] have each major category as it's own file for y'all's sakes when I inevitably do my ASD thing and find a different special interest for an indeterminate amount of time.
## **Unknown -> Parser**
  -> the one click shop for running the damn thing, probably[^1] just calling the other files in the folder.
  -> 2.21.26 update, this is a static site/web tool planned first so will be just run from html aka github on stellaris.hoovertesla.com. 
  -> 


## Glossary

  - _foo = metadata of some sort, line numbers, comments from the OG stellaris file, others
  - "FROM" is used in things like 00_diplo_greetings to reference an empire in game, NOT do the thingy that python  wants to do with dicts so it gets handled a little funny, "_EXTERNAL_FROM_BLOCK"
  - ROOT

[^1]: - What? It's 4/5/25 and I haven't built the damn thing yet. So "probably" is me trying to premetively convince me to do good coding habits and also like, do the documentation knowing that I suck at remembering to come back and update things like this. Also if I write down the names of the files that work in my head then I will rememeber the names that make sense in my head and not switch through variants of translators/extractor from books like it's a random number generator. rn everything is shoved into one file called parse_anom_LIVE because I gave up on renaming the stupid thing every iterative update. So... probably is a good thing! Unless I don't stick to it, in which case my name is Hoover and you can mutter my name under your breath in a British Accent and pretend to be a pretentious blond jackass.

***********************************************************
***********************************************************

***********************************************************
***********************************************************

## Rosetta

### To Do

    - Grab image files
    - Grab gfx instructions for those file guides

***Forge is the information handler***

### Images

    - Grab images
    - Copy to .\assets\img
    - Convert .dds to .webp

### Technology

    - Build new python version to take Rosetta out -> STT in
      - aka replace the weird gross java version

### Search

### Chain builder

***Each type of result have it's own builder***

    - When searching needs to grab references and build chain before and after results.  
    - Will need to use a style reference thingy for UI
        - or something idk about this part

### Anomalies

    - name
    - Description
    - image
    - tier
    - Spawn requirements
      - stellar body type
      - modifiers
    - results
      - rewards
      - hazards
        - if any
      


### Arc Sites

### Astral Rifts

### Events

***Coming soon***

- relics
- Collection
- Megastructures
- 



***********************************************************
***********************************************************
Returning 1.23.26

I have no idea what's going tbh. 

Returning 2.22.26

Ditto Me, ditto. 
***********************************************************
***********************************************************
