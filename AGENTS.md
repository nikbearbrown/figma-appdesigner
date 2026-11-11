# AGENTS.md: figma-appdesigner

For Codex and other coding agents: read `CLAUDE.md` in this folder. It describes the `help`, `tutorial`, `palettes` and `templates` commands and the one rule that matters most: only a person approves, rejects or defers a design, by running `./fad approve|reject|defer <D-id>` in their own terminal. Do not run those commands or write into `design/approvals/`.

The design rules are in `SKILL.md`. Building an approved design is the one job an agent does in the app's code, and only from a handoff brief in `design/handoff/`, one branch per design.
