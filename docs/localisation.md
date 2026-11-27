# Localisation: English and Sinhala

## What is included (implemented)

| Item | Implementation |
|---|---|
| Sinhala fonts | `fonts-noto-core` (Noto Sans/Serif Sinhala), `fonts-lklug-sinhala` |
| Text rendering | HarfBuzz shaping in Qt/KDE and Firefox (Debian defaults) |
| Locales | `en_US.UTF-8`, `en_GB.UTF-8`, `si_LK` generated in the image (hook `0100-mos-locales`) |
| Input methods | Fcitx 5 + m17n: **Wijesekara** (`m17n_si_wijesekara`) and **Singlish phonetic** (`m17n_si_singlish`). Default profile in `/etc/xdg/fcitx5/profile`. Switch with **Ctrl+Space**. Configure in Control Center → Language. |
| Plasma / KDE apps | Debian ships KDE's own Sinhala translations, as far as KDE translators have completed them |
| M OS apps | Small catalogue in `applications/python/mos/i18n.py`, used when `LANG`/`LANGUAGE` starts with `si` |

## Coverage status (honest)

* **M OS applications:** about 35 core strings (navigation, section names, main actions) translated. **Most descriptive text is still English only** and falls back to English.
* **KDE Plasma:** KDE's Sinhala translation is partial. Untranslated strings show in English.
* **Installer (Calamares):** uses Calamares' upstream translations. Sinhala coverage depends on upstream.
* **None of the Sinhala strings have been reviewed by a native speaker yet.**

## Planned

* Move M OS apps to Qt Linguist (`.ts`/`.qm`) or gettext with full string extraction.
* Native-speaker review and a translation coverage report in CI.
* Optionally preselect Sinhala in the live session via a GRUB menu entry (`locales=si_LK`).
