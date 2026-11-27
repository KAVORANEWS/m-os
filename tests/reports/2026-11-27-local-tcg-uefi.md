# Boot test — M-OS-0.1.0-amd64.iso (UEFI)

KVM: False · RAM 1100 MB · 2 vCPU · result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| boots to login prompt | PASS | 194.8 s |
| live user login over serial console | PASS |  |
| os-release identifies M OS | FAIL | PRETTY_NAME="Debian GNU/Linux 13 (trixie)"<br>NAME="Debian GNU/Linux"<br>ID=debian |
| booted via UEFI firmware | PASS | uefi |
| SDDM display manager active | PASS | active |

## Measurements

```
{
  "boot_to_login_prompt_s": 194.8,
  "kernel": "6.12.118+deb13-amd64"
}
```
