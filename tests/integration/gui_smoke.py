#!/usr/bin/env python3
"""Headless GUI smoke test for the M OS applications.

Creates every main window with the Qt offscreen platform, lets it run its
first refresh cycle against the real /proc and /sys of the host, and saves
a screenshot of each window to the output directory.

    QT_QPA_PLATFORM=offscreen python3 tests/integration/gui_smoke.py [outdir]
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "applications" / "python"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp(prefix="mos-gui-"))

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtGui import QIcon  # noqa: E402


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "build" / "screenshots")
    out.mkdir(parents=True, exist_ok=True)
    from mos import ui
    app = ui.make_app("mos-smoke", "M OS smoke test", "mos-logo")
    QIcon.setFallbackSearchPaths([str(ROOT / "branding/rendered/icons/128x128")])

    from mos.about import AboutWindow
    from mos.control_center import SECTIONS, ControlCenter
    from mos.system_monitor import MonitorWindow
    from mos.update_center import UpdateWindow
    from mos.welcome import WelcomeWindow

    failures = 0
    windows = {
        "about": AboutWindow,
        "system-monitor": MonitorWindow,
        "update-center": UpdateWindow,
        "welcome": WelcomeWindow,
        "control-center": ControlCenter,
    }
    for name, cls in windows.items():
        try:
            win = cls()
            win.resize(1040, 700)
            win.show()
            for _ in range(3):
                app.processEvents()
            if name == "system-monitor":
                win.refresh()
                app.processEvents()
            win.grab().save(str(out / f"{name}.png"))
            if name == "control-center":
                # Build every section page to catch runtime errors
                for i, (section, _icon, _f) in enumerate(SECTIONS):
                    win.sidebar.setCurrentRow(i)
                    app.processEvents()
                    if section in ("Personalization", "Security", "Storage"):
                        win.grab().save(str(out / f"control-center-{section.lower()}.png"))
            if name == "welcome":
                for i in range(win.stack.count()):
                    win.stack.setCurrentIndex(i)
                    app.processEvents()
                    win.grab().save(str(out / f"welcome-{i}.png"))
            win.close()
            print(f"PASS {name}")
        except Exception:  # noqa: BLE001 — report every failure
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    QTimer.singleShot(0, app.quit)
    app.exec()
    print(f"{len(windows) - failures}/{len(windows)} windows OK; screenshots in {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
