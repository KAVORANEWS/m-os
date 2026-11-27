"""M OS Control Center — one place for every system setting.

M OS-specific settings (layout, theme, accent, performance profile, firewall,
power profile) are implemented natively and call real system tools. Hardware
and account settings open the maintained KDE System Settings modules, which
are only offered when the module is actually installed.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (QButtonGroup, QColorDialog, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout,
                             QWidget)

from . import desktopctl, kcm, sysinfo, ui
from .i18n import tr

FIREWALL_HELPER = "/usr/libexec/mos/mos-firewall-helper"


def run_desktopctl(args: list[str]) -> tuple[bool, str]:
    exe = shutil.which("mos-desktopctl")
    cmd = [exe, *args] if exe else [sys.executable, "-m", "mos.desktopctl", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


# ------------------------------------------------------------------ page base
class Page(QScrollArea):
    def __init__(self, name: str, description: str):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        self.setWidget(body)
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(28, 22, 28, 22)
        self.lay.setSpacing(14)
        self.lay.addWidget(ui.title(tr(name)))
        self.lay.addWidget(ui.subtitle(description))
        self._finished = False

    def card(self, heading: str | None = None) -> ui.Card:
        c = ui.Card()
        if heading:
            c.add(ui.section(heading))
        self.lay.addWidget(c)
        return c

    def kcm_buttons(self, heading: str, modules: list[tuple[str, tuple[str, ...]]]) -> None:
        c = self.card(heading)
        row = QHBoxLayout()
        row.setSpacing(8)
        count = 0
        for label, ids in modules:
            kcm_id = kcm.first_available(*ids)
            btn = QPushButton(label)
            if kcm_id:
                btn.clicked.connect(lambda _=False, k=kcm_id: kcm.open_kcm(k))
            else:
                btn.setEnabled(False)
                btn.setToolTip("This settings module is not installed on this system.")
            row.addWidget(btn)
            count += 1
            if count % 3 == 0:
                row.addStretch(1)
                c.layout_.addLayout(row)
                row = QHBoxLayout()
        row.addStretch(1)
        c.layout_.addLayout(row)

    def finish(self) -> None:
        if not self._finished:
            self.lay.addStretch(1)
            self._finished = True

    def refresh(self) -> None:
        """Re-read live state when the page is shown."""


def choice_row(options: list[tuple[str, str, str]], current: str, on_pick) -> QWidget:
    """A row of checkable cards; options are (key, label, icon)."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    group = QButtonGroup(w)
    group.setExclusive(True)
    for key, label, icon in options:
        b = QPushButton(QIcon.fromTheme(icon), label)
        b.setObjectName("Choice")
        b.setCheckable(True)
        b.setChecked(key == current)
        b.setIconSize(QSize(32, 32))
        b.setMinimumHeight(64)
        b.clicked.connect(lambda _=False, k=key: on_pick(k))
        group.addButton(b)
        lay.addWidget(b)
    w.group = group  # keep a reference
    return w


