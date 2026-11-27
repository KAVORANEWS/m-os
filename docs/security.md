# M OS security

## Defaults

| Area | Default | Where |
|---|---|---|
| User accounts | Installer creates a normal user in the `sudo` group; root has no password (`setRootPassword: false`) | Calamares `users.conf` |
| Passwords | Minimum 8 characters in the installer; stored hashed by `chpasswd`/shadow | hook `0200-mos-installer` |
| Firewall | `ufw` on: deny incoming, allow outgoing, deny routed; enabled on first boot | `mos-firewall-setup.service` |
| Mandatory access control | AppArmor enabled (Debian kernel default) + `apparmor-profiles`, `apparmor-profiles-extra` | package list `60-mos-security` |
| Remote access | No SSH server installed; the build hook disables `ssh`/`sshd` if one gets pulled in | hook `0300-mos-system` |
| Package trust | Official Debian repositories only, signed with Debian archive keys; `trixie-security` enabled | live-build `--security true` |
| Updates | Package lists refresh and updates download daily. Installation stays user-controlled in the M OS Update Center (`unattended-upgrades` is installed but off) | `/etc/apt/apt.conf.d/52mos-unattended-security` |
| Screen lock | Auto-lock after 10 min, lock on resume | `/etc/xdg/kscreenlockerrc` |
| Kernel | `kptr_restrict=1`, `dmesg_restrict=1`, `yama.ptrace_scope=1`, unprivileged BPF disabled, BPF JIT hardening, protected links/fifos/regular files | `/etc/sysctl.d/90-mos-hardening.conf` |
| Network stack | No ICMP redirects or source routing, SYN cookies, martian logging | same file |
| Telemetry | None. M OS apps make no network requests except APT through the Update Center and links the user opens | — |

## Privileged operations

M OS apps run as the logged-in user. Administrative actions go through polkit:

* `org.mos.updatecenter.helper` → `/usr/libexec/mos/mos-update-helper {refresh|upgrade|repair}`
* `org.mos.controlcenter.firewall` → `/usr/libexec/mos/mos-firewall-helper {status|enable|disable}`

Both helpers accept a fixed verb, refuse anything else, and need administrator
authentication (`auth_admin_keep`). `upgrade` never removes packages.

## Disk encryption

The Calamares partition step has an "Encrypt system" option (LUKS). Calamares
then installs `cryptsetup-initramfs`, and the M OS Plymouth theme shows the
passphrase prompt.

* **Status: not yet tested by the M OS project.** Test it in a VM before relying on it.
* LUKS protects data at rest when the machine is off. It does not protect a running, unlocked system.
* If you lose the passphrase, the data cannot be recovered.

## Secure Boot

The ISO is built with `--uefi-secure-boot enable`, which uses Debian's
Microsoft-signed `shim` and Debian-signed GRUB and kernel. M OS's own packages
contain no kernel modules or boot code, so the chain stays Debian-signed.
**Booting with Secure Boot enabled has not been verified yet.** The CI boot test
uses OVMF without enrolled keys. See `hardware-compatibility.md` for the current status.

## Reporting vulnerabilities

See [`SECURITY.md`](../SECURITY.md).
