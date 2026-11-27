# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x (developer preview) | Security fixes on a best-effort basis |

M OS packages most software straight from Debian 13. Vulnerabilities in
Debian packages (kernel, Plasma, Firefox, …) are fixed through
`trixie-security`, which the M OS Update Center installs. Please report those
to Debian: <https://www.debian.org/security/>.

## Reporting a vulnerability in M OS code

This covers the M OS apps, helpers, polkit policy, build scripts, and default
configuration.

* Use **GitHub → Security → Report a vulnerability** (private advisory) on
  <https://github.com/dotsoftwarelk/m-os>.
* Please don't open a public issue for unfixed vulnerabilities.
* Include the affected version (`cat /usr/share/mos/build-info`), steps to reproduce, and the impact.

We aim to acknowledge reports within 7 days.

## Design rules

* No telemetry, no hidden network connections.
* No credentials or secrets in the repository. CI uses only the scoped `GITHUB_TOKEN`.
* Privileged code runs only through fixed-verb helpers authorised by polkit.
* See [docs/security.md](docs/security.md) for the security baseline.
