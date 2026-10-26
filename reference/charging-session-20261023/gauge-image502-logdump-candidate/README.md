# Image502 FAT carrier — private passed, not deployed

This independent candidate replaces only `/Image` inside a private copy of the
currently installed Image501 logdump. It does not modify boot97811, BDS, native
DTB9271, rootfs, R8 providers, camera or desktop. Rollback for this step is the
actual current 501 carrier `7e5de5b4…76cbf9`, not the older ACA carrier.

The old FAT `/Image` must be `3a656c75…8cc02`, 59,243,008 bytes. FAT
`SAMURAI.DTB` remains `a82383fa…e2cc5`; it is not boot's embedded 9271 DTB.
The frozen parent is `gauge-image501-carriers-candidate/package-logdump.py`
SHA `0b0a7d7f…93d9c7` and remains unchanged.

`prepare.py` derives the new script without reading Image502. The parser and the
complete permitted-range/fsck sequence are checked byte-for-byte against that
parent. `reuse-result.json` records those hashes. The one size-rule change is
that the new directory's size must equal the actual new Image length rather
than the old Image length. Old/new Image data clusters, their FAT16 entries and
Image directory slots are the only allowed write ranges. All other bytes and
the entire DTB entry/content must remain exact. No padding or repaired header
can be substituted for a failed check.

Default `--check-local` is read-only. Before an explicit frozen author handoff,
`Image502-pins.json` is unready, so this mode checks only the old FAT/tools and
reports `Image502_proof_ready=false`; it does not read the new Image. Execution
refuses that state. Once the author supplies exact terminal receipts and Image
SHA/size, the gate verifies build/child/parent/ABI/unchanged/source bindings before
reading it. No kernel tests or ABI scans are rerun.

The sole output is a new `gauge-image502-logdump-private-01` directory; an existing
directory refuses replay. Explicit `--execute-logdump` copies the old carrier,
normally mcopy-overwrites `/Image`, independently reads it back, verifies FAT,
entry/data and protected byte ranges, then runs pinned `fsck.fat -n` and proves
that did not write. All inputs and parent mountinfo must remain unchanged.
Failure leaves the unique directory and original logs intact.

The author handoff is frozen: build `feb6fd2e…8940e6`, ABI reuse
`b097ee93…49b230`, delivery `4e27a8da…163e21`. Image502 is
`085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955`,
59,243,008 bytes, source `00140777…e5439b`. Only frozen receipts are checked;
kernel builds, old function tests and ABI scans were not repeated.

The first read-only check failed at a single 64MiB DrvFS read with ENOMEM;
no output or tool mutation had begun. `history/` preserves its source and exact
failure/environment evidence. WSL had about 7GiB available with unlimited
AS/DATA limits, but the host reported only about 354MiB physical free. A 1MiB
streaming read produced the complete original SHA and showed no owned residual
packager. The new script now reads via fixed 1MiB chunks into BytesIO, retaining
identical bytes semantics. Its actual helper has a focused >2MiB boundary check;
the parser/content/ranges logic is unchanged. The fsck comparison uses only the
same bounded I/O replacement. No global memory, app, cache or WSL setting changed.

The subsequent default check passed with proof ready, exact Image and no output
directory. The sole actual `--execute-logdump` then passed at native exec
session22669, Linux PID955, exit0. Final candidate:

```text
E:/edk2-samurai-out/charging-management-20261023/gauge-image502-logdump-private-01/logdump-gauge502-private.img
67108864 bytes
SHA256 ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1
```

Readback Image, DTB/other entry bytes, every non-Image byte range, pinned
`fsck.fat -n` and no-write-after-fsck all passed. All parent inputs and mountinfo
remained exact. `logdump-result.json` binds the private command/result originals.
The unique directory must not be replayed. This is an undeployed candidate;
no device, transport, fastboot, reboot, SDK, Git, shared build or existing carrier
was written. There is no new physical edge/latency acceptance.
