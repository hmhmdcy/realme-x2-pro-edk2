# Session84 display diagnostic evidence

See ../../sessions/84-display-boot-tracing-and-timeout-snapshots.md.
The current #85 Image adds boot event tracing while retaining every existing
hardware source/DT change and the byte-identical initramfs. Two deployments wrote
only logdump. Image and rollback images, full configs, identity manifests, binaries
and keys stay in E:/edk2-samurai-out/kernel84 or their original private directories.

#84 booted but did not install its snapshot action: HIST_TRIGGERS was missing,
and its DRM event wildcard failed. Initial raw logs retain both errors and buffer
overruns. #85 fixes those diagnostic settings; the first capture at 65.28 seconds
has an active snapshot:count=1, all 79 events and no buffer losses or display errors.
No real display timeout has exercised the trigger yet.

Both 600-flip probes passed event/CRC checks and restored the console directly.
The first had 6055 overwritten trace events. A runtime buffer resize to 2051KiB
per CPU preserved the entire second bounded probe with no losses. This runtime
size does not survive reboot. collect-and-arm.sh preserved final observations
and armed the instance for future idle timeouts without clearing the snapshot.

flash-ready.ps1 succeeded at writing/rebooting, then failed because its EUD wait
was too short. Preserve that failure; do not replay the flash. The control device
later appeared, its identity was verified, and the existing com-up path restored
COM/NCM using only COM/VBUS control bits. COM captures were passive and released.
The incomplete first SCP archive stays private; its complete retry passed hashes.

final-validation.json verifies current partitions and twelve unchanged MP2650
registers. Those observations include fixed register-selector write messages,
but no configuration data writes. Charging/protection control remains unaccepted.
The earlier first-handoff and idle timeout faults remain open, with no new optical
or GPU acceptance in this session.

Scripts have fixed baseline guards and refuse overwriting their outputs. Several
record intermediate or failed iterations; they are evidence, not a reusable flash
recipe. run-traced-pageflip.sh was prepared for #84 but was not executed.
Audit programs verify the actual private capture archives and full configurations.
Public .gz files preserve the original raw bytes; capture-manifest.json maps raw
hashes to published filenames. Full captured configurations are deliberately absent.
SHA256SUMS seals every other file in this directory.
