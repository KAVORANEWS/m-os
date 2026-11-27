"""M OS System Monitor — live CPU, memory, disk, network, processes and sensors.

All values come from /proc and /sys via mos.sysinfo.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import os
import signal
import sys
import time
from collections import deque

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QTabWidget, QVBoxLayout, QWidget)

from . import sysinfo, ui

INTERVAL_MS = 1500
HISTORY = 60


class Sparkline(QWidget):
    """Small history graph painted with QPainter."""

    def __init__(self, color: str, maximum: float | None = 100.0):
        super().__init__()
        self.values: deque[float] = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.color = QColor(color)
        self.maximum = maximum
        self.setMinimumHeight(70)

    def push(self, value: float) -> None:
        self.values.append(value)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 4, -1, -1)
        top = self.maximum or max(max(self.values), 1.0)
        step = r.width() / (HISTORY - 1)
        path = QPainterPath(QPointF(r.left(), r.bottom()))
        for i, v in enumerate(self.values):
            path.lineTo(QPointF(r.left() + i * step, r.bottom() - r.height() * min(v / top, 1.0)))
        path.lineTo(QPointF(r.right(), r.bottom()))
        fill = QColor(self.color)
        fill.setAlpha(60)
        p.fillPath(path, fill)
        p.setPen(QPen(self.color, 2))
        line = QPainterPath()
        for i, v in enumerate(self.values):
            pt = QPointF(r.left() + i * step, r.bottom() - r.height() * min(v / top, 1.0))
            line.moveTo(pt) if i == 0 else line.lineTo(pt)
        p.drawPath(line)


class MetricCard(ui.Card):
    def __init__(self, name: str, color: str, maximum: float | None = 100.0):
        super().__init__()
        head = QHBoxLayout()
        self.name = ui.section(name)
        self.value = QLabel("—")
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight)
        head.addWidget(self.name)
        head.addWidget(self.value, 1)
        self.layout_.addLayout(head)
        self.graph = Sparkline(color, maximum)
        self.add(self.graph)
        self.detail = ui.subtitle("")
        self.add(self.detail)


class Overview(QWidget):
    def __init__(self):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(14)
        self.cpu = MetricCard("CPU", "#8B7CF8")
        self.mem = MetricCard("Memory", "#38BDF8")
        self.net = MetricCard("Network", "#10B981", maximum=None)
        self.disk = ui.Card()
        self.disk.add(ui.section("Disks"))
        self.disk_rows = QVBoxLayout()
        self.disk.layout_.addLayout(self.disk_rows)
        grid.addWidget(self.cpu, 0, 0)
        grid.addWidget(self.mem, 0, 1)
        grid.addWidget(self.net, 1, 0)
        grid.addWidget(self.disk, 1, 1)
        self.prev_stat = sysinfo.read_proc_stat()
        self.prev_net = sysinfo.read_net_dev()
        self.prev_time = time.monotonic()
        self.cpu_model = sysinfo.read_cpuinfo()
        self.tick = 0

    def refresh(self) -> None:
        now = time.monotonic()
        dt = max(now - self.prev_time, 0.001)
        stat = sysinfo.read_proc_stat()
        if "cpu" in stat and "cpu" in self.prev_stat:
            pct = sysinfo.cpu_percent(self.prev_stat["cpu"], stat["cpu"])
            self.cpu.graph.push(pct)
            self.cpu.value.setText(f"{pct:.0f}%")
            per_core = [sysinfo.cpu_percent(self.prev_stat[k], v) for k, v in stat.items()
                        if k != "cpu" and k in self.prev_stat]
            self.cpu.detail.setText(f"{self.cpu_model.model}\n" +
                                    "  ".join(f"{p:.0f}%" for p in per_core))
        self.prev_stat = stat

        mem = sysinfo.read_memory()
        if mem:
            self.mem.graph.push(mem.percent)
            self.mem.value.setText(f"{mem.percent:.0f}%")
            self.mem.detail.setText(
                f"{sysinfo.human_bytes(mem.used)} of {sysinfo.human_bytes(mem.total)} used · "
                f"swap {sysinfo.human_bytes(mem.swap_used)} / {sysinfo.human_bytes(mem.swap_total)}")

        net = sysinfo.read_net_dev()
        rx = sum(max(0, v[0] - self.prev_net.get(k, v)[0]) for k, v in net.items()) / dt
        tx = sum(max(0, v[1] - self.prev_net.get(k, v)[1]) for k, v in net.items()) / dt
        self.prev_net = net
        self.net.graph.push(rx + tx)
        self.net.value.setText(f"↓ {sysinfo.human_bytes(rx)}/s  ↑ {sysinfo.human_bytes(tx)}/s")
        self.net.detail.setText(", ".join(sorted(net)) or "No network interfaces")
        self.prev_time = now

        if self.tick % 5 == 0:  # disks change slowly
            while self.disk_rows.count():
                item = self.disk_rows.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for m in sysinfo.read_mount_usage():
                text = (f"{m.mountpoint} ({m.fstype}) — {sysinfo.human_bytes(m.used)} of "
                        f"{sysinfo.human_bytes(m.total)}")
                self.disk_rows.addWidget(QLabel(text))
                self.disk_rows.addWidget(ui.usage_bar(m.percent, text))
        self.tick += 1


class Processes(QWidget):
    COLUMNS = ["Name", "PID", "User", "CPU %", "Memory", "Command"]

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        top = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter processes…")
        self.filter.textChanged.connect(self.refresh)
        self.end_btn = QPushButton("End process")
        self.end_btn.clicked.connect(self.end_selected)
        top.addWidget(self.filter, 1)
        top.addWidget(self.end_btn)
        lay.addLayout(top)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        lay.addWidget(self.table)
        self.prev_ticks: dict[int, int] = {}
        self.prev_time = time.monotonic()
        self.hz = os.sysconf("SC_CLK_TCK")

    def refresh(self) -> None:
        now = time.monotonic()
        dt = max(now - self.prev_time, 0.001)
        procs = sysinfo.list_processes()
        needle = self.filter.text().lower()
        selected = self.selected_pid()
        self.table.setSortingEnabled(False)
        rows = [p for p in procs if not needle or needle in p.name.lower() or needle in p.cmdline.lower()]
        self.table.setRowCount(len(rows))
        for row, p in enumerate(rows):
            cpu = 100.0 * (p.cpu_ticks - self.prev_ticks.get(p.pid, p.cpu_ticks)) / self.hz / dt
            values = [p.name, p.pid, p.user, round(cpu, 1), p.rss, p.cmdline]
            for col, val in enumerate(values):
                item = QTableWidgetItem()
                if col == 4:
                    item.setData(Qt.ItemDataRole.DisplayRole, sysinfo.human_bytes(val))
                    item.setData(Qt.ItemDataRole.UserRole, val)
                elif isinstance(val, (int, float)):
                    item.setData(Qt.ItemDataRole.DisplayRole, val)
                else:
                    item.setText(str(val))
                self.table.setItem(row, col, item)
            if p.pid == selected:
                self.table.selectRow(row)
        self.table.setSortingEnabled(True)
        self.prev_ticks = {p.pid: p.cpu_ticks for p in procs}
        self.prev_time = now

    def selected_pid(self) -> int | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 1)
        return int(item.data(Qt.ItemDataRole.DisplayRole)) if item else None

    def end_selected(self) -> None:
        pid = self.selected_pid()
        if pid is None:
            return
        if QMessageBox.question(self, "End process",
                                f"Send a terminate signal to process {pid}?") != QMessageBox.StandardButton.Yes:
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except PermissionError:
            ui.error(self, f"You do not have permission to end process {pid}.",
                     "Processes owned by other users or the system can only be ended by an administrator.")
        except ProcessLookupError:
            pass


class Hardware(QWidget):
    def __init__(self):
        super().__init__()
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 16, 16)
        self.card = ui.Card(spacing=2)
        self.lay.addWidget(self.card)
        self.lay.addStretch(1)

    def refresh(self) -> None:
        while self.card.layout_.count():
            item = self.card.layout_.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cpu = sysinfo.read_cpuinfo()
        mem = sysinfo.read_memory()
        self.card.add(ui.section("Hardware"))
        self.card.add(ui.key_value_row("Processor", f"{cpu.model} ({cpu.cores}C/{cpu.threads}T)"))
        self.card.add(ui.key_value_row("Memory", sysinfo.human_bytes(mem.total) if mem else "unknown"))
        self.card.add(ui.key_value_row("Graphics", "\n".join(sysinfo.read_graphics()) or "not detected"))
        temps = sysinfo.read_temperatures()
        self.card.add(ui.section("Temperatures"))
        if temps:
            for name, value in temps:
                self.card.add(ui.key_value_row(name, f"{value:.1f} °C"))
        else:
            self.card.add(ui.subtitle("No temperature sensors are exposed on this computer."))
        batteries = sysinfo.read_batteries()
        if batteries:
            self.card.add(ui.section("Battery"))
            for b in batteries:
                self.card.add(ui.key_value_row(b["name"], f"{b['capacity']}% — {b['status']}"))


class MonitorWindow(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("M OS System Monitor")
        self.resize(980, 680)
        self.overview = Overview()
        self.processes = Processes()
        self.hardware = Hardware()
        self.addTab(self.overview, "Overview")
        self.addTab(self.processes, "Processes")
        self.addTab(self.hardware, "Hardware")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(INTERVAL_MS)
        self.currentChanged.connect(lambda _i: self.refresh())
        self.hardware.refresh()
        self.refresh()

    def refresh(self) -> None:
        self.overview.refresh()  # always sample, so graphs have history
        if self.currentWidget() is self.processes:
            self.processes.refresh()
        elif self.currentWidget() is self.hardware and self.overview.tick % 4 == 0:
            self.hardware.refresh()


def main() -> int:
    app = ui.make_app("mos-system-monitor", "M OS System Monitor", "mos-system-monitor")
    win = MonitorWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
