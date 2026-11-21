# Commands for the #517 wake-r1 module trial

Use an SDP/5 V source only. Do not attach PD, PPS, QC, or any high-voltage
charger. Do not hot-unload `samurai_usb_input`.

## 1. Local verification

```powershell
cd "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\trial-517-wake-r1"
python tests\run_tests.py
```

Expected Windows result: 106 passed, 5 platform skips, 0 failures.

## 2. Upload and read-only preflight

The archive path below is the already built package. The remote directory must
be unique; do not overwrite an existing stage receipt.

```powershell
$Key = "E:\edk2-samurai-out\kernel72\id_ed25519"
$Known = "E:\edk2-samurai-out\kernel109\known_hosts-pmos"
$Package = "E:\edk2-samurai-out\charging-management-20261023\wake-r1-package-20261027-01.tar.gz"
$Remote = "/root/charging-management-20261023/wake-r1-package-20261027-02"

ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known root@169.254.42.1 `
  "mkdir -p $Remote"

scp -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known $Package root@169.254.42.1:$Remote/package.tar.gz
```

On the device:

```sh
cd /root/charging-management-20261023/wake-r1-package-20261027-02
mkdir package
tar -xzf package.tar.gz -C package
find package -type f -exec chmod go-w {} \;
cd package
python3 -B trial_stage.py --package . --serial 62bc28a1
```

Preflight must print `"passed": true`, `"stage_execute": false`,
`"stage_mode": "module-only"`, `"restart_mode": "reboot"`, and no carrier
change. It creates only the private root and preflight receipt.

## 3. Execute after the r7 soak is closed

Do not run this while either soak PID is alive or before the final strict soak
audit passes.

```powershell
ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known root@169.254.42.1 `
  "cd /root/charging-management-20261023/wake-r1-package-20261027-02/package && python3 -B trial_stage.py --package . --serial 62bc28a1 --execute" |
  Set-Content -LiteralPath "E:\edk2-samurai-out\charging-management-20261023\wake-r1-stage-receipt.json" -Encoding utf8
```

Expected receipt fields:

- `"passed": true`
- `"stage_mode": "module-only"`
- `"restart_mode": "reboot"`
- `"restart_method": "reboot_syscall"`
- `"reboot_bootloader_requested": false`
- `"reboot_requested": true`
- `"new_carrier_written": false`
- `"original_auxiliary_modules"` contains the old `161bcc...` USB module

The device then performs one direct reboot. SSH will disconnect. Do not send a
second reboot.

## 4. Boot and acceptance check

Use NCM first; Wi-Fi is a separate recovery/control path.

```powershell
ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known root@169.254.42.1 `
  "cat /root/charging-management-20261023/charging-integration-517-wake-r1-20261027/state.json; cat /root/charging-management-20261023/charging-integration-517-wake-r1-20261027/accepted.json; sha256sum /lib/modules/$(uname -r)/extra/samurai-charging/samurai-usb-input.ko; sha256sum /usr/share/samurai-charging/manifest.json"
```

Expected:

- `state.json` reaches `accepted` for the new boot;
- the USB module hash is
  `22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529`;
- the main manifest hash is
  `d9f231dc4bef591875d7607c4eab6a7471fa66ac10c04d8f13cc9e3a790a97b7`;
- MP2650/USB input/protection are Healthy;
- no extra reboot occurred.

If the 300-second guard rejects the boot, inspect `state.json`,
`auto-audit-last.json`, and `watchdog.stderr` in the private root. Do not issue
an acceptance token manually unless the complete read-only audit independently
passes and the host review confirms the exact new manifest.

## 5. Rollback evidence

After a guard failure the private root contains `rollback.json`. Confirm:

- USB module hash returns to `161bcc...`;
- main manifest returns to `b07f...`;
- original service hash is `46b3f9b3...`;
- both carriers are unchanged from `13c988...` and `d884075...`.

## 6. Physical tests still required

These are separate from automatic acceptance:

1. Same-boot cable unplug/replug with NCM-only SSH, TCPM, MP2650, and protection
   recovery evidence.
2. s2idle with no RTC alarm, then physical USB insertion or removal; record
   `suspend_stats`, `wakeup_sources`, IRQ deltas, and matching dmesg.
3. RTC-only negative control. If RTC fires, mark the wake test invalid rather
   than passed.

Only the physical wake test can set `usb_wakeup_verified=true`.

The prepared operator is `Invoke-PhysicalUsbWake.ps1`. Run insertion mode over
Wi-Fi because the USB data cable must be disconnected before the test:

```powershell
.\Invoke-PhysicalUsbWake.ps1 -Mode insert
```

Run removal mode over NCM:

```powershell
.\Invoke-PhysicalUsbWake.ps1 -Mode remove
```

The device worker programs a 180-second RTC safety alarm. Any RTC IRQ delta or
late resume invalidates the result. Acceptance requires same boot, one
successful s2idle cycle, the expected USB online-state transition, a delta on
`usbin-plugin` or `usbin-src-change`, and no critical dmesg delta.
