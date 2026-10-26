# RX60 — even reopen reversal and offline toggle candidate

See [session 60](../../sessions/60-even-reopen-reversal-and-toggle-candidate.md).
74 observed IN frames / two short OUT, ordinary reopen: first status complete,
first Ctrl-U accepted. CRC ada51499; all 512 journal frames match directly
(169 prior RX59, 74 owner 1, 269 owner 2). Both owners manually closed.
This is the pre-defined reversal, not a stability repair or physical PID proof.

Originally prepared joint Arm never started: desktop UAC remained pending for
approximately 489 seconds, then the exact launcher was stopped after blocking
late Arm. No logger/ETW/PnP change occurred. The no-admin replacement has
explicitly different observation coverage and no initial PnP reload.

The experimental patch targets Qualcomm open-source wdfserial at 14b6fe1.
It does not patch/install the currently running proprietary qcusbser 2.1.3.5.
QCEudPreserveToggleOnOpen is a NEW candidate option, not a known setting in
that installed driver. No such registry value was written. Full Windows WDK
build, signing and hardware validation remain outstanding.

`python3 verify.py` checks exact frozen bytes, strict capture/counter/CRC/direct
matching and compiles/runs the extracted actual patched/baseline FileCreate
with mocked WDF APIs (gcc). Fourteen dispatch/resource/error cases pass.
This is an offline harness, not a complete Windows driver build. Full primary
source, scratch apply trees, executables, PE/PDB/images remain external.
Original snippets/patch retain Qualcomm BSD-3-Clause provenance. Helpers are
consumed single-use historical evidence; do not run them against these paths.
