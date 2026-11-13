Trivy reports **47 HIGH/CRITICAL findings**, all listed below with the reason they remain. None are in the Python packages the API installs; all come from Debian packages in the `python:3.12-slim` base image.

| Package | Findings | Debian status | Fixed version | Note |
|---|---|---|---|---|
| bsdutils | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libacl1 | 1 (CVE-2026-54369) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libblkid1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| liblastlog2-2 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libmount1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libncursesw6 | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libsmartcols1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libsqlite3-0 | 3 (CVE-2026-119373, CVE-2026-119374, CVE-2026-119379) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libsystemd0 | 1 (CVE-2026-16742) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libtinfo6 | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libudev1 | 1 (CVE-2026-16742) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libuuid1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| login | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| mount | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| ncurses-base | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| ncurses-bin | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| perl-base | 1 (CVE-2026-9538) | fix_deferred | - | Debian decided to defer the fix (low impact in Debian's assessment); nothing to upgrade to yet. Rescan regularly. |
| util-linux | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |

Action taken: the runtime stage of `Dockerfile.prod` runs `apt-get update && apt-get upgrade -y`, which installs every Debian security fix that exists today, and the image was rebuilt and rescanned. The remaining findings have no fix available yet; the plan is to rebuild with `docker build --pull` and rescan weekly.
