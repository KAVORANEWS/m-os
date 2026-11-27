"""Locate and launch KDE System Settings modules (KCMs).

The M OS Control Center delegates advanced settings to the maintained KDE
modules instead of re-implementing them; a module is only offered when its
plugin is actually installed.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import glob
import shutil
import subprocess

_PLUGIN_GLOBS = (
    "/usr/lib/*/qt6/plugins/plasma/kcms/systemsettings/{id}.so",
    "/usr/lib/*/qt6/plugins/plasma/kcms/systemsettings_qwidgets/{id}.so",
    "/usr/lib/*/qt6/plugins/plasma/kcms/{id}.so",
    "/usr/lib/qt6/plugins/plasma/kcms/systemsettings/{id}.so",
    "/usr/lib/qt6/plugins/plasma/kcms/systemsettings_qwidgets/{id}.so",
)


def kcm_available(kcm_id: str) -> bool:
    return any(glob.glob(p.format(id=kcm_id)) for p in _PLUGIN_GLOBS)


def first_available(*kcm_ids: str) -> str | None:
    for kcm_id in kcm_ids:
        if kcm_available(kcm_id):
            return kcm_id
    return None


def open_kcm(kcm_id: str) -> bool:
    """Open a KCM in its own window. Returns False if it cannot be launched."""
    for launcher in (["kcmshell6", kcm_id], ["systemsettings", kcm_id]):
        if shutil.which(launcher[0]):
            try:
                subprocess.Popen(launcher, start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except OSError:
                continue
    return False


def launch(cmd: list[str]) -> bool:
    if not shutil.which(cmd[0]):
        return False
    try:
        subprocess.Popen(cmd, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False
