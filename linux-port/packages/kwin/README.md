# Temporary KWin 6.8.2 stable-branch backport

This directory is a temporary downstream package used only while KDE Plasma
6.8.2 is the latest stable release. It is not a board package and contains no
Realme-specific logic. Remove it from the board build inputs once the
distribution provides KWin 6.8.3 or newer.

The two patches are unmodified upstream stable-branch commits:

- `0101-dpms-cancel-touch-sequences.patch` (`325d02d2b15`) cancels an active
  touch sequence before the DPMS input filter is installed, preventing
  pointer focus from remaining blocked after the screen turns off.
- `0102-ignore-dpms-wakeups-before-sleep.patch` (`5b0a41da8c8`, upstream
  `6a7b78b4`) ignores DPMS-on requests after logind reports
  `PrepareForSleep(true)` until the system has resumed. KDE marks this fix
  `FIXED-IN: 6.8.3`.

Plasma 6.8.2 does not contain either change. Plasma 6.8.3 is scheduled for
2026-11-10 and the `Plasma/6.8` branch already contains both. Plasma 6.7.6
contains only the touch-sequence fix.

The resulting `6.8.2-r2` keeps Alpine's package split and file layout, including
the `kwin-systemd` subpackage. Build it with pmbootstrap only while 6.8.2 is
still current.

After 6.8.3 is available as a signed Alpine binary package:

```sh
apk update
apk policy kwin
apk add --upgrade kwin kwin-systemd
apk policy kwin
```

Both `apk policy` checks must show a repository version of 6.8.3 or newer, not
the locally installed 6.8.2-r2. Restart the Plasma session and complete the
touch/power-key acceptance tests before deleting this temporary package
directory and the local build outputs. Do not ship a locally built KWin in the
board package set.
