#!/usr/bin/env python3
"""figma-appdesigner command line: help, check, init, tutorial, palettes, devices, screens,
approve/reject/defer, ledger, install.

Standard library only. Run it through ./fad.

Design rules (see SKILL.md):
  * Only a person may approve, reject or defer a design. approve/reject/defer refuse to run
    unless stdin and stdout are a terminal. That stops accidents; it is not a lock. The real
    control is that the person commits the approval file and a reviewer sees it.
  * The ledger is append-only and hash-chained. This tool only appends.
  * Nothing here writes app code. Building the app is a separate session, from a handoff brief.

The ledger, approval and tutorial machinery is the same as figma-webdesigner's fwd.py, so a
record made by one tool reads the same way in the other.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # ./fad runs python -I, which drops the script folder
import palettes as pal  # noqa: E402

VERSION = "0.2.0"
REPO = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("FAD_HOME", str(Path.home() / "figma-appdesigner-work")))
STATE_FILE = HOME / "state.json"
SKILL_LINK = Path.home() / ".claude" / "skills" / "figma-appdesigner"

REQUIRED_BRIEF = ["app_name", "one_line", "people", "top_tasks", "platform", "palette", "implementer", "approvers"]
PLATFORMS = ["ios", "android", "both"]
DECIDED = {"approved", "rejected", "deferred"}
STATES = ["default", "empty", "loading", "error"]


# ───────────────────────── small helpers ─────────────────────────

def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], cwd: str | None = None, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def design_dir(override: str | None = None) -> Path | None:
    if override:
        return Path(override).expanduser().resolve()
    ws = load_state().get("workspace")
    return Path(ws) / "design" if ws else None


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "app"


# ───────────────────────── brief.yaml (tiny reader) ─────────────────────────

def read_brief(path: Path) -> dict[str, str]:
    """Top-level `key: value` pairs only. A key with no value but indented `- ` lines counts as filled."""
    out: dict[str, str] = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return out
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val and val[0] in "\"'":
            q = val[0]
            end = val.find(q, 1)
            val = val[1:end] if end > 0 else val[1:]
        else:
            val = re.split(r"\s+#", val, maxsplit=1)[0].strip()
        if val == "":
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if re.match(r"^\s+-\s+\S", nxt):
                val = "(list)"
        if val in ("[]", "{}"):
            val = ""
        out[key] = val
    return out


def missing_brief(design: Path) -> list[str]:
    brief = read_brief(design / "brief.yaml")
    return [k for k in REQUIRED_BRIEF if not brief.get(k, "").strip()]


# ───────────────────────── ledger ─────────────────────────

def _hash_event(body: dict) -> str:
    # Same rule as figma-webdesigner: sha256 of the event without "hash", default json.dumps.
    return hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest()


def ledger_events(design: Path) -> list[dict]:
    p = design / "ledger.jsonl"
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def ledger_head(design: Path) -> str:
    ev = ledger_events(design)
    return ev[-1]["hash"] if ev else "GENESIS"


def ledger_append(design: Path, event: dict) -> dict:
    body = dict(event)
    body["at"] = now()
    body["prev"] = ledger_head(design)
    body["hash"] = _hash_event(body)
    with (design / "ledger.jsonl").open("a") as f:
        f.write(json.dumps(body, ensure_ascii=False) + "\n")
    return body


def ledger_verify(design: Path) -> list[str]:
    """Return a list of problems; empty means the chain and the approval files check out."""
    problems: list[str] = []
    prev = "GENESIS"
    events = ledger_events(design)
    for n, e in enumerate(events, 1):
        body = {k: v for k, v in e.items() if k != "hash"}
        if e.get("prev") != prev:
            problems.append(f"event {n} ({e.get('type')}): prev does not match the event before it")
        if _hash_event(body) != e.get("hash"):
            problems.append(f"event {n} ({e.get('type')}): hash does not match its contents")
        prev = e.get("hash", "")
    by_file = {e.get("approval_file"): e for e in events if e.get("approval_file")}
    for f in sorted((design / "approvals").glob("A-*.json")) if (design / "approvals").exists() else []:
        rel = f"design/approvals/{f.name}"
        ev = by_file.get(rel)
        try:
            a = json.loads(f.read_text())
        except ValueError:
            problems.append(f"{f.name}: not valid JSON")
            continue
        if ev is None:
            problems.append(f"{f.name}: no ledger event points at this approval file")
        elif a.get("ledger_hash") != ev.get("prev"):
            problems.append(f"{f.name}: ledger_hash does not match the ledger at the time it was written")
    return problems


# ───────────────────────── devices ─────────────────────────

def devices() -> dict:
    return json.loads((REPO / "starter" / "devices.json").read_text())


def devices_for(platform: str) -> list[dict]:
    d = devices()["devices"]
    want = {"ios": ["ios"], "android": ["android"], "both": ["ios", "android"]}.get(platform, [])
    return [x for x in d if x["platform"] in want]


def cmd_devices(args) -> int:
    data = devices()
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print("Screen sizes the designs are drawn at (starting points: check them against a real device):\n")
    for d in data["devices"]:
        print(f"  {d['id']:<14} {d['width']} x {d['height']} {d['unit']}  {d['name']}")
        print(f"  {'':<14} keep clear: top {d['safe_top']}, bottom {d['safe_bottom']} {d['unit']}.  Smallest thing to tap: {d['min_target']} x {d['min_target']} {d['unit']} ({d['target_source']})")
    print(f"\nYour brief's platform decides which are drawn: ios, android, or both. {data['note']}")
    return 0


# ───────────────────────── screens.json ─────────────────────────

def read_screens(design: Path) -> dict | None:
    try:
        return json.loads((design / "screens.json").read_text())
    except (OSError, ValueError):
        return None


def screens_problems(data: dict) -> list[str]:
    out: list[str] = []
    screens = data.get("screens")
    if not isinstance(screens, list) or not screens:
        return ["there are no screens yet"]
    ids = [s.get("id") for s in screens]
    for i in ids:
        if not i or not re.match(r"^S-\d{2,}$", str(i)):
            out.append(f"screen id {i!r} should look like S-01")
    for i in sorted({i for i in ids if ids.count(i) > 1}, key=str):
        out.append(f"{i} is used by more than one screen")
    starts = [s.get("id") for s in screens if s.get("start")]
    if len(starts) != 1:
        out.append(f"exactly one screen must be marked start (found {len(starts)})")
    for s in screens:
        sid = s.get("id")
        if not s.get("name"):
            out.append(f"{sid}: has no name")
        if not s.get("purpose"):
            out.append(f"{sid}: has no purpose (what the person does here)")
        for g in s.get("goes_to", []):
            if g.get("screen") not in ids:
                out.append(f"{sid}: goes to {g.get('screen')!r}, which is not a screen")
        for st in s.get("states", []):
            if st not in STATES:
                out.append(f"{sid}: state {st!r} is not one of {', '.join(STATES)}")
    reach = set(starts[:1])
    grew = True
    while grew:
        grew = False
        for s in screens:
            if s.get("id") in reach:
                for g in s.get("goes_to", []):
                    if g.get("screen") in ids and g["screen"] not in reach:
                        reach.add(g["screen"])
                        grew = True
    if len(starts) == 1:
        for i in ids:
            if i not in reach:
                out.append(f"{i}: nothing leads here from the start screen")
    return out


def cmd_screens(args) -> int:
    design = design_dir(args.design)
    if not design or not design.exists():
        print('No design folder yet. Run ./fad init "<your app\'s name>" first.')
        return 2
    data = read_screens(design)
    if data is None:
        print(f"No screen map yet ({design / 'screens.json'}). Claude writes it with you in tutorial step 3.")
        return 2
    probs = screens_problems(data)
    if args.json:
        print(json.dumps({"screens": data.get("screens", []), "problems": probs}, indent=2))
        return 1 if probs else 0
    for s in data.get("screens", []):
        mark = "start" if s.get("start") else "     "
        print(f"{mark} {s.get('id')}  {s.get('name')}: {s.get('purpose', '')}")
        for g in s.get("goes_to", []):
            print(f"        {g.get('on', 'tap')} -> {g.get('screen')}")
        if s.get("states"):
            print(f"        states to draw: {', '.join(s['states'])}")
    if probs:
        print(f"\n{len(probs)} problem(s) in the screen map:")
        for p in probs:
            print("  - " + p)
        return 1
    print(f"\n{len(data['screens'])} screen(s). Every screen can be reached from the start.")
    return 0


# ───────────────────────── checks ─────────────────────────

def _ver(cmd: list[str]) -> str:
    code, out = run(cmd)
    return out.splitlines()[0] if code == 0 and out else ""


def check_item(id_, label, status, detail, fix=None, required=True):
    return {"id": id_, "label": label, "status": status, "detail": detail, "fix": fix or [], "required": required}


def palette_check(chosen: str) -> dict:
    """Which of the default color sets the screens use. Never blocks: an unknown name falls back, out loud."""
    data = pal.load(REPO)
    known = pal.ids(data)
    if not chosen:
        return check_item("palette", "colors", "ok", f"{data['default']} (the default; ./fad palettes lists all {len(known)})", required=False)
    if chosen in known:
        return check_item("palette", "colors", "ok", f"{chosen} ({pal.find(data, chosen)['name']})", required=False)
    return check_item("palette", "colors", "warn", f"'{chosen}' is not one of: {', '.join(known)}. {data['default']} will be used",
                      ["Set palette: in design/brief.yaml to one of those, or run ./fad palettes"], required=False)


def run_checks(with_mcp: bool = True) -> list[dict]:
    state = load_state()
    items: list[dict] = []

    pv = sys.version_info
    items.append(check_item("python", "python3", "ok" if pv >= (3, 9) else "missing", f"{pv.major}.{pv.minor}.{pv.micro}",
                            [] if pv >= (3, 9) else ["Install Python 3.9 or newer from python.org."]))

    git = shutil.which("git")
    items.append(check_item("git", "git", "ok" if git else "missing", _ver(["git", "--version"]) if git else "not installed",
                            [] if git else ["macOS: xcode-select --install", "Other: https://git-scm.com/downloads",
                                            "Your approvals are files you commit, so git is needed."]))

    claude = shutil.which("claude")
    items.append(check_item("claude", "Claude Code", "ok" if claude else "warn",
                            _ver(["claude", "--version"]) if claude else "not on PATH",
                            [] if claude else ["Install Claude Code: https://claude.com/claude-code", "The design is drawn by Claude, so you need it."], required=False))

    if not with_mcp:
        items.append(check_item("figma", "Figma connection", "unknown", "skipped (--no-mcp)", required=False))
    elif not claude:
        items.append(check_item("figma", "Figma connection", "unknown", "cannot check without the claude command", required=True))
    else:
        code, out = run(["claude", "mcp", "list"], timeout=45)
        line = next((l for l in out.splitlines() if "mcp.figma.com" in l or re.search(r"\bfigma\b", l, re.I)), "")
        if code == 124:
            items.append(check_item("figma", "Figma connection", "unknown", "claude mcp list timed out", ["Run `claude mcp list` yourself and look for figma."]))
        elif not line:
            items.append(check_item("figma", "Figma connection", "missing", "no Figma server is configured in Claude Code",
                                    ["claude mcp add --transport http figma https://mcp.figma.com/mcp",
                                     "Then in Claude Code type /mcp and sign in to figma with your school Figma account."]))
        elif "Connected" in line:
            items.append(check_item("figma", "Figma connection", "ok",
                                    "connected. Claude checks your seat (whoami) in tutorial step 1; a view-only seat cannot draw."))
        else:
            items.append(check_item("figma", "Figma connection", "missing", "configured but not signed in",
                                    ["In Claude Code type /mcp, choose figma, and sign in with your school Figma account."]))

    design = design_dir()
    if not design or not design.exists():
        items.append(check_item("app", "your app (design folder)", "missing", "none started yet",
                                ['./fad init "<your app\'s name>"', "A working name is fine. You can change it in the brief."]))
    else:
        items.append(check_item("app", "your app (design folder)", "ok", f"{state.get('app_name', '')}: {design}"))
        miss = missing_brief(design)
        items.append(check_item("brief", "the brief (brief.yaml)", "ok" if not miss else "todo",
                                "complete" if not miss else "still to fill in: " + ", ".join(miss) + " (Claude asks in step 2)", required=False))
        brief = read_brief(design / "brief.yaml")
        items.append(palette_check(brief.get("palette", "")))
        plat = brief.get("platform", "")
        if plat and plat not in PLATFORMS:
            items.append(check_item("platform", "platform", "warn", f"'{plat}' is not one of: {', '.join(PLATFORMS)}",
                                    ["Set platform: in design/brief.yaml to ios, android or both"], required=False))
        data = read_screens(design)
        if data is None:
            items.append(check_item("screens", "screen map", "todo", "not written yet (step 3)", required=False))
        else:
            probs = screens_problems(data)
            items.append(check_item("screens", "screen map", "ok" if not probs else "warn",
                                    f"{len(data.get('screens', []))} screen(s)" if not probs else f"{len(probs)} problem(s): {probs[0]}",
                                    [] if not probs else ["./fad screens"], required=False))

    linked = SKILL_LINK.exists()
    items.append(check_item("install", "installed as a Claude skill", "ok" if linked else "warn",
                            str(SKILL_LINK) if linked else "not installed: Claude only sees it when opened in this folder",
                            [] if linked else ["./fad install"], required=False))
    return items


MARK = {"ok": "[ok]     ", "missing": "[missing]", "warn": "[check]  ", "unknown": "[?]      ", "todo": "[todo]   "}


def blocking(items: list[dict]) -> list[dict]:
    return [i for i in items if i["required"] and i["status"] in ("missing",)]


def next_step(items: list[dict]) -> tuple[str, list[str]]:
    miss = blocking(items)
    if miss:
        i = miss[0]
        return f"Fix: {i['label']}. {i['detail']}.", i["fix"]
    unk = [i for i in items if i["required"] and i["status"] == "unknown"]
    if unk:
        return f"Check by hand: {unk[0]['label']}. {unk[0]['detail']}.", unk[0]["fix"]
    step = tutorial_status()
    cur = next((s for s in step if not s["done"]), None)
    if cur:
        return f"Start the tutorial: step {cur['id']}, {cur['title']}.", ["./fad tutorial"]
    return "You have finished the tutorial.", []


def print_checks(items: list[dict]) -> None:
    w = max(len(i["label"]) for i in items)
    for i in items:
        print(f"{MARK[i['status']]} {i['label']:<{w}}  {i['detail']}")
        if i["status"] in ("missing", "warn", "unknown") and i["fix"]:
            for line in i["fix"]:
                print(f"{'':<{len(MARK['ok']) + 1}}{'':<{w}}    {line}")


# ───────────────────────── tutorial ─────────────────────────

def tutorial_steps() -> dict:
    return json.loads((REPO / "tutorial" / "steps.json").read_text())


def read_decisions(design: Path) -> list[dict]:
    out = []
    for f in sorted((design / "decisions").glob("D-*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except ValueError:
            pass
    return out


def tutorial_status() -> list[dict]:
    spec = tutorial_steps()["steps"]
    state = load_state()
    manual_done = set(state.get("tutorial_done", []))
    design = design_dir()
    has = bool(design and design.exists())
    req_ok = not blocking(run_checks(with_mcp=False))
    decisions = read_decisions(design) if has else []
    screens = read_screens(design) if has else None
    all_decided = bool(decisions) and all(d.get("status") in DECIDED for d in decisions)
    derived = {
        1: req_ok and has,
        2: has and not missing_brief(design),
        3: bool(screens) and not screens_problems(screens),
        6: all_decided,
        7: all_decided and all((design / "handoff" / f"{d['id']}.md").exists() for d in decisions if d.get("status") == "approved"),
    }
    out = []
    prev_done = True
    for s in spec:
        done = derived[s["id"]] if s["mode"] == "derived" else s["id"] in manual_done
        out.append({**s, "done": bool(done), "blocked": not prev_done})
        prev_done = prev_done and bool(done)
    return out


def cmd_tutorial(args) -> int:
    spec = tutorial_steps()
    st = tutorial_status()
    if args.action == "done":
        if not (args.n or "").isdigit():
            print("Say which step: ./fad tutorial done 4")
            return 2
        n = int(args.n)
        step = next((s for s in st if s["id"] == n), None)
        if not step:
            print(f"There is no step {n}.")
            return 2
        if step["mode"] == "derived":
            print(f"Step {n} is marked done by what is on disk, not by hand: {step['done_when']}")
            return 2
        if step["blocked"]:
            print(f"Finish the steps before step {n} first.")
            return 2
        state = load_state()
        state["tutorial_done"] = sorted(set(state.get("tutorial_done", [])) | {n})
        save_state(state)
        print(f"Step {n} marked done: {step['title']}.")
        return 0
    if args.action == "reset":
        state = load_state()
        state["tutorial_done"] = []
        save_state(state)
        print("Hand-marked steps cleared. Steps decided by files on disk stay as they are.")
        return 0
    print(f"Tutorial: {spec['title']}\n{spec['intro']}\n")
    which = app_tutorials().get(load_state().get("app_tutorial") or "")
    if which:
        print(f"You are following: {which['title']} ({which['folder'] / 'README.md'})\n")
    cur = next((s for s in st if not s["done"]), None)
    for s in st:
        mark = "[x]" if s["done"] else ("[>]" if cur and s["id"] == cur["id"] else "[ ]")
        print(f"{mark} {s['id']}. {s['title']}")
    if cur:
        print(f"\nNOW: step {cur['id']}, {cur['title']}\n  You:    {cur['you']}\n  Claude: {cur['claude']}\n  Done when: {cur['done_when']}")
        if cur["mode"] == "manual":
            print(f"  (Claude runs ./fad tutorial done {cur['id']} when this is true.)")
    else:
        print("\nAll seven steps are done. Design the next screen: ask Claude for it by its number in ./fad screens.")
    return 0


# ───────────────────────── app tutorials ─────────────────────────

def app_tutorials() -> dict[str, dict]:
    """The ready-made tutorials in tutorial/apps/<slug>/, keyed by slug."""
    out = {}
    for d in sorted((REPO / "tutorial" / "apps").glob("*/tutorial.json")):
        try:
            t = json.loads(d.read_text())
        except ValueError:
            continue
        t["folder"] = d.parent
        out[t["slug"]] = t
    return out


def cmd_tutorials(args) -> int:
    tuts = app_tutorials()
    if not args.slug:
        print("Tutorials for common apps. Each gives you an example brief and a proposed screen map to change.\n")
        w = max(len(k) for k in tuts)
        for slug, t in tuts.items():
            print(f"  {slug:<{w}}  {t['title']}: teaches {t['teaches']}.")
        print(f'\nStart one:   ./fad init "<your app\'s name>" --tutorial {next(iter(tuts))}')
        print("Read one:    ./fad tutorials <name>")
        return 0
    t = tuts.get(args.slug)
    if not t:
        print(f"There is no tutorial called '{args.slug}'. The tutorials are: {', '.join(tuts)}.")
        return 2
    screens = json.loads((t["folder"] / "screens.json").read_text())
    print(f"{t['title']}  ({t['slug']})\nTeaches {t['teaches']}.\n")
    print(f"The example brief\n  {t['one_line']}\n  For: {t['people'][0]}")
    for i, task in enumerate(t["top_tasks"], 1):
        print(f"  {i}. {task}")
    print("\nThe proposed screens")
    for sc in screens["screens"]:
        first = "  <- drawn first" if sc["id"] == screens.get("draw_first") else ""
        print(f"  {sc['id']}  {sc['name']}: {sc['purpose']} ({', '.join(sc.get('states', []))}){first}")
    print(f"\nWhat the check found when it was drawn ({t['drawn']['date']})")
    for m in t["drawn"]["measured"]:
        print("  - " + m.replace("**", ""))
    cat = load_templates(REPO / "templates")
    by_url = {e["url"]: e for e in cat["code"] + cat["design"]}
    print("\nTemplates to look at (give the credit shown if you build on one)")
    for url in t["templates"]["design"] + t["templates"]["code"]:
        e = by_url.get(url)
        print("  - " + (e.get("credit") or url if e else f"{url} (no longer in the catalog)"))
    print(f"\nThe walkthrough, with pictures: {t['folder'] / 'README.md'}")
    print(f'Start it:  ./fad init "{t["example_name"]}" --tutorial {t["slug"]}')
    return 0


def yaml_list(items: list[str]) -> str:
    return "\n" + "\n".join(f"  - {json.dumps(x, ensure_ascii=False)}" for x in items)


# ───────────────────────── init ─────────────────────────

BRIEF_TEMPLATE = """# design/brief.yaml. Claude fills the blank fields by asking you; nothing is drawn until every required one is filled.{tutorial_note}
app_name: {name}              # required: a working name is fine
one_line: {one_line}                  # required: what it does, for whom, in one sentence
people: {people}                    # required: who uses it (one line each)
top_tasks: {top_tasks}                    # required: the three things a person must be able to do
platform: {platform}          # required: ios, android or both (./fad devices)
palette: {palette}            # required: {palette_ids} (./fad palettes)
dark_mode: false              # also draw the palette's dark mode, where it has one
implementer: ""               # required: who builds it later, "claude-code" or "codex"
stack: undecided              # swiftui, compose, react-native, flutter, or undecided
approvers: []                 # required: your name and role
conformance_target: "WCAG 2.2 AA"
existing_app: none            # path to a repo if you are redesigning an app that exists
figma_file: ""                # blank until Claude creates the Figma file for this app
out_of_scope: []
"""


def cmd_init(args) -> int:
    name = (args.name or "").strip()
    if not name:
        print('Give the app a working name:\n  ./fad init "Trail Notes"')
        return 2
    pdata = pal.load(REPO)
    palette = args.palette or pdata["default"]
    if palette not in pal.ids(pdata):
        print(f"'{palette}' is not one of the color sets: {', '.join(pal.ids(pdata))}. Nothing was created.")
        return 2
    tut = None
    if getattr(args, "tutorial", None):
        tut = app_tutorials().get(args.tutorial)
        if not tut:
            print(f"There is no tutorial called '{args.tutorial}'. The tutorials are: {', '.join(app_tutorials())}. Nothing was created.")
            return 2
    platform = args.platform or (tut["platform"] if tut else "ios")
    if platform not in PLATFORMS:
        print(f"'{platform}' is not a platform this tool draws: {', '.join(PLATFORMS)}. Nothing was created.")
        return 2
    label = slug(name)
    ws = HOME / label
    design = ws / "design"
    created = not design.exists()
    for d in ("rulebook", "decisions", "approvals", "handoff", "checks", "schema"):
        (design / d).mkdir(parents=True, exist_ok=True)
    if not (design / "brief.yaml").exists():
        fill = {"one_line": '""', "people": "[]", "top_tasks": "[]", "tutorial_note": ""}
        if tut:
            fill = {"one_line": json.dumps(tut["one_line"], ensure_ascii=False), "people": yaml_list(tut["people"]), "top_tasks": yaml_list(tut["top_tasks"]),
                    "tutorial_note": f"\n# This is the example from the '{tut['slug']}' tutorial. Change anything. Claude reads it back to you and asks who may approve before it draws."}
        (design / "brief.yaml").write_text(BRIEF_TEMPLATE.format(name=json.dumps(name), platform=platform, palette=palette,
                                                                 palette_ids=", ".join(pal.ids(pdata)), **fill))
    if tut and not (design / "screens.proposed.json").exists() and not (design / "screens.json").exists():
        # a proposal, not the screen map: it becomes screens.json only when the person has confirmed it
        shutil.copy(tut["folder"] / "screens.json", design / "screens.proposed.json")
    if not (design / "rulebook" / "rules.yaml").exists():
        shutil.copy(REPO / "starter" / "rules.yaml", design / "rulebook" / "rules.yaml")
    repo_made = False
    if shutil.which("git") and not (ws / ".git").exists():
        repo_made = run(["git", "init", "-q", str(ws)])[0] == 0
    if created:
        ledger_append(design, {"type": "workspace.initialized", "by": "fad init", "app_name": name, "platform": platform,
                               "palette": palette, "tutorial": tut["slug"] if tut else None, "tool_version": VERSION})
    state = load_state()
    state.update({"app_name": name, "label": label, "workspace": str(ws), "app_tutorial": tut["slug"] if tut else state.get("app_tutorial") if not created else None})
    save_state(state)
    print(f"{'Created' if created else 'Found'} your design folder: {design}")
    print(f"App: {name}. Platform: {platform}. Colors: {palette}.")
    if repo_made:
        print(f"Made {ws} a git repository, so you can commit your approvals. Nothing was committed.")
    if tut:
        print(f"Tutorial: {tut['title']}. The example brief is filled in, and the proposed screens are in {design / 'screens.proposed.json'}.")
        print(f"Walkthrough: {tut['folder'] / 'README.md'}")
    print("\nNext: in Claude Code, type: tutorial   (open it in the figma-appdesigner folder, or anywhere after ./fad install)")
    return 0


# ───────────────────────── approve / reject / defer ─────────────────────────

OUTCOME = {"approve": "approved", "reject": "rejected", "defer": "deferred"}


def next_approval_id(design: Path) -> str:
    nums = [int(m.group(1)) for f in (design / "approvals").glob("A-*.json") if (m := re.match(r"A-(\d+)\.json", f.name))]
    return f"A-{(max(nums) + 1) if nums else 1:04d}"


def decide(verb: str, decision_id: str, design: Path, ask=input, say=print, reopen: bool = False) -> int:
    """The person decides. All input comes through `ask`; the caller guarantees a terminal."""
    outcome = OUTCOME[verb]
    dfile = design / "decisions" / f"{decision_id}.json"
    if not dfile.exists():
        say(f"No decision {decision_id} in {design / 'decisions'}.")
        return 2
    d = json.loads(dfile.read_text())
    cur = d.get("status")
    if cur in ("approved", "rejected") and not reopen:
        say(f"{decision_id} is already {cur}. Changing it reopens it, which is a deliberate act: add --reopen.")
        return 2
    if cur in ("applied", "verified", "regressed"):
        say(f"{decision_id} is {cur}; it has been built. Open a new decision instead.")
        return 2

    say(f"\n{decision_id}: {d.get('title', '')}")
    say(f"Proposal: {d.get('proposal', '')}")
    if d.get("screens"):
        say(f"Screens: {', '.join(d['screens'])}")
    for a in d.get("alternatives", []):
        say(f"  Passed over: {a.get('option')} ({a.get('why_not')})")
    if d.get("consequences"):
        say(f"Consequences: {d['consequences']}")
    if d.get("finding_ids"):
        say(f"Open findings on it: {', '.join(d['finding_ids'])}")
    say("")

    name = ask("Your name (this goes in the record): ").strip()
    if not name:
        say("A name is required. Nothing was written.")
        return 2
    scope = ""
    not_approved = ""
    reason = ""
    if verb == "approve":
        scope = ask("What exactly are you approving? (Enter = as written above): ").strip() or "as written in the decision record"
        not_approved = ask("What is NOT approved? (Enter = nothing else): ").strip() or "nothing else"
    else:
        reason = ask(f"Why are you {'rejecting' if verb == 'reject' else 'deferring'} it? ").strip()
        if not reason:
            say("A reason is required. Nothing was written.")
            return 2
    figma_version = ask("Figma version ID you saved for this design (Enter = none): ").strip() or None
    confirm = ask(f"Type {decision_id} to {verb} it: ").strip()
    if confirm != decision_id:
        say("Not confirmed. Nothing was written.")
        return 2

    aid = next_approval_id(design)
    approval = {
        "id": aid, "decisions": [decision_id], "outcome": outcome, "approver": name, "at": now(),
        "scope": scope or None, "not_approved": not_approved or None, "reason": reason or None,
        "figma_version_id": figma_version, "ledger_hash": ledger_head(design),
        "supersedes_status": cur if reopen else None,
        "written_by": f"fad {verb}, run by the approver in a terminal",
    }
    (design / "approvals" / f"{aid}.json").write_text(json.dumps(approval, indent=2) + "\n")
    d.setdefault("status_history", []).append({"status": outcome, "by": name, "at": approval["at"], "approval_file": f"design/approvals/{aid}.json", "from": cur})
    d["status"] = outcome
    dfile.write_text(json.dumps(d, indent=2) + "\n")
    ledger_append(design, {"type": f"decision.{outcome}", "decision_id": decision_id, "approval_file": f"design/approvals/{aid}.json", "by": name})
    say(f"\n{decision_id} is now {outcome}. Wrote design/approvals/{aid}.json and a ledger event.")
    say("Commit that file yourself: the commit is what makes it yours.")
    return 0


def cmd_decide(args) -> int:
    design = design_dir(args.design)
    if not design or not design.exists():
        print('No design folder yet. Run ./fad init "<your app\'s name>" first.')
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(f"Only a person can {args.verb} a design, and this is not a terminal a person is typing in.\n"
              f"Open your own terminal and run:\n  ./fad {args.verb} {args.decision}\n"
              "(Chat messages and agent-run commands do not count as approval.)")
        return 3
    return decide(args.verb, args.decision, design, reopen=args.reopen)


# ───────────────────────── palettes ─────────────────────────

def cmd_palettes(args) -> int:
    data = pal.load(REPO)
    bad = pal.problems(data)
    if bad:
        print("palettes/palettes.json has problems:")
        for b in bad:
            print("  - " + b)
        return 1
    if args.figma:
        if args.name and not pal.find(data, args.name):
            print(f"There is no color set called '{args.name}'. The sets are: {', '.join(pal.ids(data))}.")
            return 2
        print(pal.figma_script(REPO, data, args.name))
        return 0
    if args.json:
        one = pal.find(data, args.name) if args.name else None
        if args.name and not one:
            print(json.dumps({"error": f"no palette {args.name}", "known": pal.ids(data)}))
            return 2
        chosen = [one] if one else data["palettes"]
        print(json.dumps({"checked": data["checked"], "default": data["default"], "roles": data["roles"],
                          "palettes": [{**p, "contrast": pal.checks(p)} for p in chosen]}, indent=2))
        return 0
    if not args.name:
        pal.print_list(data)
        print("\nSee one in full, with its contrast worked out:  ./fad palettes <id>")
        return 0
    one = pal.find(data, args.name) or (pal.wireframe(data) if args.name == "wireframe" else None)
    if not one:
        print(f"There is no color set called '{args.name}'. The sets are: {', '.join(pal.ids(data))}.")
        return 2
    pal.print_one(one)
    return 0


# ───────────────────────── templates ─────────────────────────

USABLE_ORDER = ["copy with credit", "copyleft: share alike", "look only"]


def load_templates(folder: Path) -> dict:
    """The two catalogs, tolerant of a missing or broken file. Entries are shown as recorded, never trusted as audited."""
    out = {"code": [], "design": [], "checked": {}, "problems": []}
    for key, name in (("code", "code-templates.json"), ("design", "design-templates.json")):
        p = folder / name
        if not p.exists():
            out["problems"].append(f"{name} is not here yet")
            continue
        try:
            data = json.loads(p.read_text())
        except ValueError:
            out["problems"].append(f"{name} is not valid JSON")
            continue
        out[key] = [e for e in data.get("entries", []) if isinstance(e, dict) and e.get("url")]
        out["checked"][key] = data.get("checked", "")
    return out


def licence_words(entry: dict) -> str:
    """The licence as recorded, and whether anyone read it from the source. Never upgrades an unread licence."""
    lic = entry.get("license")
    if not lic:
        return "licence not confirmed"
    if entry.get("license_checked") is False:
        return f"{lic}, not confirmed"
    return str(lic)


def template_kind(entry: dict) -> str:
    return str(entry.get("app_kind") or entry.get("kind") or "other").lower()


def template_matches(entry: dict, word: str) -> bool:
    hay = " ".join(str(entry.get(k, "")) for k in ("kind", "app_kind", "name", "what", "stack")).lower()
    return word.lower() in hay


def credits_markdown(cat: dict) -> str:
    """templates/CREDITS.md, made from the catalogs so it cannot drift from them."""
    lines = ["# Credits", "",
             "Every template and design kit this tool points to, with the licence it is offered under and who made it.",
             "This tool links to these works; it does not contain copies of them. If you build on one, this is the credit to give,",
             "and its licence file is the thing to read first.", "",
             f"Made by `./fad templates --credits` from the two catalogs in this folder ({len(cat['code'])} code, {len(cat['design'])} design). Do not edit by hand.", ""]
    for key, title in (("design", "Design kits and files"), ("code", "Code templates")):
        lines += [f"## {title}", ""]
        by_lic: dict[str, list[dict]] = {}
        for e in cat[key]:
            by_lic.setdefault(str(e.get("license")), []).append(e)
        for lic in sorted(by_lic, key=lambda k: (-len(by_lic[k]), k)):
            lines += [f"### {lic} ({len(by_lic[lic])})", ""]
            for e in sorted(by_lic[lic], key=lambda e: (e.get("name", "").lower(), e.get("path", ""))):
                label = e.get("name", "") + (f" / {e['path']}" if e.get("path") else "")
                who = e.get("by") or e.get("name", "").split("/")[0] + " and contributors"
                lines.append(f"- [{label}]({e['url']}), by {who}")
            lines.append("")
    return "\n".join(lines)


def cmd_templates(args) -> int:
    cat = load_templates(REPO / "templates")
    if getattr(args, "credits", False):
        print(credits_markdown(cat), end="")
        return 0
    if not cat["code"] and not cat["design"]:
        print("No template catalogs yet: " + "; ".join(cat["problems"]) + ".")
        return 2
    if args.json:
        pick = (lambda e: template_matches(e, args.kind)) if args.kind else (lambda e: True)
        print(json.dumps({"checked": cat["checked"], "code": [e for e in cat["code"] if pick(e)],
                          "design": [e for e in cat["design"] if pick(e)], "problems": cat["problems"]}, indent=2))
        return 0
    if not args.kind:
        print("Free templates and design kits for common kinds of app.\n")
        for key, title in (("code", "CODE (open-source apps and starter kits)"), ("design", "DESIGN (kits and files to open in Figma)")):
            if not cat[key]:
                continue
            print(f"{title}: {len(cat[key])}, gathered {cat['checked'].get(key, '?')}")
            counts: dict[str, int] = {}
            for e in cat[key]:
                counts[template_kind(e)] = counts.get(template_kind(e), 0) + 1
            line = ", ".join(f"{k} {n}" for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
            print("  " + line + "\n")
        print('See one kind:  ./fad templates chat      (any word: "e-commerce", "flutter", "wireframe")')
        print("These lists were gathered by search and spot-checked, not audited. Open a template's licence before you build on it.")
        return 0
    code = [e for e in cat["code"] if template_matches(e, args.kind)]
    design = [e for e in cat["design"] if template_matches(e, args.kind)]
    if not code and not design:
        print(f"Nothing in the catalogs matches '{args.kind}'. Run ./fad templates to see the kinds.")
        return 2
    if code:
        print(f"CODE: {len(code)} matching '{args.kind}'")
        code.sort(key=lambda e: (USABLE_ORDER.index(e["usable"]) if e.get("usable") in USABLE_ORDER else 9, -(e.get("stars") or 0)))
        for e in code:
            flags = "".join(f" [{f}]" for f in ("official", "archived", "stale") if e.get(f))
            label = e.get("name", "") + (f" / {e['path']}" if e.get("path") else "")
            print(f"  {label}  ({e.get('stack', '?')}, {licence_words(e)}: {e.get('usable', 'look only')}){flags}")
            print(f"      {e.get('what', '')}")
            print(f"      {e['url']}")
    if design:
        print(f"{chr(10) if code else ''}DESIGN: {len(design)} matching '{args.kind}'")
        for e in design:
            print(f"  {e.get('name')}  ({e.get('format', '?')}, {licence_words(e)})")
            print(f"      {e.get('what', '')}")
            if e.get("limits"):
                print(f"      Limits: {e['limits']}")
            print(f"      {e['url']}")
    print()
    if code:
        print("copy with credit = you may build from it and must keep its licence notice. copyleft = your app must be shared under the same terms. look only = read it, copy nothing.")
    if design:
        print("CC-BY-4.0 = you may use and adapt it if you credit its author. A kit with its own terms (Apple's, for one) is bound by those.")
    print("Gathered by search and spot-checked, not audited. Open the licence before you build on one.")
    return 0


# ───────────────────────── ledger / install / help ─────────────────────────

def cmd_ledger(args) -> int:
    design = design_dir(args.design)
    if not design or not (design / "ledger.jsonl").exists():
        print('No ledger found. Run ./fad init "<your app\'s name>" first, or pass --design <path to design folder>.')
        return 2
    problems = ledger_verify(design)
    n = len(ledger_events(design))
    if problems:
        print(f"Ledger has {len(problems)} problem(s) in {n} events:")
        for p in problems:
            print("  - " + p)
        return 1
    print(f"Ledger is valid: {n} events, chain intact, every approval file matches.")
    return 0


def cmd_install(_args) -> int:
    if SKILL_LINK.exists() or SKILL_LINK.is_symlink():
        if SKILL_LINK.resolve() == REPO:
            print(f"Already installed: {SKILL_LINK}")
            return 0
        print(f"{SKILL_LINK} already exists and is not this folder. Move it aside first; nothing was changed.")
        return 2
    SKILL_LINK.parent.mkdir(parents=True, exist_ok=True)
    SKILL_LINK.symlink_to(REPO)
    print(f"Installed: {SKILL_LINK} -> {REPO}\nOpen Claude Code in any folder and ask it to use figma-appdesigner.")
    return 0


HELP_HEAD = f"""figma-appdesigner {VERSION}
Design a phone app by talking to Claude, drawn in Figma, with a paper trail.

