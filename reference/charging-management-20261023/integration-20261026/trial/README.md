# Charging integration #513 bounded APSD-retry trial

This package is prepared for a later on-device trial. It was not executed
against a phone, and no carrier was flashed or rebooted while preparing it.

## Scope

- Kernel version pin: `#513 SMP PREEMPT Mon Oct 26 16:51:54 CST 2026`
- Image: `3893a1c29a143325e7067e1d88fdf539332ae7ec11ac83fea263a86956d372b5`
  (59374080 bytes)
- Trial id: `charging-integration-513-20261026-03`
- Private staging root:
  `/root/charging-management-20261023/charging-integration-trial-20261026-03`
- Device: serial `62bc28a1`, product `msmnile`
- Fixed 5 V only. High voltage, PPS, PD voltage changes, and charger register
  writes are not part of this trial.
- One 300 second acceptance window per boot. The token is valid only for the
  `boot_id` recorded in `accepted.json`.

## Carrier pins

| Carrier | Bytes | Old | New |
| --- | ---: | --- | --- |
| boot | 100663296 | `5c8d23d4d5e834593dd3a24537044af8b57e2df53ed3a91fb7880ad7541f8311` | `8af84ca536c9d4e1f09d7395adb303ba6f2ed6fa9138adef074df95e68e56680` |
| logdump | 67108864 | `b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff` | `074518a70b23d8fe7380355af174a5c42da0fdba4e1f19f95f0bf1c77e45df58` |
| DTB (embedded in boot) | 116966 | n/a | `9aa3e6fce7833f294a2dd7dc9b8f9d4fc95f3627d0c2386ba2ce183bc4316cd6` |

## Files

- `trial_guard.py`: OpenRC `start_pre` guard, one watchdog per boot, rollback.
- `trial_common.py`: pinned hashes, safe file primitives, manifest checks.
- `trial_stage.py`: backs up old carriers, the original init service, and the
  original main manifest, installs the guard/service wrapper, records partition
  identity, and requests `reboot bootloader`. It never writes a carrier.
- `service/samurai-charging`: OpenRC wrapper with the guard in `start_pre`.
- `postboot_audit.py`: strictly read-only acceptance evidence collector.
- `acknowledge_trial.py`: separate, explicit token issuance after review.
- `fastboot_operator.ps1`: Windows host operator. The canonical command uses
  `-NoFetch`, because the bootloader does not implement `fetch`. The operator
  flashes logdump first, then boot, and sends one reboot. Carrier content
  readback is delegated to the guard after boot.
- The operator also pins the DTB file and the #513 boot-package receipt. It
  verifies that the receipt names the same boot hash, DTB hash/path, and DTB
  input before and after packaging. The DTB is embedded in boot and is not
  flashed as a separate partition.
- `manifest.json`: source, target, carrier, fastboot, and postboot pins.
- `tests/`: local controls using synthetic small carriers and fake fastboot.

## Stage behavior

The stage helper runs as root on the old kernel. In preflight mode it changes
nothing. With `--execute` it:

1. Verifies the explicit `--serial 62bc28a1` operator assertion and the current
   boot/logdump pins. The receipt records `serial_source: operator_cli`.
2. Copies old boot and logdump into the private evidence directory and verifies
   both copies.
3. Copies the original `/etc/init.d/samurai-charging` and
   `/usr/share/samurai-charging/manifest.json` into the evidence tree.
4. Records partuuid, start sector, sector count, and partition number.
5. Runs `/usr/sbin/samurai-charging stop` normally, then `sync` and fsyncs the
   old carriers, both original-file backups, plan, and manifest.
6. Installs only the guard, its common library, the OpenRC wrapper, the patched
   main manifest, and the trial manifest. Only the wrapper hash in
   `installed_files` changes in the main manifest.
7. Writes and fsyncs `stage.json` and `stage-result.json`.
8. Calls AArch64 `syscall(142)` (`RESTART2`) with
   `0xfee1dead, 672274793, 0xa1b2c3d4, "bootloader"` exactly once and does not
   retry. BusyBox `/sbin/reboot bootloader` is not used.

