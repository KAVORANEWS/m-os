"""Unit tests for the Update Center APT parsers and mos-desktopctl command plans."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "applications" / "python"))

from mos import aptparse, desktopctl  # noqa: E402


class AptParseTest(unittest.TestCase):
    LIST = """Listing...
libssl3t64/trixie-security 3.5.1-1+deb13u2 amd64 [upgradable from: 3.5.1-1+deb13u1]
firefox-esr/trixie-security,trixie-updates 140.6.0esr-1~deb13u1 amd64 [upgradable from: 140.5.0esr-1~deb13u1]
tzdata/trixie-updates 2026b-0+deb13u1 all [upgradable from: 2026a-0+deb13u1]
"""

    def test_parse_upgradable(self):
        ups = aptparse.parse_upgradable(self.LIST)
        self.assertEqual([u.name for u in ups], ["firefox-esr", "libssl3t64", "tzdata"])
        self.assertTrue(ups[0].is_security)
        self.assertFalse(ups[2].is_security)
        self.assertEqual(ups[1].old_version, "3.5.1-1+deb13u1")
        self.assertEqual(aptparse.parse_upgradable("Listing...\n"), [])

    def test_status_lines(self):
        s = aptparse.parse_status_line("pmstatus:libssl3t64:42.8571:Installing libssl3t64 (amd64)")
        self.assertEqual((s.kind, s.package), ("install", "libssl3t64"))
        self.assertAlmostEqual(aptparse.overall_percent(s), 30 + 42.8571 * 0.7, places=3)
        d = aptparse.parse_status_line("dlstatus:1:50:Retrieving file 1 of 2")
        self.assertAlmostEqual(aptparse.overall_percent(d), 15.0)
        msg = aptparse.parse_status_line("pmerror:foo:10:dpkg: error: something: with colons")
        self.assertEqual(msg.message, "dpkg: error: something: with colons")
        self.assertIsNone(aptparse.parse_status_line("Get:1 http://deb.debian.org trixie InRelease"))


class DesktopCtlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["XDG_CONFIG_HOME"] = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_layout_plan_uses_lookandfeel_and_restores_theme(self):
        plan = desktopctl.plan_layout("classic", theme="light")
        self.assertEqual(plan[0], ["plasma-apply-lookandfeel", "--apply", "org.mos.classic.desktop", "--resetLayout"])
        self.assertIn(["plasma-apply-colorscheme", "MOSLight"], plan)
        flat = [" ".join(c) for c in plan]
        self.assertTrue(any("ButtonsOnRight IAX" in c for c in flat))

    def test_profile_plans_are_inverse(self):
        perf = desktopctl.plan_profile("performance")
        bal = desktopctl.plan_profile("balanced")
        self.assertIn(["balooctl6", "disable"], perf)
        self.assertIn(["balooctl6", "enable"], bal)
        self.assertTrue(any(c[-1] == "--delete" for c in bal))
        self.assertIn(desktopctl.kwrite("kwinrc", "Plugins", "blurEnabled", "false"), perf)

    def test_accent_validation(self):
        self.assertEqual(desktopctl.plan_accent("#6D5DF6"),
                         [["plasma-apply-colorscheme", "--accent-color", "#6D5DF6"]])
        with self.assertRaises(ValueError):
            desktopctl.plan_accent("purple; rm -rf /")

    def test_dry_run_does_not_write_state(self):
        with redirect_stdout(io.StringIO()) as out:
            rc = desktopctl.main(["--dry-run", "theme", "light"])
        self.assertEqual(rc, 0)
        self.assertIn("plasma-apply-colorscheme MOSLight", out.getvalue())
        self.assertFalse(desktopctl.state_file().exists())

    def test_state_roundtrip(self):
        desktopctl.save_state({"layout": "classic"})
        desktopctl.save_state({"theme": "light"})
        self.assertEqual(desktopctl.load_state(), {"layout": "classic", "theme": "light"})

    def test_layouts_exist_in_branding(self):
        root = Path(__file__).resolve().parents[2] / "packages/mos-branding/files/usr/share/plasma/look-and-feel"
        for lnf in desktopctl.LAYOUTS.values():
            self.assertTrue((root / lnf / "metadata.json").exists(), lnf)
            self.assertTrue((root / lnf / "contents/layouts/org.kde.plasma.desktop-layout.js").exists())


if __name__ == "__main__":
    unittest.main()
