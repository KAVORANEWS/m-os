"""M OS About — system identity and hardware summary.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import QT_VERSION_STR, Qt
from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from . import DOCS_URL, ISSUES_URL, PROJECT_URL, sysinfo, ui
from .i18n import tr


def collect() -> list[tuple[str, str]]:
    osr = sysinfo.read_os_release()
    build = sysinfo.read_build_info()
    cpu = sysinfo.read_cpuinfo()
    mem = sysinfo.read_memory()
    gpus = sysinfo.read_graphics()
    disks = sysinfo.read_block_devices()
    cpu_text = f"{cpu.model} — {cpu.cores} cores / {cpu.threads} threads"
    if cpu.max_mhz:
        cpu_text += f" @ {cpu.max_mhz / 1000:.2f} GHz"
    rows = [
        ("Operating system", osr.get("PRETTY_NAME", "M OS")),
        ("Version", osr.get("VERSION", osr.get("VERSION_ID", "unknown"))),
        ("Build", " · ".join(x for x in (build.get("BUILD_ID"), build.get("BUILD_DATE"),
                                          build.get("GIT_COMMIT", "")[:12]) if x) or "development build"),
        ("Based on", "Debian " + osr.get("DEBIAN_VERSION_FULL", osr.get("VERSION_CODENAME", "13"))),
        ("Kernel", sysinfo.kernel_version()),
        ("Desktop", f"KDE Plasma {sysinfo.plasma_version() or 'not detected'}"),
        ("KDE Frameworks", sysinfo.kde_frameworks_version() or "not detected"),
        ("Qt", QT_VERSION_STR),
        ("Processor", cpu_text),
        ("Memory", sysinfo.human_bytes(mem.total) if mem else "unknown"),
        ("Graphics", "\n".join(gpus) if gpus else "not detected"),
        ("Storage", "\n".join(
            f"{d.name}: {sysinfo.human_bytes(d.size, binary=False)} {d.model} "
            f"({'HDD' if d.rotational else 'SSD/flash'}{', ' + d.transport.upper() if d.transport else ''})"
            for d in disks) or "not detected"),
        ("Session", "Live session (not installed)" if sysinfo.is_live_session() else "Installed system"),
    ]
    return rows


class AboutWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("About M OS"))
        self.resize(640, 720)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        logo = QLabel()
        logo.setPixmap(QIcon.fromTheme("mos-logo").pixmap(112, 112))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        name = ui.title("M OS")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name)
        slogan = ui.subtitle(tr("Your Computer. Your Experience. Your OS."))
        slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(slogan)

        self.rows = collect()
        card = ui.Card(spacing=2)
        for key, value in self.rows:
            card.add(ui.key_value_row(key, value))
        lay.addWidget(card)

        lic = ui.Card()
        lic.add(ui.section("License"))
        lic.add(ui.subtitle(
            "M OS is free software built on Debian GNU/Linux and KDE Plasma. M OS's own code is "
            "licensed under GPL-3.0-or-later and its artwork under CC-BY-SA-4.0. Each bundled "
            "package keeps its own license — see /usr/share/doc/<package>/copyright."))
        lay.addWidget(lic)

        buttons = QHBoxLayout()
        for text, url in (("Website", PROJECT_URL), ("Documentation", DOCS_URL), ("Report a problem", ISSUES_URL)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, u=url: ui.open_url(u))
            buttons.addWidget(b)
        copy = ui.primary_button("Copy details")
        copy.clicked.connect(self.copy_details)
        buttons.addStretch(1)
        buttons.addWidget(copy)
        lay.addLayout(buttons)
        lay.addStretch(1)

    def copy_details(self) -> None:
        QGuiApplication.clipboard().setText("\n".join(f"{k}: {v}" for k, v in self.rows))


def main() -> int:
    app = ui.make_app("mos-about", "About M OS", "mos-about")
    win = AboutWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
