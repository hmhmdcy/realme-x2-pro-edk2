# Commands for charging-integration-r8-status-precharge-20261027

No command below was executed while this scaffold was prepared.

## Local verification

```powershell
cd "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\trial-517-r8-status-precharge"
python tests\run_tests.py
```

## Inspection before deployment

```powershell
python -B "E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026\prepare-trial-517-r8.py" --self-check
Get-Content -Raw .\manifest.json
Get-Content -Raw .\TRIAL-R8-PREPARATION.json
```

## Operator sequence

Use an SDP/5 V source only. Stop if the main-manifest hash on the device is not
the exact `main_manifest.old_sha256` in `manifest.json`.

1. Upload this directory to a new, unique remote package path.
2. Run `python3 -B trial_stage.py --package . --serial 62bc28a1` as preflight.
3. Require `stage_mode=carrier`, `restart_mode=bootloader`, and no carrier write.
4. Run stage with `--execute`; it installs userspace and both modules, then
   enters the bootloader once.
5. Run `fastboot_operator.ps1` with the stage receipt. It writes logdump first,
   boot second, and reboots once.
6. If the guard rejects the new boot, keep the generated rollback evidence and
   do not manually issue another reboot.

## New-boot acceptance

```powershell
$Key = "E:\edk2-samurai-out\kernel72\id_ed25519"
$Known = "E:\edk2-samurai-out\kernel109\known_hosts-pmos"
ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known root@169.254.42.1 `
  "cat /root/charging-management-20261023/trial-517-r8-status-precharge/state.json; sha256sum /usr/share/samurai-charging/manifest.json; sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai-k363/extra/samurai-charging/samurai-mp2650.ko; sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai-k363/extra/samurai-charging/samurai-usb-input.ko"
```

The guard must reach `accepted` on the new boot before any new soak is counted.