The host fastboot operator refuses to run without a successful stage receipt.
The receipt is an operator assertion, not remote attestation, because the
phone can no longer be queried by adb while it is in bootloader mode.

## Guard behavior

`start_pre` verifies the installed file hashes and the stage receipt. It does
not arm while the phone is still in the stage boot. After the host has written
the new pair, it:

1. Verifies both new carrier hashes and the recorded partition identities.
2. Starts one 300 second watchdog.
3. Accepts only a token whose `boot_id`, token, and manifest hash all match.
4. On timeout or any unexpected carrier/kernel state, restores old boot, then
   old logdump, the original main manifest, and the original init service, in
   that order, and requests reboot.

The private evidence tree is retained after rollback for inspection.

## Read-only postboot acceptance

The audit checks:

- exact #513 version string and the same boot as the guard state;
- `cdc_ncm` interface binding and NCM dmesg evidence;
- `qcom,pmic-typec` binding, one TCPM supply, one Type-C port, and its partner;
- native SDP and TCPM both at 500000 uA, 5 V, Type-C, sink/device roles;
- MP2650 500000/250000/8725000 uA/uA/uV, health `Good`, behavior `auto`;
- protection profile `0x2719`, safety/PF/error zero, managed sample fault zero;
- APSD/ADC preparation includes a bounded 2 second retry at 20 ms intervals
  for the early `-EAGAIN` sampling case. It is inferred from a successful
  qcom_pmic_typec binding, Type-C partner, and TCPM supply, with no
  `full-PD APSD/QC takeover refused` line. No successful startup log string is
  required; the source only prints `fixed5V callbacks joined` at shutdown.
- The explicit `realme,apsd-handoff-trial` DT property is checked by presence,
  not its value, on the Type-C node.
- The guard hashes the actual boot and logdump after boot and writes
  `carrier-readback.json`; postboot acceptance requires that same-boot evidence.
- no new critical warning lines and no taint bits beyond `baseline_tainted`;
- fixed 5 V sink PDO `04019032`.

It does not write an accepted token. `acknowledge_trial.py` is a separate
mutating step and must be run only after the report is reviewed.

## Tests

Run locally:

```powershell
python tests\run_tests.py
```

The suite uses only temporary directories, small synthetic carriers, and a
fake `fastboot` PowerShell script. It never opens a real device.
Current verification: 45 passed, 0 failed.

## Known limits and risks

- Userspace rollback cannot recover a hang before the guard starts. A bad boot
  carrier can still require known-good host recovery.
- The actual bootloader does not support `fetch`. Canonical operation therefore
  uses `-NoFetch`; the host cannot verify carrier contents before or after a
  flash in this mode. The guard must perform the postboot carrier readback.
- In `-NoFetch` mode, a flash failure triggers one restoration using only the
  pinned old carrier files. If an old-carrier flash command fails, no reboot is
  sent.
- If a new carrier write or readback fails, the operator restores only the
  pinned old boot and logdump. It does not retry an unknown new write.
- The stage bootloader transition relies on the verified AArch64 Restart2
  syscall. If it returns an error, the original main manifest and service are
  restored and no second syscall is attempted.
- If `fastboot reboot` fails after a verified new pair, no recovery write is
  attempted after that reboot request; the device state is uncertain.
- The stage receipt gates the operator but is not cryptographic hardware
  attestation. The explicit serial is only an operator assertion. The fastboot
  operator independently requires exactly one real device and serial
  `62bc28a1`. Do not edit or fabricate the receipt.
- The 300 second window is deliberately short. Review the read-only report
  quickly, then issue the boot-bound token only if every check is acceptable.
- Strict dmesg matching and the `4096` taint baseline can produce a false
  negative. Treat a failed audit as no acceptance, not as permission to relax
  checks.

The host private mirror for this package is
`E:\edk2-samurai-out\charging-management-20261023\charging-integration-trial-20261026-03`.

