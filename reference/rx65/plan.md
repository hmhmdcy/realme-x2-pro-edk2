# RX65 — reconnect through WSL and measure full-packet console overlap

User selected WSL as a route around qcusbser and connected the phone. Fresh
state was fastboot, serial62bc28a1/productmsmnile, no EUD or existing owner.
One scoped fastboot reboot returned the existing image; no flashing planned.

Before USB data, require three healthy EUD nodes, exact existing original
driver/terminal/logdump bytes, one current shared 9505 and no known owner.
Resolve current BUSID/instance/port after boot; never assume old6-5/COM14.
Attach only that shared device to WSL, use existing usbmon/PyUSB support, no
forcebind, reset, automatic driver detach or reconfiguration. Finally dispose
the sole USB owner and detach back to Windows.

The prepared helper changes RX52's continuous-reader experiment only in the
marker and probe: once-only R65H=12345678 LF is payload14/wire16, instead of
the old payload7/wire9 probe. Marker delay152ms, existing1009-byte kmsg write,
receipt4sec, continuous IN/separate sink and LEN2 reservation are unchanged.
This is a new full-packet busy-console condition, not a rerun of the old7-byte
passing overlap. No Windows candidate or ZLP registry change is involved.

One manual owner, global180sec, maximum12 manual steps. Fresh Ctrl-U receipt
before data, at most two manual startup attempts. Baseline/overlap/value and
RX/IRQ queries, one immutable dd bs4096 count1 journal and base64 export, drain
and close. Missing ordinary data receipt stops unsent remainder without retry.
If the single overlap probe lacks a receipt, only bounded manual Ctrl-U may
restore sync for diagnostic queries; never resend the probe/command.

Retain exact wire/raw/target-only usbmon, actual OUT length/zero-length OUT,
receipt payload/source, BusyBox value and IRQ/fault/console counts. Compare
the CRC-valid512-record TX journal directly without filling missing bytes.
usbmon is the WSL virtual HCD, not physical DATA0/1/ACK proof. Success would
validate this current WSL/full16 condition, not fix qcusbser reopen or prove
all terminal stability. Full original scope and RX62/RX63 driver trial remain.
Preserve TOP_CFG0x11/RX53 console/IRQ/F1/native and compatible terminals/RX48.
Record/push fork/master only; raw binaries/full driver packages stay external.
