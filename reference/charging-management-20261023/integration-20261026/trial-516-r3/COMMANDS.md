# Commands for a later trial

These commands were not executed during package preparation. They use a
USB SDP/5 V connection only. Do not connect a PD/PPS/high-voltage source.

## 1. Local control tests

```powershell
cd "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\trial-516-r3"
python tests\run_tests.py
```

## 2. Stage preflight on the old boot

Copy the package to the private root named by the manifest, then run:

```text
ssh -T -i "E:\edk2-samurai-out\kernel72\id_ed25519" `
  -o "UserKnownHostsFile=E:\edk2-samurai-out\kernel109\known_hosts-pmos" `
  root@169.254.42.1 `
  "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-07/trial_stage.py --serial 62bc28a1"
```

The preflight verifies the old carrier hashes and prints a receipt. It does not
install files, back up carriers, patch the main manifest, or reboot.

## 3. Stage execute

```text
ssh -T -i "E:\edk2-samurai-out\kernel72\id_ed25519" `
  -o "UserKnownHostsFile=E:\edk2-samurai-out\kernel109\known_hosts-pmos" `
  root@169.254.42.1 `
  "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-07/trial_stage.py --serial 62bc28a1 --execute" |
  Set-Content -LiteralPath "E:\path\to\stage-receipt.json" -Encoding utf8
```

The explicit serial is an operator assertion recorded as
`"serial_source": "operator_cli"`; the fastboot operator never trusts it and
must still see exactly one real `fastboot devices` serial equal to `62bc28a1`.
This backs up old carriers, the original service, the original MP2650 module,
and the original main manifest. It atomically installs guard/service and the
new `04da...` MP2650 module, updates the main manifest service and module pins,
and verifies or adds the OpenRC `default` runlevel link for
`samurai-charging`. The receipt records the runlevel state before the change.
It then issues one AArch64 Restart2 syscall
(`syscall 142, 0xfee1dead, 672274793, 0xa1b2c3d4, "bootloader"`). It first runs
`/usr/sbin/samurai-charging stop`, `sync`, and fsyncs the critical backups/plan,
then fsyncs the installed receipt before the single syscall. It never writes a
new carrier. BusyBox `reboot bootloader` is not used. Keep
`stage-receipt.json` on the Windows host. The receipt must contain
`"host_fetch_unavailable": true` for this trial.

## 4. Verify and flash from Windows

First run local validation without `-Execute`. This checks the stage receipt
and all local files, but does not invoke fastboot:

```powershell
$Trial = "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\trial-516-r3"
& "$Trial\fastboot_operator.ps1" `
  -FastbootPath "C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe" `
  -StageReceipt "E:\path\to\stage-receipt.json" `
  -ReportPath "E:\path\to\fastboot-validation.json" `
  -NoFetch
```

After the phone is manually confirmed in bootloader mode, execute:

```powershell
& "$Trial\fastboot_operator.ps1" `
  -FastbootPath "C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe" `
  -StageReceipt "E:\path\to\stage-receipt.json" `
  -ReportPath "E:\path\to\fastboot-report.json" `
  -Execute -NoFetch
```

The operator checks one device with serial `62bc28a1`, product `msmnile`, and
the pinned partition sizes. It also checks the pinned DTB file and #516 boot
package receipt: boot hash, DTB hash/path, and DTB before/after input hashes
must agree. The DTB is embedded in boot and is not flashed separately. It
flashes logdump then boot and issues one `fastboot reboot`. With `-NoFetch`,
there are no host-side `fetch` commands; the guard must hash the actual
boot/logdump pair after boot. A missing or mismatching guard readback fails the
postboot audit.

Any write/readback failure triggers one restoration of the pinned old boot and
old logdump, followed by one reboot if restoration is verified. The operator
never retries an unknown new write. If restoration cannot be verified, it does
not issue a reboot.

## 5. Read-only postboot audit

Run as root on the #516 boot with the phone on the normal SDP/5 V link:

```text
ssh -T -i "E:\edk2-samurai-out\kernel72\id_ed25519" `
  -o "UserKnownHostsFile=E:\edk2-samurai-out\kernel109\known_hosts-pmos" `
  root@169.254.42.1 `
  "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-07/postboot_audit.py" |
  Set-Content -LiteralPath "E:\path\to\acceptance.json" -Encoding utf8
```

The report must contain `"passed": true`, `"read_only": true`, and
`"accepted_token_written": false`. It must also show the correct default
runlevel link, a live Type-C/TCPM 5 V contract, the bound `usb0` gadget
interface, and direct PM8150B ADC/VBUS samples inside 4.40-5.50 V. The legacy
BC1.2 observer is diagnostic only. The audit also requires the live runtime DT
properties `charger@5c/typec-supply`, the exact
`adc@3100/channel@8/label=usb_in_v_div_16`, and
`realme,apsd-handoff-trial`. Review all listed evidence and hashes on the host.

## 6. Optional acceptance token

This is separate from the read-only audit and is the only step that authorizes
the new pair to survive the 300 second watchdog. Run it only after reviewing a
passed report and before the watchdog deadline.

```powershell
$Report = Get-Content -LiteralPath "E:\path\to\acceptance.json" -Raw | ConvertFrom-Json
scp -i "E:\edk2-samurai-out\kernel72\id_ed25519" `
  -o "UserKnownHostsFile=E:\edk2-samurai-out\kernel109\known_hosts-pmos" `
  "E:\path\to\acceptance.json" `
  root@169.254.42.1:/root/charging-management-20261023/charging-integration-trial-20261026-07/acceptance.json
ssh -T -i "E:\edk2-samurai-out\kernel72\id_ed25519" `
  -o "UserKnownHostsFile=E:\edk2-samurai-out\kernel109\known_hosts-pmos" `
  root@169.254.42.1 `
  "python3 -B /root/charging-management-20261023/charging-integration-trial-20261026-07/acknowledge_trial.py --report /root/charging-management-20261023/charging-integration-trial-20261026-07/acceptance.json --confirm-boot-id $($Report.boot_id) --execute"
```

The token records the current `boot_id`, manifest hash, and audit report hash.
It is rejected on any other boot.

## 7. Failure handling

- Guard timeout or wrong expected state: do not issue a token. The guard restores
  old boot, old logdump, the original main manifest, original MP2650 module,
  and original init service, then reboots.
- Host flash failure: let the operator's single old-pair restoration finish.
  Do not manually replay a new flash.
- Operator restoration failure: stop. Do not improvise a write sequence.
- Pre-userspace boot hang: userspace guard cannot run; use only the known old
  carriers and a separate, reviewed recovery procedure.

