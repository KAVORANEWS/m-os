"""Read hardware and system state from Linux kernel interfaces.

Pure-Python and Qt-free so it can be unit tested. Every function either
parses text that it is given (``parse_*``) or reads a real system source
(``read_*`` / ``list_*``); nothing here returns fabricated values — when a
source is unavailable the functions return ``None`` or empty containers.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import json
import os
import platform
import pwd
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REAL_FILESYSTEMS = {"ext2", "ext3", "ext4", "btrfs", "xfs", "vfat", "exfat", "ntfs", "ntfs3",
                    "fuseblk", "f2fs", "jfs", "reiserfs", "zfs"}


# --------------------------------------------------------------------------- utils
def human_bytes(n: float | int | None, binary: bool = True) -> str:
    """Format a byte count, e.g. 8254390272 -> '7.7 GiB'."""
    if n is None:
        return "—"
    step = 1024.0 if binary else 1000.0
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"] if binary else ["B", "kB", "MB", "GB", "TB", "PB"]
    value = float(n)
    for unit in units:
        if abs(value) < step or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= step
    return f"{value:.1f} {units[-1]}"


def _read(path: str | Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _run(cmd: list[str], timeout: float = 5.0) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


# --------------------------------------------------------------------------- os-release
def parse_os_release(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value.replace('\\"', '"')
    return data


def read_os_release() -> dict[str, str]:
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        text = _read(path)
        if text:
            return parse_os_release(text)
    return {}


def read_build_info(path: str = "/usr/share/mos/build-info") -> dict[str, str]:
    text = _read(path)
    return parse_os_release(text) if text else {}


def is_live_session() -> bool:
    return os.path.isdir("/run/live/medium") or os.path.isdir("/run/initramfs/live")


# --------------------------------------------------------------------------- memory
def parse_meminfo(text: str) -> dict[str, int]:
    """Return /proc/meminfo values in bytes."""
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        parts = rest.split()
        if not parts:
            continue
        try:
            number = int(parts[0])
        except ValueError:
            continue
        if len(parts) > 1 and parts[1].lower() == "kb":
            number *= 1024
        values[key.strip()] = number
    return values


@dataclass
class MemoryState:
    total: int
    available: int
    swap_total: int
    swap_free: int

    @property
    def used(self) -> int:
        return max(0, self.total - self.available)

    @property
    def percent(self) -> float:
        return 100.0 * self.used / self.total if self.total else 0.0

    @property
    def swap_used(self) -> int:
        return max(0, self.swap_total - self.swap_free)


def memory_state(meminfo: dict[str, int]) -> MemoryState:
    total = meminfo.get("MemTotal", 0)
    available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    return MemoryState(total, available, meminfo.get("SwapTotal", 0), meminfo.get("SwapFree", 0))


def read_memory() -> MemoryState | None:
    text = _read("/proc/meminfo")
    return memory_state(parse_meminfo(text)) if text else None


# --------------------------------------------------------------------------- cpu
def parse_proc_stat(text: str) -> dict[str, tuple[int, int]]:
    """Return {cpu-name: (total_jiffies, idle_jiffies)} from /proc/stat."""
    result: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        if not line.startswith("cpu"):
            continue
        parts = line.split()
        nums = [int(x) for x in parts[1:]]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)  # idle + iowait
        # guest/guest_nice are already included in user/nice
        total = sum(nums[:8]) if len(nums) >= 8 else sum(nums)
        result[parts[0]] = (total, idle)
    return result


def cpu_percent(prev: tuple[int, int], cur: tuple[int, int]) -> float:
    dt = cur[0] - prev[0]
    di = cur[1] - prev[1]
    if dt <= 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (dt - di) / dt))


def read_proc_stat() -> dict[str, tuple[int, int]]:
    text = _read("/proc/stat")
    return parse_proc_stat(text) if text else {}


@dataclass
class CpuInfo:
    model: str
    sockets: int
    cores: int
    threads: int
    max_mhz: float | None = None


def parse_cpuinfo(text: str) -> CpuInfo:
    model = ""
    threads = 0
    physical: set[str] = set()
    cores_per: dict[str, int] = {}
    current_phys = "0"
    for line in text.splitlines():
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "processor":
            threads += 1
        elif key == "model name" and not model:
            model = " ".join(value.split())
        elif key == "physical id":
            current_phys = value
            physical.add(value)
        elif key == "cpu cores":
            try:
                cores_per[current_phys] = int(value)
            except ValueError:
                pass
    sockets = max(1, len(physical))
    cores = sum(cores_per.values()) if cores_per else threads
    return CpuInfo(model or platform.processor() or "Unknown processor", sockets, cores, threads)


def read_cpuinfo() -> CpuInfo:
    info = parse_cpuinfo(_read("/proc/cpuinfo") or "")
    mhz = _read("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
    if mhz and mhz.strip().isdigit():
        info.max_mhz = int(mhz.strip()) / 1000.0
    return info


# --------------------------------------------------------------------------- network
def parse_net_dev(text: str) -> dict[str, tuple[int, int]]:
    """Return {iface: (rx_bytes, tx_bytes)} from /proc/net/dev, excluding loopback."""
    result: dict[str, tuple[int, int]] = {}
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        name, _, data = line.partition(":")
        name = name.strip()
        if name == "lo":
            continue
        fields = data.split()
        if len(fields) >= 9:
            result[name] = (int(fields[0]), int(fields[8]))
    return result


def read_net_dev() -> dict[str, tuple[int, int]]:
    text = _read("/proc/net/dev")
    return parse_net_dev(text) if text else {}


# --------------------------------------------------------------------------- storage
@dataclass
class MountUsage:
    device: str
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int

    @property
    def percent(self) -> float:
        return 100.0 * self.used / self.total if self.total else 0.0


def parse_mounts(text: str) -> list[tuple[str, str, str]]:
    seen: set[str] = set()
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mountpoint, fstype = parts[0], parts[1].replace("\\040", " "), parts[2]
        if fstype not in REAL_FILESYSTEMS or device in seen:
            continue
        seen.add(device)
        out.append((device, mountpoint, fstype))
    return out


def read_mount_usage() -> list[MountUsage]:
    result = []
    for device, mountpoint, fstype in parse_mounts(_read("/proc/mounts") or ""):
        try:
            usage = shutil.disk_usage(mountpoint)
        except OSError:
            continue
        result.append(MountUsage(device, mountpoint, fstype, usage.total, usage.used, usage.free))
    return result


@dataclass
class BlockDevice:
    name: str
    size: int
    model: str
    transport: str
    rotational: bool
    removable: bool


def parse_lsblk_json(text: str) -> list[BlockDevice]:
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return []
    out = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue

        def truthy(v):
            return v in (True, 1, "1", "true")
        out.append(BlockDevice(
            name=dev.get("name", "?"),
            size=int(dev.get("size") or 0),
            model=(dev.get("model") or "").strip(),
            transport=(dev.get("tran") or "").strip(),
            rotational=truthy(dev.get("rota")),
            removable=truthy(dev.get("rm")),
        ))
    return out


def read_block_devices() -> list[BlockDevice]:
    text = _run(["lsblk", "-J", "-b", "-d", "-o", "NAME,SIZE,MODEL,TYPE,ROTA,TRAN,RM"])
    return parse_lsblk_json(text) if text else []


# --------------------------------------------------------------------------- graphics
def parse_lspci_mm(text: str) -> list[str]:
    """Extract display adapters from `lspci -mm` output."""
    adapters = []
    for line in text.splitlines():
        fields = []
        current = ""
        inside = False
        for ch in line:
            if ch == '"':
                inside = not inside
                if not inside:
                    fields.append(current)
                    current = ""
            elif inside:
                current += ch
        if len(fields) >= 3 and any(k in fields[0] for k in ("VGA", "3D controller", "Display controller")):
            adapters.append(f"{fields[1]} {fields[2]}".strip())
    return adapters


def read_graphics() -> list[str]:
    text = _run(["lspci", "-mm"])
    return parse_lspci_mm(text) if text else []


# --------------------------------------------------------------------------- sensors
def read_temperatures(root: str = "/sys/class/hwmon") -> list[tuple[str, float]]:
    temps = []
    base = Path(root)
    if not base.is_dir():
        return temps
    for hw in sorted(base.iterdir()):
        chip = (_read(hw / "name") or hw.name).strip()
        for inp in sorted(hw.glob("temp*_input")):
            raw = _read(inp)
            if not raw or not raw.strip().lstrip("-").isdigit():
                continue
            label = _read(inp.with_name(inp.name.replace("_input", "_label")))
            name = f"{chip} {label.strip()}" if label else chip
            temps.append((name, int(raw.strip()) / 1000.0))
    return temps


def read_batteries(root: str = "/sys/class/power_supply") -> list[dict[str, str]]:
    result = []
    base = Path(root)
    if not base.is_dir():
        return result
    for dev in sorted(base.iterdir()):
        if (_read(dev / "type") or "").strip() != "Battery":
            continue
        result.append({
            "name": dev.name,
            "capacity": (_read(dev / "capacity") or "?").strip(),
            "status": (_read(dev / "status") or "Unknown").strip(),
        })
    return result


# --------------------------------------------------------------------------- processes
@dataclass
class ProcessInfo:
    pid: int
    name: str
    user: str
    uid: int
    state: str
    rss: int            # bytes
    cpu_ticks: int      # utime + stime
    cmdline: str = field(default="")


def parse_proc_pid_stat(text: str) -> tuple[str, str, int]:
    """Return (comm, state, utime+stime) from /proc/<pid>/stat."""
    lpar, rpar = text.index("("), text.rindex(")")
    comm = text[lpar + 1:rpar]
    rest = text[rpar + 2:].split()
    state = rest[0]
    utime, stime = int(rest[11]), int(rest[12])
    return comm, state, utime + stime


def list_processes(proc_root: str = "/proc") -> list[ProcessInfo]:
    page = os.sysconf("SC_PAGE_SIZE")
    users: dict[int, str] = {}
    result = []
    for entry in os.scandir(proc_root):
        if not entry.name.isdigit():
            continue
        try:
            stat = Path(entry.path, "stat").read_text()
            comm, state, ticks = parse_proc_pid_stat(stat)
            statm = Path(entry.path, "statm").read_text().split()
            rss = int(statm[1]) * page
            uid = entry.stat().st_uid
            raw_cmd = Path(entry.path, "cmdline").read_bytes()
        except (OSError, ValueError, IndexError):
            continue  # process exited or is inaccessible
        if uid not in users:
            try:
                users[uid] = pwd.getpwuid(uid).pw_name
            except KeyError:
                users[uid] = str(uid)
        cmd = raw_cmd.replace(b"\0", b" ").decode("utf-8", "replace").strip()
        result.append(ProcessInfo(int(entry.name), comm, users[uid], uid, state, rss, ticks, cmd))
    return result


# --------------------------------------------------------------------------- versions
def kernel_version() -> str:
    return platform.release()


def plasma_version() -> str | None:
    out = _run(["plasmashell", "--version"])
    if out:
        return out.strip().split()[-1]
    return None


def kde_frameworks_version() -> str | None:
    out = _run(["kf6-config", "--version"])
    if out:
        for line in out.splitlines():
            if line.startswith("KDE Frameworks"):
                return line.split(":", 1)[-1].strip()
    return None
