# Flowchart Style Reference

## Purpose
Shared visual style for chain-style content in:
- Anomalies
- Event Chains
- Arc Sites
- Astral Rifts

## Layout Rules
- Containers use `chain-card` blocks with a header and a body.
- The body uses `chain-flow` as a vertical sequence of `chain-node` cards.
- Each `chain-node` has:
  - Title line (localized title + ID)
  - Description line(s)
  - One-line-per-response options section (`chain-option-line`)
- Linked follow-up targets render as `chain-path-link` buttons.

## Interaction Rules
- Chain sections are collapsed by default from list/table rows.
- Expanding one row renders the chain inline inside that row.
- Clicking follow-up links highlights selected nodes (`is-selected`) and active links (`is-active`).
- Search navigation should open the relevant module/pane and expand the matching chain row.

## Color/Contrast Direction
- Keep STT-aligned dark panels and high-contrast text.
- Node frame: muted blue-gray border.
- Selected path/node: orange emphasis.
- Metadata: muted gray text.

## Reuse Notes
- Do not duplicate per-module chain CSS; use shared classes.
- If a data type has no chain edges available, still render node cards with available event data.
- Keep response rendering one option per line even when localization is missing.
