# Troubleshooting

## Boot

| Symptom | Try |
|---|---|
| USB drive not listed in the boot menu | Re-write it in Rufus with DD mode. In the firmware setup, enable USB boot. For UEFI, disable "CSM only" mode. |
| "Secure Boot violation" | Secure Boot support is not verified yet. Turn Secure Boot off in the firmware setup and report your hardware in an issue. |
| Black screen after selecting "Try or Install M OS" | Reboot and pick **Try or Install M OS (safe graphics)** (`nomodeset`). |
| Stuck at the M OS logo | Pick **Troubleshooting → Boot with verbose messages** to see where it stops. |
| Very slow live session | Normal for USB 2.0 ports. Use a USB 3 port, or choose **copy to RAM** if you have 8 GB+. |

## Desktop

| Symptom | Try |
|---|---|
| Panels broken after experiments | `mos-desktopctl layout modern` (or `classic`) rebuilds the layout. |
| Effects feel slow | `mos-desktopctl profile performance`, or Control Center → Personalization → Performance. |
| Wayland problem in an app | On the login screen, choose the **Plasma (X11)** session (bottom-left session menu). |
| Can't type Sinhala | Press Ctrl+Space. If nothing happens, run `fcitx5 -d` and check Control Center → Language → Input methods. |
| Welcome shows on every login | Untick **Show at startup**, or `touch ~/.config/mos/welcome-done`. |

## Updates

| Symptom | Try |
|---|---|
| "Checking for updates failed" | Check your internet connection. Open the Update Center details to see the APT error. |
| Interrupted update | Run `sudo /usr/libexec/mos/mos-update-helper repair`, or `sudo dpkg --configure -a && sudo apt-get -f install`. |

## Installer

* Calamares log: `~/.cache/calamares/session.log` (live session) and `/var/log/installer/` on the installed system.
* "Not enough space": M OS needs at least 20 GB.
* If installation fails, save the log before rebooting and attach it to an issue.

## Collecting logs for a bug report

```bash
journalctl -b -p warning --no-pager > journal.txt
cat /usr/share/mos/build-info
inxi -Fxz 2>/dev/null || (lspci -nn; lsusb)
```
