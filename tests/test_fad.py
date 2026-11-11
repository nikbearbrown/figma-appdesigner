import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fad  # noqa: E402


def ns(**kw):
    base = dict(name="Trail Notes", platform=None, palette=None, tutorial=None)
    base.update(kw)
    return argparse.Namespace(**base)


def script(*answers):
    it = iter(answers)
    return lambda prompt="": next(it)


GOOD_SCREENS = {"screens": [
    {"id": "S-01", "name": "Notes list", "start": True, "purpose": "See your notes", "states": ["default", "empty", "loading", "error"],
     "goes_to": [{"on": "tap a note", "screen": "S-02"}]},
    {"id": "S-02", "name": "Note", "purpose": "Write a note", "states": ["default"], "goes_to": [{"on": "back", "screen": "S-01"}]},
]}

FULL_BRIEF = '''app_name: "Trail Notes"
one_line: "Notes for hikers, kept offline"
people:
  - day hikers
top_tasks:
  - write a note
platform: ios
palette: bear-brown
implementer: claude-code
approvers:
  - Ann, owner
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        fad.HOME = self.root / "work"
        fad.STATE_FILE = fad.HOME / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def init(self, **kw):
        self.assertEqual(fad.cmd_init(ns(**kw)), 0)
        return fad.design_dir()

    def add_decision(self, design, did="D-0001", status="proposed"):
        (design / "decisions" / f"{did}.json").write_text(json.dumps(
            {"id": did, "title": "Notes list, first design", "proposal": "A list with one add button.", "screens": ["S-01"],
             "finding_ids": [], "alternatives": [{"option": "grid of cards", "why_not": "fewer notes per screen"}], "status": status}))


class Init(Base):
    def test_init_creates_the_folder_and_is_idempotent(self):
        design = self.init()
        for d in ("rulebook", "decisions", "approvals", "handoff", "checks"):
            self.assertTrue((design / d).is_dir())
        self.assertTrue((design / "rulebook" / "rules.yaml").exists())
        brief = fad.read_brief(design / "brief.yaml")
        self.assertEqual((brief["app_name"], brief["platform"], brief["palette"]), ("Trail Notes", "ios", "bear-brown"))
        self.assertEqual(len(fad.ledger_events(design)), 1)
        (design / "brief.yaml").write_text(FULL_BRIEF)
        self.init()
        self.assertEqual(len(fad.ledger_events(design)), 1)
        self.assertEqual((design / "brief.yaml").read_text(), FULL_BRIEF)  # a second init never overwrites the brief

    def test_init_takes_platform_and_palette(self):
        design = self.init(platform="both", palette="northeastern")
        brief = fad.read_brief(design / "brief.yaml")
        self.assertEqual((brief["platform"], brief["palette"]), ("both", "northeastern"))

    def test_init_refuses_unknown_choices_and_creates_nothing(self):
        self.assertEqual(fad.cmd_init(ns(palette="mauve")), 2)
        self.assertEqual(fad.cmd_init(ns(platform="watch")), 2)
        self.assertEqual(fad.cmd_init(ns(name="  ")), 2)
        self.assertFalse(fad.HOME.exists())

    def test_brief_template_starts_incomplete(self):
        design = self.init()
        self.assertEqual(fad.missing_brief(design), ["one_line", "people", "top_tasks", "implementer", "approvers"])
        (design / "brief.yaml").write_text(FULL_BRIEF)
        self.assertEqual(fad.missing_brief(design), [])


class Ledger(Base):
    def test_chain_and_tamper(self):
        design = self.init()
        fad.ledger_append(design, {"type": "request.made", "by": "Ann", "words": "make the add button bigger"})
        self.assertEqual(fad.ledger_verify(design), [])
        p = design / "ledger.jsonl"
        p.write_text(p.read_text().replace("bigger", "smaller"))
        self.assertTrue(any("hash does not match" in x for x in fad.ledger_verify(design)))


class Screens(Base):
    def test_good_map(self):
        self.assertEqual(fad.screens_problems(GOOD_SCREENS), [])

    def test_problems_are_named(self):
        bad = {"screens": [
            {"id": "S-01", "name": "A", "start": True, "purpose": "p", "goes_to": [{"screen": "S-09"}], "states": ["sleepy"]},
            {"id": "S-01", "name": "B", "purpose": "p"},
            {"id": "home", "name": "", "purpose": ""},
        ]}
        probs = "\n".join(fad.screens_problems(bad))
        for want in ("used by more than one", "should look like S-01", "has no name", "has no purpose",
                     "which is not a screen", "is not one of default", "nothing leads here"):
            self.assertIn(want, probs)

    def test_needs_exactly_one_start(self):
        two = json.loads(json.dumps(GOOD_SCREENS))
        two["screens"][1]["start"] = True
        self.assertTrue(any("exactly one screen" in p for p in fad.screens_problems(two)))
        self.assertEqual(fad.screens_problems({"screens": []}), ["there are no screens yet"])

    def test_cli(self):
        design = self.init()
        self.assertEqual(fad.main(["screens"]), 2)  # no map yet
        (design / "screens.json").write_text(json.dumps(GOOD_SCREENS))
        self.assertEqual(fad.main(["screens"]), 0)
        orphan = json.loads(json.dumps(GOOD_SCREENS))
        orphan["screens"].append({"id": "S-03", "name": "Settings", "purpose": "Change settings"})
        (design / "screens.json").write_text(json.dumps(orphan))
        self.assertEqual(fad.main(["screens"]), 1)


class Decide(Base):
    def test_approve_writes_file_status_and_ledger(self):
        design = self.init()
        self.add_decision(design)
        said = []
        rc = fad.decide("approve", "D-0001", design, ask=script("Ann", "", "", "", "D-0001"), say=said.append)
        self.assertEqual(rc, 0)
        a = json.loads((design / "approvals" / "A-0001.json").read_text())
        self.assertEqual((a["outcome"], a["approver"], a["decisions"]), ("approved", "Ann", ["D-0001"]))
        self.assertEqual(json.loads((design / "decisions" / "D-0001.json").read_text())["status"], "approved")
        self.assertEqual(fad.ledger_events(design)[-1]["type"], "decision.approved")
        self.assertEqual(fad.ledger_verify(design), [])
        self.assertTrue(any("Screens: S-01" in s for s in said))

    def test_wrong_confirmation_writes_nothing(self):
        design = self.init()
        self.add_decision(design)
        self.assertEqual(fad.decide("approve", "D-0001", design, ask=script("Ann", "", "", "", "yes"), say=lambda *_: None), 2)
        self.assertEqual(list((design / "approvals").glob("*.json")), [])
        self.assertEqual(json.loads((design / "decisions" / "D-0001.json").read_text())["status"], "proposed")

    def test_reject_needs_a_reason_and_a_name(self):
        design = self.init()
        self.add_decision(design)
        self.assertEqual(fad.decide("reject", "D-0001", design, ask=script("Ann", ""), say=lambda *_: None), 2)
        self.assertEqual(fad.decide("reject", "D-0001", design, ask=script(""), say=lambda *_: None), 2)
        self.assertEqual(fad.decide("reject", "D-0001", design, ask=script("Ann", "too busy", "", "D-0001"), say=lambda *_: None), 0)

    def test_decided_needs_reopen(self):
        design = self.init()
        self.add_decision(design, status="approved")
        self.assertEqual(fad.decide("reject", "D-0001", design, ask=script(), say=lambda *_: None), 2)

    def test_cli_refuses_without_a_terminal(self):
        design = self.init()
        self.add_decision(design)
        self.assertEqual(fad.main(["approve", "D-0001"]), 3)  # the test runner is not a terminal
        self.assertEqual(list((design / "approvals").glob("*.json")), [])

    def test_approval_file_edited_after_the_fact_is_caught(self):
        design = self.init()
        self.add_decision(design)
        fad.decide("approve", "D-0001", design, ask=script("Ann", "", "", "", "D-0001"), say=lambda *_: None)
        f = design / "approvals" / "A-0001.json"
        a = json.loads(f.read_text())
        a["ledger_hash"] = "0" * 64
        f.write_text(json.dumps(a))
        self.assertTrue(any("ledger_hash does not match" in p for p in fad.ledger_verify(design)))


class Tutorial(Base):
    def done(self):
        return [s["done"] for s in fad.tutorial_status()]

    def test_steps_follow_the_files(self):
        self.assertEqual(self.done(), [False] * 7)
        design = self.init()
        self.assertEqual(self.done()[:3], [True, False, False])
        (design / "brief.yaml").write_text(FULL_BRIEF)
        self.assertEqual(self.done()[:3], [True, True, False])
        (design / "screens.json").write_text(json.dumps(GOOD_SCREENS))
        self.assertEqual(self.done()[:4], [True, True, True, False])
        self.assertEqual(fad.main(["tutorial", "done", "4"]), 0)
        self.assertEqual(fad.main(["tutorial", "done", "5"]), 0)
        self.add_decision(design)
        self.assertEqual(self.done(), [True, True, True, True, True, False, False])
        fad.decide("approve", "D-0001", design, ask=script("Ann", "", "", "", "D-0001"), say=lambda *_: None)
        self.assertEqual(self.done()[5:], [True, False])
        (design / "handoff" / "D-0001.md").write_text("brief")
        self.assertEqual(self.done(), [True] * 7)

    def test_manual_steps_cannot_skip_ahead_or_mark_derived(self):
        self.init()
        self.assertEqual(fad.main(["tutorial", "done", "4"]), 2)  # steps 2 and 3 are not done
        self.assertEqual(fad.main(["tutorial", "done", "2"]), 2)  # derived from files, not by hand
        self.assertEqual(fad.main(["tutorial", "done"]), 2)
        self.assertEqual(fad.main(["tutorial", "done", "9"]), 2)

    def test_steps_file_matches_the_code(self):
        steps = fad.tutorial_steps()["steps"]
        self.assertEqual([s["id"] for s in steps], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual([s["id"] for s in steps if s["mode"] == "manual"], [4, 5])


class Checks(Base):
    def test_no_app_blocks_with_a_fix(self):
        items = fad.run_checks(with_mcp=False)
        app = next(i for i in items if i["id"] == "app")
        self.assertEqual(app["status"], "missing")
        self.assertTrue(any("fad init" in f for f in app["fix"]))
        self.assertIn("your app", fad.next_step(items)[0])

    def test_app_ok_then_points_at_the_tutorial(self):
        design = self.init()
        items = fad.run_checks(with_mcp=False)
        self.assertEqual(next(i for i in items if i["id"] == "app")["status"], "ok")
        self.assertEqual(next(i for i in items if i["id"] == "brief")["status"], "todo")
        self.assertIn("step 2", fad.next_step(items)[0])
        (design / "brief.yaml").write_text(FULL_BRIEF.replace("platform: ios", "platform: watch").replace("bear-brown", "mauve"))
        items = fad.run_checks(with_mcp=False)
        self.assertEqual(next(i for i in items if i["id"] == "platform")["status"], "warn")
        self.assertEqual(next(i for i in items if i["id"] == "palette")["status"], "warn")


class PalettesAndDevices(Base):
    def test_the_four_default_sets(self):
        data = fad.pal.load(fad.REPO)
        self.assertEqual(fad.pal.ids(data), ["bear-brown", "brutalist", "northeastern", "humanitarians"])
        self.assertEqual(fad.pal.problems(data), [])
        for p in data["palettes"]:
            for c in fad.pal.checks(p):
                if c["pair"] in ("text", "text on cards", "secondary text", "button label"):
                    self.assertTrue(c["passes"], (p["id"], c))

    def test_same_palette_file_as_the_web_designer_when_it_is_next_door(self):
        sibling = fad.REPO.parent / "figma-webdesigner" / "palettes" / "palettes.json"
        if not sibling.exists():
            self.skipTest("figma-webdesigner is not checked out beside this folder")
        self.assertEqual(json.loads(sibling.read_text()), fad.pal.load(fad.REPO))
        self.assertEqual((sibling.parent.parent / "scripts" / "palettes.py").read_text(), (fad.REPO / "scripts" / "palettes.py").read_text())

    def test_devices(self):
        self.assertEqual([d["id"] for d in fad.devices_for("ios")], ["iphone"])
        self.assertEqual([d["id"] for d in fad.devices_for("both")], ["iphone", "android-phone"])
        self.assertEqual(fad.devices_for("watch"), [])
        for d in fad.devices()["devices"]:
            self.assertGreaterEqual(d["min_target"], 44)

    def test_rulebook_rules_have_the_fields_the_skill_relies_on(self):
        text = (fad.REPO / "starter" / "rules.yaml").read_text()
        rules = [l for l in text.splitlines() if l.startswith("- {")]
        self.assertGreaterEqual(len(rules), 10)
        for r in rules:
            for key in ("id:", "title:", "tier:", "mode:", "source:"):
                self.assertIn(key, r)
            self.assertRegex(r, r"tier: (normative|heuristic|house)")

    def test_cli(self):
        self.assertEqual(fad.main(["palettes"]), 0)
        self.assertEqual(fad.main(["palettes", "northeastern"]), 0)
        self.assertEqual(fad.main(["palettes", "mauve"]), 2)
        self.assertEqual(fad.main(["devices"]), 0)
        self.assertEqual(fad.main(["nonsense"]), 2)


class FigmaScripts(Base):
    def test_script_is_filled_in_from_the_file(self):
        data = fad.pal.load(fad.REPO)
        script = fad.pal.figma_script(fad.REPO, data)
        self.assertNotIn("__MODES__", script)
        modes = fad.pal.figma_modes(data)
        self.assertEqual([m["name"] for m in modes][-1], "Wireframe")  # last, so Figma's default mode is a real color set
        self.assertEqual(len(modes), 8)
        for m in modes:
            self.assertIn(m["roles"]["accent"], script)
        self.assertEqual(fad.main(["palettes", "--figma"]), 0)
        self.assertEqual(fad.main(["palettes", "mauve", "--figma"]), 2)

    def test_saved_scripts_never_carry_a_typed_color(self):
        import re
        for name in ("palette-variables.js", "sample-screen.js", "kit-components.js", "tutorial-screens.js", "measure-screen.js"):
            text = (fad.REPO / "figma" / name).read_text()
            self.assertEqual(re.findall(r"#[0-9A-Fa-f]{6}\b", text), [], name)


class Templates(Base):
    def catalogs(self):
        folder = self.root / "templates"
        folder.mkdir()
        (folder / "code-templates.json").write_text(json.dumps({"checked": "2026-11-10", "entries": [
            {"name": "a/chat-app", "url": "https://github.com/a/chat-app", "kind": "chat", "stack": "flutter", "what": "A chat app",
             "license": "MIT", "usable": "copy with credit", "stars": 10},
            {"name": "b/shop", "url": "https://github.com/b/shop", "kind": "e-commerce", "stack": "swiftui", "what": "A shop",
             "license": None, "usable": "look only", "stars": 99, "archived": True},
            {"name": "no-url"},
        ]}))
        (folder / "design-templates.json").write_text("{not json")
        return folder

    def test_load_is_tolerant(self):
        cat = fad.load_templates(self.catalogs())
        self.assertEqual([e["name"] for e in cat["code"]], ["a/chat-app", "b/shop"])  # the entry with no url is dropped
        self.assertEqual(cat["design"], [])
        self.assertTrue(any("not valid JSON" in p for p in cat["problems"]))
        self.assertEqual(fad.load_templates(self.root / "nowhere")["code"], [])

    def test_matching(self):
        cat = fad.load_templates(self.catalogs())
        self.assertTrue(fad.template_matches(cat["code"][0], "CHAT"))
        self.assertTrue(fad.template_matches(cat["code"][0], "flutter"))
        self.assertFalse(fad.template_matches(cat["code"][1], "chat"))
        self.assertEqual(fad.template_kind({"app_kind": "Weather", "kind": "ui kit"}), "weather")

    def test_an_unread_licence_is_never_shown_as_confirmed(self):
        self.assertEqual(fad.licence_words({"license": None}), "licence not confirmed")
        self.assertEqual(fad.licence_words({"license": "CC-BY-4.0", "license_checked": False}), "CC-BY-4.0, not confirmed")
        self.assertEqual(fad.licence_words({"license": "MIT", "license_checked": True}), "MIT")

    def test_shipped_catalogs_are_well_formed_when_present(self):
        folder = fad.REPO / "templates"
        if not (folder / "code-templates.json").exists() and not (folder / "design-templates.json").exists():
            self.skipTest("no catalogs shipped yet")
        cat = fad.load_templates(folder)
        self.assertEqual([p for p in cat["problems"] if "not valid JSON" in p], [])
        for e in cat["code"]:
            self.assertTrue(e["url"].startswith("https://github.com/"), e)
            # published = a confirmed licence that allows reuse, and a credit to give
            self.assertIn(e.get("usable"), ("copy with credit", "copyleft: share alike"), e)
            self.assertTrue(e.get("license_checked") and e.get("license") not in (None, "none"), e)
            self.assertIn(e["license"], e.get("credit", ""), e)
        for e in cat["design"]:
            self.assertTrue(e["url"].startswith("https://"), e)
            self.assertTrue(e.get("license_checked") and e.get("license"), e)
            self.assertNotIn("Apple", e["license"], e)
            self.assertIn(e["by"], e.get("credit", ""), e)
        urls = [e["url"].lower().rstrip("/") for e in cat["code"] + cat["design"]]
        self.assertEqual(len(urls), len(set(urls)), "a template is listed twice")

    def test_credits_file_matches_the_catalogs(self):
        folder = fad.REPO / "templates"
        if not (folder / "CREDITS.md").exists():
            self.skipTest("no credits file shipped yet")
        cat = fad.load_templates(folder)
        self.assertEqual((folder / "CREDITS.md").read_text(), fad.credits_markdown(cat))
        for e in cat["code"] + cat["design"]:
            self.assertIn(e["url"], fad.credits_markdown(cat))

    def test_wireframe_set_is_readable(self):
        data = fad.pal.load(fad.REPO)
        wf = fad.pal.wireframe(data)
        self.assertTrue(all(c["passes"] for c in fad.pal.checks(wf)))
        self.assertEqual(fad.main(["palettes", "wireframe"]), 0)


class AppTutorials(Base):
    def test_three_tutorials_each_complete_and_consistent(self):
        tuts = fad.app_tutorials()
        self.assertEqual(sorted(tuts), ["chat", "to-do", "weather"])
        cat = fad.load_templates(fad.REPO / "templates")
        urls = {e["url"] for e in cat["code"] + cat["design"]}
        import re
        for slug, t in tuts.items():
            screens = json.loads((t["folder"] / "screens.json").read_text())
            self.assertEqual(fad.screens_problems(screens), [], slug)
            self.assertIn(t["draw_first"], [s["id"] for s in screens["screens"]], slug)
            self.assertEqual(len(t["top_tasks"]), 3, slug)
            served = {x for s in screens["screens"] for x in s.get("serves", [])}
            self.assertEqual(set(t["top_tasks"]) - served, set(), f"{slug}: a top task no screen serves")
            self.assertTrue((fad.REPO / t["drawn"]["picture"]).exists(), slug)
            for u in t["templates"]["design"] + t["templates"]["code"]:
                self.assertIn(u, urls, f"{slug}: {u} is not in the published catalog")
            readme = (t["folder"] / "README.md").read_text()
            for u in re.findall(r"\]\((https://[^)]+)\)", readme):
                self.assertIn(u, urls, f"{slug} README links {u}, which is not in the published catalog")

    def test_init_with_a_tutorial_seeds_a_brief_the_person_must_still_finish(self):
        self.assertEqual(fad.cmd_init(ns(name="Sky Today", tutorial="weather")), 0)
        design = fad.design_dir()
        brief = fad.read_brief(design / "brief.yaml")
        self.assertIn("weather", brief["one_line"])
        self.assertEqual(fad.missing_brief(design), ["implementer", "approvers"])  # left for the person, on purpose
        self.assertTrue((design / "screens.proposed.json").exists())
        self.assertFalse((design / "screens.json").exists())  # a proposal is not the agreed map
        self.assertEqual([s["done"] for s in fad.tutorial_status()][:3], [True, False, False])

    def test_unknown_tutorial_creates_nothing(self):
        self.assertEqual(fad.cmd_init(ns(tutorial="banking")), 2)
        self.assertFalse(fad.HOME.exists())

    def test_cli(self):
        self.assertEqual(fad.main(["tutorials"]), 0)
        self.assertEqual(fad.main(["tutorials", "chat"]), 0)
        self.assertEqual(fad.main(["tutorials", "banking"]), 2)


if __name__ == "__main__":
    unittest.main()
