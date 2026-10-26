# RX61 — EUD WDF package inputs and build preparation

See [session 61](../../sessions/61-eud-wdf-package-and-build-preparation.md).
Unchanged RX60 toggle-preservation patch applied to complete official source
14b6fe1. Dedicated 9505-only INF/project, nine-module provenance and source
review, literal KMDF stamp token and DIRID 13 prepared. Stock upstream INF has
no EUD match. This is **not a complete WDK build, signed package or repair**.

At the frozen download observation eight curl shards were live, 57.29% of the
20,002,537,472-byte EWDK ISO. Refresh the external observer; do not infer the
current process state from these historical files. Do not restart merely
because a tool session ended. The first snapshot contains an observer bug
(UTC date conversion and total accumulation), corrected in the second.

Installed driver remains Microsoft-signed qcusbser 2.1.3.5 / oem102.inf;
Secure Boot is enabled and memory integrity is running. No boot/trust/security
settings changed. Four exact rollback files copied locally, binaries external.
Three EUD nodes normal, no serial owner, no trace/logging, unchanged firmware.

`python3 verify.py` checks frozen bytes, authored XML/INF, module provenance
report, historical download accounting and preserved baseline. It performs no
device action and is not InfVerif/Inf2Cat or a hardware test.

Other helpers are consumed single-use historical evidence. Their absolute
external paths and already-existing outputs must be inspected before reuse.
Full Qualcomm source ZIP/tree, ISO/shards, rollback PE/catalog and future
binary/private signing material remain outside Git. Retain Qualcomm notices.
Next finish full build and validation, then resolve supported loading before
a same-binary disabled/enabled causal comparison. Preserve TOP_CFG=0x11,
whole-frame RX, console/F1/terminals/rollback and once-only command input.
