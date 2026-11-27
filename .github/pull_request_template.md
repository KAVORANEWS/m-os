## Summary

<!-- What does this change and why? -->

## Type
- [ ] Build / ISO
- [ ] Desktop configuration / branding
- [ ] M OS application
- [ ] Installer
- [ ] Security
- [ ] Documentation

## Testing
<!-- Real results only. Say "not tested" if it was not tested. -->
- [ ] `./scripts/validate-build.sh`
- [ ] `python3 -m unittest discover -s tests/unit`
- [ ] `./scripts/build-packages.sh` + `tests/packaging/test-packages.sh`
- [ ] ISO built and boot-tested (`tests/boot/boot-test.sh`) — firmware: BIOS / UEFI
- [ ] Tested on real hardware (model: …)

## Checklist
- [ ] No credentials, tokens or secrets added
- [ ] No proprietary artwork or assets added
- [ ] Docs updated (implemented vs. tested vs. planned kept accurate)
