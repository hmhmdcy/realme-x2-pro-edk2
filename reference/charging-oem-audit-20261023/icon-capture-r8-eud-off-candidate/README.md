# R8 / adopted EUD-off USB and icon observation

Offline candidate only. Preparation used cached files and fake OS/transport boundaries; no phone, SSH, USB, SDK, build or Git operation ran. Root owns the physical window and the human prompt. This code changes no charger, USB descriptor, UDC, UPower or screen state.

`worker.py`, `audit.py` and the passed 32-case receipt are byte-identical to `charging-ui-audit-20261023/icon-capture-r7-candidate`. The old 32 collector cases and eight R7 migration cases are historical evidence, not rerun or new physical acceptance. Twelve affected-path groups passed using the actual new launcher, RPC identity functions, strict transport with a mocked subprocess, sample adapter and inherited Cycle. Hashes are in `migration-test-result.json` and `delivery.json`.

The launcher binds the actual adopted EUD-off boot, candidate boot hash `4126a297…bbfcf`, retained Image363, R8 manifest `320316c3…c10a1f`, camera481 postboot receipt and adopted guard. `identity-pins.json` hashes the existing private adoption/request/result, R3 postboot/receiver and original-key endpoint. Actual boot/guard, kernel release/version, rootfs and live module notes are checked at launch and readiness. The pinned transport uses observed IPv6 peer/interface29, the original key and known-host file, strict host-key checking and original HostKeyAlias. There is no fallback endpoint or key relaxation.

## Observation scope

`capture-entry.py` supplies only two derived classes to the original worker, then restores the original classes when main returns. The sample adapter adds these standard read-only fields to every row and extends that row's `t_end` to include their read time:

| Field | Actual source / meaning |
| --- | --- |
| `source.usb_type` | `samurai-usb-input/usb_type` |
| `source.current_max_ua` | `samurai-usb-input/current_max`, effective source allowance |
| `source.input_current_limit_ua` | `samurai-usb-input/input_current_limit`, native DWC callback allowance, when valid |
| `hardware_input.input_current_limit_ua`, `.status` | `mp2650-input/input_current_limit` and `status` |
| `udc.state`, `.current_speed` | `a600000.usb` standard UDC attributes |
| `MaxPower_ma` | Existing `samurai/configs/c.1/MaxPower` descriptor value |
| `battery.current_avg_ua` | Discovered standard Battery `current_avg`; an absent attribute remains an errno object |

The original telemetry includes effective `budget_ua` and this board's signed instantaneous `gauge_current_ua` (0x0c). Standard Battery status/current_now are retained unchanged; the gauge candidate is not installed. Each value is a sequential read, not an atomic simultaneous snapshot. Missing values and ENODATA are preserved, never filled with 100mA. No new bare gauge/charger register query is made. The original kernel uevent and UPower DBus streams are unchanged. UDC configured and a descriptor of 500mA do not independently prove a physical connection or accepted source allowance.

The deadline is fixed at **300 BOOTTIME seconds from worker start**. The original three-sample / two-second physical source **and** ACOK off/on qualification and sample-gap reset rules remain. A derived Cycle delays only the original successful reconnect completion from 25 to **90 continuous seconds after stable-on confirmation**. A new off/gap restarts settling. The worker may therefore finish before 300 seconds; a late reconnect may reach the overall deadline before 90 seconds. The capture must show the actual coverage rather than claim every run has 90 seconds after reconnect.

The host readiness gate requires two fresh advancing ticks, exact PID/start_ticks/argv, live phase, same identity, bounded RPC and at least **130 seconds remaining after RPC allowance**. The worker's original 45-second flag is only an input to this stricter host gate. A launch receipt alone never permits a prompt.

## Root commands

Choose one new transaction and retain it across all actions; the example below has not been launched. These commands are for root's coordinated window only. The default action is local checking and makes no transport call.

```powershell
$collector = '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/icon-capture-r8-eud-off-candidate/launcher.py'
wsl -d Ubuntu -u root -- python3 -B $collector check-local
wsl -d Ubuntu -u root -- python3 -B $collector launch --transaction charging-icon-r8-eud-off-001 --window-confirmed
wsl -d Ubuntu -u root -- python3 -B $collector status --transaction charging-icon-r8-eud-off-001
```

Only `may_prompt_user:true` from fresh status permits root to immediately prompt once for the physical disconnect/reconnect. If the prompt cannot follow within three seconds, obtain fresh status. If readiness fails, preserve evidence and inspect reasons; do not ask for action on the old result. Root should launch and status immediately after actual camera/Bluetooth handback, so the 300-second budget starts near the prompt. This collector does not write the persistent startup or current MaxPower.

After reconnect, allow the 90-second settling interval and fetch from the same worker/transaction. Fetching while active preserves a partial observation and performs no stop/restart. An unknown launch outcome leaves its marker; the transaction is status/fetch only and must not be launched again.

```powershell
wsl -d Ubuntu -u root -- python3 -B $collector fetch --transaction charging-icon-r8-eud-off-001
```

Host originals: `/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture-r8-eud-off/<transaction>/fetch-*/`. Remote originals: `/root/charging-ui-audit-20261023/icon-capture-r8-eud-off/<transaction>` and adjacent `<transaction>-bundle`. Fetch retains original bytes/hashes and requires no final log from a vanished old `/run` or another boot.

Launch/status fail closed on identity mismatch. Fetch keeps the same-boot/adopted-guard hard gate, but records other identity failures as `identity_unchanged:false` plus private `identity_errors` and still retrieves originals; this cannot authorize readiness or identity acceptance. `cleanup_confirmed` certifies only exact original worker terminal/absent and event monitor cleanup, separately from identity and capture success. No automatic kill, replay, unload or device recovery is attempted.

For final assessment retain `capture/capture-private.json`, all samples/events, clock brackets, result and terminal cleanup. The unchanged auditor's `physical_cycle_passed` covers its qualified physical source/ACOK cycle and recorded observation; it does not prove 500mA acceptance, target UPower direction, screen pixel latency or a causal path. Its first-State timing remains a timing observation. Budget acceptance needs the actual native/effective/hardware fields; charging direction needs the signed current and Battery/Display state evidence. Root owns those conclusions after the new physical capture.
