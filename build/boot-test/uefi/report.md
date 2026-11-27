# Boot test — M-OS-0.1.0-amd64.iso (UEFI)

KVM: False · RAM 1400 MB · 2 vCPU · result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| boots to login prompt | PASS | 193.4 s |
| live user login over serial console | PASS |  |
| os-release identifies M OS | FAIL |  |
| booted via UEFI firmware | FAIL |  |

## Measurements

```
{
  "boot_to_login_prompt_s": 193.4,
  "kernel": ""
}
```
