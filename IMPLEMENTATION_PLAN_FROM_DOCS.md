# Implementation Plan From `docs/` (Review Before Execution)

## Goal
Implement the highest-impact items described in `docs/` that are actionable now, while deferring open product decisions for your review.

## Constraints From Docs
- Do not modify or delete docs content; docs are planning notes and may contain placeholders/dead links.
- Prioritize visible user value first: search quality, readable chain views, tab structure, and Databank access.
- Keep UI styling aligned with Stellaris Tech Tree (STT) visual language.

## Execution Strategy
1. Build reusable foundations first (icons, flowchart styles, shared UI behaviors).
2. Implement core tab UX (WebUI + Databank + Search + Tech fixes).
3. Implement data-type pages (Anomalies, Arc Sites, Astral Rifts, Events) with shared chain rendering.
4. Fix prerequisite data correctness (`OR` logic) before finalizing tech interactions.
5. Add Empire scaffolding with discoveries bookmarks workflow.
6. Validate with focused checks and document residual gaps.

## Confirmed Findings: `OR` Logic Breakpoint
- Submodule web UI currently enforces prerequisites as `AND` when clickable status checks run.
  - Evidence: `stellaris-tech-tree/assets/js/tech-tracking.js` checks every prerequisite status span and blocks activation if any are inactive.
- Submodule data currently drops/loses some `OR` prerequisite structures.
  - Example mismatch:
    - `output/common/technology/00_megastructures.json` has `tech_mega_engineering.prerequisites` with `OR` + additional required values.
    - `stellaris-tech-tree/phoenix-4.0.10/engineering.json` has `tech_mega_engineering.prerequisites` as a flat list.
    - `output/common/technology/00_eng_tech.json` has `tech_titans.prerequisites.OR = [tech_battleships, tech_stinger_growth_2]`.
    - `stellaris-tech-tree/phoenix-4.0.10/engineering.json` has `tech_titans.prerequisites = []`.
- External extractor referenced by STT appears to be a root cause:
  - `.../stellaris-technology/.../TechnologyVisitor.java` only reads `prerequisites` when parsed as an array and does not model logical groups.
  - `.../stellaris-technology/.../AbstractConfigParser.java` builds tree parent from `prerequisites.get(0)`, which cannot represent `OR` branches.

## Phase 0: Baseline + Safety
- Inventory current `webUI`, `forge`, and `rosetta` integration points.
- Snapshot current behavior for:
  - Search result ranking and navigation.
  - Event/anomaly chain rendering.
  - Existing tech tree interactions.
- Define test checklist for regression checks.

Deliverables:
- Short implementation notes in root (what exists, what changed, what remains).

## Phase 1: Shared Foundations
- Add shared style module for "flowchart/chain" presentation used across Events, Anomalies, and Rifts.
- Add human-readable style reference doc in `docs/` (requested in `Data Types.md`) without changing existing instructions.
- Implement global right-click suppression behavior where needed (`Technology.md` + `WebUI.md` intent).
- Standardize icon loading helpers for topbar, subbar, and inline text icons.

Deliverables:
- Reusable flowchart UI component/CSS.
- Centralized icon and interaction helpers.

## Phase 2: Navigation + WebUI Core
- Main tab structure:
  - Empire
  - Events
  - Tech
  - Databank (icon-only as requested)
- Databank entry behavior:
  - Hover reveals "Databank" and category list.
  - Click opens Databank tile/index view.
- Apply favicon `ProjectLogo_tech_galactic_archivism.ico`.
- Add credits/legal section split into:
  - Hoover Tesla
  - STT developers
  - Paradox/Stellaris assets

Deliverables:
- Updated top-level navigation and Databank access behavior.
- Favicon and credits/legal content in UI.

## Phase 3: Search Improvements
- Keep current autocomplete behavior.
- Add result navigation that jumps to exact in-tab target (especially technology nodes).
- Ranking policy:
  - Prioritize current tab relevance.
  - Prefer terms over localization-only matches.
  - Include content-inside-node matching (example: searching a component surfaces its parent tech).
- Add keyboard shortcut support with configurable shortcut settings UI inside the current settings page above the credits.

Deliverables:
- Improved search relevance + direct navigation.
- Shortcut settings surface (initial version).

## Phase 4: Technology Module Fixes
- Phase 4A: prerequisite correctness first
  - Add `OR`-aware prerequisite model in generated tech data (preserve grouped logic, not flattened only).
  - Decide implementation path:
    - Preferred: use Forge/Rosetta-generated tech graph as source of truth for web UI.
    - Alternate: patch external STT extractor and regenerate submodule JSON.
  - Add renderer support for logical prerequisite groups (`AND` set + one-or-more `OR` groups).
  - Update click/activation checks to evaluate logical prerequisite groups correctly.
