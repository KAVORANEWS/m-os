"""M OS Welcome — first-login setup and getting-started guide.

Choices are applied immediately through mos-desktopctl (real Plasma
configuration). In the live session it also offers the installer.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QHBoxLayout, QLabel, QPushButton,
                             QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from . import DOCS_URL, desktopctl, kcm, sysinfo, ui
from .control_center import run_desktopctl
from .i18n import tr

PREVIEW_DIR = "/usr/share/plasma/look-and-feel/{}/contents/previews/preview.png"


def done_flag() -> Path:
    return desktopctl.config_home() / "mos" / "welcome-done"


def recommended_profile() -> str:
    mem = sysinfo.read_memory()
    return "performance" if mem and mem.total < 6 * 1024 ** 3 else "balanced"


class ChoiceCards(QWidget):
    def __init__(self, options, current, on_pick, icon_size=QSize(200, 112)):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setSpacing(16)
        self.group = QButtonGroup(self)
        for key, label, image in options:
            b = QToolButton()
            b.setObjectName("Choice")
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setText(label)
            if image and os.path.exists(image):
                b.setIcon(QIcon(QPixmap(image)))
            else:
                b.setIcon(QIcon.fromTheme(image or "mos-logo"))
            b.setIconSize(icon_size)
            b.setMinimumWidth(icon_size.width() + 40)
            b.setChecked(key == current)
            b.clicked.connect(lambda _=False, k=key: on_pick(k))
            self.group.addButton(b)
            lay.addWidget(b)
        lay.addStretch(1)


class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("Welcome to M OS"))
        self.resize(860, 600)
        self.live = sysinfo.is_live_session()
        self.state = desktopctl.current_status()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 22)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.feedback = ui.subtitle("")
        root.addWidget(self.feedback)

        nav = QHBoxLayout()
        self.autostart = QCheckBox("Show at startup")
        self.autostart.setChecked(not done_flag().exists())
        self.back = QPushButton(tr("Back"))
        self.next = ui.primary_button(tr("Next"))
        self.back.clicked.connect(lambda: self.go(-1))
        self.next.clicked.connect(lambda: self.go(1))
        nav.addWidget(self.autostart)
        nav.addStretch(1)
        nav.addWidget(self.back)
        nav.addWidget(self.next)
        root.addLayout(nav)

        for builder in (self.page_hello, self.page_layout, self.page_theme, self.page_performance,
                        self.page_privacy, self.page_finish):
            self.stack.addWidget(builder())
        self.update_nav()

    # ------------------------------------------------------------------ pages
    def _page(self, heading: str, text: str) -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)
        lay.addWidget(ui.title(heading))
        lay.addWidget(ui.subtitle(text))
        return w, lay

    def page_hello(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addStretch(1)
        logo = QLabel()
        logo.setPixmap(QIcon.fromTheme("mos-logo").pixmap(128, 128))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        t = ui.title("Welcome to M OS")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        si = QLabel("M OS වෙත සාදරයෙන් පිළිගනිමු")
        si.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(si)
        s = ui.subtitle("Your Computer. Your Experience. Your OS.\n\nLet's set up your desktop. "
                        "Every choice can be changed later in the M OS Control Center.")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(s)
        if self.live:
            row = QHBoxLayout()
            row.addStretch(1)
            inst = ui.primary_button(tr("Install M OS"))
            inst.setEnabled(bool(shutil.which("calamares-install-debian") or shutil.which("calamares")))
            inst.clicked.connect(self.start_installer)
            row.addWidget(inst)
            row.addStretch(1)
            lay.addLayout(row)
            note = ui.subtitle("You are trying M OS from the live medium. Nothing is written to your disks "
                               "unless you start the installer and confirm the changes.")
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(note)
        lay.addStretch(2)
        return w

    def page_layout(self) -> QWidget:
        w, lay = self._page(tr("Desktop layout"), "Choose how your desktop is organised.")
        lay.addWidget(ChoiceCards(
            [("modern", "M OS Modern\nTop bar and centered dock", PREVIEW_DIR.format("org.mos.modern.desktop")),
             ("classic", "M OS Classic\nTaskbar and start menu", PREVIEW_DIR.format("org.mos.classic.desktop"))],
            self.state["layout"], lambda k: self.apply(["layout", k], f"M OS {k.title()} layout applied.")))
        lay.addStretch(1)
        return w

    def page_theme(self) -> QWidget:
        w, lay = self._page(tr("Appearance"), "Pick a light or dark appearance and an accent colour.")
        lay.addWidget(ChoiceCards(
            [("dark", tr("Dark"), "weather-clear-night"), ("light", tr("Light"), "weather-clear")],
            self.state["theme"], lambda k: self.apply(["theme", k], f"{k.title()} appearance applied."),
            icon_size=QSize(64, 64)))
        row = QHBoxLayout()
        row.addWidget(QLabel("Accent colour"))
        for color in ("#6D5DF6", "#3B82F6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#EC4899"):
            b = QPushButton()
            b.setFixedSize(30, 30)
            b.setStyleSheet(f"background:{color}; border-radius:15px;")
            b.clicked.connect(lambda _=False, c=color: self.apply(["accent", c], "Accent colour updated."))
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    def page_performance(self) -> QWidget:
        rec = recommended_profile()
        mem = sysinfo.read_memory()
        w, lay = self._page(tr("Performance"),
                            f"This computer has {sysinfo.human_bytes(mem.total) if mem else 'unknown'} of memory. "
                            f"Recommended: M OS {rec.title()}.")
        lay.addWidget(ChoiceCards(
            [("balanced", "M OS Balanced\nFull visual effects", "speedometer"),
             ("performance", "M OS Performance\nLighter, for 4–8 GB RAM", "battery-profile-performance")],
            self.state["profile"], lambda k: self.apply(["profile", k], f"M OS {k.title()} profile applied."),
            icon_size=QSize(64, 64)))
        lay.addStretch(1)
        return w

    def page_privacy(self) -> QWidget:
        w, lay = self._page(tr("Privacy"), "M OS respects your privacy.")
        card = ui.Card()
        for line in ("• No telemetry: M OS does not collect or send usage data.",
                     "• The firewall blocks incoming connections by default.",
                     "• No remote-access services are enabled.",
                     "• Software comes from signed Debian repositories.",
                     "• Web browsing data is handled by Firefox's own privacy settings."):
            card.add(QLabel(line))
        lay.addWidget(card)
        lang = ui.Card()
        lang.add(ui.section("සිංහල / Sinhala"))
        lang.add(ui.subtitle("Sinhala fonts and input methods are installed. Press Ctrl+Space to switch "
                             "between English and Sinhala (Wijesekara or Singlish) typing."))
        b = QPushButton("Language settings")
        b.clicked.connect(lambda: kcm.open_kcm(kcm.first_available("kcm_regionandlang") or "kcm_regionandlang"))
        lang.add(b)
        lay.addWidget(lang)
        lay.addStretch(1)
        return w

    def page_finish(self) -> QWidget:
        w, lay = self._page("You're all set", "Here are some places to start.")
        grid = QHBoxLayout()
        for label, icon, cmd in (("Control Center", "mos-control-center", ["mos-control-center"]),
                                 ("App Store", "plasma-discover", ["plasma-discover"]),
                                 ("Updates", "mos-update-center", ["mos-update-center"]),
                                 ("Files", "system-file-manager", ["dolphin"])):
            b = QToolButton()
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setIcon(QIcon.fromTheme(icon))
            b.setIconSize(QSize(56, 56))
            b.setText(label)
            b.setMinimumWidth(130)
            b.setEnabled(bool(shutil.which(cmd[0])))
            b.clicked.connect(lambda _=False, c=cmd: kcm.launch(c))
            grid.addWidget(b)
        grid.addStretch(1)
        lay.addLayout(grid)
        tips = ui.Card()
        for tip in ("Meta key — open the application launcher",
                    "Meta + W — overview of windows and desktops",
                    "Meta + ← / → — snap a window to half of the screen",
                    "Ctrl + Alt + T — open a terminal (Konsole)",
                    "Print — take a screenshot"):
            tips.add(QLabel(tip))
        lay.addWidget(tips)
        docs = QPushButton("Read the M OS documentation")
        docs.clicked.connect(lambda: ui.open_url(DOCS_URL))
        lay.addWidget(docs, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------ actions
    def apply(self, args: list[str], done: str) -> None:
        self.feedback.setText("Applying…")
        self.repaint()
        ok, msg = run_desktopctl(args)
        self.feedback.setText(done if ok else f"Could not apply all settings: {msg}")

    def start_installer(self) -> None:
        for cmd in (["calamares-install-debian"], ["pkexec", "calamares"]):
            if shutil.which(cmd[0]):
                subprocess.Popen(cmd, start_new_session=True)
                return
        ui.error(self, "The installer is not available on this medium.")

    def go(self, delta: int) -> None:
        i = self.stack.currentIndex() + delta
        if i >= self.stack.count():
            self.finish()
            return
        self.stack.setCurrentIndex(max(0, i))
        self.feedback.setText("")
        self.update_nav()

    def update_nav(self) -> None:
        i = self.stack.currentIndex()
        self.back.setEnabled(i > 0)
        self.next.setText(tr("Finish") if i == self.stack.count() - 1 else
                          (tr("Get started") if i == 0 else tr("Next")))

    def finish(self) -> None:
        self.save_autostart()
        self.close()

    def save_autostart(self) -> None:
        flag = done_flag()
        if self.autostart.isChecked():
            flag.unlink(missing_ok=True)
        else:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("1\n")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.save_autostart()
        super().closeEvent(event)


def main() -> int:
    if "--autostart" in sys.argv and done_flag().exists():
        return 0
    app = ui.make_app("mos-welcome", "M OS Welcome", "mos-welcome")
    win = WelcomeWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
