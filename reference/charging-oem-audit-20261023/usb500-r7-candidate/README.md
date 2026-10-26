# R7 USB500 directed migration — frozen, not executed here

This directory ports only the current R7 identity, guard, original-key IPv6
route and raw/effective source fields of the frozen R6 USB500 diagnostic.
The root has reviewed the migration. Worker/launcher/parent bytes are frozen.
No coordinator, host USB reader, phone worker, SSH, USB API or SDK was invoked
by this offline work. Original R6 sources and historical failed results remain
unchanged. This is not a successful USB500 trial or a physical icon acceptance.

## Exact entry point, only after actual handback

Use **PowerShell7 (`pwsh.exe`)**, not WindowsPowerShell5.1. From PowerShell:

```powershell
& (Get-Command pwsh.exe).Source -NoProfile -NonInteractive -File 'E:/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/usb500-r7-candidate/host-parent.ps1' -WindowConfirmed
```

`-WindowConfirmed` records root's actual coordinated camera/Bluetooth return;
it is not evidence that a handback happened. Do not invoke this entry point,
including its host reader, before the real device window is returned. No
administrator elevation, Windows IPv4 change, PnP restart or EUD API is part of
the command. Do not manually precreate its nonce/output directory. Do not
invoke device `r7-base.py` as a standalone program: it is the imported helper,
not an R7 updater or launcher.

The parent reserves a new48-lowercase-hex nonce and creates:

```text
E:/edk2-samurai-out/charging-management-20261023/usb500-r7-<nonce>/
  parent-start-private.json
  reader-owned-private.json
  host-ready-private.json
  parent-dispatch-once-private.json     # at most one dispatch
  launch-request-private.json          # durable request before SSH
  parent-result-private.json           # parent coordinator outcome
  reader-stdout-private.json / reader-stderr-private.txt
  launch-parent-stdout-private.json / launch-parent-stderr-private.txt
  fetch-parent-stdout-private.json / fetch-parent-stderr-private.txt
  host-reader/
    metadata-private.json
    ready.json
    ports-private.jsonl
    summary.json                       # host reader terminal; not result.json
  launch-<time_ns>-stdout-private.json / ...-stderr-private.txt / ...-receipt-private.json
  fetch-<time_ns>-stdout-private.json / ...-stderr-private.txt / ...-receipt-private.json
  fetch-<time_ns>/
    result.json                        # actual device worker result
    phases-private.jsonl
    worker.pid
    execution-started-private.json
    launch-receipt-private.json
    config-private.json
    worker-private.log
    worker.py / r7-base.py / health.py / test-result.json
```

The **parent stdout** ends with JSON fields `nonce`, `output`, `dispatch_count`,
`reader_exited`, `reader_watchdog_killed`, `failure`, `launch_pid`, `launch_exited`,
`fetch_pid`, `fetch_exited`, and `phone_worker_killed=false`. It does not attest
to device success. The launch stdout may be lost during re-enumeration; that
does not authorize redispatch. A completed fetch stdout has `process_state`,
`retained_directory`, `result` and `terminal_verified`. `terminal_verified` is
separate from `result.passed`, `restore100_verified` and a physically accepted
budget. Keep all envelopes and the original retained nonce if fetch fails.

## Narrow changes

- Exact manifest is now `5638db4c…552c68`, with USB module `7d4e0f94…33c4f70`;
  charger `fac827cf…889cb6`, protection `75b97e0d…e783c7`, and manager
  `61451ffe…355aa4` remain the accepted R6 versions. The actual new R7 adopted
  guard is pinned; old k449 guard and R6 manifest must fail. The local baseline
  is `r7-handoff/snapshot-private.json`, with its R7 result/modules, real SDP100,
  current guard and observed new boot checked. Its saved age is historical:
  the worker still requires a new live complete healthy sample before mutation.
- Independent R7 TX/lease/capture names prevent old transaction replay. The
  launcher refuses either old R6 or new R7 live diagnostic workers. It stages
  only four precisely hashed files and requires the directed R7 test receipt.
  That receipt does not claim the old51-case suite was rerun on changed bytes.
- The source receiver now retains both `limits.native_ua` (raw native
  `input_current_limit`) and `limits.source_budget_ua` (`current_max`, effective
  budget). Sample budget must agree with effective source budget. This
  experiment requires **SDP**, and both properties/physical input paths must
  equal the requested100 or500mA. CDP1.5A with raw native100 is valid ordinary
  charging evidence, but cannot qualify as this SDP500 trial.
