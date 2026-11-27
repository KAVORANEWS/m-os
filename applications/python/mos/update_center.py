"""M OS Update Center — check for and install Debian package updates.

Uses the real APT system through a fixed-verb helper run with pkexec
(/usr/libexec/mos/mos-update-helper), streaming APT's machine-readable
progress into the UI.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPlainTextEdit,
                             QProgressBar, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from . import aptparse, sysinfo, ui
from .i18n import tr

HELPER = "/usr/libexec/mos/mos-update-helper"
LISTS_DIR = "/var/lib/apt/lists"


def last_refresh_text() -> str:
    try:
        ts = max(os.path.getmtime(os.path.join(LISTS_DIR, f)) for f in os.listdir(LISTS_DIR)
                 if f.endswith("Packages") or f.endswith("InRelease"))
    except (OSError, ValueError):
        return "never"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def read_upgradable() -> list[aptparse.Upgrade]:
    out = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True,
                         env={**os.environ, "LC_ALL": "C.UTF-8"}, check=False)
    return aptparse.parse_upgradable(out.stdout)


class UpdateWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("M OS Update Center")
        self.resize(820, 640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        lay.addWidget(ui.title(tr("Updates")))
        self.status = ui.subtitle("")
        lay.addWidget(self.status)

        actions = QHBoxLayout()
        self.check_btn = QPushButton(tr("Check for updates"))
        self.check_btn.clicked.connect(self.check)
        self.install_btn = ui.primary_button(tr("Install updates"))
        self.install_btn.clicked.connect(self.install)
        self.install_btn.setEnabled(False)
        actions.addWidget(self.check_btn)
        actions.addStretch(1)
        actions.addWidget(self.install_btn)
        lay.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.phase = QLabel("")
        self.phase.setVisible(False)
        lay.addWidget(self.phase)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Package", "Installed", "Available", "Source"])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.tree, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Noto Sans Mono", 9))
        self.log.setMaximumHeight(150)
        self.log.setVisible(False)
        self.log_toggle = QPushButton("Show details")
        self.log_toggle.setCheckable(True)
        self.log_toggle.toggled.connect(self.log.setVisible)
        self.log_toggle.toggled.connect(
            lambda on: self.log_toggle.setText("Hide details" if on else "Show details"))
        lay.addWidget(self.log_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.log)

        self.proc: QProcess | None = None
        self.mode = ""
        self.reboot_needed = False
        self.buffer = ""
        if sysinfo.is_live_session():
            self.status.setText("You are running the live session. Updates installed now are lost "
                                "when the computer restarts.")
        self.populate()

    # ------------------------------------------------------------- list
    def populate(self) -> None:
        upgrades = read_upgradable()
        self.tree.clear()
        security = 0
        for u in upgrades:
            item = QTreeWidgetItem([u.name, u.old_version, u.new_version,
                                    "Security update" if u.is_security else ", ".join(u.suites)])
            if u.is_security:
                security += 1
                f = item.font(3)
                f.setBold(True)
                item.setFont(3, f)
            self.tree.addTopLevelItem(item)
        self.install_btn.setEnabled(bool(upgrades) and self.proc is None)
        base = f"Last checked: {last_refresh_text()}. "
        if upgrades:
            text = f"{len(upgrades)} update(s) available"
            if security:
                text += f", including {security} security update(s)"
            self.status.setText(base + text + ".")
        else:
            self.status.setText(base + tr("Your system is up to date."))
        if os.path.exists("/var/run/reboot-required"):
            self.status.setText(self.status.text() + " " + tr("Restart required") + ".")

    # ------------------------------------------------------------- helper process
    def run_helper(self, verb: str) -> None:
        if not shutil.which("pkexec") or not os.path.exists(HELPER):
            ui.error(self, "The update helper is not installed.",
                     f"Expected pkexec and {HELPER}.")
            return
        self.mode = verb
        self.buffer = ""
        self.check_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.phase.setVisible(True)
        self.phase.setText("Waiting for authorisation…")
        self.log.appendPlainText(f"$ pkexec {HELPER} {verb}")
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.on_output)
        self.proc.finished.connect(self.on_finished)
        if verb == "refresh":
            self.progress.setRange(0, 0)  # apt-get update has no reliable percentage
        else:
            self.progress.setRange(0, 1000)
        self.proc.start("pkexec", [HELPER, verb])

    def on_output(self) -> None:
        self.buffer += bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        *lines, self.buffer = self.buffer.split("\n")
        for line in lines:
            status = aptparse.parse_status_line(line)
            if status:
                if status.kind in ("download", "install"):
                    self.progress.setValue(int(aptparse.overall_percent(status) * 10))
                    self.phase.setText(status.message)
                elif status.kind == "error":
                    self.log.appendPlainText(f"ERROR {status.package}: {status.message}")
                continue
            if line.strip() == "mos:reboot-required":
                self.reboot_needed = True
                continue
            if line.strip():
                self.log.appendPlainText(line)
                if self.mode == "refresh":
                    self.phase.setText(line.strip()[:120])

    def on_finished(self, code: int, _status) -> None:
        self.progress.setRange(0, 1000)
        self.progress.setVisible(False)
        self.phase.setVisible(False)
        self.check_btn.setEnabled(True)
        self.proc = None
        if code in (126, 127):  # pkexec: dismissed / not authorised
            self.log.appendPlainText("Authorisation was cancelled.")
        elif code != 0:
            self.log_toggle.setChecked(True)
            ui.error(self, "The update operation failed." if self.mode == "upgrade"
                     else "Checking for updates failed. Check your internet connection.",
                     self.log.toPlainText()[-4000:])
        elif self.mode == "upgrade":
            msg = "Updates were installed successfully."
            if self.reboot_needed or os.path.exists("/var/run/reboot-required"):
                msg += "\n\nRestart the computer to finish applying the updates."
                if QMessageBox.question(self, tr("Restart required"), msg + "\n\nRestart now?") \
                        == QMessageBox.StandardButton.Yes:
                    subprocess.Popen(["systemctl", "reboot"])
            else:
                QMessageBox.information(self, "M OS Update Center", msg)
        self.populate()

    def check(self) -> None:
        self.run_helper("refresh")

    def install(self) -> None:
        count = self.tree.topLevelItemCount()
        if QMessageBox.question(self, tr("Install updates"),
                                f"Download and install {count} update(s)? Keep the computer "
                                "powered on until the installation finishes.") \
                == QMessageBox.StandardButton.Yes:
            self.run_helper("upgrade")


def main() -> int:
    app = ui.make_app("mos-update-center", "M OS Update Center", "mos-update-center")
    win = UpdateWindow()
    win.show()
    if "--check" in sys.argv:
        win.check()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
