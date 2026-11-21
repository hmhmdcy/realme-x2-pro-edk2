# Commands for charging-integration-r9-status-precharge-20261027

No command below was executed while this scaffold was prepared.

## Local verification

```powershell
# Run from this frozen package directory after extraction.
python .\tests\run_tests.py
```

Physical USB wake and cycle launchers require PowerShell 7 (`pwsh.exe`).

## Inspection before deployment

```powershell
python tests\run_tests.py --output test-results-local.json
Get-Content -Raw .\manifest.json
Get-Content -Raw .\TRIAL-R14-PREPARATION.json
```

## Operator sequence

Use an SDP/5 V source only. Stop if the main-manifest hash on the device is not
the exact `main_manifest.old_sha256` in `manifest.json`.

1. Upload this directory to a new, unique remote package path. After extraction,
   run `chmod -R go-w <package>` so the fail-closed file-mode checks can pass,
   then require `sha256sum -c SHA256SUMS` to pass before any device access.
   The current canonical archive is `-14-upload.tar`.
2. Run `python3 -B trial_stage.py --package . --serial 62bc28a1` as preflight.
3. Require `stage_mode=carrier`, `restart_mode=bootloader`, and no carrier write.
4. Run stage with `--execute`, capturing stdout to a local receipt file before
   SSH disconnects:

   ```powershell
   ssh ... "cd <remote-package> && python3 -B trial_stage.py --package . --serial 62bc28a1 --execute" |
     Set-Content -LiteralPath .\stage-receipt.json -Encoding utf8NoBOM
   ```

   Require the receipt's `passed`, `manifest_sha256`, `version_pin`, and
   `restart2` fields to match the package before invoking fastboot.
5. Run `fastboot_operator.ps1` with the stage receipt. It writes logdump first,
   boot second, and reboots once.
6. A non-crash audit or watchdog attention does not auto-rollback the carrier.
   Inspect the evidence, fix the userspace/package issue, and flash the repaired
   package directly. Automatic rollback remains reserved for crash or carrier
   integrity recovery.

## New-boot acceptance

```powershell
$Key = "E:\edk2-samurai-out\kernel72\id_ed25519"
$Known = "E:\edk2-samurai-out\kernel109\known_hosts-pmos"
ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known root@169.254.42.1 `
  "cat /root/charging-management-20261023/trial-517-r9-status-precharge/state.json; sha256sum /usr/share/samurai-charging/manifest.json; sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko; sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko"
```

The guard must reach `accepted` on the new boot before any new soak is counted.
