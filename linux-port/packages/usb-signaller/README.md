# usb-signaller board descriptor and lifecycle backports (0.4.3-r11)

This package tracks Alpine's `usb-signaller` 0.4.3 and adds an upstreamable
configuration layer for USB device descriptors. The standard postmarketOS
stack still owns gadget modes, D-Bus, NetworkManager, FunctionFS, MTP and
udev integration; the patch only lets a board supply values that were
previously hard-coded.

Board values live in
`samurai-platform:/etc/usb-signaller.d/90-samurai.toml`. No board-specific
USB transport or kernel ABI is added.

Patch contents:

- optional `[gadget]` and per-mode descriptor overrides;
- device class, configuration power and NCM `qmult`;
- longer enumeration wait before starting userspace services;
- safe handling of an initramfs gadget with no configuration metadata;
- serialized D-Bus mode changes so the startup default cannot race a user
  request;
- OpenRC mode services that fail instead of remaining permanently `crashed`
  after their one-shot network setup exits;
- standard `/etc/unudhcpd.conf` address loading and explicit
  NetworkManager ownership of the NCM interface;
- bounded wait/retry for `usb0` before `nmcli connection up`, preventing
  a valid gadget from being left in charging-only state during a slow
  host re-enumeration;
- bounded retry of `nmcli device set ... managed yes`, because a post-role
  switch netdev can appear before NetworkManager accepts it.
- preserve Developer/Tethering when the host has addressed the gadget but
  stopped before SET_CONFIGURATION, so the board recovery service can
  reconnect the public UDC interface instead of downgrading to Charging.
- stop the Developer/Tethering/MTP mode service before switching to the
  DWC3 host role. Without this, OpenRC keeps the old one-shot service
  marked as started; returning to device mode calls `rc-service start`,
  which is a no-op, leaving the new `usb0` unmanaged and `unudhcpd` on a
  stale socket.
- tolerate an already-removed `usb0` or NetworkManager connection during
  mode teardown. The stop path is best effort when host/role teardown has
  already removed the netdev; otherwise OpenRC retains the service as
  started and the next gadget replacement cannot run its `up` path.
- stop the mode services in the `usb-signaller` OpenRC `start_pre` hook,
  so a fresh daemon starts the selected mode instead of inheriting a
  stale one-shot service state.
- retry the mode-service `start` operation a bounded number of times
  when the preceding one-shot service is still settling. This avoids
  deleting the new configfs gadget and falling back to Charging merely
  because `rc-service start` returned a transient error.
- keep the NCM profile `autoconnect` enabled but only request an explicit
  NetworkManager activation after `usb0` reports carrier 1.  A gadget
  bound to a UDC exists before a host enumerates it; forcing `nmcli
  connection up` at carrier 0 leaves a false wired-network indicator in
  the Plasma status bar and deactivates only when the mode service is
  stopped.
- wait up to 10 seconds for the UDC to appear after a device-role switch.
  `URS::set_role()` returns when the role sysfs value changes, but the
  associated UDC can be registered asynchronously; the old immediate
  `discover_udcs()` could return empty and report `UDC failed`.  Host
  mode still returns immediately and no board-specific path is added.

The patches are intended to be submitted upstream. Until accepted, they are
version-pinned to upstream tag `v0.4.3`; the current package is
`0.4.3-r11`.

With the deployed dual-role kernel, upstream usb-signaller also discovers
the standard `a600000.usb-role-switch` provider. It advertises
`host_mode` through `com.meego.usb_moded`, reports `mode_request` as
`host_mode` while the role is host, and restores Developer mode when the
role returns to device. The board does not implement a private configfs
or URS handler for this.

On 2026-11-13 the packaged `0.4.3-r9` main and OpenRC APKs were installed
with the 0006/0007/0008 lifecycle fixes:

```text
/usr/bin/usb-signaller
SHA-256 5dfd694cf325cac36ab490cf27e95013a1029b0877f17902fdd1b4ab99bcba18

usb-signaller-0.4.3-r9.apk
SHA-256 fe4c960a22a92ef875fb2f5d9df5cf2880319bd281ed15fbadc18f62525c0c12

usb-signaller-openrc-0.4.3-r9.apk
SHA-256 4c87cec580658701234e957a85d8badeaa1babca3dfd904d6376097e9ef1a66b

usb-signaller-systemd-0.4.3-r9.apk
SHA-256 03954a4c5be9203488cd7b57f9bcf83556942905db5f9a5e111ef1e8676d806f
```

The standard host-mode test passes on the RMX1931 after the package
install: host mode registers xHCI, and returning to device restores
`usb0` managed, carrier 1, `unudhcpd.usb0` restarted, Windows DHCP
`172.16.42.2/24` and USB NCM SSH. Three consecutive packaged host→device
rounds passed at 12:20 CST. The full mode-cycle and four offline
recovery regressions also pass with r9.

The board config now also supplies
`[main] default_mode = "developer_mode"`; a stopped usb-signaller can
therefore recreate Developer after a clean start.

Patch 0008 closes the OpenRC supervisor restart race by retrying only
the mode-service `start` operation, up to eight times at five-second
intervals. The first installed r9 check kept UDC `configured`, carrier
1, NetworkManager `usb0:connected` and `unudhcpd.usb0` running for the
full 65-second observation window. Five consecutive plain
`rc-service usb-signaller restart` rounds then passed with zero
failures. This does not retry or mask `stop` errors, and it remains
disabled after the bounded budget is exhausted.

On 2026-11-14 the r11 main/OpenRC/systemd APKs were built natively on
RMX1931 and verified:

```text
usb-signaller-0.4.3-r11.apk
SHA-256 c021d2d3d4f2c3fe32669f56e9c20d4cdbf55be9ed79fa0459d9baee39caa465

usb-signaller-openrc-0.4.3-r11.apk
SHA-256 543c0982a3e7bfb449b075376416a2d1995c0c8f20f2bb7f9b6bea2f86abb051

usb-signaller-systemd-0.4.3-r11.apk
SHA-256 9778856bc4ce8201f9ffb2a8e2878cd5e2f116609d644e44a3251d4b5a9e9359
```

`apk verify` passed, and `apk add --no-network --upgrade` installed
main + OpenRC r11. Restarting the packaged binary applied Developer
mode with `UDC=present`, kept `usb0` NetworkManager-`unavailable` at
carrier 0, and did not activate `Samurai NCM`. `set_mode host_mode`
restored URS/Type-C host and re-enumerated the mouse receiver. Old r9
binary remains at `/root/usb-signaller-r9-20261114` for rollback.
