# Implementation Notes (Docs Plan Execution)

## Baseline Observations
- Existing web UI had partial modules for anomalies/events/arc sites and STT embedding.
- Search and navigation existed but did not cover Databank/Empire structure or tech-node jumps reliably.
- STT prerequisite interaction was effectively `AND`-only at click-evaluation time.

## Completed Changes In This Pass
- Forge dataset builder expanded with:
  - `astral_rifts` entity + `astral_rift_to_events` chains
  - `tech_prerequisites` entity with preserved logical prerequisite groups (`all_of` + `any_of`)
  - enriched event records (options + category classification)
  - Databank category index + per-category entity feeds
- Web UI restructured to:
  - main tabs: Empire, Events, Tech, Databank (icon-only), plus Settings access
  - empire subtabs: Government, Discoveries, Tech
  - events subtabs: Anomalies, Event Chains, Arc Sites, Astral Rifts
  - Databank tile hub + category detail tables
  - searchable navigation across modules/data/tech entries
- Shared chain-flow styling and rendering integrated across chain-driven pages.
- Discoveries bookmark flow implemented in UI (backend persistence intentionally deferred).
- STT bridge updated for:
  - OR-aware prerequisite checks from Forge tech logic
  - tech chain focus/highlight behavior
  - bioship visibility toggle hook
  - tier summary feed + tech search-entry export
  - removal of save/load backend initialization path

## Deferred / Remaining
- Backend save-system implementation (explicitly deferred).
- Native/global hotkeys outside browser focus (browser-only scope retained).
- Some Databank categories still depend on future Forge source mapping depth.
