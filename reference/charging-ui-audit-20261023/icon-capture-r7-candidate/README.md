# R7 physical USB / charging state capture

Offline candidate. No phone, SSH or SDK operation was performed to prepare it. Root owns the phone window and sends the human prompt. This launcher sends no question and does not decide camera/Bluetooth ownership.

`worker.py` and `audit.py` are byte-for-byte the frozen generic collector. The old 32 collector tests and 13 launcher tests are retained with `baseline-` names, as historical evidence only. Eight new affected-path tests passed in `migration-test-result.json`; no R6 physical result is reused as R7 acceptance. The last actual old capture had no physical edge and remains unqualified.

The new launcher pins R7 manifest `5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68`. `identity-pins.json` binds the reviewed adoption pointer, R7 guard creation receipt/request, postboot passed baseline, original-key IPv6 endpoint/probe, and transport helper bytes. The current adopted boot must agree across the request and transport probe; the remote RPC checks actual boot, adopted guard and manifest at both ends. Local file changes fail closed and require a reviewed revision. There is no IPv4 fallback, key relaxation or reconnect retry. Original `r7-transport.py` uses `-6`, the observed link-local peer/interface29, strict original known-host file/key, and `HostKeyAlias=169.254.42.1`.

Default duration is 180 BOOTTIME seconds. It does not exit merely because the online state is stable: it waits for three baseline samples, then continuous source AND ACOK offline (at least three samples spanning two seconds), then continuous online and 25 further seconds after reconnect confirmation. A cycle that begins at second100 and reconnects at110 completes at137 in the actual scheduler test. No observed cycle by180 produces a deadline failure and preserves raw evidence. Explicit `--max-seconds 600` is supported but unnecessary for a user already ready. Do not relaunch the same transaction or extend an expired prompt.

## Coordinator commands

Use one fresh ID and retain it across all actions. The following unused example is `charging-icon-r7-caf7c4710676`; root can choose another fresh ID. Run under WSL, matching the reviewed transport helper paths.

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-r7-candidate/launcher.py' launch --transaction charging-icon-r7-caf7c4710676 --window-confirmed
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-r7-candidate/launcher.py' status --transaction charging-icon-r7-caf7c4710676
```

Launch creates its host marker before the one-shot dispatch and a detached PID/receipt in a new remote bundle/output directory. Launch itself cannot authorize a user prompt. Only a fresh status result with `may_prompt_user:true` permits root to immediately prompt for one physical unplug for about10seconds and same-port reconnect. Status verifies two exact live PID/start_ticks/cmdline observations, advancing ticks, timestamps no older than3seconds, remote observation spacing1–5seconds and at least45seconds remaining after RPC allowance. If root cannot prompt within3seconds, obtain a fresh status. On `may_prompt_user:false`, retain evidence and inspect reasons; never tell the user to act on an expired capture.

After user reports reconnected, allow the required settling interval, then fetch; fetching while active is read-only and may give partial evidence. It neither terminates nor restarts the worker. If terminal status is not yet present, keep the same transaction and fetch later; do not repeat launch. A transport failure preserves host stderr/stdout and never triggers a launch retry. Final proof requires exact worker exited and collector cleanup complete, not merely an SSH response.

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-r7-candidate/launcher.py' fetch --transaction charging-icon-r7-caf7c4710676
```

Host originals are saved under `/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture-r7/<transaction>/fetch-*/`. Remote files are under `/root/charging-ui-audit-20261023/icon-capture-r7/`. After a complete fetch, inspect `capture/result.json`, the full `capture/capture-private.json`, `capture/config.json`, and launcher `cleanup_confirmed:true`/`identity_unchanged:true`. The frozen auditor can recompute from that capture directory without phone access:

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-r7-candidate/audit.py' --directory '/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture-r7/<transaction>/fetch-<timestamp>/capture'
```

`physical_cycle_passed:true` means one qualified source/ACOK power cycle and complete observation. It does not certify the rendered screen icon. UDC configured, zero budget, synthetic worker summary or missing offline samples cannot establish unplug. Missing UPower `State` events leave latency null. Negative native battery current/status remains Discharging. Kernel→UPower event intervals use start/end clock mapping and are estimates; none force a state or refresh.

## Review/test scope

`launcher-r6-to-r7.diff` contains the launcher migration. Worker/audit unchanged, no kernel changes, no extra monitor or broadcast, no REG14 read. Eight tests execute the actual launcher adoption, dispatch/ready/fetch functions, the actual strict IPv6 helper with mocked subprocess boundary, and actual worker/auditor with fake sampled OS time. They cover new boot/manifest/guard semantics, changed identity rejection, exact key/transport flags, new once-only180second launch, fresh readiness, late true edge acceptance, deadline/mixed-source rejection and read-only terminal fetch. `delivery.json` binds current bytes. This is preparation for a new R7 experiment, not a physical acceptance result.
