"""Shared Qt 6 widgets and styling for the M OS applications.

Styling follows the active KDE color scheme (M OS Dark/Light by default)
through QPalette and only adds M OS shapes: rounded cards, sidebar and
accent buttons.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QIcon, QPalette
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox,
                             QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

ACCENT = "#6D5DF6"


def accent_color(app: QApplication) -> str:
    color = app.palette().color(QPalette.ColorRole.Highlight)
    return color.name() if color.isValid() else ACCENT


def stylesheet(app: QApplication) -> str:
    pal = app.palette()
    base = pal.color(QPalette.ColorRole.Window)
    dark = base.lightness() < 128
    card = base.lighter(118) if dark else base.darker(103)
    border = base.lighter(150) if dark else base.darker(112)
    sidebar = base.darker(115) if dark else base.darker(104)
    accent = accent_color(app)
    return f"""
    QFrame#Card {{ background: {card.name()}; border: 1px solid {border.name()}; border-radius: 12px; }}
    QListWidget#Sidebar {{ background: {sidebar.name()}; border: none; padding: 8px; outline: 0; }}
    QListWidget#Sidebar::item {{ padding: 8px 10px; border-radius: 8px; margin: 1px 0; }}
    QListWidget#Sidebar::item:selected {{ background: {accent}; color: white; }}
    QPushButton#Primary {{ background: {accent}; color: white; border: none; border-radius: 8px;
                           padding: 8px 18px; font-weight: 600; }}
    QPushButton#Primary:disabled {{ background: {border.name()}; color: {pal.color(QPalette.ColorRole.PlaceholderText).name()}; }}
    QPushButton#Choice {{ border: 2px solid {border.name()}; border-radius: 12px; padding: 10px; text-align: left; }}
    QPushButton#Choice:checked {{ border: 2px solid {accent}; }}
    QLabel#Title {{ font-size: 20pt; font-weight: 700; }}
    QLabel#Subtitle {{ color: {pal.color(QPalette.ColorRole.PlaceholderText).name()}; }}
    QLabel#SectionTitle {{ font-size: 13pt; font-weight: 600; }}
    QProgressBar {{ border: none; border-radius: 5px; background: {border.name()}; height: 10px; text-align: center; }}
    QProgressBar::chunk {{ border-radius: 5px; background: {accent}; }}
    """


def make_app(app_id: str, display_name: str, icon: str) -> QApplication:
    QApplication.setDesktopFileName(app_id)
    app = QApplication(sys.argv)
    app.setApplicationName(app_id)
    app.setApplicationDisplayName(display_name)
    app.setOrganizationName("M OS")
    app.setWindowIcon(QIcon.fromTheme(icon, QIcon.fromTheme("mos-logo")))
    app.setStyleSheet(stylesheet(app))
    return app


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, spacing: int = 8):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(16, 14, 16, 14)
        self.layout_.setSpacing(spacing)

    def add(self, widget: QWidget) -> QWidget:
        self.layout_.addWidget(widget)
        return widget


def title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Title")
    return lbl


def subtitle(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Subtitle")
    lbl.setWordWrap(True)
    return lbl


def section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("SectionTitle")
    return lbl


def primary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def key_value_row(key: str, value: str) -> QWidget:
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 2, 0, 2)
    k = QLabel(key)
    k.setObjectName("Subtitle")
    k.setMinimumWidth(150)
    v = QLabel(value)
    v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    v.setWordWrap(True)
    v.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    lay.addWidget(k)
    lay.addWidget(v, 1)
    return row


def usage_bar(percent: float, text: str) -> QProgressBar:
    bar = QProgressBar()
    bar.setRange(0, 1000)
    bar.setValue(int(percent * 10))
    bar.setFormat(text)
    bar.setTextVisible(False)
    bar.setToolTip(text)
    bar.setFixedHeight(10)
    return bar


def bold(font: QFont, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    f = QFont(font)
    f.setWeight(weight)
    return f


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def error(parent: QWidget | None, text: str, details: str = "") -> None:
    box = QMessageBox(QMessageBox.Icon.Warning, "M OS", text, QMessageBox.StandardButton.Ok, parent)
    if details:
        box.setDetailedText(details)
    box.exec()