# ------------------------------------------------------------------ pages
class PersonalizationPage(Page):
    def __init__(self):
        super().__init__("Personalization", "Desktop layout, theme, accent colour and the performance profile.")
        state = desktopctl.current_status()
        self.feedback = ui.subtitle("")

        c = self.card(tr("Desktop layout"))
        c.add(choice_row([("modern", "M OS Modern — top bar and dock", "mos-logo"),
                          ("classic", "M OS Classic — taskbar and start menu", "start-here")],
                         state["layout"], self.set_layout))
        c.add(ui.subtitle("Switching layout rebuilds your panels. Custom panel widgets are replaced."))

        c = self.card(tr("Appearance"))
        c.add(choice_row([("dark", tr("Dark"), "weather-clear-night"),
                          ("light", tr("Light"), "weather-clear")], state["theme"], self.set_theme))
        accents = QHBoxLayout()
        accents.addWidget(QLabel("Accent colour"))
        for color in ("#6D5DF6", "#3B82F6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#EC4899"):
            b = QPushButton()
            b.setFixedSize(28, 28)
            b.setToolTip(color)
            b.setStyleSheet(f"background:{color}; border-radius:14px; border:2px solid rgba(255,255,255,0.35);")
            b.clicked.connect(lambda _=False, col=color: self.set_accent(col))
            accents.addWidget(b)
        custom = QPushButton("Custom…")
        custom.clicked.connect(self.pick_accent)
        reset = QPushButton("Reset")
        reset.clicked.connect(lambda: self.set_accent("reset"))
        accents.addWidget(custom)
        accents.addWidget(reset)
        accents.addStretch(1)
        c.layout_.addLayout(accents)

        c = self.card(tr("Performance"))
        c.add(choice_row([("balanced", "M OS Balanced — full visual experience", "speedometer"),
                          ("performance", "M OS Performance — for 4–8 GB computers", "battery-profile-performance")],
                         state["profile"], self.set_profile))
        c.add(ui.subtitle("Performance reduces animations, disables blur/transparency effects and file "
                          "indexing, and stops the background update notifier."))
        self.lay.addWidget(self.feedback)
        self.kcm_buttons("More appearance settings", [
            ("Global theme", ("kcm_lookandfeel",)), ("Colours", ("kcm_colors",)),
            ("Fonts", ("kcm_fonts",)), ("Icons", ("kcm_icons",)),
            ("Wallpaper", ("kcm_wallpaper",)), ("Window decorations", ("kcm_kwindecoration",))])
        self.finish()

    def _apply(self, args: list[str], done: str) -> None:
        self.feedback.setText("Applying…")
        self.repaint()
        ok, msg = run_desktopctl(args)
        self.feedback.setText(done if ok else f"Some settings could not be applied: {msg}")

    def set_layout(self, key: str) -> None:
        self._apply(["layout", key], f"Layout changed to M OS {key.title()}.")

    def set_theme(self, key: str) -> None:
        self._apply(["theme", key], f"{key.title()} theme applied.")

    def set_accent(self, color: str) -> None:
        self._apply(["accent", color], "Accent colour updated." if color != "reset" else "Accent colour reset.")

    def pick_accent(self) -> None:
        col = QColorDialog.getColor(QColor(ui.ACCENT), self, "Accent colour")
        if col.isValid():
            self.set_accent(col.name())

    def set_profile(self, key: str) -> None:
        self._apply(["profile", key], f"M OS {key.title()} profile applied.")


