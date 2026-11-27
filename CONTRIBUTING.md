# Contributing to M OS

Thanks for helping build M OS!

1. Fork the repository. Create `feature/<short-topic>` from `main`.
2. Read [docs/developer-guide.md](docs/developer-guide.md).
3. Before opening a pull request, run:
   ```bash
   ./scripts/validate-build.sh
   python3 -m unittest discover -s tests/unit
   ./scripts/build-packages.sh && tests/packaging/test-packages.sh dist/packages
   ```
4. In the PR, describe **what you actually tested** (VM/hardware, BIOS/UEFI). "Not tested" is a fine answer. Invented results are not.

## Ground rules

* Only original or properly licensed artwork. No Apple, Microsoft, or other proprietary assets, icons, fonts, or wallpapers.
* Prefer maintained Debian packages over custom code.
* No fake functionality. A button either does the real thing, or it's disabled with an explanation.
* Never commit secrets.
* Code: GPL-3.0-or-later. Artwork: CC-BY-SA-4.0.

## Translations

The Sinhala catalogue is in `applications/python/mos/i18n.py` (see
`docs/localisation.md`). Native-speaker reviews are very welcome.
