#!/usr/bin/env python3
"""Automated boot test for the M OS ISO in QEMU.

Boots the ISO through its real boot path (SeaBIOS or OVMF UEFI firmware →
GRUB → live-boot), adds a serial console by editing the GRUB entry with
simulated key presses, logs into the live session over the serial line and
runs checks inside the running system. Screenshots of the graphical screen
are captured through QMP.

    tests/boot/qemu_boot_test.py --iso dist/M-OS-0.1.0-amd64.iso --firmware uefi --out build/boot-uefi

Exit status is non-zero if the system did not boot or a required check failed.
No physical disk is touched; an optional blank virtual disk can be attached.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

OVMF_CODE = "/usr/share/OVMF/OVMF_CODE_4M.fd"
OVMF_VARS = "/usr/share/OVMF/OVMF_VARS_4M.fd"
QCODES = {" ": "spc", "=": "equal", ",": "comma", ".": "dot", "-": "minus", "/": "slash", "_": "shift-minus"}


class QMP:
    def __init__(self, path: str):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        for _ in range(100):
            try:
                self.sock.connect(path)
                break
            except OSError:
                time.sleep(0.1)
        self.file = self.sock.makefile("rw")
        self.file.readline()  # greeting
        self.cmd("qmp_capabilities")

    def cmd(self, name: str, **args):
        self.file.write(json.dumps({"execute": name, "arguments": args}) + "\n")
        self.file.flush()
        while True:
            line = self.file.readline()
            if not line:
                return None
            msg = json.loads(line)
            if "return" in msg or "error" in msg:
                return msg

    def key(self, *qcodes: str):
        keys = [{"type": "qcode", "data": k} for k in qcodes]
        self.cmd("send-key", keys=keys, **{"hold-time": 60})
        time.sleep(0.08)

    def type_text(self, text: str):
        for ch in text:
            code = QCODES.get(ch, ch.lower())
            if code.startswith("shift-"):
                self.key("shift", code[6:])
            elif ch.isupper():
                self.key("shift", code)
            else:
                self.key(code)

    def screenshot(self, path: Path):
        ppm = str(path.with_suffix(".ppm"))
        self.cmd("screendump", filename=ppm)
        time.sleep(0.5)
        if shutil.which("convert") and os.path.exists(ppm):
            subprocess.run(["convert", ppm, str(path)], check=False)
            os.unlink(ppm)


class Serial:
    def __init__(self, proc: subprocess.Popen, logfile: Path):
        self.proc = proc
        self.q: queue.Queue[str] = queue.Queue()
        self.buffer = ""
        self.log = open(logfile, "w", encoding="utf-8", errors="replace")
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            data = self.proc.stdout.read1(4096) if hasattr(self.proc.stdout, "read1") else self.proc.stdout.read(1)
            if not data:
                break
            text = data.decode("utf-8", "replace")
            self.log.write(text)
            self.log.flush()
            self.q.put(text)

    def expect(self, pattern: str, timeout: float) -> re.Match | None:
        rx = re.compile(pattern)
        end = time.time() + timeout
        while time.time() < end:
            m = rx.search(self.buffer)
            if m:
                self.buffer = self.buffer[m.end():]
                return m
            try:
                self.buffer += self.q.get(timeout=0.5)
            except queue.Empty:
                if self.proc.poll() is not None:
                    return None
            self.buffer = self.buffer[-200000:]
        return None

    def send(self, text: str):
        self.proc.stdin.write(text.encode())
        self.proc.stdin.flush()

    def run(self, command: str, timeout: float = 60) -> tuple[int | None, str]:
        tag = f"T{int(time.time() * 1000) % 10**8}"
        self.send(f"echo {tag}-BEGIN; {command}; echo {tag}-END $?\n")
        m = self.expect(rf"(?s){tag}-BEGIN\r?\n(.*?){tag}-END (\d+)", timeout)
        if not m:
            return None, ""
        out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", m.group(1)).replace("\r", "").strip()
        return int(m.group(2)), out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True)
    ap.add_argument("--firmware", choices=["bios", "uefi"], default="uefi")
    ap.add_argument("--out", default="build/boot-test")
    ap.add_argument("--mem", default="4096")
    ap.add_argument("--cpus", default="2")
    ap.add_argument("--grub-wait", type=float, default=None, help="seconds before editing the GRUB entry")
    ap.add_argument("--boot-timeout", type=float, default=None)
    ap.add_argument("--no-desktop", action="store_true",
                    help="boot to multi-user.target and skip graphical checks (low-RAM / no-KVM hosts)")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    kvm = os.access("/dev/kvm", os.W_OK)
    grub_wait = args.grub_wait or (12 if kvm else 60)
    boot_timeout = args.boot_timeout or (420 if kvm else 3600)
    tmp = tempfile.mkdtemp(prefix="mos-boot-")
    qmp_path = os.path.join(tmp, "qmp.sock")

    cmd = ["qemu-system-x86_64", "-m", args.mem, "-smp", args.cpus, "-display", "none",
           "-device", "virtio-vga", "-serial", "stdio", "-monitor", "none",
           "-qmp", f"unix:{qmp_path},server=on,wait=off",
           "-nic", "user,model=virtio-net-pci",
           "-drive", f"file={args.iso},media=cdrom,readonly=on", "-boot", "d"]
    cmd += ["-enable-kvm", "-cpu", "host"] if kvm else ["-cpu", "max"]
    if args.firmware == "uefi":
        vars_copy = os.path.join(tmp, "OVMF_VARS.fd")
        shutil.copy(OVMF_VARS, vars_copy)
        cmd += ["-machine", "q35", "-drive", f"if=pflash,format=raw,readonly=on,file={OVMF_CODE}",
                "-drive", f"if=pflash,format=raw,file={vars_copy}"]
    else:
        cmd += ["-machine", "pc"]

    report = {"iso": os.path.basename(args.iso), "firmware": args.firmware, "kvm": kvm,
              "mem_mb": int(args.mem), "cpus": int(args.cpus), "checks": {}, "measurements": {}}
    print("QEMU:", " ".join(cmd))
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    serial = Serial(proc, out / "serial.log")
    qmp = QMP(qmp_path)
    ok = True

    def check(name: str, passed: bool, detail: str = "", required: bool = True):
        nonlocal ok
        report["checks"][name] = {"passed": bool(passed), "detail": detail[:2000], "required": required}
        print(f"{'PASS' if passed else ('FAIL' if required else 'WARN')}  {name}" + (f" — {detail[:200]}" if detail else ""))
        if required and not passed:
            ok = False

    try:
        # Keep GRUB on the first entry (stops the countdown), then edit it.
        end = t0 + grub_wait
        shot_taken = False
        while time.time() < end:
            qmp.key("up")
            time.sleep(1.5)
            if not shot_taken and time.time() > end - 3:
                qmp.screenshot(out / "01-grub-menu.png")
                shot_taken = True
        qmp.key("e")
        time.sleep(2)
        # Entry layout: "setparams ...", blank line, "linux ..." -> move to the
        # linux line (a single logical line even when wrapped) and append.
        qmp.key("down")
        time.sleep(0.5)
        qmp.key("down")
        time.sleep(0.5)
        qmp.key("end")
        time.sleep(0.5)
        extra = " systemd.unit=multi-user.target" if args.no_desktop else ""
        qmp.type_text(" console=tty0 console=ttyS0,115200" + extra)
        time.sleep(3)  # let GRUB process the queued keystrokes
        qmp.screenshot(out / "02-grub-edit.png")
        qmp.key("ctrl", "x")

        # Wait for the login prompt, saving a progress screenshot every 5 min
        m = None
        deadline = t0 + grub_wait + boot_timeout
        n = 0
        while m is None and time.time() < deadline:
            m = serial.expect(r"login:", min(300, max(1, deadline - time.time())))
            if m is None:
                n += 1
                qmp.screenshot(out / f"03-boot-progress-{n:02d}.png")
        report["measurements"]["boot_to_login_prompt_s"] = round(time.time() - t0, 1)
        check("boots to login prompt", m is not None, f"{report['measurements']['boot_to_login_prompt_s']} s")
        if not m:
            qmp.screenshot(out / "99-failure.png")
            raise SystemExit
        serial.send("mos\n")
        if serial.expect(r"Password:", 30):
            serial.send("live\n")
        logged_in = serial.expect(r"\$ ", 60) is not None
        check("live user login over serial console", logged_in)
        if not logged_in:
            raise SystemExit
        serial.run("export TERM=dumb PAGER=cat SYSTEMD_PAGER= SYSTEMD_COLORS=0; stty cols 200", 10)

        rc, txt = serial.run("grep -E '^(NAME|PRETTY_NAME|ID)=' /etc/os-release")
        check("os-release identifies M OS", rc == 0 and 'NAME="M OS"' in txt, txt)
        rc, txt = serial.run("[ -d /sys/firmware/efi ] && echo uefi || echo bios")
        check(f"booted via {args.firmware.upper()} firmware", txt.strip() == args.firmware, txt)
        rc, txt = serial.run("uname -r")
        report["measurements"]["kernel"] = txt
        rc, txt = serial.run("systemctl is-active sddm", 30)
        if args.no_desktop:
            report["mode"] = "no-desktop (multi-user.target): graphical checks skipped"
            print("SKIP  graphical session checks (--no-desktop)")
        else:
            check("SDDM display manager active", txt.strip() == "active", txt)

        if not args.no_desktop:
            # Wait for the Plasma desktop of the auto-logged-in live user
            desktop = False
            t_desk = time.time()
            while time.time() - t_desk < (240 if kvm else 1800):
                rc, txt = serial.run("pgrep -u mos -x plasmashell >/dev/null && pgrep -u mos -x kwin_wayland -o >/dev/null "
                                     "&& echo DESKTOP-UP || (pgrep -u mos -x plasmashell >/dev/null && pgrep -u mos kwin_x11 >/dev/null && echo DESKTOP-UP)", 30)
                if "DESKTOP-UP" in txt:
                    desktop = True
                    break
                time.sleep(5)
            report["measurements"]["boot_to_desktop_s"] = round(time.time() - t0, 1)
            check("Plasma desktop running (plasmashell + KWin)", desktop,
                  f"{report['measurements']['boot_to_desktop_s']} s after power-on")
            rc, txt = serial.run("loginctl list-sessions --no-legend; loginctl show-user mos -p Display --value", 15)
            rc2, sess = serial.run("for s in $(loginctl list-sessions --no-legend | awk '{print $1}'); do "
                                   "loginctl show-session $s -p Type -p Desktop -p Name; done", 15)
            report["measurements"]["sessions"] = sess
            time.sleep(25)  # let autostart apps (M OS Welcome) appear
            qmp.screenshot(out / "03-desktop.png")

            rc, txt = serial.run("pgrep -u mos -af mos-welcome | head -1", 15)
            check("M OS Welcome autostarted", "mos-welcome" in txt, txt, required=False)
        rc, txt = serial.run("ls /usr/bin/mos-welcome /usr/bin/mos-control-center /usr/bin/mos-update-center "
                             "/usr/bin/mos-system-monitor /usr/bin/mos-about", 15)
        check("M OS applications installed", rc == 0, txt)
        rc, txt = serial.run("python3 -c 'import mos.sysinfo as s; m=s.read_memory(); "
                             "print(s.read_cpuinfo().model, s.human_bytes(m.total))'", 30)
        check("M OS Python library runs on target", rc == 0, txt)
        rc, txt = serial.run("mos-desktopctl --dry-run layout classic | head -3", 15)
        check("mos-desktopctl available", rc == 0 and "plasma-apply-lookandfeel" in txt, txt)
        rc, txt = serial.run("sudo -n ufw status", 30)
        check("firewall active (ufw)", "Status: active" in txt, txt)
        rc, txt = serial.run("sudo -n aa-status --enabled && echo AA-ON; sudo -n aa-status 2>/dev/null | head -1", 30)
        check("AppArmor enabled", "AA-ON" in txt, txt)
        rc, txt = serial.run("ss -Hltn | grep -v '127.0.0\\|::1\\|\\[::1\\]' || true", 15)
        check("no network services listening on external interfaces", txt.strip() == "", txt or "none")
        rc, txt = serial.run("systemctl is-enabled ssh 2>/dev/null || echo not-installed", 15)
        check("SSH not enabled", "enabled" != txt.strip(), txt)
        rc, txt = serial.run("swapon --show=NAME,SIZE --noheadings", 15)
        check("zram swap active", "zram" in txt, txt, required=False)
        rc, txt = serial.run("fc-list :lang=si family | head -3", 15)
        check("Sinhala fonts available", rc == 0 and txt.strip() != "", txt)
        rc, txt = serial.run("locale -a | grep -iE 'si_LK|en_US'", 15)
        check("English and Sinhala locales generated", "si_LK" in txt and "en_US" in txt, txt)
        rc, txt = serial.run("ls /usr/lib/x86_64-linux-gnu/fcitx5/ 2>/dev/null | grep -c m17n; "
                             "ls /usr/share/m17n/si-*.mim | head", 15)
        check("Sinhala input methods present", "si-wijesekara" in txt or "si-" in txt, txt, required=False)
        rc, txt = serial.run("systemctl --failed --no-legend --plain | head -20", 30)
        check("no failed systemd units", txt.strip() == "", txt or "none", required=False)
        rc, txt = serial.run("free -m | awk '/Mem:/{print $3}'", 15)
        report["measurements"]["ram_used_mb_desktop_idle"] = txt
        rc, txt = serial.run("cat /proc/loadavg", 15)
        report["measurements"]["loadavg"] = txt
        rc, txt = serial.run("systemd-analyze 2>/dev/null | head -1", 30)
        report["measurements"]["systemd_analyze"] = txt
        rc, txt = serial.run("ps -u mos -o rss=,comm= --sort=-rss | head -8", 15)
        report["measurements"]["top_user_processes_rss_kb"] = txt
        rc, txt = serial.run("calamares --version 2>/dev/null | tail -1; ls /etc/calamares/branding/mos/", 30)
        check("Calamares installer with M OS branding present", "branding.desc" in txt, txt)

        qmp.screenshot(out / ("04-console-final.png" if args.no_desktop else "04-desktop-final.png"))
        serial.run("sudo -n systemctl poweroff", 5)
        try:
            proc.wait(timeout=120)
            check("clean shutdown", True, required=False)
        except subprocess.TimeoutExpired:
            check("clean shutdown", False, "VM did not power off within 120 s", required=False)
    except SystemExit:
        pass
    except (BrokenPipeError, ConnectionError, OSError) as e:
        qemu_rc = proc.poll()
        check("VM kept running during the test", False,
              f"QEMU terminated (exit {qemu_rc}): {e}. On small hosts this is usually the host OOM killer.")
    finally:
        if proc.poll() is None:
            proc.kill()
        report["passed"] = ok
        report["duration_s"] = round(time.time() - t0, 1)
        (out / "report.json").write_text(json.dumps(report, indent=2))
        lines = [f"# Boot test — {report['iso']} ({args.firmware.upper()})", "",
                 f"KVM: {kvm} · RAM {args.mem} MB · {args.cpus} vCPU · mode: {report.get('mode', 'full desktop')} · "
                 f"result: **{'PASS' if ok else 'FAIL'}**", "",
                 "| Check | Result | Detail |", "|---|---|---|"]
        for name, c in report["checks"].items():
            res = "PASS" if c["passed"] else ("FAIL" if c["required"] else "WARN")
            detail = c["detail"].replace("\n", "<br>").replace("|", "\\|")[:300]
            lines.append(f"| {name} | {res} | {detail} |")
        lines += ["", "## Measurements", "", "```", json.dumps(report["measurements"], indent=2), "```"]
        (out / "report.md").write_text("\n".join(lines) + "\n")
        print(f"Boot test {'PASSED' if ok else 'FAILED'}; report in {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
