# RMX1931 Plasma Mobile desktop recipe 4-r19

This package is the thin board layer around the postmarketOS Plasma Mobile
baseline. It owns the tinydm session selection and the old-session cleanup
hook; it does not own the power-key or DPMS policy.

## Official path

The official postmarketOS Plasma stack uses:

- `postmarketos-base-ui` with `HandlePowerKey=ignore` in
  `/etc/elogind/logind.conf`;
- KWin's `DpmsInputEventFilter` for wake-on-input and DPMS transitions;
- PowerDevil's mobile default `PowerButtonAction=ToggleScreenOnOff` (128).

## Auto-suspend is disabled by default (4-r17, both keys since 4-r19)

`powerdevilrc` is installed as `/etc/xdg/powerdevilrc`, so it is a system
default rather than a per-user override, and a user's own
`~/.config/powerdevilrc` still wins.

All three profiles pin both spellings of KDE's "Never":

```ini
[AC][SuspendAndShutdown]
AutoSuspendAction=0
AutoSuspendIdleTimeoutSec=0
[Battery][SuspendAndShutdown]
AutoSuspendAction=0
AutoSuspendIdleTimeoutSec=0
[LowBattery][SuspendAndShutdown]
AutoSuspendAction=0
AutoSuspendIdleTimeoutSec=0
```

The two keys exist because KDE's two power frontends write "Never"
differently: the desktop KCM sets `AutoSuspendAction=0`
(`PowerDevil::PowerButtonAction::NoAction`), the Plasma Mobile KCM sets
`AutoSuspendIdleTimeoutSec=0`.  Setting both means either UI reports and
enforces "Never" instead of "Sleep after 0 seconds".

The reason is measured, not stylistic: on the 7.3.1 kernel the device only
supports `s2idle`, and entering `s2idle` takes down both the USB/NCM link
and the Wi-Fi link.  Those are the only remote access paths, so an
unattended suspend makes the device unreachable until someone presses the
power key.  Logged on 2026-11-19:

```text
systemd-logind: suspend requested from client ... ('org_kde_powerde')
kernel: PM: suspend entry (s2idle)
kernel: PM: suspend exit            (13 minutes later, on power key)
```

`AutoSuspendAction=0` is not a private debug flag: it is the same value the
desktop KCM writes when "When inactive: Never" is selected, and
`PowerDevilProfileSettings.kcfg` defines it as a normal profile setting
(`UInt`, `NoAction = 0`).  The acceptance checks assert all three sections
contain both keys and reject any other action, so a future refactor cannot
silently re-enable suspend.

The upstream **critical battery** action is deliberately left alone.  At
5% charge PowerDevil still follows `[BatteryManagement]
BatteryCriticalAction`, whose default is `Sleep` when the system can
suspend.  That is a safety floor against over-discharging the pack, not
idle auto-suspend, and it is not affected by the profile keys above.

An explicit suspend (KDE menu, `systemctl suspend`) still works and still
drops the links.  Use the power key to wake.

Runtime evidence on the live device (2026-11-19):

```text
22:17:45 suspend requested from client ... ('org_kde_powerde')   <- before
22:17:45 kernel: PM: suspend entry (s2idle)
22:30:53 kernel: PM: suspend exit                                  (power key)
22:36:51 plasma-settings: Setting to never suspend                <- changed
23:36:58 suspend requests this boot: 1                            <- 60 min, no more
```

Two verification layers are used, since PowerDevil does not expose the
idle timeout as a D-Bus property:

- `linux-port/scripts/check-settings-provenance.sh` asserts all three
  sections in `/etc/xdg/powerdevilrc` contain `AutoSuspendAction=0` and
  `AutoSuspendIdleTimeoutSec=0`, and that neither key has any other value.
- `linux-port/scripts/check-powerdevil-effective.sh` additionally proves
  the live service answers on the session bus and that the boot log
  contains no repeated suspend request after the setting was pinned.

There is no per-device power-key daemon in the official pmaports design.

### Ownership caveat for images built outside apk

The live image on 2026-11-20 shows `samurai-desktop 4-r16` installed while
`/etc/xdg/powerdevilrc` exists and is *not* listed in
`/lib/apk/db/installed`.  The image builder wrote the file directly into
the filesystem, so the value is live but no package owns the path.  That is
harmless for the running system, and it is why
`check-settings-provenance.sh` now reports it: a file no package owns
cannot be replaced by `apk`.

apk-tools 3.x does not treat this as a conflict.  In
`apk_db_migrate_files_for_priority()` an existing file with no installed
owner takes the `COMMIT` path and is then recorded as owned by the new
package, so installing a repository build converts the stray file into
a normal, tracked one.  Until that happens, the source of truth for this
default is the package plus the prebuilt image, not the installed database.

## Local change

4-r16 removes the retired `samurai-powerkey` Python bridge and its OpenRC
service from the package. During upgrade, the post-install script stops and
disables the old service, removes its binary and init script, and leaves
`/var/log/samurai-powerkey.log` in place as evidence. The KWin/PowerDevil
path then owns the physical power key directly.

The remaining files are:

- `/usr/share/samurai/plasma-mobile`: session metadata;
- `/usr/libexec/samurai-tinydm-stop`: bounded cleanup of a stale KWin session
  before tinydm restarts the autologin seat;
- `samurai-desktop.post-install`: tinydm session selection and migration away
  from historical board overrides;
- `/etc/xdg/powerdevilrc`: the board's "never auto-suspend" system default
  described above.

## Tradeoff and evidence

The bridge previously masked a panel-side wake bug by forcing a KScreen
modeset and rewriting backlight sysfs. That made the power key appear to work
while causing repeated 60/90 Hz panel initialization. The panel wake issue is
being fixed in the panel driver instead, so the bridge is no longer part of
the production path.

The installed `kwin-6.8.2-r2` package includes the upstream touch-sequence
cancel fix: the constructor of `KWin::DpmsInputEventFilter` calls
`KWin::TouchInputRedirection::cancel()` before installing the DPMS filter.

## Rollback

The last bridge-based package is kept as
`samurai-desktop-4-r15.apk`. Reinstall it only for a bounded diagnostic
comparison; do not treat it as the target architecture.
