# DWC failed-suspend SUSPHY restoration candidate

This is an offline kernel candidate against the exact Image503 DWC source. It repairs one demonstrated failed-suspend residue. It does not complete the core resume error unwind, and has not been linked into an Image or deployed.

## Actual defect and bounded change

In `core.c`, non-runtime `dwc3_suspend_common()` temporarily enables SUSPHY when its saved port-0 policy is false. The DEVICE and OTG-device branches then call `dwc3_gadget_suspend()`. When the actual gadget function reports failure, the old immediate return leaves those temporary bits installed even though `dwc3_core_exit()` was not reached and core/PHY/IRQ resources remain ACTIVE. The actual old function reproduces this residue in the new fixture.

The patch records the old SUSPHY bits and the exact same-read changes made by this attempt. On the two existing gadget failure exits it restores only those changed bits, preserving unrelated current register bits and the original return value. This includes quirks that clear rather than set SUSPHY, multiple ports, and absent USB2/USB3 port classes. A previously true policy or an attempt that changed no bit incurs no restoration write. Successful DEVICE and HOST write sequences remain the original sequences in the tested configurations.

The record is stack-only: no `struct dwc3`, public header, ABI, persistent fault flag or new resource ownership. HOST still uses the existing helper. No error path is changed to `core_exit()`, PHY power-off, event-buffer free, IRQ park or PM-state transition. The existing resume functions and their callers remain byte-for-byte unchanged.

## Exact inputs and validation

- Original `core.c` is the fixed ba61/Image363 source also retained by Image503, SHA `bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf`.
- Image503 `gadget.c` is `ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314`; its `core.h` is `9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67`.
- Candidate `core.c` is `5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f`. `prepare.py` derives the patch and exact extracted test functions, and checks that other existing functions remain unchanged.
- `test-result.json`: 24 new actual-function cases, GCC ASan/UBSan/Werror, both original compiler and test processes terminal 0. The MMIO, PM, PHY, IRQ and callback boundaries are fake. Coverage includes original failure reproduction; primary errno/reconnect failure; four quirk combinations; maximum/mixed/zero port classes; old-true/no-write; runtime/OTG exits; unrelated-bit preservation; and eight original-versus-candidate successful DEVICE/HOST sequence comparisons. The final control explicitly preserves the unresolved softconnect=false gap described below.
- The first fixture compilation failed only because its fake counter named `puts` collided with libc. That receipt remains in `history/`; the fixed fake counter uses a new private test output. No kernel source change was made to address that fixture error.
- `build-result.json`: one private AArch64 `core.o`, W=1 plus Werror, GCC PID803 terminal 0, no diagnostics, 219528 bytes, SHA `7a93b92b90736f520a703a131755396b745153d574a58bcc17fbaf640d8c29c3`. It uses the actual Image503 saved command and generated headers/config. Only the new private core source and output are written. Original284 Ubuntu/root storage guard is reused; the original Image503/shared source, config, symvers, Image and object hashes remain equal before/after. Parent mountinfo after the helper remains unchanged. The original exec handle reached exit 0 and the storage window was returned; no anchor, SDK, make, link, module or Image operation was used.

Old 20/126 test receipts are historical context and were not rerun. No module ABI or hardware acceptance is claimed by this single-object result.

## Remaining rejected/unresolved paths

1. `dwc3_resume_common()` still ignores DEVICE `dwc3_gadget_resume()` failure. Returning that error alone is unsafe: runtime/system callers can mark PM suspended while the core is initialized, and the pending-event/PM-reference/IRQ tail may be skipped. The earlier direct-return and permanent-broken/IRQ-parking drafts are not incorporated.
2. A HALT failure is not proven recoverable by `dwc3_event_buffers_cleanup()`: that helper skips cleanup without DEVCTRLHLT, while `dwc3_core_exit()` would still power off/exit PHY and clocks. This patch never calls it on a new failure path.
3. The exact existing `dwc3_gadget_suspend()` suppresses a soft-disconnect error when `softconnect` is false, then reports success to the core. That can still reach the old IRQ-join/core-exit sequence without a HALT proof. The new fixture retains this as an explicitly unresolved control, not as a successful safety check. Fixing it requires a separately reviewed primary-error/resource-ownership change.

No desktop/Phosh/UPower change, handset operation, resume experiment, charging-state change or latency acceptance is part of this leaf.
