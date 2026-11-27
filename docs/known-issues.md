# Known issues — M OS 0.1 preview

This list is updated from real test runs. See `tests/reports/`.

| # | Issue | Status |
|---|---|---|
| KI-1 | Installer (Calamares) has no automated end-to-end test yet. Manual VM installation is the only supported verification. | open |
| KI-2 | Not tested on real hardware, including the i5-6500 / HD 530 target. | open |
| KI-3 | Secure Boot with enrolled Microsoft keys is configured (Debian-signed chain) but not verified. | open |
| KI-4 | Sinhala UI translation is partial and not reviewed by native speakers. | open |
| KI-5 | `mos-desktopctl layout` resets panel customisations, because the layout is re-applied from the global theme. | by design, documented |
| KI-6 | Because of `Conflicts: desktop-base`, Debian metapackages that depend on `desktop-base` (e.g. `task-desktop`) cannot be installed. | by design |
| KI-7 | M OS packages are installed from the ISO only. There is no M OS APT repository yet, so M OS-specific packages don't get updates after installation (Debian packages do). | planned for 0.5 |
