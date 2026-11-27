"""mos-desktopctl — apply M OS desktop layouts, themes and performance profiles.

All operations use supported KDE Plasma tools (plasma-apply-lookandfeel,
plasma-apply-colorscheme, kwriteconfig6, balooctl6, D-Bus) and act on the
current user's configuration only — no root privileges are involved.

    mos-desktopctl layout  modern|classic
    mos-desktopctl theme   dark|light
    mos-desktopctl accent  '#RRGGBB'|reset
    mos-desktopctl profile balanced|performance
    mos-desktopctl status
    mos-desktopctl --dry-run ...   (print the commands instead of running them)

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LAYOUTS = {"modern": "org.mos.modern.desktop", "classic": "org.mos.classic.desktop"}
THEMES = {"dark": ("MOSDark", "Papirus-Dark"), "light": ("MOSLight", "Papirus-Light")}
PROFILES = ("balanced", "performance")
# kwin effects reduced by the Performance profile
HEAVY_EFFECTS = ("blur", "contrast", "translucency", "wobblywindows", "magiclamp",
                 "sheet", "fallapart", "glide")
BUTTONS = {"modern": ("XIA", ""), "classic": ("", "IAX")}
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def state_file() -> Path:
    return config_home() / "mos" / "desktop.json"


def load_state() -> dict:
    try:
        return json.loads(state_file().read_text())
    except (OSError, ValueError):
        return {}


def save_state(update: dict) -> None:
    state = load_state()
    state.update(update)
    path = state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def kwrite(file: str, group: str | list[str], key: str, value: str | None) -> list[str]:
    cmd = ["kwriteconfig6", "--file", file]
    for g in ([group] if isinstance(group, str) else group):
        cmd += ["--group", g]
    cmd += ["--key", key]
    if value is None:
        cmd.append("--delete")
    else:
        cmd += ["--type", "bool", value] if value in ("true", "false") else [value]
    return cmd


def kwin_reconfigure() -> list[str]:
    return ["dbus-send", "--session", "--type=method_call", "--dest=org.kde.KWin",
            "/KWin", "org.kde.KWin.reconfigure"]


def find_changeicons() -> str:
    hits = glob.glob("/usr/lib/*/libexec/plasma-changeicons") + glob.glob("/usr/libexec/plasma-changeicons")
    return hits[0] if hits else "plasma-changeicons"


# ---------------------------------------------------------------- command plans
def plan_theme(theme: str) -> list[list[str]]:
    scheme, icons = THEMES[theme]
    return [["plasma-apply-colorscheme", scheme], [find_changeicons(), icons]]


def plan_layout(layout: str, theme: str | None = None) -> list[list[str]]:
    left, right = BUTTONS[layout]
    cmds = [
        ["plasma-apply-lookandfeel", "--apply", LAYOUTS[layout], "--resetLayout"],
        kwrite("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft", left),
        kwrite("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight", right),
        kwrite("ksplashrc", "KSplash", "Theme", LAYOUTS[layout]),
        kwin_reconfigure(),
    ]
    if theme:  # look-and-feel resets the color scheme; restore the user's choice
        cmds += plan_theme(theme)
    return cmds


def plan_accent(color: str) -> list[list[str]]:
    if color == "reset":
        state = load_state()
        scheme = THEMES.get(state.get("theme", "dark"), THEMES["dark"])[0]
        return [kwrite("kdeglobals", "General", "AccentColor", None),
                kwrite("kdeglobals", "General", "LastUsedCustomAccentColor", None),
                ["plasma-apply-colorscheme", scheme]]
    if not HEX_COLOR.match(color):
        raise ValueError(f"invalid colour {color!r}; expected #RRGGBB")
    return [["plasma-apply-colorscheme", "--accent-color", color]]


def plan_profile(profile: str) -> list[list[str]]:
    perf = profile == "performance"
    cmds = [kwrite("kdeglobals", "KDE", "AnimationDurationFactor", "0.5" if perf else None)]
    for effect in HEAVY_EFFECTS:
        cmds.append(kwrite("kwinrc", "Plugins", f"{effect}Enabled", "false" if perf else None))
    cmds.append(kwrite("baloofilerc", "Basic Settings", "Indexing-Enabled", "false" if perf else "true"))
    cmds.append(["balooctl6", "disable" if perf else "enable"])
    cmds.append(kwrite("plasmarc", "PlasmaToolTips", "Delay", "1200" if perf else None))
    cmds.append(kwin_reconfigure())
    return cmds


def discover_notifier_override(profile: str, dry_run: bool) -> str:
    """Hide/show the Discover update notifier autostart for the Performance profile."""
    path = config_home() / "autostart" / "org.kde.discover.notifier.desktop"
    if dry_run:
        return f"# {'write' if profile == 'performance' else 'remove'} {path}"
    if profile == "performance":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[Desktop Entry]\nType=Application\nName=Discover Notifier\nHidden=true\n")
    elif path.exists():
        path.unlink()
    return str(path)


# ---------------------------------------------------------------- execution
def run_plan(cmds: list[list[str]], dry_run: bool = False) -> int:
    failures = 0
    for cmd in cmds:
        if dry_run:
            print(" ".join(cmd))
            continue
        if not shutil.which(cmd[0]):
            print(f"warning: {cmd[0]} is not installed; skipped", file=sys.stderr)
            failures += 1
            continue
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(f"warning: {' '.join(cmd)} failed: {proc.stderr.strip()}", file=sys.stderr)
            failures += 1
    return failures


def current_status() -> dict:
    state = load_state()
    status = {
        "layout": state.get("layout", "modern"),
        "theme": state.get("theme", "dark"),
        "accent": state.get("accent", "default"),
        "profile": state.get("profile", "balanced"),
    }
    if shutil.which("kreadconfig6"):
        out = subprocess.run(["kreadconfig6", "--file", "kdeglobals", "--group", "General",
                              "--key", "ColorScheme"], capture_output=True, text=True, check=False)
        if out.stdout.strip():
            status["color_scheme"] = out.stdout.strip()
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mos-desktopctl", description="Configure the M OS desktop.")
    parser.add_argument("--dry-run", action="store_true", help="print commands without running them")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("layout").add_argument("name", choices=sorted(LAYOUTS))
    sub.add_parser("theme").add_argument("name", choices=sorted(THEMES))
    sub.add_parser("accent").add_argument("color", help="#RRGGBB or 'reset'")
    sub.add_parser("profile").add_argument("name", choices=PROFILES)
    sub.add_parser("status")
    args = parser.parse_args(argv)

    if args.command == "status":
        print(json.dumps(current_status(), indent=2))
        return 0
    if args.command == "layout":
        rc = run_plan(plan_layout(args.name, load_state().get("theme")), args.dry_run)
        update = {"layout": args.name}
    elif args.command == "theme":
        rc = run_plan(plan_theme(args.name), args.dry_run)
        update = {"theme": args.name}
    elif args.command == "accent":
        try:
            plan = plan_accent(args.color)
        except ValueError as exc:
            parser.error(str(exc))
        rc = run_plan(plan, args.dry_run)
        update = {"accent": "default" if args.color == "reset" else args.color}
    else:
        rc = run_plan(plan_profile(args.name), args.dry_run)
        print(discover_notifier_override(args.name, args.dry_run)) if args.dry_run else \
            discover_notifier_override(args.name, False)
        update = {"profile": args.name}
    if not args.dry_run:
        save_state(update)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