class SecurityPage(Page):
    def __init__(self):
        super().__init__("Security", "Firewall, application confinement, screen locking and updates.")
        self.fw = self.card("Firewall")
        self.fw_state = QLabel("Checking…")
        self.fw.add(self.fw_state)
        row = QHBoxLayout()
        self.fw_on = ui.primary_button("Turn on")
        self.fw_off = QPushButton("Turn off")
        self.fw_on.clicked.connect(lambda: self.firewall("enable"))
        self.fw_off.clicked.connect(lambda: self.firewall("disable"))
        row.addWidget(self.fw_on)
        row.addWidget(self.fw_off)
        row.addStretch(1)
        self.fw.layout_.addLayout(row)
        self.fw.add(ui.subtitle("When on, M OS blocks unsolicited incoming connections and allows "
                                "outgoing traffic. Administrator authentication is required to change it."))

        self.aa = self.card("AppArmor")
        self.aa_state = QLabel("")
        self.aa.add(self.aa_state)

        c = self.card("Privacy")
        c.add(ui.subtitle("M OS contains no telemetry and sends no usage data. Remote access services "
                          "(such as SSH) are not installed or enabled by default."))
        self.kcm_buttons("More security settings", [
            ("Firewall rules", ("kcm_firewall",)), ("Screen locking", ("kcm_screenlocker",)),
            ("Password & account", ("kcm_users",)), ("Wallet", ("kwalletconfig5", "kcm_kwallet5", "kcm_kwallet")),
            ("Application permissions", ("kcm_app-permissions",))])
        self.finish()
        self.refresh()

    def refresh(self) -> None:
        enabled = None
        try:
            with open("/etc/ufw/ufw.conf", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip().startswith("ENABLED="):
                        enabled = line.strip().split("=", 1)[1].strip().lower() == "yes"
        except OSError:
            pass
        if enabled is None:
            self.fw_state.setText("Firewall (ufw) is not installed.")
            self.fw_on.setEnabled(False)
            self.fw_off.setEnabled(False)
        else:
            self.fw_state.setText("Status: ON — incoming connections are blocked" if enabled
                                  else "Status: OFF — the computer is not protected by the firewall")
            self.fw_on.setEnabled(not enabled)
            self.fw_off.setEnabled(enabled)
        aa = ""
        try:
            with open("/sys/module/apparmor/parameters/enabled", encoding="utf-8") as fh:
                aa = fh.read().strip()
        except OSError:
            pass
        profiles = 0
        try:
            with open("/sys/kernel/security/apparmor/profiles", encoding="utf-8") as fh:
                profiles = sum(1 for _ in fh)
        except OSError:
            profiles = -1
        if aa == "Y":
            self.aa_state.setText("AppArmor is active" + (f" with {profiles} loaded profiles." if profiles >= 0
                                                          else " (profile count requires administrator rights)."))
        else:
            self.aa_state.setText("AppArmor is not active in this kernel session.")

    def firewall(self, verb: str) -> None:
        if not shutil.which("pkexec"):
            ui.error(self, "pkexec is not installed.")
            return
        proc = subprocess.run(["pkexec", FIREWALL_HELPER, verb], capture_output=True, text=True, check=False)
        if proc.returncode not in (0, 126, 127):
            ui.error(self, "Could not change the firewall setting.", proc.stderr or proc.stdout)
        self.refresh()


class PowerPage(Page):
    def __init__(self):
        super().__init__("Power", "Power profile, sleep and screen energy saving.")
        self.c = self.card("Power profile")
        self.state = QLabel("")
        self.c.add(self.state)
        self.row = QHBoxLayout()
        self.c.layout_.addLayout(self.row)
        self.kcm_buttons("More power settings", [("Energy saving", ("kcm_powerdevilprofilesconfig",)),
                                                 ("Battery & brightness", ("kcm_powerdevilglobalconfig",))])
        self.finish()
        self.refresh()

    def refresh(self) -> None:
        while self.row.count():
            item = self.row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not shutil.which("powerprofilesctl"):
            self.state.setText("power-profiles-daemon is not installed.")
            return
        cur = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, check=False)
        lst = subprocess.run(["powerprofilesctl", "list"], capture_output=True, text=True, check=False)
        if cur.returncode != 0:
            self.state.setText("The power profile service is not running.")
            return
        current = cur.stdout.strip()
        self.state.setText(f"Current profile: {current}")
        names = [ln.strip().lstrip("* ").rstrip(":") for ln in lst.stdout.splitlines()
                 if ln.strip().endswith(":")]
        for name in names:
            b = QPushButton(name.replace("-", " ").title())
            b.setCheckable(True)
            b.setChecked(name == current)
            b.clicked.connect(lambda _=False, n=name: self.set_profile(n))
            self.row.addWidget(b)
        self.row.addStretch(1)

    def set_profile(self, name: str) -> None:
        proc = subprocess.run(["powerprofilesctl", "set", name], capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            ui.error(self, f"Could not switch to the {name} profile.", proc.stderr)
        self.refresh()


class StoragePage(Page):
    def __init__(self):
        super().__init__("Storage", "Disk usage, drives and partitions.")
        self.c = self.card("Mounted drives")
        self.rows = QVBoxLayout()
        self.c.layout_.addLayout(self.rows)
        tools = self.card("Tools")
        row = QHBoxLayout()
        for label, cmd in (("Disk usage analyser", ["filelight"]), ("Partition manager", ["partitionmanager"]),
                           ("File manager", ["dolphin"])):
            b = QPushButton(label)
            b.setEnabled(bool(shutil.which(cmd[0])))
            b.clicked.connect(lambda _=False, c=cmd: kcm.launch(c))
            row.addWidget(b)
        row.addStretch(1)
        tools.layout_.addLayout(row)
        tools.add(ui.subtitle("Partition changes can destroy data. Back up important files first."))
        self.finish()
        self.refresh()

    def refresh(self) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for m in sysinfo.read_mount_usage():
            text = f"{m.mountpoint} — {sysinfo.human_bytes(m.free)} free of {sysinfo.human_bytes(m.total)} ({m.fstype})"
            self.rows.addWidget(QLabel(text))
            self.rows.addWidget(ui.usage_bar(m.percent, text))


class LanguagePage(Page):
    def __init__(self):
        super().__init__("Language", "System language, formats and keyboard input (English and Sinhala).")
        c = self.card("Current language")
        c.add(ui.key_value_row("LANG", os.environ.get("LANG", "not set")))
        locales = subprocess.run(["locale", "-a"], capture_output=True, text=True, check=False).stdout.split()
        c.add(ui.key_value_row("Installed locales", ", ".join(l for l in locales if "utf8" in l.lower()) or "—"))
        c = self.card("Typing in Sinhala — සිංහලෙන් ලිවීම")
        c.add(ui.subtitle("M OS includes the Wijesekara and Singlish (phonetic) Sinhala input methods through "
                          "Fcitx 5. Press Ctrl+Space to switch between English and Sinhala, or use the "
                          "keyboard icon in the system tray."))
        self.kcm_buttons("Language settings", [("Region & language", ("kcm_regionandlang",)),
                                               ("Input methods", ("kcm_fcitx5",)),
                                               ("Keyboard layouts", ("kcm_keyboard",))])
        self.finish()


class DateTimePage(Page):
    def __init__(self):
        super().__init__("Date and time", "Clock, time zone and network time synchronisation.")
        self.c = self.card("Status")
        self.rows = QVBoxLayout()
        self.c.layout_.addLayout(self.rows)
        self.kcm_buttons("Settings", [("Date & time", ("kcm_clock",)), ("Formats", ("kcm_regionandlang",))])
        self.finish()
        self.refresh()

    def refresh(self) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        info = {}
        if shutil.which("timedatectl"):
            out = subprocess.run(["timedatectl", "show"], capture_output=True, text=True, check=False).stdout
            info = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
        self.rows.addWidget(ui.key_value_row("Local time", time.strftime("%A %d %B %Y, %H:%M")))
        self.rows.addWidget(ui.key_value_row("Time zone", info.get("Timezone", time.tzname[0])))
        self.rows.addWidget(ui.key_value_row("Network time", "synchronised" if info.get("NTPSynchronized") == "yes"
                                             else ("enabled" if info.get("NTP") == "yes" else "not active")))


class UsersPage(Page):
    def __init__(self):
        super().__init__("Users", "Accounts, passwords and administrator rights.")
        import grp
        import pwd
        me = pwd.getpwuid(os.getuid())
        groups = [g.gr_name for g in grp.getgrall() if me.pw_name in g.gr_mem]
        c = self.card("Your account")
        c.add(ui.key_value_row("Name", me.pw_gecos.split(",")[0] or me.pw_name))
        c.add(ui.key_value_row("Username", me.pw_name))
        c.add(ui.key_value_row("Administrator", "yes (sudo group)" if "sudo" in groups else "no"))
        c.add(ui.subtitle("M OS uses a standard (non-root) account for everyday work; administrator actions "
                          "ask for your password."))
        self.kcm_buttons("Account settings", [("Users", ("kcm_users",))])
        self.finish()


class LauncherPage(Page):
    """Page that summarises a hardware area and opens the KDE modules for it."""

    def __init__(self, name: str, description: str, modules: list[tuple[str, tuple[str, ...]]], info=None):
        super().__init__(name, description)
        if info:
            c = self.card("Status")
            for k, v in info():
                c.add(ui.key_value_row(k, v))
        self.kcm_buttons("Settings", modules)
        self.finish()


def network_info():
    rows = []
    if shutil.which("nmcli"):
        out = subprocess.run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
                             capture_output=True, text=True, check=False).stdout
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[1] not in ("loopback",):
                rows.append((parts[0], f"{parts[1]} — {parts[2]}{' (' + parts[3] + ')' if parts[3] else ''}"))
    return rows or [("Network", "NetworkManager is not available")]


