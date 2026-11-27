"""Parsers for APT output used by the M OS Update Center.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_UPGRADABLE = re.compile(
    r"^(?P<name>[^/\s]+)/(?P<suites>\S+)\s+(?P<new>\S+)\s+(?P<arch>\S+)"
    r"\s+\[upgradable from:\s+(?P<old>[^\]]+)\]")


@dataclass
class Upgrade:
    name: str
    suites: list[str]
    new_version: str
    old_version: str
    arch: str

    @property
    def is_security(self) -> bool:
        return any(s.endswith("-security") for s in self.suites)


def parse_upgradable(text: str) -> list[Upgrade]:
    """Parse `apt list --upgradable` output."""
    result = []
    for line in text.splitlines():
        m = _UPGRADABLE.match(line.strip())
        if not m:
            continue
        result.append(Upgrade(
            name=m["name"],
            suites=m["suites"].split(","),
            new_version=m["new"],
            old_version=m["old"].strip(),
            arch=m["arch"],
        ))
    result.sort(key=lambda u: (not u.is_security, u.name))
    return result


@dataclass
class StatusLine:
    kind: str          # "download", "install", "error", "conffile", "media"
    package: str
    percent: float
    message: str


_KINDS = {"dlstatus": "download", "pmstatus": "install", "pmerror": "error",
          "pmconffile": "conffile", "media-change": "media"}


def parse_status_line(line: str) -> StatusLine | None:
    """Parse one line of APT's machine-readable progress (APT::Status-Fd).

    Format: ``<type>:<package>:<percent>:<message>``.
    """
    parts = line.rstrip("\n").split(":", 3)
    if len(parts) < 4 or parts[0] not in _KINDS:
        return None
    try:
        percent = float(parts[2])
    except ValueError:
        percent = 0.0
    return StatusLine(_KINDS[parts[0]], parts[1], percent, parts[3])


def overall_percent(status: StatusLine) -> float:
    """Map download (0-100) and install (0-100) phases onto a single 0-100 bar."""
    if status.kind == "download":
        return status.percent * 0.3
    if status.kind == "install":
        return 30.0 + status.percent * 0.7
    return 0.0
