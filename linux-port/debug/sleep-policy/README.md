# Debug-only sleep policy helpers

These files are deliberately outside `linux-port/packages/`.

They are not installed by `samurai-platform`, not registered in OpenRC and
not part of the production settings baseline. Use them only for a bounded
debug session, then remove the process and any temporary config.

The production system uses postmarketOS defaults:

- `/etc/sleep-inhibitor.conf` with `ssh-session-open` and `apk-running`;
- the upstream `sleep-inhibitor` service;
- KDE PowerDevil's own default power policy;
- no `powerdevilrc` written by a board package.

## Manual carrier-only guard

`usb-sleep-guard` is the historical helper that returns exit status 254
when a USB NCM gadget is attached. It is only meaningful as a
`sleep-inhibitor` plugin. If a debug session must survive without an open
SSH session, create a temporary config outside `/etc`:

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

## Suspend test

Use `linux-port/scripts/test-suspend-rtcwake.sh` only with a physical
recovery path and `SAMURAI_ALLOW_SUSPEND=1`. Do not use `loginctl suspend`
or direct `wakealarm` writes for unattended tests.