def display_info():
    from PyQt6.QtGui import QGuiApplication
    return [(s.name() or "Screen", f"{s.size().width()}×{s.size().height()} @ {s.refreshRate():.0f} Hz, "
             f"scale {s.devicePixelRatio():g}") for s in QGuiApplication.screens()]


def bluetooth_info():
    import glob
    adapters = glob.glob("/sys/class/bluetooth/hci*")
    return [("Adapters", str(len(adapters)) if adapters else "No Bluetooth adapter detected")]


class AboutPage(Page):
    def __init__(self):
        super().__init__("About M OS", "Version and hardware information.")
        osr = sysinfo.read_os_release()
        c = self.card()
        c.add(ui.key_value_row("System", osr.get("PRETTY_NAME", "M OS")))
        c.add(ui.key_value_row("Kernel", sysinfo.kernel_version()))
        cpu = sysinfo.read_cpuinfo()
        c.add(ui.key_value_row("Processor", cpu.model))
        mem = sysinfo.read_memory()
        c.add(ui.key_value_row("Memory", sysinfo.human_bytes(mem.total) if mem else "unknown"))
        b = ui.primary_button("Open M OS About")
        b.clicked.connect(lambda: kcm.launch(["mos-about"]))
        self.lay.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        self.finish()


class UpdatesPage(Page):
    def __init__(self):
        super().__init__("Updates", "Security and software updates from the official Debian repositories.")
        c = self.card()
        c.add(ui.subtitle("Updates come from signed Debian repositories (trixie, trixie-updates, "
                          "trixie-security). Applications can also be managed in Discover."))
        row = QHBoxLayout()
        b = ui.primary_button("Open Update Center")
        b.clicked.connect(lambda: kcm.launch(["mos-update-center"]))
        d = QPushButton("Open Discover")
        d.setEnabled(bool(shutil.which("plasma-discover")))
        d.clicked.connect(lambda: kcm.launch(["plasma-discover"]))
        row.addWidget(b)
        row.addWidget(d)
        row.addStretch(1)
        c.layout_.addLayout(row)
        self.finish()


