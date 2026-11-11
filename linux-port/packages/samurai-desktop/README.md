# RMX1931 Plasma Mobile desktop recipe 4-r16

This package is the thin board layer around the postmarketOS Plasma Mobile
baseline. It owns the tinydm session selection and the old-session cleanup
hook; it does not own the power-key or DPMS policy.

## Official path

The official postmarketOS Plasma stack uses:

- `postmarketos-base-ui` with `HandlePowerKey=ignore` in
  `/etc/elogind/logind.conf`;
- KWin's `DpmsInputEventFilter` for wake-on-input and DPMS transitions;
- PowerDevil's mobile default `PowerButtonAction=ToggleScreenOnOff` (128).

There is no per-device power-key daemon in the official pmaports design.

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
  from historical board overrides.

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
