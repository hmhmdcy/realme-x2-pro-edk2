# R7 USB500 actual-trial audit

The bounded diagnostic completed and100mA was restored. **500mA was not
accepted.** This audit reads only the retained original trial
`E:/edk2-samurai-out/charging-management-20261023/usb500-r7-18306f77ab5726a7929b99d2131242353f7a7c45a1f69e24`,
specifically `fetch-1792747154239432418`. It makes no device/SSH/USB/SDK calls,
edits no root report, and reruns no previous test matrix.

The copyable current result candidate is [usb500-r7-result.json](usb500-r7-result.json).
Its `audit_passed=true` means the retained evidence agrees; `passed=false`
correctly preserves the failed500mA objective. `audit.py` verifies original
fetch envelope bytes/hashes, all staged sources and config/nonce/boot, worker
PID9274/startticks/argv, execution marker, process `absent`, journal/result
agreement and the independent parent terminal. There was exactly one dispatch;
no unknown mutation remained. No retained original was modified.

## What happened

All six UDC/MaxPower writes returned0; the largest recorded round trip was
139.291ms. The frozen actual configure function verified local configfs500 and
bound `a600000.usb`, then entered its observation phase. These are local
configuration facts, not proof the host read/accepted a500mA USB configuration.

The500 observation produced55 samples over41.646937s, at most0.908923s apart.
All55 report UDC `addressed`, raw native100mA, effective source100mA, fresh
sample budget100mA and both physical input paths100mA. No500 sample passed the
actual stage receiver. The gauge's signed instantaneous net current ranged
from−77mA to−2mA. No current-budget property was written.

The100 restoration produced18 snapshots. **The first is not an accepted
healthy snapshot:** REG08&0x18 was0x08 while its later-read telemetry said
desired_enable1. The first500 snapshot had the same mismatch. The actual
receiver correctly refused each; sequential register/telemetry capture is
not atomic, so this alone does not establish an electrical or policy fault.
The subsequent54/17 snapshots respectively had normal0x10 charge readback.

The continuous accepted100 streak is exactly snapshots2–18,17 samples:

| Clock | First accepted | Last accepted |
|---|---|---|
| Device UTC | 2026-10-23 09:17:48.983107844Z | 2026-10-23 09:18:01.277926092Z |
| China time | 17:17:48.983107844 | 17:18:01.277926092 |
| Device monotonic ns | 2542506323828 | 2554801140930 |

Their event timestamps span12.294817102s, with no gap over0.788s. The event
timestamp precedes journal flush and the stable loop's `io.now()`, so the audit
does not simply equate those clocks. The following accepted event is after
the original loop's mandatory0.5s pause: this bounds the actual first accepted
`observed` time above by the next event minus0.5s. The final `observed` is at
or after its event. Consequently actual accepted-observation duration is at
least **12.029529147s**, independently supporting the returned12s criterion.
The final fresh100 observation also passes the actual receiver. Same boot,
taint0, all three notes, camera PM/m2m and the four same-window user processes
are retained. This comparison uses this trial's own before state, not old PIDs.

## What the host capture establishes

The host reader ended normally after140s:683 complete seven-port sweeps,
4781 GETs,0 query errors. `redecode-cache.ps1` replayed every retained raw
response through the exact frozen static C# decoder, comparing every decoded
field; all matched. It constructed **no HubSession**, opened0 USB handles and
issued0 IOCTLs. `raw-redecode-result.json` binds the source/capture hashes.

Port7 reported DeviceConnected451, DeviceReset2, NoDeviceConnected230;
DeviceNotEnoughPower(Status5) was never observed. The largest port7 polling
gap was0.239296s. Connected observations before/after carry device descriptor
identity0525:a4a1 and CurrentConfigurationValue1. This collector reads only
hub NodeInformation and ConnectionInformationEx. It did **not** retrieve a
standard ConfigurationDescriptor, device bmAttributes or bMaxPower. The500
number comes from local configfs stage/readback, not a host config-descriptor GET.

## Time association and limits

Two original SSH request brackets give a device-realtime minus launcher-host
offset intersection of approximately **+56.286ms to+785.056ms**. One-way delay
is unknown. The association treats launcher WSL and Windows reader wall clocks
as the host UTC basis; a separate WSL↔Windows offset was not calibrated. The
device realtime/monotonic deltas are checked for consistency in the report.

The device `configured-local500`→`restore100-start` interval is42.850461s. Using
the whole recorded offset interval rather than an invented point estimate,
206 complete port7 queries are certainly inside that phase **under this clock
model**:204 NoDeviceConnected and2 DeviceReset;0 have a valid device descriptor
or nonzero CurrentConfigurationValue. Allowing any possible phase overlap
gives213 queries:211 absent and2 reset. The full capture encloses the outer
phase bounds. Complete sweeps do not observe what happened between polls.
Exact UTC ranges, sweep IDs and transition queries are retained in the JSON.

Thus the evidence establishes an enumeration/configuration attempt that did
not produce native500 authorization, followed by verified100 restoration.
**Absence is not the power-rejection status code.** The bus-powered EUD hub is
known context, not a proven cause of this trial's failure. A power-policy,
enumeration or topology cause cannot be selected from this capture alone.

Root separately reports Windows history checks: Configuration last12:18,
DeviceInstall05:33 and SetupAPI12:09 precede the17:16 trial; System had no
window records; the requested USBHUB3/UCX Analytic channels were unavailable.
Those are root-supplied supplementary findings, not independently read by this
audit. They provide no contemporaneous failure event proving power rejection.

No new phone action or broader matrix is needed to reproduce this result.
The frozen worker's ordinary charging/full/icon behavior is not reaccepted by
this USB-budget diagnostic, and no UI state is forced to Charging.
