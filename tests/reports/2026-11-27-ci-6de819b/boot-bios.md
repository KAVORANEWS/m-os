# Boot test — M-OS-0.1.0-amd64.iso (BIOS)

KVM: True · RAM 4096 MB · 2 vCPU · result: **PASS**

| Check | Result | Detail |
|---|---|---|
| boots to login prompt | PASS | 45.0 s |
| live user login over serial console | PASS |  |
| os-release identifies M OS | PASS | PRETTY_NAME="M OS 0.1 Preview"<br>NAME="M OS"<br>ID=mos |
| booted via BIOS firmware | PASS | bios |
| SDDM display manager active | PASS | active |
| Plasma desktop running (plasmashell + KWin) | PASS | 50.4 s after power-on |
| M OS Welcome autostarted | PASS | 2086 /usr/bin/python3 /usr/bin/mos-welcome --autostart |
| M OS applications installed | PASS | /usr/bin/mos-about  /usr/bin/mos-control-center  /usr/bin/mos-system-monitor  /usr/bin/mos-update-center  /usr/bin/mos-welcome |
| M OS Python library runs on target | PASS | AMD EPYC 9V45 96-Core Processor 3.8 GiB |
| mos-desktopctl available | PASS | plasma-apply-lookandfeel --apply org.mos.classic.desktop --resetLayout<br>kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnLeft <br>kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnRight IAX |
| firewall active (ufw) | PASS | Status: active |
| AppArmor enabled | PASS | AA-ON<br>apparmor module is loaded. |
| no network services listening on external interfaces | PASS | none |
| SSH not enabled | PASS | not-found<br>not-installed |
| zram swap active | WARN | Command 'swapon' is available in the following places<br> * /sbin/swapon<br> * /usr/sbin/swapon<br>The command could not be located because '/sbin:/usr/sbin' is not included in the PATH environment variable.<br>This is most likely caused by the lack of administrative privileges associated with your  |
| Sinhala fonts available | PASS | Noto Serif Sinhala,Noto Serif Sinhala SemiCondensed Black<br>Noto Sans Sinhala,Noto Sans Sinhala SemiCondensed ExtraLight<br>Noto Serif Sinhala,Noto Serif Sinhala Condensed Medium |
| English and Sinhala locales generated | PASS | en_US.utf8<br>si_LK<br>si_LK.utf8 |
| Sinhala input methods present | PASS | 1<br>/usr/share/m17n/si-phonetic-dynamic.mim<br>/usr/share/m17n/si-samanala.mim<br>/usr/share/m17n/si-sayura.mim<br>/usr/share/m17n/si-singlish.mim<br>/usr/share/m17n/si-sumihiri.mim<br>/usr/share/m17n/si-trans.mim<br>/usr/share/m17n/si-wijesekara.mim |
| no failed systemd units | PASS | none |
| Calamares installer with M OS branding present | PASS | branding.desc  logo.png  show.qml  slide-bg.png  welcome.png |
| clean shutdown | PASS |  |

## Measurements

```
{
  "boot_to_login_prompt_s": 45.0,
  "kernel": "6.12.118+deb13-amd64",
  "boot_to_desktop_s": 50.4,
  "sessions": "Name=mos\nDesktop=KDE\nType=wayland\nName=mos\nDesktop=\nType=unspecified\nName=mos\nDesktop=\nType=tty",
  "ram_used_mb_desktop_idle": "1678",
  "loadavg": "1.13 0.33 0.11 1/393 2410",
  "systemd_analyze": "Startup finished in 3.025s (kernel) + 9.497s (userspace) = 12.523s",
  "top_user_processes_rss_kb": "549436 plasmashell\n338900 plasma-welcome\n277760 kwin_wayland\n247140 DiscoverNotifie\n189732 mos-welcome\n154116 kded6\n152780 xwaylandvideobr\n148016 kdeconnectd"
}
```
