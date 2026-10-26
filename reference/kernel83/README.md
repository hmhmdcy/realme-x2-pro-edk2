# Session83 source evidence

See ../../sessions/83-androidr-and-cyborg-charging-source-comparison.md.

The user identified cyborgdc2000 as the source of the previous Android 16 ROM's
kernel/device repositories and confirmed the Android 11 vendor base shared with
Realme UI2.0. Pinned current repository heads do not establish the exact historical
build commit. The official Android R repository supersedes the early 4.14.83
source as the primary OEM comparison for this work.

Manifests pin 54 source files by repository, commit, URL, length and SHA256.
audit-androidr-sources.py verifies these private downloads and the unchanged
same-handset Android DT archive entirely offline. Fourteen selected raw policy
values match both source trees. Gauge/short C and short header files are identical;
MP2650 initialization, charger core and msm8150Q files differ.

The I2C name fallback can match cyborg's oppo-prefixed DT nodes to the drivers'
I2C IDs despite differing OF prefixes. This source inference does not establish
runtime binding, initialization or independently validated hardware protection.

No device access, partition write, reboot, panel cycle or charger/gauge setting
change occurred in session83. Latest phone observations remain in kernel82.
Protection/temperature/input-budget/communication-loss validation remains open.
Full source, binary images, full configuration and private diffs are not published.
SHA256SUMS seals every other file in this directory.
