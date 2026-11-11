# Temporary KWin 6.8.2 stable-branch backport

This directory is a temporary downstream package used only while KDE Plasma
6.8.2 is the latest stable release. It is not a board package and contains no
Realme-specific logic. Remove it from the board build inputs once the
distribution provides KWin 6.8.3 or newer.

The first two patches are unmodified upstream stable-branch commits:

- `0101-dpms-cancel-touch-sequences.patch` (`325d02d2b15`) cancels an active
  touch sequence before the DPMS input filter is installed, preventing
  pointer focus from remaining blocked after the screen turns off.
- `0102-ignore-dpms-wakeups-before-sleep.patch` (`5b0a41da8c8`, upstream
  `6a7b78b4`) ignores DPMS-on requests after logind reports
  `PrepareForSleep(true)` until the system has resumed. KDE marks this fix
  `FIXED-IN: 6.8.3`.

The third patch is a temporary downstream workaround:

- `0103-retry-transient-ebusy-commits.patch` retries an atomic commit when
  the msm/DPU driver reports `EBUSY` for a plane that is not attached to a
  CRTC. The pageflip event can be delivered before the plane's fake commit
  reaches `hw_done`, which otherwise makes KWin drop a frame after a wake.
  Retries are bounded and the original failure path remains visible. This is
  a separate transient-commit workaround; it is not the root cause of the
  SOFEF03F 1024/HBM black-screen bug fixed in the kernel panel driver.

Plasma 6.8.2 does not contain either upstream change. Plasma 6.8.3 is
scheduled for 2026-11-10 and the `Plasma/6.8` branch already contains both.
Plasma 6.7.6 contains only the touch-sequence fix. The `0103` workaround is a
local driver-timing workaround and is not part of that branch.

The resulting `6.8.2-r3` keeps Alpine's package split and file layout, including
the `kwin-systemd` subpackage. Build it with an explicit target while 6.8.2 is
still current:

```sh
pmbootstrap build --arch aarch64 kwin
```

Use `--lax` for local incremental rebuilds. Because the APKBUILD declares
`arch=all`, omitting `--arch` lets pmbootstrap autodetect the x86_64 host and
compile an unusable x86_64 package.

The aarch64 `6.8.2-r3` package was built with pmbootstrap 3.12.0 and installed
on the RMX1931 test device. After a `tinydm` restart, ten automated cycles of
lock screen -> DPMS off/on -> synthetic touch swipe produced no new
`Atomic commit failed: EBUSY` and no kernel `busy with a previous commit`.
The automated evidence is in
`E:/edk2-samurai-out/standard-arm64-v731/panel-touch-ebusy-20261110/`.
The final physical-panel visibility check remains a user visual acceptance
step.

After 6.8.3 is available as a signed Alpine binary package:

```sh
apk update
apk policy kwin
apk add --upgrade kwin kwin-systemd
apk policy kwin
```

Both `apk policy` checks must show a repository version of 6.8.3 or newer, not
the locally installed 6.8.2-r3. Restart the Plasma session and complete the
touch/power-key acceptance tests, including repeated lock-screen wake and
swipe cycles with no `Atomic commit failed: EBUSY`, before deleting this
temporary package directory and the local build outputs. Do not ship a locally
built KWin in the board package set unless the distribution version still
reproduces the EBUSY frame drop.
