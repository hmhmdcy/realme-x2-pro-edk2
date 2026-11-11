# Debug-only sleep policy helpers

These files are deliberately outside `linux-port/packages/`.

They are not installed by `samurai-platform` and not part of the
production settings baseline. The optional `usbwake-debug` OpenRC service
is also debug-only; do not enable it on a production system.

The production system uses postmarketOS defaults:

- `/etc/sleep-inhibitor.conf` with `ssh-session-open` and `apk-running`;
- the upstream `sleep-inhibitor` service;
- KDE PowerDevil's own default power policy;
- no `powerdevilrc` written by a board package.

## Manual carrier-only guard

`usb-sleep-guard` is a compatibility wrapper around `usbwake-guard` in
`ncm` mode. It returns exit status 254 when a USB network gadget is
attached and its carrier is up. Keep both files together when copying the
helper. If a debug session must survive without an open SSH session,
create a temporary config outside `/etc`:

```sh
tmp=$(mktemp)
cat >"$tmp" <<'EOF'
plugins:
  - path: /path/to/linux-port/debug/sleep-policy/usb-sleep-guard
    name: USB NCM attached (debug only)
    period: .1
    what: sleep
EOF
sudo sleep-inhibitor --config "$tmp"
```

Do not copy this into `/etc/sleep-inhibitor.conf` on a production system.

## PinePhone-style plugged-in guard

`usbwake-guard` adds the PinePhone-style "do nothing while plugged in"
policy without writing a user's `powerdevilrc`. It is a standard
`sleep-inhibitor` plugin, so it also works if the desktop changes.

Modes:

- `power`: hold the sleep lock while a Mains/USB power supply is online;
- `ncm`: hold the sleep lock while the NCM gadget is configured and its
  carrier is up;
- `either` (default): hold the lock when either condition is true.

The NCM side is discovered without board names: the guard scans all
configured UDCs, finds the ConfigFS gadget bound to one of them, then
reads the `ifname` of any `ncm`, `ecm`, `rndis` or `eem` function and
checks that interface's carrier. It accepts `Mains`, `USB_CDP`,
`USB_DCP`, `USB_PD`, `USB_PD_DRP` and `Wireless` supplies as external
power. On this handset the external input happens to be
`/sys/class/power_supply/mp2650-input` (`type=USB`, `online=1` while a
cable is connected); that name is documentation, not a code dependency.

Run the debug instance in the foreground:

```sh
USBWAKE_GUARD_MODE=either \
  sh /path/to/linux-port/debug/sleep-policy/run-usbwake-guard.sh
```

Run it detached for a bounded debug session:

```sh
nohup env USBWAKE_GUARD_MODE=either \
  sh /path/to/linux-port/debug/sleep-policy/run-usbwake-guard.sh \
  >/tmp/usbwake-guard.log 2>&1 &
```

Stop only the detached debug instance:

```sh
pkill -TERM -f '/path/to/linux-port/debug/sleep-policy/run-usbwake-guard.sh'
```

## Optional debug OpenRC service

For a reproducible debug service, install the generic plugin and a
separate `sleep-inhibitor` instance. This mirrors the upstream OpenRC
layout (`supervise-daemon`, `/etc/conf.d`, cgroup cleanup) without
editing the official `/etc/sleep-inhibitor.conf`.

```sh
# Inspect the plan first
sh /path/to/linux-port/debug/sleep-policy/install-usbwake-debug.sh \
  --mode either

# Install and start it
sudo sh /path/to/linux-port/debug/sleep-policy/install-usbwake-debug.sh \
  --enable --mode either
```

Verify:

```sh
rc-service usbwake-debug status
elogind-inhibit --list | grep 'USBwake'
```

Stop and disable:

```sh
rc-service usbwake-debug stop
rc-update del usbwake-debug default
rm -f /usr/libexec/usbwake-guard /usr/libexec/usbwake-run \
  /etc/usbwake-sleep-inhibitor.conf /etc/init.d/usbwake-debug \
  /etc/conf.d/usbwake-debug
```

The service is intentionally not named after the phone or SoC. The only
local policy is the `USBWAKE_GUARD_MODE` value in
`/etc/conf.d/usbwake-debug`; the plugin discovers the actual UDC,
gadget and network function.

Check the raw decision:

```sh
sh /path/to/linux-port/debug/sleep-policy/usbwake-guard
echo $?
```

An exit status of `254` means "hold a sleep inhibitor"; `0` means
"allow normal power policy". While the debug instance is active,
`elogind-inhibit --list` should show
`USBwake power/NCM guard (debug only)`.

Do not load this guard while testing U3/L2 host resume: the power mode
intentionally prevents the system from suspending while plugged in.
It is a debug flywheel policy, not a production power-saving policy.

## Suspend test

Use `linux-port/scripts/test-suspend-rtcwake.sh` only with a physical
recovery path and `SAMURAI_ALLOW_SUSPEND=1`. Do not use `loginctl suspend`
or direct `wakealarm` writes for unattended tests.
