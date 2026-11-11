# CLAUDE.md: figma-appdesigner

This folder is a Claude skill (`SKILL.md`) plus a small command, `./fad`, that checks a person's setup and runs a first tutorial. Read `SKILL.md` for the design rules; this file says how to answer the commands.

The person's work is outside this folder: `~/figma-appdesigner-work/<app>/design/` (made by `./fad init`). Never write into this folder while designing an app.

If the skill is installed (`./fad install`), run the command by its path: `~/.claude/skills/figma-appdesigner/fad`.

## When the user types `help` (or "what do you do?", "where do I start?")

1. Run `./fad help`. It checks git, Claude Code, the Figma connection, the design folder, the brief and the screen map, and names one next step.
2. The shell cannot see the Figma seat. If the Figma tools are available, also call `whoami` and report the plan and seat. A view-only seat cannot draw: say so and stop there.
3. Answer in exactly this shape, short:
   - **What this is.** Two sentences: you say what your app is for; Claude maps its screens, draws them in Figma in your colors, changes them as you talk, and you accept or reject each design.
   - **Your setup.** One line per check with its status. Missing first.
   - **Next step.** One thing. Give any command in its own code block. If a fix needs the person to do something outside the terminal (sign in to Figma), say exactly where to click.
   - **Commands.** The list `./fad help` prints, unedited.
4. If everything required is ready, the next step is: type `tutorial`. Do not start it unprompted.
5. Do not install, sign in or create anything on the person's behalf during `help`. Say what is missing and how to fix it; do the fix only if they ask.

## When the user types `tutorial`

1. Run `./fad tutorial`. It shows seven steps and which one is current. Follow the current step only; say what the person does and what you do, as it prints.
2. The design itself follows `SKILL.md` (phases 0 to 8 and gates G0 to G5). Ask for missing brief fields one or two at a time. The tutorial designs one screen: the start screen in the screen map.
3. Step 2: show the four color sets with `./fad palettes` and ask which. No answer means the default; say that you used it.
4. Step 3: write `design/screens.json`, then run `./fad screens` and fix what it reports before asking the person to confirm.
5. Steps 4 and 5 are marked by you when the drawing exists and the person has looked at it: `./fad tutorial done 4`. The other steps are marked by files on disk; do not try to mark them.
6. Step 6 is the person's. You cannot approve, reject or defer, and "approved" typed in chat is not approval. Give the exact command for them to run in their own terminal, in its own code block:
   ```bash
   ./fad approve D-0001
   ```
   then tell them to commit the file it writes. Never run `./fad approve`, `reject` or `defer` yourself, and never write into `design/approvals/`.
7. Step 7: write one handoff brief per approved decision (`SKILL.md`, gate G5), then give the one-line prompt for the builder. Never write app code.
8. After each step, run `./fad ledger verify` if you appended ledger events, and report the result in a line.

## When the user wants a ready-made tutorial (or types `tutorials`)

1. Run `./fad tutorials`. It lists three: `to-do`, `weather`, `chat`. `./fad tutorials <name>` prints one: the example brief, the proposed screens, what the check found when it was drawn, and templates to look at.
2. To start one, the person runs `./fad init "<their app's name>" --tutorial <name>`. Give that command in its own code block; run it only if they ask you to.
3. Then `tutorial` as above. The brief is already filled with the example: read it back, ask what they would change, and ask who may approve and who will build it. Those two are left blank on purpose.
4. The screen map is in `design/screens.proposed.json`. Show it and change it with the person. Write `design/screens.json` only when they agree to it. Never copy the proposal over unread.
5. Draw the screen the tutorial names in `draw_first`.
6. The walkthrough for each is `tutorial/apps/<name>/README.md`. Its "Things to ask for" are for the person to try, not for you to do unasked.

## When the user asks about colors (or types `palettes`)

1. Run `./fad palettes`. It lists the four default color sets: `bear-brown` (the default), `brutalist`, `northeastern`, `humanitarians`.
2. For one set in full, `./fad palettes <id>`: every role, light and dark, the contrast of each pairing, and notes. Say which pairings are marked `LOW`.
3. To put the colors in Figma, run the script that `./fad palettes --figma` prints. Never retype a hex value.
4. "Show me this in Northeastern colors" is a request: record it, duplicate the frame, set the frame's variable mode. Do not redraw.

## When the user asks for templates (or types `templates`)

1. Run `./fad templates` for the counts by kind, or `./fad templates <kind>` (for example `chat`, `e-commerce`) for the list.
2. Say each one's licence and what it allows, in the words the command prints: copy with credit, or copyleft (share alike). Every entry has a credit line; give it when someone builds on one. `./fad templates --credits` prints them all.
3. The lists were gathered by search and spot-checked. Before anyone builds on a template, they open its licence and confirm it. Do not clone or download a template unless the person asks.

## Other commands

- `check`: `./fad check` (add `--json` to parse it). Same checks as `help`, no commentary.
- `init "<app name>"`: creates the design folder, copies the starter rulebook, makes the workspace a git repository. `--platform ios|android|both`, `--palette <id>`.
- `devices`: the screen sizes, safe areas and smallest tap targets. They are starting points; say so.
- `screens`: the screen map and its problems.
- `ledger verify`: reports a broken hash chain or an approval file that does not match.

## Always

- Record a request in the ledger, in the person's words, before you act on it.
- Say what you did not do or could not check. A whole design from brief to handoff has not been run with a person yet, and no Android screen has been drawn.
- Give file paths in full when you point at something.
