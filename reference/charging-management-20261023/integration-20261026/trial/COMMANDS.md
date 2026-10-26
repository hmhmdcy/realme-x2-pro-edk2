# Commands for a later trial

These commands were not executed during package preparation. They use a
USB SDP/5 V connection only. Do not connect a PD/PPS/high-voltage source.

## 1. Local control tests

```powershell
cd "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\trial"
python tests\run_tests.py
```

## 2. Stage preflight on the old boot

Copy the package to the private root named by the manifest, then run:

```text
adb shell su -c "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-02/trial_stage.py --serial 62bc28a1"
```

The preflight verifies the old carrier hashes and prints a receipt. It does not
install files, back up carriers, or reboot.

## 3. Stage execute

```text
adb shell su -c "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-02/trial_stage.py --serial 62bc28a1 --execute" > stage-receipt.json
```

The explicit serial is an operator assertion recorded as
`"serial_source": "operator_cli"`; the fastboot operator never trusts it and
must still see exactly one real `fastboot devices` serial equal to `62bc28a1`.
This backs up old carriers and the original service, installs guard/service,
prints a stage receipt, and issues one AArch64 Restart2 syscall
(`syscall 142, 0xfee1dead, 672274793, 0xa1b2c3d4, "bootloader"`). It first runs
`/usr/sbin/samurai-charging stop`, `sync`, and fsyncs the critical backups/plan,
then fsyncs the installed receipt before the single syscall. It never writes a
new carrier. BusyBox `reboot bootloader` is not used. Keep
`stage-receipt.json` on the Windows host.

## 4. Verify and flash from Windows

First run local validation without `-Execute`. This checks the stage receipt
and all local files, but does not invoke fastboot:

```powershell
$Trial = "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\trial"
& "$Trial\fastboot_operator.ps1" `
  -FastbootPath "C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe" `
  -StageReceipt "E:\path\to\stage-receipt.json" `
  -ReportPath "E:\path\to\fastboot-validation.json"
```

After the phone is manually confirmed in bootloader mode, execute:

```powershell
& "$Trial\fastboot_operator.ps1" `
  -FastbootPath "C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe" `
  -StageReceipt "E:\path\to\stage-receipt.json" `
  -ReportPath "E:\path\to\fastboot-report.json" `
  -Execute
```

The operator checks one device with serial `62bc28a1`, product `msmnile`, and
the pinned partition sizes. It also checks the pinned DTB file and #510 boot
package receipt: boot hash, DTB hash/path, and DTB before/after input hashes
must agree. The DTB is embedded in boot and is not flashed separately. It
verifies the currently installed pair is the exact old pair, flashes logdump
then boot, fetches and hashes each write, and issues one `fastboot reboot`.

Any write/readback failure triggers one restoration of the pinned old boot and
old logdump, followed by one reboot if restoration is verified. The operator
never retries an unknown new write. If restoration cannot be verified, it does
not issue a reboot.

## 5. Read-only postboot audit

Run as root on the #510 boot with the phone on the normal SDP/5 V link:

```text
adb shell su -c "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-02/postboot_audit.py" > acceptance.json
```

The report must contain `"passed": true`, `"read_only": true`, and
`"accepted_token_written": false`. Review all listed dmesg evidence and hashes
on the host.

## 6. Optional acceptance token

This is separate from the read-only audit and is the only step that authorizes
the new pair to survive the 300 second watchdog. Run it only after reviewing a
passed report and before the watchdog deadline.

```powershell
$Report = Get-Content -LiteralPath "E:\path\to\acceptance.json" -Raw | ConvertFrom-Json
adb push "E:\path\to\acceptance.json" /root/charging-management-20261023/charging-integration-trial-20261026-02/acceptance.json
adb shell su -c "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-02/acknowledge_trial.py --report /root/charging-management-20261023/charging-integration-trial-20261026-02/acceptance.json --confirm-boot-id $($Report.boot_id) --execute"
```

The token records the current `boot_id`, manifest hash, and audit report hash.
It is rejected on any other boot.

## 7. Failure handling

- Guard timeout or wrong expected state: do not issue a token. The guard restores
  old boot, old logdump, and the original init service, then reboots.
- Host flash failure: let the operator's single old-pair restoration finish.
  Do not manually replay a new flash.
- Operator restoration failure: stop. Do not improvise a write sequence.
- Pre-userspace boot hang: userspace guard cannot run; use only the known old
  carriers and a separate, reviewed recovery procedure.

