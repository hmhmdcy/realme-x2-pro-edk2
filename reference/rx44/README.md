# RX44 evidence

Read sessions/44-rx-receipt-counters.md for chronology, artifact hashes,
limitations and next steps; source-audit.md links fixed primary sources.

Raw captures are byte-identical exports from E:\edk2-samurai-out\rx44.
SHA256SUMS protects the raw files. Text/event exports have LF line endings
and trailing whitespace removed; original exports remain in that directory.

`python3 verify.py` decodes raw frames and checks the before/after counters,
the failed native command's missing-pending boundary, a successful native
payload/output, boot, F1 and final live receipt. It cannot distinguish a
short-lived unsampled pending state from no EUD delivery, and it does not
certify reliable delivery or lossless TX.

`save-evidence.py` performs only filesystem export, with no device access.
The current driver is linux-port/eud.c; it has the same RX41 hardware access
order, wait state and TX pacing, plus software counters and a longer Ctrl-U
diagnostic receipt. The original RX41 source and both intermediate/current
Image backups are retained externally as named in the session.
