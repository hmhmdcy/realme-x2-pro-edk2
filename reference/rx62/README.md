# RX62 — real full driver build and file-only test-signed package

See [session 62](../../sessions/62-eud-wdf-build-and-test-signed-package.md).
The unchanged RX60 toggle-preservation code now has a successful nine-module
WDK build, zero warnings/errors, valid Windows Driver INF and explicit Win11
catalog. Candidate project adds UTF8 compilation; INF minimum AMD64 build
26100 is required for its DIRID13 package. These metadata fixes preserve code.

SYS/CAT were test-signed offline. CMS signatures and the exact PE image digest
verify; original code bytes are unchanged by signing. Certificate absent from
six checked stores, temporary PFX removed, all kit mounts closed in finally.
The candidate is **not Microsoft release-signed, installed, loaded or hardware
validated**. Secure Boot/HVCI remain enabled; original driver and phone unchanged.

`python3 verify.py` checks frozen bytes and recorded results. `--external`
also checks the actual external unsigned/signed package and nine source modules
if their recorded local paths exist. It does not compile, sign, open USB/COM,
install a driver or prove runtime stability. Other helpers are consumed
historical scripts; inspect their guards and existing outputs before reuse.

Binary package: `E:\edk2-samurai-out\rx62\package-test-signed`.
Exact old-driver rollback: `E:\edk2-samurai-out\rx61\rollback-qcusbser-2.1.3.5`.
See [loading review](loading-review.md) and [full acceptance plan](validation-plan.md).
The testing environment choice is pending; no timeout counts as authorization.
Next same-binary opt-in off/on trial, actual reset observation and first-frame
comparison. Full 16-byte OUT/ZLP remains separate. Preserve TOP_CFG=0x11,
RX53 console/IRQ, F1/compatible/native terminals/RX48 rollback, once-only data
and manual bounded finally-close. Original goal remains open.

ISO/source ZIP/SYS/PDB/CAT/public certificate binaries and private material
remain external. Microsoft kit script bodies are omitted; hashes retained.
Qualcomm BSD notices retained. Initial failed build/tool invocations stay as
local workflow evidence, not extra phone failures or a claimed repair.
Raw tool logs/stamped INF retain original whitespace and exact hashed bytes.
