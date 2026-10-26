# RX65 — WSL full native input succeeds; tty TX loss remains

See [session 65](../../sessions/65-wsl-full-packet-console-overlap-and-tx-gap.md).

One busy-console native14/wire16 probe, once only, accepted via=console and
independently executed by BusyBox. All990 console digits arrive. The same
continuous owner subsequently loses nine source1 tty TX frames: CPU journal
seq8221,8223..8228,8230..8231,36 payload/54 wire bytes. The other503 records
match directly. Complete virtual HCD positive IN equals every raw capture.
This does not require qcusbser or COM reopen; WSL is not a complete repair.

The initial immutable snapshot export is short and fails CRC. A separate
compressed export of the same saved snapshot passes gzip and journal CRC
44ba763a,512 records seq7868..8379. No evidence is filled or reconstructed.
`python3 analyze.py . --out /tmp/rx65-analysis.json` verifies the byte/receipt/
CRC/unique-anchor boundaries against preserved captures; output path is external.

Raw/usbmon are deterministic gzip copies (mtime0); decompressed SHA and exact
stored SHA are in manifest.json. Text artifacts are UTF8 LF. Consumed helper
and launchers reference the external experiment paths; do not rerun them.
Three startup/preflight errors are documented in session65; failed metadata
wsl-journal.json is not a completed capture. Helpers/scripts are evidence,
not a released interactive terminal. No driver/image/private key is included.

Preserve TOP_CFG0x11/whole-frame/RX53 console IRQ/F1/compatible and native
terminals/RX48 rollback. No flash, driver/security change or Windows COM owner;
one existing-image fastboot reboot and normal cold-start com-up. Finally all
USB owners close/dispose/detach, final three nodes OK, COM14 old binding.
Original full stability and Windows candidate validation remain open.
