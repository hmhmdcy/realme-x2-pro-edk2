# usb-signaller board descriptor overrides (0.4.3-r3)

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
  host re-enumeration.

The patch is intended to be submitted upstream. Until accepted, it is
version-pinned to upstream tag `v0.4.3`; the installed package is
`0.4.3-r3`.
