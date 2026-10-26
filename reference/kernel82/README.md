# Session82 evidence

See ../../sessions/82-charging-policy-units-and-android-backup-provenance.md.

Two guarded fixed observations retain the same boot_id and kernel #76. MP2650
fields are unchanged; only standard gauge words are queried. Existing DRM frame
timeouts remain two; no new timeout is observed. No flash/reboot/panel cycle or
charger configuration writes occurred. No short IC registers were read.

The policy audit compiles exact old stock temperature-reader/classifier functions
and the current mainline temperature reader with simulated register results.
The offline fault/boundary results are not a complete controller or safety test.
DT values are from the same handset's archived Android tree, decoded under the
normal policy branch; they are not recommended parameters for a new controller.

The saved Android rollback boot image embeds a DroidSpaces/KernelSU kernel. Its
filename containing stock does not establish OEM factory provenance. Only its
hash, version and selected configuration metadata are public. Full binaries,
configuration, downloaded source and generated C harness remain private.

Source manifests pin Realme, HyperTeam and crDroid revisions. The old Realme
short-protection code contains stubs; maintained OPLUS implementations contain
register writes and are not deployed by this session. Exact installed-source
mapping and independent protection validation remain open.

collect-observations.sh and collect-usb-budget.sh use the fixed session79 boot
guard. audit-observations.py checks device SHA and immutable raw captures;
audit-stock-policy.py runs the offline tests using verified private inputs.
SHA256SUMS seals every other file in this directory.
