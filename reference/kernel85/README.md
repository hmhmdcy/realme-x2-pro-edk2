# kernel85: fixed OEM chemistry and short-IC observations

Session85 uses the existing diagnostic kernel #85 from session84. It makes no
kernel/DT/initramfs change, reboot, panel cycle, partition or configuration write.
Raw I2C queries include selector and MAC request writes; they do not write
charging parameters, NVM/OTP, FET/OTG, authentication keys or MCU firmware.

QUP15 address58 identity00 returned ENXIO on its sole attempt, so threshold02
and mode03 were not queried. This does not prove physical absence. The guarded
FFA5/2719/exact-FW OEM chemistry004b returned LION. Operation0054 payload386
has OEM balancing bit28=0. Four-byte OEM reads and whole-block checks agree.
The wrong adapter was refused before I2C access. The archived Android gauge
node and both pinned reference nodes omit the balancing temperature flag.

Two offline auditors check pinned private inputs and publish selected evidence.
Three device archives preserve26 raw members and23 device member hashes.
Dmesg is published as deterministic gzip, preserving decompressed bytes exactly.
Full vendor headers/source, DT archive, tools/binaries and images remain private.
No protection calibration, exact2719 safety mapping or charging rate is accepted.
The final2477.32s state retains #85, taint0, display timeout0, trace on1 and an
unused snapshot:count=1. Session77/80 display faults remain open.

See [session85](../../sessions/85-oem-chemistry-and-short-ic-observations.md) for
source links, query boundaries, observations and unresolved hardware work.
