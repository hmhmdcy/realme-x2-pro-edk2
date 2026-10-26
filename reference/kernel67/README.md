# Kernel 67 evidence: USB provider restored; CPU7 DTB candidate not active

`verify.py` audits the compressed captures offline. It checks every received
frame, decoded payload, positive virtual USB IN/raw equality, worker closure,
device SHA256/gzip CRC, exact one-option config change, and final ownership.
No reconstruction or insertion of missing bytes is used.

The two full device-side dmesg snapshots are independently validated:

| Snapshot | Plain bytes / SHA256 | Compressed bytes / SHA256 |
|---|---|---|
| DTB-only boot #59 | 52982 / `7c72b69f83170e06789106996541f79b02e341f5f81f159e3750453b4ad27d61` | 12227 / `6f58add5ab25919e445e25448420e4486bca0a0aff9fd3fd282174ca1936a782` |
| USB provider boot #60 | 53788 / `1a42e5406e88458205f01e8acdec3593508e9b8e31a039c1659a047f6caa874a` | 12618 / `5dd9f486e5df2a9f1172816e8669d061691f7eae583182ed9e7cce411c8643a5` |

`opp-facts`, `opp-live-dt`, and `usb-facts` also pass device hash and gzip CRC.
Boot #60 has HS PHY and dwc3 bindings, a UDC, empty devices_deferred, and taint 0.
This confirms controller initialization; no USB network/gadget function or
host peripheral transaction has been tested. CPU7 OPP warnings remain.

The first OPP log export has damaged base64; the first USB log export decodes
12609 instead of 12618 bytes and fails SHA256/CRC. Their exact received sections
and failed metadata are preserved. The first live-DT export lost its start
marker and is retained in the untouched capture. A USB facts command stops
after a missing receipt: 13 data frames submitted, 12 acknowledged, no automatic
data retry. The next owner clears the unfinished line with a fresh Ctrl-U and
exports the same saved snapshot. These failures are observation limits.

The DTB-only candidate adds a CPU7 2.9568 GHz OPP, sourced from the pinned
maintained SM8150 tree. Compilation and FAT extraction match, but checksum-valid
live-DT facts say `OPP_ABSENT`. The current EFI loader takes the firmware DTB;
the FAT DTB is not active. This attempt is not a runtime OPP-content test.
`mirror-before.diff` separately records stale Windows EUD/PON/bootargs entries
being synchronized from the already-running actual tree; they are not new fixes.

Only two logdump flashes occurred. No boot, userdata, GPT, Windows driver,
EUD code, earlycon pacing, initramfs, or terminal change. F1 is used once per
flash, followed by independent fastboot serial/product validation. Helpers
close in finally; final state is COM14 Windows, Shared/unattached, three healthy
nodes, no known owner. Image/DTB binaries remain external; source and integrity
evidence are kept here. All captures contain kernel/sysfs diagnostics only.

Sources, priorities and limitations: [session67](../../sessions/67-usb-provider-and-dtb-activation.md).
