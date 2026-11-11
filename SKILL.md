---
name: figma-appdesigner
description: Designs a phone app in Figma by conversation. The user says what the app is for; the skill writes a brief, maps the screens, draws wireframes and then styled screens through the Figma MCP in one of four default color sets (Bear Brown, Brutalist, Northeastern, Humanitarians AI), changes them as the user talks, measures its own drawing against a versioned rulebook (WCAG 2.2 AA, Apple and Material tap-target guidance, heuristics, house rules), records every design and its human sign-off in an append-only ledger, and hands approved designs to Claude Code or Codex as build briefs. Use whenever the user wants to design an app, mock up app screens, wireframe an app idea, make an iPhone or Android screen in Figma, pick app colors, or turn an app idea into Figma screens, even if they only say "design my app" or "draw the home screen". Also use when the user types `help`, `check`, `tutorial`, `palettes`, `screens` or `templates` in this skill's folder, or asks what figma-appdesigner needs or where to start. For redesigning a website that already exists, use the sibling skill figma-webdesigner.
---

# App idea → Screens in Figma → Decision ledger

## Purpose

Turn a person's description of an app into: (1) a written brief, (2) a screen map, (3) wireframes and styled screens in Figma, drawn with color and type variables so one screen can be shown in any of the four default color sets, (4) a record of every change the person asked for, in their words, (5) findings from measuring the drawing against a rulebook, (6) decision records and human approvals, and (7) build briefs for approved designs. The git-tracked design folder is the source of truth. Figma is a projection of it. This skill designs and records; it never writes app code.

It is the sibling of `figma-webdesigner`. That skill starts from a site that exists and audits it. This one starts from nothing but what the person says. They share the color sets (`palettes/palettes.json`), the ledger format and the approval command.

## How a session goes

The person talks; Claude draws. A turn is one of four things:

- **A fact about the app** ("it's for hikers, it works offline"). Goes in the brief.
- **A request** ("make the add button bigger", "move search to the top", "show me this in Northeastern colors"). Claude records the words, makes the change in Figma, and says what changed.
- **A question** ("is that button big enough?"). Claude measures and answers with the number and the rule.
- **A decision** ("yes, build this one"). Only a person can make it, and only with `fad approve` in their own terminal.

Ask one or two questions at a time. Draw early: a wrong wireframe the person can point at is worth more than a long interview.

## Commands

The skill folder has a command, `fad`, and a `CLAUDE.md` that says how to answer it.

