# Actual Image504 FAT carrier result

The source plan in README.md and source-delivery.json remains byte-for-byte
unchanged. That plan described the state before this later, single authorized
packaging execution.

Original exec47694 returned0. Packager PID579 used the original mcopy803,
readback808 and readonly fsck820 children, each actually waited to return0.
There was no timeout, kill, restart or replay. No process or storage window
remains owned by this packaging step.

The new private64MiB carrier is:

`E:/edk2-samurai-out/charging-management-20261023/image504-budget-logdump-private-01/logdump-image504-private.img`

SHA256 `4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83`,
67108864 bytes. Its Image readback is exactly actual504
`f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4`,
59243008 bytes.

The exact available rollback is the saved, passed candidate502 carrier
`ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1`,
67108864 bytes. It remains at its original private gauge-image502 path. The
current501/7e5 phone state is not treated as already-adopted502. First physical
use remains the independently prepared502 transaction.

Actual FAT parsing/readback verified that only the permitted Image data,
directory entries and FAT chain bytes changed. SAMURAI.DTB A823 and every
other byte were preserved. Readonly fsck returned0, reporting3 files and
14493/16363 clusters, and did not change the carrier. The source carrier,
actual Image504, tool binaries, completed-build receipts and source plan inputs
remained exact; parent mountinfo remained exact.

The raw tool logs, Image readback, complete FAT ranges and private result are
retained in the private output. logdump-result.json, execution-receipt.json and
delivery.json bind the actual terminal/result and artifacts. finalize.py only
reads these saved facts, rehashes the carrier and rollback and verifies the
frozen source snapshot; it cannot execute packaging.

Provider module2691 can be paired separately with this Image; it is neither
installed nor bound here. Native DEVICE/runtime-on and provider-first limits
remain unchanged. This result proves a consistent undeployed carrier, not
phone boot, PM recovery, USB budget, physical latency or icon acceptance. No
phone, SSH, USB, SDK, storage helper/volume, Git, rootfs or existing carrier was
changed. No new guard, request or deployment binding was produced.
