# kernel86: MP2650 observations and a real display timeout snapshot

The phone runs #86, boot32bf2d8f-8dde-47dc-9b88-e87db9e95198. MP2650 software
binding was tested and later released; no persistent DT binding exists. Online
and Full status work, but changing ADC bytes produced EAGAIN and three empty
power_supply uevents. The corrected driver and #87 Image are built but untested.
flash-final.ps1 is stopped explicitly until a new fault-reviewed deployment.

The actual display snapshot triggered during fbcon idle activity, with two
timeouts and no underrun by515.97s. The trace remains stopped, snapshot:count=0,
and its bytes were preserved twice identically. The snapshot shows a done IRQ,
idle IRQ disable and a later timeout; this is evidence, not a root-cause fix.

The new driver only reads fixed status/input registers. It has no hardware
configuration writes, fault register read, setter, ADC enable or watchdog service.
Final code allows at most three ADC consistency attempts and returns ENODATA
for unavailable ADC data so other uevent properties survive. Bus errors stop.
High-byte equality is not proof of an atomic conversion or calibrated readings.

Six raw archives preserve76 members with70 device hashes. Full configuration,
vendor sources, images, binaries and invalid PDF responses remain private.
Published gzip logs reproduce the raw bytes. Audit PASS means evidence integrity;
charge control, input budget, thermal/independent protection and fast charge are
not accepted. All earlier source/initramfs/DT fixes and boot remain preserved.

See [session86](../../sessions/86-mp2650-input-status-and-real-display-timeout-snapshot.md)
for pinned Android references, MPS/OEM status differences, failed attempts,
candidate hashes, deployment boundaries and remaining hardware work.