- `help` runs `fad help` (setup checks plus one next step) and, with the Figma tools present, `whoami` for the seat.
- `tutorial` runs the seven-step first tutorial (design your app's first screen). It is this skill's own phases, driven step by step.
- `fad tutorials [name]` lists the ready-made tutorials for common apps (`to-do`, `weather`, `chat`) or prints one. `fad init "<name>" --tutorial to-do` starts a design folder with that tutorial's example brief and proposed screens. See Tutorials for common apps.
- `fad init "<app name>"` starts a design folder. `--platform ios|android|both`, `--palette <id>`.
- `fad palettes [id]` lists the four default color sets, or prints one with its roles and worked-out contrast. `--json` for a script. `--figma` prints the ready-to-run Figma script that creates the color variables.
- `fad devices` prints the screen sizes, safe areas and smallest tap targets designs are drawn to.
- `fad screens` prints the screen map and checks it (one start screen, nothing unreachable, no link to a screen that does not exist).
- `fad templates [kind]` lists open-licensed templates and design kits for common kinds of app, with each one's licence and the credit to give. `--credits` prints the whole credits list.
- `fad approve|reject|defer <D-id>` is the person's, run in their own terminal. Non-negotiable 1 applies.
- `fad ledger verify` checks the hash chain and that each approval file matches the ledger.

## Non-negotiables

1. Only a human may set a decision to approved, rejected, or deferred, or reopen one. Never write those states. Never write files in `design/approvals/`. Never run `fad approve`, `reject` or `defer`.
2. Every finding cites a `rule_id` from `design/rulebook/rules.yaml`. No rule, no finding: record it as an `observation` for the human.
3. Finding labels follow the rule tier: normative → `failure`, heuristic → `concern`, house → `deviation`. Apple's and Google's guidance is heuristic tier: a 40-point button on iOS is a concern, not a failure. Never use pass/fail icons or words on heuristic findings.
4. Record a request before acting on it: a `request.made` ledger event with the person's words, verbatim, and which screen. Then the `figma.write` receipt. The record is what lets someone ask later why the button moved.
5. A request that breaks a rule is still the person's to make. Say which rule and by how much, offer the nearest version that passes, and draw what they choose. If they keep the rule-breaking version, write the finding; it rides along into the decision record. Do not quietly "fix" what they asked for, and do not refuse.
6. Every color on a screen is a `Palette` variable and every font family a `type/` variable. No loose hex on a screen node. The values come from `fad palettes`, never from memory.
7. Never modify or delete nodes the skill did not create. Find your own nodes from the node IDs recorded in the ledger, never by layer name, color or text.
8. Never set Dev Mode status (Ready for dev / Completed). Never resolve or delete human comments.
9. Draw only in a Figma file this skill created for this app, or in a file the person named after they saved a baseline version of it and gave you its ID. A file the run created starts empty and is its own baseline; record that in `capabilities.json`.
10. Never write app code. Building happens only in a separate Claude Code or Codex session, from a handoff brief for an approved decision.
11. Never place a real organisation's logo, name or trademark on a screen unless the person supplies it and says they may use it. The Northeastern color set is a published palette, not permission to use the university's marks.
12. Never copy a template's or another app's screens. A template (see Templates) is something to read for structure and to build from under its licence, with credit recorded in the brief; anything without an open licence is for looking only.
13. Draw every screen with its states. A screen that loads or lists things has `default`, `empty`, `loading` and `error` drawn before it can be proposed (rule `HOUSE-STATES`).

## Directory layout

```
design/
  brief.yaml                  # human-populated (Phase 0)
  rulebook/rules.yaml         # human-confirmed (Phase 1)
  screens.json                # the screen map (Phase 2)
  capabilities.json           # what this run could actually do
  checks/R-YYYYMMDD-NN/       # measurements of the drawing: checks.json, findings.json, exported PNGs
  decisions/D-NNNN.json
  approvals/A-NNNN.json       # humans only
  handoff/                    # build briefs, approved decisions only
    README.md                 # shared rules for the builder
    D-NNNN.md                 # one brief per approved decision
  ledger.jsonl                # append-only, hash-chained events
```

`fad init` puts this at `~/figma-appdesigner-work/<app>/design/` and makes `~/figma-appdesigner-work/<app>/` a git repository, so approvals can be committed. It commits nothing.

## Phase 0 — Brief (Gate G0)

If `design/brief.yaml` is missing or has empty required fields, ask for the missing fields conversationally, one or two at a time. Do not draw anything until every required field is filled by the person.

```yaml
app_name: ""                  # required: a working name is fine
one_line: ""                  # required: what it does, for whom, in one sentence
people: []                    # required: who uses it
top_tasks: []                 # required: the three things a person must be able to do
platform: ios                 # required: ios, android or both
palette: bear-brown           # required: bear-brown, brutalist, northeastern, humanitarians
dark_mode: false              # also draw the palette's dark mode, where it has one
implementer: ""               # required: "claude-code" or "codex"
stack: undecided              # swiftui, compose, react-native, flutter, or undecided
approvers: []                 # required: names and roles
conformance_target: "WCAG 2.2 AA"
existing_app: none            # path to a repo if redesigning an app that exists
figma_file: ""                # blank until the file is created
out_of_scope: []
```

Good `top_tasks` are things a person does ("write a note with no signal"), not features ("offline sync"). If the person gives features, ask what someone is trying to get done.

## Phase 1 — Rulebook (Gate G1)

Summarize the rulebook (rule count by tier and mode). Ask the person to confirm or edit. The starter names its sources so they can be opened; say that the Apple and Material entries are named, not linked, and should be confirmed against the current guidance. Record a `schema.confirmed` ledger event with the person's name and the date. Do not proceed without it.

## Runtime capability probe

Before the first Figma write, write `capabilities.json`:

- Which Figma MCP tools are present (`use_figma`, `create_new_file`, `create_session`, `get_screenshot`, `get_metadata`, `generate_diagram`, `get_libraries`, `search_design_system`).
- `whoami`: the plan and seat that will own the file. A view-only seat cannot draw: set `mode: json-only`, say so, and stop before Phase 3. With more than one plan, use the one with a Full seat; if two have one, ask.
- Load Figma's `figma-use` skill before any `use_figma` call, and `figma-create-new-file` before `create_new_file`. For the variables load `figma-generate-library`; for screens load `figma-generate-design`. Pass the names of the Figma skills you are following in `skillNames`.
- Call `create_session` once the file key is known and pass its `sessionId` on every later file call.
- Known from the first run (2026-11-10, education plan, student tier, Full seat). Re-verify rather than assume:
  - One variable collection accepted **eight modes** (the four color sets, three of them with a dark mode, and the grey Wireframe mode).
  - A `STRING` variable scoped `FONT_FAMILY`, bound to a text node's `fontFamily`, switches the typeface with the mode. Every family in every mode must be loaded first.
  - EB Garamond, Inter and Lato each had Regular, Medium and Bold. Lato has no "Semi Bold". Use only those three weights so one text node works in every mode.
  - `frame.setExplicitVariableModeForCollection(collection, modeId)` re-colors and re-types everything inside the frame, including component instances.
  - A component on the kit page can be instanced on another page in the same call: fetch it with `figma.getNodeByIdAsync(id)` and call `createInstance()`.
  - A text layer in an auto-layout frame with `maxWidth` set and `textAutoResize = 'WIDTH_AND_HEIGHT'` hugs a short line and wraps a long one (the chat bubbles).
  - From `figma-webdesigner`'s first run: `figma.saveVersionHistoryAsync` is not supported (the person saves versions), `figma.root.name` cannot be set (name the file when creating it), annotations work.
- If the plan refuses a second mode (`modeErrors` in the script's receipt), use the chosen color set's light mode only and record `modes: 1`.

Name the Figma file for the app when calling `create_new_file`; it cannot be renamed afterwards.

## Colors

Screens are drawn in one of four default color sets. They are in `palettes/palettes.json`, each read from the site it is named for (the file records the page and the date). `figma-webdesigner` ships the same file.

| id | Name | Read from | Modes | Type |
|---|---|---|---|---|
| `bear-brown` (default) | Bear Brown | bearbrown.co | light, dark | EB Garamond, Inter |
| `brutalist` | Brutalist | brutalist.art | light, dark | Inter |
| `northeastern` | Northeastern | brand.northeastern.edu, the color page | light | Lato |
| `humanitarians` | Humanitarians AI | humanitarians.ai | light, dark | Inter |

Each set fills the same seven roles: `ground`, `surface`, `ink`, `ink-soft`, `border`, `accent`, `on-accent`.

1. **Ask, don't assume.** In Phase 0, show the four (`fad palettes`) and ask which. With no answer, use the default and say so.
2. **Get the values from the command.** `fad palettes --figma` prints `figma/palette-variables.js` with the colors filled in. Run that script; do not type a hex value.
3. **Put all four in the file.** The script makes one `Palette` collection with a mode for every color set and its dark mode, plus a grey `Wireframe` mode, so the person can ask to see any screen in another set without a redraw: set the frame's mode. The brief's `palette` is the mode screens are drawn in by default. The first mode (Figma's default) is always a real color set; `Wireframe` is last.
4. **Report the low pairs.** `fad palettes <id>` marks any text or control pairing under its WCAG minimum as `LOW`. Tell the person which are low in their set, and never put text on a low pair. Two exist today: Brutalist's secondary text on its slate surface (4.34:1), and the Humanitarians dark-mode red against its dark ground (2.47:1).
5. **One main action per screen carries the accent** (`HOUSE-ONE-MAIN-ACTION`). Accent is not decoration.
6. **A color of the person's own** ("our brand is teal") is a new variable mode they name, added to the file's `Palette` collection with all seven roles filled and its contrast worked out the same way before it is used. Do not edit the four default sets.

## Devices

`fad devices` prints what `starter/devices.json` holds: an iPhone frame of 390 × 844 pt and an Android frame of 412 × 915 dp, each with a safe area and a smallest tap target (44 pt, Apple Human Interface Guidelines; 48 dp, Material Design 3). These are starting points for drawing. Say so when you use them, and tell the person to check them on a real device before building. `platform` in the brief decides which are drawn; `both` draws each screen twice.

## `use_figma` script conventions

Every script this skill sends through `use_figma` follows Figma's `figma-use` rules and these:

1. **Fonts first.** Load every family and weight any mode can show (`Promise.all` at the top) before creating or editing text. A text node bound to `type/heading` needs all of that variable's families loaded.
2. **Auto-layout for anything with children.** `figma.createAutoLayout()`, append the child, then set `layoutSizingHorizontal`/`Vertical`. `resize()` before sizing modes.
3. **Bind, don't paint.** Fills, strokes and text colors through `figma.variables.setBoundVariableForPaint(...)`; font family through `node.setBoundVariable('fontFamily', variable)`. Resolve variables by the IDs in the ledger with `getVariableByIdAsync`.
4. **Build a thing once.** A button, a list row, a tab bar: make a local component on the `Components` area, then place instances. No flat tree of look-alike frames.
5. **Name frames by what they are:** `S-01 Notes list / iphone / wire / default`, `S-01 Notes list / iphone / styled / empty`. Screen id and name, device, `wire` or `styled`, state.
6. **Return a write receipt:** `createdNodeIds`, `mutatedNodeIds`, `pageId`, plus the sizes of what was made. For a change to an existing node, also the previous values.
7. **Ledger the receipt** as a `figma.write` event with the run ID, the request or decision it belongs to, and the before-values.
8. **Fail loudly.** A lookup that finds nothing throws with a list of what was found. Never report success for a no-op.
9. **One screenshot per composition.** After drawing, take one screenshot and look at it for clipped text, overlap, and a wrong typeface. After a fix, one more. Figma's MCP has a daily call limit on education plans; do not spend it on repeat screenshots.

The scripts in `figma/` are the ones from the first runs, kept as working examples: `palette-variables.js` (filled in by `fad palettes --figma`), `sample-screen.js`, `kit-components.js`, `tutorial-screens.js` and `measure-screen.js`.

## Phase 2 — Screen map (Gate G2)

From the brief's `top_tasks`, propose the screens. Write `design/screens.json`:

```json
{"screens": [
  {"id": "S-01", "name": "Notes list", "start": true,
   "purpose": "See your notes and open one",
   "serves": ["write a note with no signal"],
   "states": ["default", "empty", "loading", "error"],
   "goes_to": [{"on": "tap a note", "screen": "S-02"}, {"on": "tap +", "screen": "S-02"}]}
]}
```

Every top task must be reachable in the map; say how many taps from the start each one takes. Run `fad screens`: it must report no problems. Draw the flow with `generate_diagram` (load Figma's `figma-generate-diagram` skill first) when the tool is present. The person confirms the map and names the first screen to draw. Record `screens.confirmed`.

Keep the first map small. Five screens that cover the top tasks beat fifteen that cover everything.

## Phase 3 — Kit

In the app's Figma file, pages are stages: `00 Kit`, `01 Wireframes`, `02 Screens`, `03 Findings`.

1. Run the script from `fad palettes --figma`. Ledger the receipt (collection ID, mode IDs, variable IDs, `modeErrors`, `fontReport`).
2. On `00 Kit`, build the components the first screens need (button, list row, text field, navigation bar, tab bar) as local components, bound to the variables. Before building one, check for a platform kit: `get_libraries`, then `search_design_system` for the component. If the person's file has Apple's or Material's kit added, use its components for platform chrome (status bar, navigation bar, tab bar) and bind this file's colors where the kit allows.
3. Sizes come from `fad devices`: nothing to tap is smaller than the platform's minimum.

## Phase 4 — Wireframes

Draw the first screen on `01 Wireframes` at each device size, from the kit's components, with real words and no decoration, inside a frame set to the `Wireframe` mode: greys only, so nobody argues about color yet. Draw each of its states. Give the person the link and one screenshot. Take requests (see below) until the layout is right. Structure is cheap to change here and dear to change later, so do not style a screen whose layout the person has not looked at.

## Phase 5 — Styled screens

Build the agreed screen on `02 Screens` in a frame set to the chosen color set's mode. It is the same drawing as the wireframe: only the frame's mode differs, so the type and the accent arrive with the mode. Check that the accent lands on the one main action and nowhere else. If `dark_mode` is true and the set has a dark mode, place the dark frame beside it. To show another color set, duplicate the frame and set its mode; do not redraw. (Build it again on the new page rather than moving the wireframe: moving a node to another page in a later call is not reliable.)

## Requests: talking to the design

For each request:

1. Append `request.made` to the ledger: `{"type": "request.made", "by": "<person>", "words": "<verbatim>", "screen": "S-01", "request_id": "Q-0007"}`.
2. If it is unclear which thing or which way, ask one question. Do not guess between two readings.
3. Check it against the rulebook before drawing. If it would break a rule, apply non-negotiable 5.
4. Make the change with a targeted script on the nodes named in the ledger. Return before-values.
5. Ledger the `figma.write` receipt with the `request_id`.
6. Say what changed in a sentence, with the number if there is one ("the add button is now 56 by 56 points; it was 44").

Requests change the drawing; they do not approve it. A request to undo is a new request, applied from the recorded before-values.

## Phase 6 — Check

Measure the drawing, not your intention. Run `figma/measure-screen.js` (read-only, one call per page) with the frame IDs from the ledger, the device from `fad devices --json`, and the list of what a person can tap in this design: the script cannot guess that, so say it. It returns, for every screen frame, each tap target's size, every text's size and its contrast against the fill behind it, any color not bound to a variable, and anything inside the safe areas. Save what it returns as `design/checks/R-…/checks.json`. Then:

- **Automated rules** become findings directly: tap targets under the platform minimum (`HIG-TARGET-44`, `M3-TARGET-48`) or under 24 px (`WCAG22-2.5.8`); text contrast under 4.5:1, or 3:1 for large text (`WCAG22-1.4.3`); text under 11 pt on iOS (`HIG-TEXT-11`); anything to read or tap inside the safe area (`HOUSE-SAFE-AREA`); a loose hex (`HOUSE-PALETTE-ONLY`); a state in `screens.json` with no frame (`HOUSE-STATES`).
- **Assisted and judgment rules** (`WCAG22-1.4.11`, the Nielsen and Laws of UX entries, `HOUSE-ONE-MAIN-ACTION`) become findings with a severity 0–4, a confidence, and one sentence on what the drawing shows. You are one evaluator; say so.

Work the contrast out from the resolved colors with the WCAG formula. Do not reuse a ratio from a note. Present findings as a table: ID, rule, label, screen, severity, confidence, one line of evidence. The person accepts, rejects or re-scores each; record each call as a ledger event in their name.

## Phase 7 — Decisions (Gate G4)

A decision is a design the person could say yes to. Write `design/decisions/D-NNNN.json`:

```json
{"id": "D-0001", "title": "Notes list, first design", "screens": ["S-01"],
 "proposal": "A single list, newest first, search on top, one add button at the bottom.",
 "alternatives": [{"option": "grid of cards", "why_not": "fewer notes per screen; titles truncate"}],
 "consequences": "Search is one tap away on every visit; adding a note is a thumb's reach.",
 "requests": ["Q-0003", "Q-0007"], "finding_ids": ["F-0002"],
 "figma": {"file_key": "…", "node_ids": ["…"]},
 "status": "proposed", "proposed_by": "claude"}
```

One decision per screen design, plus one for any choice that crosses screens (the navigation pattern, the tab order). List the alternatives you really considered. Open findings stay attached: the person approves knowing them. Append `decision.proposed`, then tell the person which approvers in the brief need to review, and give the command in its own code block:

```bash
./fad approve D-0001
```

Never infer approval from chat, Figma comments, emoji or Dev Mode status. If the person says "approved" in chat, point them to the command.

## Gate G5 — Handoff to a builder

Only for decisions with `status: approved` backed by a valid approval file (`fad ledger verify` passes). Write `design/handoff/README.md` once and `design/handoff/D-NNNN.md` per approved decision.

**README.md** (shared rules for the builder, Claude Code or Codex per `implementer`):
- One decision per branch and per pull request. Branch name `design/D-NNNN-<slug>`.
- The decision ID in every commit message and the PR title.
- Build only what the brief says is approved. If the build conflicts with the design, or needs something the design does not show, stop and record it in the PR as a proposed follow-up.
- Never edit anything under `design/`. Never merge your own PR.
- Read the frames with the Figma MCP. Figma's own skills apply: `figma-design-to-code` before `get_design_context`, and `figma-swiftui` for a SwiftUI build.

**D-NNNN.md**:
- Title, proposal and approved scope exactly as in the approval file, including what was not approved.
- Figma anchors: file key, node IDs and links for every state of every screen in the decision, and a reference PNG exported into `design/handoff/`.
- Tokens: the seven roles for the chosen color set and mode, light and dark, as values and as the variable code syntax (`var(--palette-accent)`, `Palette.accent`, `paletteAccent`), from `fad palettes <id> --json`.
- Device sizes and safe areas drawn to, marked as starting points.
- Acceptance checks: the rule IDs and thresholds to re-measure on the built screen (for example `HIG-TARGET-44 ≥ 44 pt on S-01`).
- Open findings the person approved knowingly.
- Any template built from, with its licence and the credit it requires.
- Out of scope: everything not named above.

Give the person, in its own code block, the one-line prompt to start the builder: "Read design/handoff/README.md and design/handoff/D-0001.md and build it." Append `handoff.created`.

## Phase 8 — Verify

After the build, compare the running screen with the frame: a screenshot from the simulator or device beside the Figma export, and the acceptance checks re-measured. Automated-rule checks that pass move the decision to `verified`; failures to `regressed`. Judgment rules need a person. A re-run never overwrites: each run of checks is its own `checks/R-…` folder and its own frame on `03 Findings`, with a "Changes since R-…" block. This phase has not been run yet (see What has not been tried).

## Tutorials for common apps

`tutorial/apps/` holds ready-made tutorials for the three kinds of app the catalogs cover best: `to-do`, `weather` and `chat`. Each has a `README.md` (the walkthrough, with a picture of the real drawing and what the check found), a `tutorial.json` (the example brief and the templates to point at) and a `screens.json` (the proposed screen map).

- `fad init "<name>" --tutorial <slug>` fills the brief with the example and copies the screen map to `design/screens.proposed.json`. It leaves `implementer` and `approvers` blank on purpose.
- The example brief is still the person's to confirm (Gate G0). Read it back, ask what they would change, and ask who may approve. Do not draw until they have answered.
- `screens.proposed.json` is a proposal. Show it, change it with the person, and only then write `design/screens.json` and run `fad screens`. Never copy it over unread: step 3 is done when the person has agreed to a map, not when a file exists.
- Draw the screen named in `draw_first`. For chat that is the conversation, not the start screen.
- Each tutorial lists requests to try. They are prompts for the person, not a script for you: wait for the person to ask.
- The pictures and measurements in each walkthrough are from one real run on 2026-11-10. The person's own drawing will differ; measure theirs.

## Templates

`templates/` holds two catalogs: `code-templates.json` (open-source apps and starter kits on GitHub) and `design-templates.json` (design kits and Figma files), and `CREDITS.md`, made from them. `fad templates` lists them; `fad templates chat` filters by kind of app.

Only works with a confirmed licence that allows reuse are published in the catalogs, each with a `credit` line. What the search found without one (no licence file, a licence that could not be read, or a publisher's own terms such as Apple's design resources) is kept out, in an unpublished folder. Apple's and Google's own design kits are worth knowing about all the same: point the person to the publisher's page and say that the publisher's terms apply.

- Offer templates when the brief names a common kind of app. Say the licence with each one.
- `copy with credit` (MIT, Apache-2.0, BSD and similar): the builder may start from it; record the credit line in the handoff brief.
- `copyleft: share alike` (GPL, AGPL and similar): the person's app would have to be released under the same terms. Say that plainly before they choose it.
- When a builder starts from a template, its credit line and licence go into the handoff brief, and the template's own licence notice stays in the code.
- A design kit's own terms apply. Apple's design resources are for designing apps for Apple platforms.
- The catalogs were gathered by search on a date written in each file and spot-checked, not audited. Before building on a template, open its licence file and confirm it.
- Non-negotiable 12 applies: never reproduce a template's screens as the person's design.

## Refusals

- Asked to approve, reject, or defer: decline in one sentence and give the `fad approve` command.
- Asked to mark frames Ready for dev: decline; that status is set by a person in Figma.
- Asked to edit someone else's nodes or an existing file with no baseline: ask for the baseline version first.
- Asked to add a finding with no rule: record it as an `observation` and offer to draft a house rule for the person to confirm.
- Asked to write the app's code from this skill: decline; write the handoff brief for approved decisions and name the builder.
- Asked for a handoff brief for a design that isn't approved: decline; say which approval is missing.
- Asked to copy another app's screens, or to use an organisation's logo or name without their say-so: decline; offer a design with the same structure and their own content.
- Asked to hide or drop a finding so a design "passes": decline; findings stay in the record, and the person can approve knowing them.

## Outputs per run

1. `brief.yaml`, `screens.json` and the screen-flow diagram.
2. Figma pages `00 Kit`, `01 Wireframes`, `02 Screens`, `03 Findings`.
3. Ledger events: every request in the person's words, a `figma.write` receipt for every Figma write.
4. `checks/R-…/findings.json` and a findings table in chat.
5. Decision records; `handoff/D-NNNN.md` for approved ones only.
6. A run summary: what was drawn, what was measured, what was judged, what is waiting on which person, and what this run could not do (from `capabilities.json`).

## What has not been tried

Say these plainly when they matter:

- The Figma part has been run twice (2026-11-10): the `Palette` variables and a sample screen in every mode (`docs/palette-kit.png`), and the first screen of the three tutorial apps as wireframes and styled screens (`docs/tutorials/`). A whole design, from brief to handoff, has not been run with a person.
- Phase 6's measuring script has been run once, on those six tutorial screens. It measures what it is told is tappable; it does not find tappable things by itself, and it has not been tried on a screen with images, gradients or overlapping layers. Phase 8 has not been run.
- Nobody has walked a tutorial from step 1 to step 7.
- Android: no Android screen has been drawn. The Android frame size and system-bar insets in `starter/devices.json` are from memory of common devices.
- A machine without Claude Code or the Figma connection, and Windows.
