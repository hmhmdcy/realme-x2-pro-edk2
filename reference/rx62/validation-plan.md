# RX62 validation target — original native EUD stability

This is a prepared plan, not an executed phone experiment or a completed repair.
Keep RX41 TOP_CFG=0x11 / whole-frame payload and RX53 console/IRQ behavior.
The existing native and compatible terminals and RX48 firmware rollback remain.

## Build and loading prerequisites

1. Assemble only the eight completed, exact Microsoft HTTPS ranges. Inspect
   the kit launch scripts and verify Microsoft's compiler/tool signatures.
2. Build the nine-module candidate as Release|x64, with signing and deployment
   disabled. Record actual compiler/linker diagnostics and binary provenance.
3. Stamp and validate the EUD-only INF with WDK InfVerif. Generate the catalog
   with Inf2Cat using local time and explicit supported Windows x64 targets.
4. Resolve a supported loading environment before any driver installation.
   Current Secure Boot and memory-integrity settings are read-only evidence;
   this plan does not change them, install trust roots or modify BCD.
5. Keep the exact original qcusbser 2.1.3.5 / oem102.inf rollback copy. Limit
   any later driver comparison to the single present 05c6:9505 device. Resolve
   its current software registry key from PnP instead of assuming slot 0008
   remains the same after rebinding. No 9501/control interface changes.

## Primary causal comparison: ordinary reopen

Use the **same compiled candidate binary**, first with the new
QCEudPreserveToggleOnOpen DWORD disabled, then enabled. Changes between
ordinary closes and reopens are restricted to this option; its helper reads
the option at FileCreate, so no PnP reload is needed for the comparison.
Confirm observed pipe resets for disabled and their absence for enabled.
Replacing the old proprietary driver alone is not an isolated intervention.

Predefine odd/even successful short-IN close boundaries and keep short OUT
only, separating the full-packet/ZLP issue. Count actual successful USB IN
completions, retain wire/raw bytes, and cross-check the device CRC journal.
Do not infer physical DATA0/1 from CPU-issued journal records alone.

One owner at a time. Manual bounded steps. A fresh startup receipt must
precede once-only data; only the existing bounded startup Ctrl-U retry is
allowed. Close/Dispose/Detach in finally; drain diagnostic queries before
close. Stop on unexpected device state or the predeclared time bound.

The positive result needed is elimination of the previously predicted odd
ordinary-reopen first-packet gap **with the intervention actually active**,
not another passing even sample, timestamp-only inference or swallowed loss.
Record limitations and repetitions required for a stability claim.

## Remaining native acceptance requirements

| Requirement | Evidence needed before completion |
|---|---|
| Ordinary reopen first-frame preservation | Exact first wire/status bytes vs CRC journal, driver receive count/raw and USB trace, with same-binary flag-off/on observation |
| Startup reception | Fresh receipt with startup retries distinguished from once-only command input |
| Native multi-character command input | Accepted full payload for LEN 1 and 3..14, and correct BusyBox execution/output without data retransmission |
| Full LEN14 / 16-byte wire OUT | Separate ZLP/default comparison; no extra-zero-transfer fault or hidden truncation; keep installed native max14 semantics |
| Console overlap | Receipt and executed output during long console TX; IRQ remains active, no fault/drops |
| F1 and compatibility | Reserved header-only LEN2 enters the already verified fastboot path; compatible terminal still works; return restores TOP_CFG |
| Preserved device/host state | Only authorized boot/logdump flashing if needed; no fuse/PHY/clock changes, extra interface rebinding or unexplained lingering owners/logging |
| Reproducibility and delivery | Actual build/package hashes, meaningful checks, documented measured outcome and fork/master publication |

Only after these requirements are satisfied can the original stability goal
be marked complete. A compiled package or a successful short-command variant
does not by itself prove native terminal stability.