- Host transport uses only the current, hash-pinned `r7-transport.py`: actual
  observed peer `fe80::62:bcff:fe28:a101%29`, original
  `HostKeyAlias=169.254.42.1`, and original pinned key. It checks the current
  boot against the R7 guard. No optional IPv4 transport path is used.
- After each gadget bind the device keeps the original `usb0` link up, then
  waits up to3seconds within the existing phase deadline for the exact original
  `fe80::62:bcff:fe28:a101/64` link-local address to finish DAD. It neither adds
  an IPv4/IPv6 address nor changes address-generation settings. Missing,
  tentative, failed-DAD or different addresses fail; no address/interface
  fallback occurs. Windows interface29 is independently part of the verified
  host route. An index change cannot be repaired by guessing another route.

`migration.patch` contains the exact differences. `r7-base.py` is derived from
the original helper with only guard/manifest profile and source-budget read/
agreement changes. Its old updater functions are inert/uninvoked by this
diagnostic. The variable name `r6` inside worker remains to preserve proven
control bodies byte-for-byte structurally; it imports the pinned R7 helper.

## Preserved boundaries

The actual `configure`, `stable`, `transaction`, `gadget_state`, `write`,
`net_command`, `check_window`, `event` and `finish` ASTs equal the frozen worker.
There is one temporary500 attempt with a45-second deadline, then a single
finally100 restoration on either success or known failure. Continuous12-second
fresh healthy evidence and both physical input limits are required. Exact
healthy Full charge-only hold remains eligible; TCA/fault/timeout/thermal waits
do not. No CHG/AUTO/INHIBIT action, module change, source-budget write, permanent
startup edit, descriptor impersonation or self-powered/EUD manipulation was
added. Only the original volatile UDC/MaxPower and existing link-up mutations
are permitted.

“Finally restore100” is conditional on a **known completed** mutating-child and
sysfs state. A pending/unknown write keeps the original worker and shared
service lock quarantined and performs no next mutation. Network timeout only
allows recovery after the owned helper is killed and positively reaped. The
original cleanup exceptions allow only the same touched/owned transaction to
restore100 despite lease/observation expiry; they cannot authorize another500.
Nothing automatically guarantees recovery from a kernel hang or power loss.

The Windows collector/decoder are byte-for-byte frozen. They retain actual
hub-node and port `IOCTL_USB_GET_NODE_CONNECTION_INFORMATION_EX` GET responses,
including ConnectionStatus and returned device descriptor/configuration. A
fresh unique current NCM target, not simply an old logical configured state,
must establish the initial gate. The reader remains independent during NCM
loss for140seconds, with160-second owned-reader watchdog; parent conservative
remaining time must be at least110seconds at dispatch. Only that owned local
read-only reader may be killed; phone workers are never killed or replayed.

## Directed offline evidence

`orchestration-test-result.json` binds all current source hashes and the three
component receipts:14 device,7 host/receiver and3 actual PowerShell gate tests.
The device fixtures reuse the actual saved R7 handoff telemetry, execute the
actual receiver and IPv6 helper with fake file/process edges, verify unchanged
control-flow ASTs, and cover accepted/rejected500 with one100 cleanup plus
unknown-child no-next-mutation. Host tests execute actual identity, strict-route,
remote config and fetch functions with fake transport; no external helper or
SSH is invoked. Parent tests execute only extracted gate functions with the
current local PowerShell process as the owned-process fixture. They never run
the coordinator main body, reader or WSL launcher.

The original51/62/11+12 suites were **not rerun**. Their source/receipt hashes
were checked as frozen references. No current hardware acceptance follows
from these tests. Ring-count snapshot equality is still only that narrow gate,
not a guarantee of complete new-fault coverage.

| Frozen artifact | SHA-256 |
|---|---|
| device `worker.py` | `57a2c8c216204fcabf955ea69a55b7dec2ff464698db1018326244e80cec8a80` |
| `host-launcher.py` | `c6834f847d2d66f03cff6489345925799ee302d76bfebec27e6cf026ba203f2b` |
| `host-parent.ps1` | `3f7e03746babb7a712cbf54014e151a791903970853b9c4e36c207d4a0eab692` |
| collector | `31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5` |
| decoder | `9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716` |

Remaining runtime uncertainties are the real host's500mA authorization behind
the bus-powered EUD hub, its refusal status/descriptor if rejected, NCM recovery
and the fixed IPv6 route after re-enumeration. The trial cannot promise that
500 will be accepted or that chemical net charging/icon timing will follow
immediately. Native callback and current samples remain the evidence; no UI
state is forced to Charging. Root must obtain the next actual handback, use a
new live host gate and preserve any failed/unknown outcome before deciding
whether the phone can be returned to another session.
