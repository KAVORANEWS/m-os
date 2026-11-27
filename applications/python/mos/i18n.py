"""Minimal English/Sinhala string catalogue for the M OS applications.

Strings without a Sinhala translation fall back to English. Translation
coverage is tracked in docs/localisation.md — it is NOT yet complete.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import os

SINHALA = {
    "Welcome to M OS": "M OS වෙත සාදරයෙන් පිළිගනිමු",
    "Your Computer. Your Experience. Your OS.": "ඔබේ පරිගණකය. ඔබේ අත්දැකීම. ඔබේ OS.",
    "Next": "ඊළඟ",
    "Back": "ආපසු",
    "Finish": "අවසන්",
    "Skip": "මඟ හරින්න",
    "Desktop layout": "ඩෙස්ක්ටොප් සැකැස්ම",
    "Appearance": "පෙනුම",
    "Performance": "කාර්ය සාධනය",
    "Privacy": "පෞද්ගලිකත්වය",
    "Language": "භාෂාව",
    "Get started": "ආරම්භ කරන්න",
    "Install M OS": "M OS ස්ථාපනය කරන්න",
    "Dark": "අඳුරු",
    "Light": "දීප්ත",
    "Balanced": "සමබර",
    "Personalization": "පුද්ගලීකරණය",
    "Display": "සංදර්ශකය",
    "Sound": "ශබ්දය",
    "Network": "ජාලය",
    "Bluetooth": "බ්ලූටූත්",
    "Keyboard": "යතුරු පුවරුව",
    "Mouse": "මූසිකය",
    "Date and time": "දිනය සහ වේලාව",
    "Users": "පරිශීලකයින්",
    "Security": "ආරක්ෂාව",
    "Updates": "යාවත්කාලීන",
    "Storage": "ගබඩාව",
    "Power": "බලය",
    "About M OS": "M OS ගැන",
    "Check for updates": "යාවත්කාලීන පරීක්ෂා කරන්න",
    "Install updates": "යාවත්කාලීන ස්ථාපනය කරන්න",
    "Your system is up to date.": "ඔබේ පද්ධතිය යාවත්කාලීනයි.",
    "Restart required": "නැවත ආරම්භ කිරීම අවශ්‍යයි",
}


def is_sinhala() -> bool:
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value:
            return value.startswith("si")
    return False


def tr(text: str) -> str:
    return SINHALA.get(text, text) if is_sinhala() else text
