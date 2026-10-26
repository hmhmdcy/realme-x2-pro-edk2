# RX45 evidence: persistent RX mask alone does not fix missing receipts

2026-10-09. Read [session 45](../../sessions/45-rx-mask-before-arrival.md) for
the measured result, retained state and next step. This is an excluded
diagnostic, not a stability fix. At the end of session 45, the current driver
was restored to RX44. Session 46 subsequently adds an IRQ diagnostic; this
historical verifier checks the archived pre-RX45 source, not a future driver.

Raw captures are byte-identical exports from E:\edk2-samurai-out\rx45.
The boot helper appended extensions to `mask-boot.raw`; the export calls
that capture `mask-boot` without changing its bytes. Text and events are
normalized to LF with trailing whitespace removed. Originals remain external.
SHA256SUMS covers the raw captures and exact tested candidate source.

`python3 verify.py` checks the missing-pending boundary, exact successful
14-byte command/output, F1, logdump-only flashes and baseline return. It
reports resynchronization bytes explicitly: the mask boot had 8 stray bytes,
so it must not be described as a lossless boot capture. Probe captures have
no stray or incomplete bytes; this alone still does not prove lossless TX.

`save-evidence.py` exports files only. The tested candidate and build script
are retained for audit; neither replaces the current restored driver.
The candidate build succeeded with one format warning: `u32 | BIT(0)` is
unsigned long, passed to a `%02x` boot diagnostic. The independent masked
MMIO readback checked the configured value, and the log printed `1d` as
expected on arm64. Preserve the exact tested source; fix the format before
reusing this diagnostic in any permanent implementation.