# ------------------------------------------------------------------ window
SECTIONS = [
    ("Personalization", "preferences-desktop-theme", PersonalizationPage),
    ("Display", "preferences-desktop-display", lambda: LauncherPage(
        "Display", "Resolution, scaling, multiple monitors and night light.",
        [("Displays", ("kcm_kscreen",)), ("Night light", ("kcm_nightlight", "kcm_nightcolor"))], display_info)),
    ("Sound", "preferences-desktop-sound", lambda: LauncherPage(
        "Sound", "Output and input devices and volume.", [("Audio devices", ("kcm_pulseaudio",)),
                                                          ("Notifications", ("kcm_notifications",))])),
    ("Network", "preferences-system-network", lambda: LauncherPage(
        "Network", "Wi-Fi, Ethernet, VPN and proxy.", [("Connections", ("kcm_networkmanagement",)),
                                                       ("Proxy", ("kcm_proxy",))], network_info)),
    ("Bluetooth", "preferences-system-bluetooth", lambda: LauncherPage(
        "Bluetooth", "Pair and manage Bluetooth devices.", [("Bluetooth devices", ("kcm_bluetooth",))],
        bluetooth_info)),
    ("Keyboard", "preferences-desktop-keyboard", lambda: LauncherPage(
        "Keyboard", "Layouts, repeat rate and shortcuts.", [("Keyboard", ("kcm_keyboard",)),
                                                            ("Shortcuts", ("kcm_keys",))])),
    ("Mouse", "preferences-desktop-mouse", lambda: LauncherPage(
        "Mouse", "Pointer speed, buttons and touchpad.", [("Mouse", ("kcm_mouse",)),
                                                          ("Touchpad", ("kcm_touchpad",))])),
    ("Language", "preferences-desktop-locale", LanguagePage),
    ("Date and time", "preferences-system-time", DateTimePage),
    ("Users", "system-users", UsersPage),
    ("Privacy", "preferences-system-privacy", lambda: LauncherPage(
        "Privacy", "Recent files history, file search indexing and location data. M OS has no telemetry.",
        [("Recent files", ("kcm_recentFiles",)), ("File search", ("kcm_baloofile",)),
         ("Application permissions", ("kcm_app-permissions",))])),
    ("Security", "security-high", SecurityPage),
    ("Updates", "system-software-update", UpdatesPage),
    ("Storage", "drive-harddisk", StoragePage),
    ("Power", "preferences-system-power-management", PowerPage),
    ("Accessibility", "preferences-desktop-accessibility", lambda: LauncherPage(
        "Accessibility", "High contrast, larger text, reduced motion and screen reader.",
        [("Accessibility", ("kcm_access",)), ("Fonts & text size", ("kcm_fonts",)),
         ("Animation speed", ("kcm_workspace",))])),
    ("About M OS", "mos-about", AboutPage),
]


class ControlCenter(QWidget):
    def __init__(self, initial: str | None = None):
        super().__init__()
        self.setWindowTitle("M OS Control Center")
        self.resize(1040, 700)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setIconSize(QSize(22, 22))
        self.stack = QStackedWidget()
        self.factories = {}
        for name, icon, factory in SECTIONS:
            item = QListWidgetItem(QIcon.fromTheme(icon), tr(name), self.sidebar)
            item.setSizeHint(QSize(0, 38))
            placeholder = QWidget()
            self.stack.addWidget(placeholder)
            self.factories[self.stack.count() - 1] = factory
        lay.addWidget(self.sidebar)
        lay.addWidget(self.stack, 1)
        self.sidebar.currentRowChanged.connect(self.show_page)
        names = [s[0].lower() for s in SECTIONS]
        start = names.index(initial.lower()) if initial and initial.lower() in names else 0
        self.sidebar.setCurrentRow(start)

    def show_page(self, index: int) -> None:
        if index in self.factories:  # build pages lazily
            page = self.factories.pop(index)()
            old = self.stack.widget(index)
            self.stack.insertWidget(index, page)
            self.stack.removeWidget(old)
            old.deleteLater()
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if isinstance(page, Page):
            page.refresh()


def main() -> int:
    app = ui.make_app("mos-control-center", "M OS Control Center", "mos-control-center")
    initial = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    win = ControlCenter(initial)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
