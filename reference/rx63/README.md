# RX63 — live compatibility and guarded single-device trial tools

See [session63](../../sessions/63-single-device-driver-compatibility-and-trial-tools.md).
Actual native SetupAPI audits identify exactly one candidate and one rollback
node for the present EUD COM 9505. Runtime CI flags F401 confirm TESTSIGN off,
HVCI kernel enforcement on. Packages/binding unchanged; zero stage/bind calls.
These are metadata/policy checks, not loaded driver or USB stability proof.

`eud-driver-trial.ps1` and `EudDeviceDriver.cs` must stay together. Audit is the
default; Install/Restore branches remain unexecuted and require the selected
supported environment and documented gates. No auto-UAC, root/BCD/security
changes, driver deletion, broad update, force bind or reboot. Fifteen pure
gate cases pass, including failed-load rollback with healthy Control/hub.
Read [trial review](trial-review.md) before any later action; do not reuse an
existing output path. Exact external RX62 package and RX61 rollback unchanged.

ZLP option loads at DeviceAdd; ordinary reopen does not apply it. Primary
toggle comparison must keep ZLP default, then prove actual reread/zero-byte OUT
in a separate phase. Native payload14/wire16 and historical MPS16 retained;
no new descriptor/payload experiment. Original full acceptance matrix stays
in reference/rx62/validation-plan.md. TOP_CFG0x11/RX53/F1/terminals/RX48 remain.

`python3 verify.py` only checks frozen bytes/recorded outcomes. It performs no
native API/serial/staging/install. Historical helpers are consumed evidence.
Initial null software-key PortName and ANSI JSON reader were corrected to
hardware parameters/UTF8; initial raw audit retained. No phone action consumed
those tooling errors. Full kit/source/binary/private material stays external.
Environment choice still pending; elapsed time/goal continuation is no approval.
Goal remains open; actual installation, rollback, reset off/on and native
stability are unverified. Record/push fork/master only.
