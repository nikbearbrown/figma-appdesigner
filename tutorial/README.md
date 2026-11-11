# Tutorial: design your app's first screen

About 45 minutes the first time. You need an idea for an app and a Figma account (education plans work). You do not need to know how to design or how to code.

```bash
cd figma-appdesigner
./fad help
```

`./fad help` tells you what is missing and the one thing to do next. Fix it, run it again, and when it says to, type `tutorial` in Claude Code.

What happens, in order:

1. **Get set up.** Figma connected, and a design folder: `./fad init "Trail Notes"`.
2. **Say what the app is.** What it does and for whom, the three things a person must be able to do, iPhone or Android, and which of the four color sets (`./fad palettes`).
3. **Map the screens.** Claude lists the screens and how one leads to the next. You add, remove and rename until it matches the app in your head.
4. **See the first screen as a wireframe.** Plain boxes and real words, at phone size. Say what is in the wrong place before any color goes on.
5. **See it in your colors, and talk to it.** Ask for changes in plain words. Claude makes them, records what you asked, and measures its own drawing: what is too small to tap, too faint to read, or missing.
6. **Accept or reject.** You run `./fad approve D-0001` (or `reject`, or `defer`) in your own terminal and commit the file. Claude cannot do this for you.
7. **Hand off.** Claude writes a short brief for Claude Code or Codex to build from. This tool never writes app code.

Where things are kept: `~/figma-appdesigner-work/<your app>/design/`. Plain files you can read and commit: the brief, the screen map, findings, decisions, approvals, and an append-only ledger with every change you asked for in your own words. `./fad ledger verify` checks nobody altered the history.

## Three ready-made tutorials

If you would rather start from an example than a blank brief:

| Tutorial | You design | It teaches |
|---|---|---|
| [to-do](apps/to-do/README.md) | A list of what to get done today | Lists, the empty state, and how big a thing to tap must be |
| [weather](apps/weather/README.md) | Today's weather and the next few days | Showing numbers at a glance, and what a screen says when it has no data |
| [chat](apps/chat/README.md) | A conversation between two people | A text box that stays reachable, and telling two speakers apart without color |

```bash
./fad init "Today List" --tutorial to-do
```

Each one gives you an example brief and a proposed set of screens to change, a picture of the first screen drawn for real, what the check found on it, and open-licensed templates to look at. They were chosen because they are the kinds of app with the most usable templates in the catalog (`./fad templates`).
