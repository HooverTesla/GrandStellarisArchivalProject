# Web App, name WIP

## Do not delete from this document, may add to it at the bottom

## General todo

    - Event chains with multiple options should show branching paths, 
    - Main bar up top should have multiple tabs including empire/home, anomalies, events, archeological sites, astral rifts, more added later. 
    - Search bar up top searches everything and changes tab to each result
    - add a plus button or something to add it the empire tab/home/saved location. \
    - Need to set up siteground to accept this as a git pushed static site
        - needs research

## Aesthetics

    - Style should be more closely aligned with the STT

## Empire tab

    - Will eventually save anomalies, rifts etc in one location for easy user access
    - custom name, logo, details, modifiers
    - saves in browser for players
        - could be a cookie, or a seed/key, downloaded json/text, or mayyyyyybe account/cloud but probably unneeded
    









## Roadmap

### Not anytime soon but eventually want the following features

    - save game file parsing
        - Ideally live but that's probably a stretch
    - Overlay for keyboard shortcuts
    - empire graphic editer icon for the saved empire tab
    - full database of relics, collections, ethics etc
        - eventually full wiki replacement
    - Keyboard shortcuts for things not able to be shortcutted in game
        - grand archive
        - relics
        - etc

## UI Sprite Notes

    - Button sprite metadata for `assets/stellaris/gfx/interface/buttons/*.webp` is generated to:
        - `assets/data/v1/media/button_sprite_instructions.json`
    - Generation script:
        - `python scripts/generate-button-sprite-instructions.py`
    - Current UI uses 3-frame horizontal strips as:
        - frame 0 = normal
        - frame 1 = hover/focus
        - frame 2 = pressed/active
    
