# RX48: bounded IRQ grace and CRC-protected issued-TX records

See [session 48](../../sessions/48-irq-grace-and-tx-journal.md) and
[source audit](source-audit.md). Only logdump was flashed: candidate A added
an IRQ watchdog observation grace; candidate B added a software TX journal
and explicit read-only GIC state query. TOP_CFG=0x11, whole-frame RX,
console/F1, TX pacing and the installed RX47 terminal are retained.

The immutable 3120-byte snapshot has a valid CRC and 512 issued MMIO frame
records, all matched in the same owner's original capture. No TX loss was
observed in that window. The grace wait/recovery/expiry branches were not
exercised. These results do not establish a physical root cause or solve
the historical missing receipts/TX text. Compatible startup needed a retry.

`.raw`, `.bin` and C source snapshots are byte-identical external copies.
Other text is normalized to UTF-8/LF without trailing whitespace; original
and exported hashes are retained in `exports.json`, and `SHA256SUMS` covers
the exports. No raw bytes are repaired. Images, existing all-device ETL/XML
and unrelated USB device inventories stay external.

Run `python3 verify.py` for evidence integrity, exact input/receipt/output,
boot/F1, compatibility and an independent journal CRC/frame comparison.
`analyze-journal.py native-journal.raw --out /tmp/rx48-journal` exports a
validated snapshot and reports an alignment aid. Unknown prefix/suffix
and invalid CRC are never converted into loss claims. Software records
prove issued MMIO values, not physical USB delivery or acknowledgements.