- Remove/adjust blue boxed container mismatch to desired gray-background integration.
- On tech click, filter to prerequisite/postrequisite chain (cross-category included).
- Remove save/load/progress bar from STT bottom area if still present.
- Add bioship toggle in tech sub-nav (empire-aware filtering hook prepared).
- Add per-discipline tier tracker in sub-nav using level icon styling.
- Correct known wrong-info mappings where data allows:
  - Mega-Engineering battleship/stinger requirement representation.
  - FE tech edge cases noted in docs.

Deliverables:
- Tech tree interaction parity with requested behavior.
- Clear list of corrected vs still-unresolved data issues.
- Verified `OR` prerequisites displayed and evaluated correctly for representative techs (including `tech_mega_engineering` and `tech_titans`).

## Phase 5: Data-Type Pages + Chain UX
- Anomalies:
  - Table layout with required metadata fields.
  - Distinct hazard/negative outcome indicators.
  - Collapsible event chain blocks, closed by default.
- Arc Sites:
  - Table with icon/name, rewards, spawn requirements.
    - Collapsible event chain blocks, closed by default.
- Astral Rifts:
  - Table with outcomes.
    - Collapsible event chain blocks, closed by default.
  - Chain graph with selectable path highlighting and reward-to-path reveal.
- Events:
  - Category split (Empire, Colony, Pre-FTL, Misc).
  - One-line-per-response rendering (instead of merged list blocks).

Deliverables:
- Functional pages for all listed data types using shared chain style.

## Phase 6: Databank + Inline Text Icon System
- Databank as hub (not a single giant text page):
  - Tile/index landing page.
  - Individual linked category pages with shared stylesheet.
  - Default information layout as readable tables unless data requires alternative.
- Inline text-icon parsing/rendering with:
  - Tooltip short definitions.
  - Click-through links to destination pages.
  - No recursive tooltip chains.
- Pipe data extraction requirements into Forge/Rosetta hooks where missing.

Deliverables:
- Databank with working icon-tooltip-link behavior.
- Extraction/transform notes for any missing source fields.
- Linked Databank subpages populated from Forge outputs where data is available.

## Phase 7: Empire + Discoveries Workflow
- Build icon-only sub-tabs:
  - Government
  - Discoveries
  - Tech
- Discoveries subtab scope (Empire-only, no standalone top tab):
  - Saved/bookmarked entries only.
  - Entry types limited to:
    - Anomalies
    - Arc Sites
    - Astral Rifts
    - Event Chains
  - Section order:
    - Anomalies first
    - Arc Sites
    - Astral Rifts
    - Event Chains
  - Table rows gain leftmost save button using `button_new_zone.webp`.
  - Save action adds item to Discoveries; remove action available from Discoveries list.
- Government panel scaffolding:
  - Ethics layout area.
  - Civics selection panel.
  - Ascension Perks grid interactions.
  - Traditions popup shell.
  - Shipset and Species placeholders linked for future detail pages.
- Add persistence abstraction with pluggable backend.

Deliverables:
- Usable Empire shell with Discoveries bookmark workflow and save/load abstraction.

## Phase 8: Placeholder + Extended Data-Type Pages
- Create first-pass pages/routes for current placeholder/missing-linked data type headings, including the trailing headings listed in `docs/Data Types.md`.
- Use shared stylesheet and table-first layouts for readability.
- Populate pages from Forge outputs where available; mark unavailable datasets cleanly.
- Add generation hooks so new Forge data updates can auto-populate/update these pages.

Deliverables:
- Linked pages exist for placeholder categories.
- Auto-population/update pipeline for new data refreshes.

## Decisions Needed Before Execution
1. Persistence default for Empire data:
   - Option A: Browser local storage
   - Option B: Download/upload JSON
   - Option C: Seed/key encoding
2. Search shortcuts:
   - Plan default: support in-browser configurable hotkeys now.
   - System-wide/global hotkeys outside browser focus remain out of scope for web build unless we later add a desktop companion.

## Acceptance Criteria (Review Gate)
- User can navigate all main tabs with correct icons and active states.
- Search can locate and jump to specific nodes/content (not only titles).
- Chain-based content displays in readable flowchart style across supported modules.
  - Responses should chain to the linked event splitting for branches in the event chain
- Databank tab exists and can serve as destination for inline text-icon references.
- Databank acts as a hub of linked pages with shared styles, not a monolithic single page.
- Tech module no longer exhibits listed high-priority UX mismatches.
- `OR`/mixed prerequisite logic is preserved in data and correctly enforced in UI.
- Discoveries exists only under Empire and supports `button_new_zone.webp` bookmark flow for the allowed entry types.
- No regressions in existing generated data loading.

## Proposed Delivery Order
1. Phase 0-1
2. Phase 2-3
3. Phase 4
4. Phase 5-6
5. Phase 7
6. Phase 8
7. Final bugfix pass and documentation

## Out Of Scope For First Execution Pass
- Save file editing.
- Achievement re-enable mechanics.
- OCR overlay tooling.
- Full custom galaxy generation.
- Any feature requiring desktop-native global input hooks beyond normal browser capabilities.
