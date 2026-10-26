# RX63 — single-device trial and exact rollback tools

These tools are prepared and default to read-only **Audit**. Actual Install/
Restore branches have not run. No UAC, certificate import, driver staging,
binding, BCD/security change, flash, phone/PC reboot or serial open this session.
The loading environment question from RX62 remains pending; do not infer
approval from an automatic goal continuation or elapsed time.

## What the live audit now proves

Native SetupAPI compatible-list enumeration, restricted to one explicit
present `USB\VID_05C6&PID_9505\...` and one INF at a time, identifies exactly
one candidate EudInstall node (5.47.2.26) and one original QportInstall00 node
(2.1.3.5). The latter matters for forced, targeted downgrade rollback.
This is Windows metadata compatibility, not installation or USB validation.

Current kernel CI flags are `0x0000F401`: TESTSIGN bit 0x2 is absent and HVCI
kernel-enforced bit 0x400 present. Secure Boot remains 1. The exact public test
certificate does not satisfy the machine Root/TrustedPublisher trust gate. Current Install gate
refuses before any stage/bind call. No security policy was changed.

Microsoft says `pnputil /add-driver /install` does not force a lower-ranked
driver; it can update any matching device. Do not use that as proof of exact
rollback. The prepared native path stages one fixed package with
SetupCopyOEMInf, then passes an explicit driver node to DiInstallDevice for
the single opened device-info element. It does not invoke broad
UpdateDriverForPlugAndPlayDevices/DiInstallDriver, delete drivers, force-bind
USBIP, install a null driver or alter 9501/control devices.

## Scope and gates

`eud-driver-trial.ps1`, `EudDeviceDriver.cs` must remain together. Root defaults
are the existing RX62 test-signed package and RX61 exact rollback copy. Every
candidate and rollback file is pinned by SHA256 before and after the audit;
native selection must return the exact supplied INF and a 9505 hardware ID.

Install/Restore additionally require an elevated 64-bit process, one present
9505, healthy Control/hub, no known serial owner or USBIP attach, and exact
package and current binding hashes. Install additionally requires observed
current TESTSIGN, Secure Boot off, the exact unexpired public certificate
already trusted in machine Root and TrustedPublisher, and original driver
bound. The tool does not make those changes itself or launch UAC.

Restore requires this exact candidate binding. It permits a failed 9505 node
when Control/hub remain healthy, because rollback must still be available if
the candidate fails to load. It does not require disabling HVCI or retaining
test-signing when restoring the original Microsoft-signed driver.

After a later authorized binding, check actual INF/SYS/service/port and Control/
hub state before any serial data. PortName is read from the device hardware
`Enum/.../Device Parameters` key; the WDF options use the separate device
software key resolved from live PnP. Never assume software slot 0008 or port
COM14 survived rebinding. A reported NeedReboot stops the tool; it never
reboots automatically. Preserve output even on a failure. No automatic retry,
driver package deletion or silent security workaround.

## Commands and measured limits

Safe default/read-only audit, from native Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\edk2-samurai-out\rx63\eud-driver-trial.ps1 -Action Audit -OutputPath E:\edk2-samurai-out\rx63\fresh-audit.json
```

Existing audit files are consumed evidence and must not be overwritten.
On another selected physical host supply its exact InstanceId and actual
candidate/rollback paths; rerun read-only audit and document topology first.
Install/Restore arguments are prepared only for the later agreed environment;
they are not a request to run them now. All mutation calls remain unexecuted.

Fifteen actual pure-gate tests cover wrong PID, multiple nodes, ownership,
altered package, untrusted/expired cert, wrong kernel policy, non-admin,
unknown driver and failed-load recovery. They also read live COM14 binding.
Those tests do not prove that a native stage/bind call will succeed. Both
read-only native compatibility audits used zero stage/install calls. Finally
destroys driver/device info lists and frees allocated detail buffers. Serial
Close/Dispose/Detach still applies to later actual owners; none opened here.

## Independent ZLP phase

The unchanged compiled source reads QCDeviceZLPEnabled in **DeviceAdd**, not
ordinary FileCreate or necessarily PrepareHardware/D0Entry. Value absent/
failed read or positive DWORD means enabled; DWORD 0 disables it. It populates
driver-global configuration, so the trial is restricted to this one device.

For the historically measured 16-byte endpoints, native payload14 produces
wire16 and satisfies the append-ZLP condition. The worker makes that decision
from requested length after submitting the write, not from its successful
completion. No new endpoint control transfer was performed to obtain this
historical descriptor. No flag or binary was changed here.

Keep this default unchanged in the primary same-binary reopen/reset comparison.
Only afterward try ZLP off separately. Prove DeviceAdd/registry reread and
observe zero-byte OUT disappearing; don't assume closing/opening the serial
handle, or a power-only restart, applies this option. Keep native max14/F1
semantics and once-only data. All original requirements remain in RX62's
validation-plan.md: full startup/BusyBox/output/console/reopen/F1/compatible
behavior, not just a passing short frame or a compiled tool.

Sources:
- https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax
- https://learn.microsoft.com/en-us/windows/win32/api/newdev/nf-newdev-diinstalldevice
- https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdibuilddriverinfolist
- https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupcopyoeminfw
- https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation

No measured repair yet. Preserve TOP_CFG=0x11/full-frame/RX53 console/IRQ/F1/
native/compatible terminals and RX48 firmware rollback. Boot/logdump are still
the only permitted flash partitions; this trial needs no initial phone flash.