You say what the app is for. Claude maps its screens, draws them in Figma in your
colors, and changes them as you talk. It checks its own drawing against written rules,
and you accept or reject each design. Accepted designs go to Claude Code or Codex to build.
Nothing here writes app code.
"""

HELP_COMMANDS = """COMMANDS
  ./fad help                   this screen: checks your setup, names the next step
  ./fad check [--json]         the checks alone (--no-mcp skips the slow Figma check)
  ./fad init "<app name>"      start a design folder (--platform ios|android|both, --palette <id>, --tutorial <name>)
  ./fad tutorial               the seven steps, and the one you are on
  ./fad tutorials [name]       ready-made tutorials for common apps: to-do, weather, chat
  ./fad palettes [id]          the default colors: bear-brown, brutalist, northeastern, humanitarians
  ./fad devices                the screen sizes designs are drawn at
  ./fad screens                your app's screens and how they connect
  ./fad templates [kind]       free templates and design kits for common apps, with licences
  ./fad approve <D-id>         YOU accept a design (also: reject, defer). Your terminal only.
  ./fad ledger verify          check the record has not been altered
  ./fad install                make this a Claude skill available in every folder
"""


def cmd_help(args) -> int:
    print(HELP_HEAD)
    print("YOUR SETUP")
    items = run_checks(with_mcp=not args.no_mcp)
    print_checks(items)
    msg, fix = next_step(items)
    print(f"\nNEXT STEP\n  {msg}")
    for line in fix:
        print(f"    {line}")
    print("\n" + HELP_COMMANDS)
    return 0


def cmd_check(args) -> int:
    items = run_checks(with_mcp=not args.no_mcp)
    if args.json:
        print(json.dumps({"version": VERSION, "ready": not blocking(items), "checks": items}, indent=2))
    else:
        print_checks(items)
        msg, fix = next_step(items)
        print(f"\nNext: {msg}")
        for line in fix:
            print(f"  {line}")
    return 1 if blocking(items) else 0


class QuietParser(argparse.ArgumentParser):
    def error(self, message):  # our own short message replaces argparse's usage dump
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    p = QuietParser(prog="fad", add_help=False)
    sub = p.add_subparsers(dest="cmd")
    h = sub.add_parser("help", add_help=False)
    h.add_argument("--no-mcp", action="store_true")
    c = sub.add_parser("check", add_help=False)
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-mcp", action="store_true")
    i = sub.add_parser("init", add_help=False)
    i.add_argument("name")
    i.add_argument("--platform")
    i.add_argument("--palette")
    i.add_argument("--tutorial")
    t = sub.add_parser("tutorial", add_help=False)
    t.add_argument("action", nargs="?", default="show", choices=["show", "done", "reset"])
    t.add_argument("n", nargs="?")
    pp = sub.add_parser("palettes", add_help=False)
    pp.add_argument("name", nargs="?")
    pp.add_argument("--json", action="store_true")
    pp.add_argument("--figma", action="store_true")
    dv = sub.add_parser("devices", add_help=False)
    dv.add_argument("--json", action="store_true")
    sc = sub.add_parser("screens", add_help=False)
    sc.add_argument("--json", action="store_true")
    sc.add_argument("--design")
    tp = sub.add_parser("templates", add_help=False)
    tp.add_argument("kind", nargs="?")
    tp.add_argument("--json", action="store_true")
    tp.add_argument("--credits", action="store_true")
    tu = sub.add_parser("tutorials", add_help=False)
    tu.add_argument("slug", nargs="?")
    for verb in OUTCOME:
        d = sub.add_parser(verb, add_help=False)
        d.set_defaults(verb=verb)
        d.add_argument("decision")
        d.add_argument("--design")
        d.add_argument("--reopen", action="store_true")
    l = sub.add_parser("ledger", add_help=False)
    l.add_argument("action", choices=["verify"])
    l.add_argument("--design")
    sub.add_parser("install", add_help=False)
    sub.add_parser("version", add_help=False)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        argv = ["help"] + argv[1:]
    p = build_parser()
    try:
        args = p.parse_args(argv)
    except SystemExit:
        print("That command was not understood.\n")
        print(HELP_COMMANDS)
        return 2
    table = {"help": cmd_help, "check": cmd_check, "init": cmd_init, "tutorial": cmd_tutorial, "palettes": cmd_palettes,
             "devices": cmd_devices, "screens": cmd_screens, "templates": cmd_templates, "tutorials": cmd_tutorials, "ledger": cmd_ledger, "install": cmd_install}
    if args.cmd in table:
        return table[args.cmd](args)
    if args.cmd in OUTCOME:
        return cmd_decide(args)
    if args.cmd == "version":
        print(VERSION)
        return 0
    print(HELP_COMMANDS)
    return 2


if __name__ == "__main__":
    sys.exit(main())
