# Trial 517 r8 full-boot packaging plan

This scaffold prepares the next RMX1931 full-boot charging trial without
touching the phone, SSH, adb, fastboot, a device wrapper, or the live charging
service. It does not create `trial-517-r8-status-precharge` yet.

## Planned package

- Source framework: `trial-517-wake-r1`
- Final destination: `trial-517-r8-status-precharge`
- Stage mode: `carrier`
- Restart mode: `bootloader`
- Full-boot replacement: new boot and new logdump/FAT
- Rollback boot: current #517 boot
- Rollback Image: current #517 Image
- Primary module: rebuilt `samurai-mp2650.ko`
- Auxiliary module: existing wake `samurai-usb-input.ko`
- Required built-in export: `bq27xxx_battery_set_status_override`,
  owner `vmlinux`, type `EXPORT_SYMBOL_GPL`

The generated manifest will update both module pins, all five bundled userspace
files, the main-manifest old hash, both carriers, the Image/FAT/boot receipts,
and a new deterministic trial token.

## Known pins

| Item | SHA-256 |
| --- | --- |
| Current rollback boot | `13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756` |
| Current rollback Image | `6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f` |
| Current primary module | `04da6a7bf492e44d6afa533816e662d54b5a5f0391f4fe0e5e6e7f8555cedf69` |
| Current logdump | `d884075a04d00112c95d0d3215ae342d43fb94d03a19b7753bf3f6deee2bbb43` |
| Runtime DTB | `d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b` |
| Wake USB module | `22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529` |
| Current old USB module | `161bcc3376864e6f867aa5cc0371b5ab61ba9d716108aad0f45e6c765d378f86` |
| Wake-r1 source manifest | `ab69570b74e64715267b0aec62c00660c0c651856416a375452b5d7351a8f147` |

The old USB pin defaults to `161bcc...`. If wake-r1 is installed before the r8
full-boot stage, pass `--usb-old-sha256 226041... --usb-old-bytes 91896`.
Likewise, the current main-manifest old hash is normally `b07f...`, but after a
successful wake-r1 install it is the preflight-recorded `d9f231...`; it must be
supplied through `--main-manifest-sha256`, never guessed.

## Inputs still required

- Final new Image manifest path, host-readable copy, byte size, and SHA-256.
- Final kernel release and exact `#N SMP ...` build label.
- Final host-readable WSL/build root containing `Image`, `vmlinux`,
  `System.map`, `Module.symvers`, and `include/config/kernel.release`.
- Final new boot path, size, SHA-256, and boot package receipt.
- Final new logdump/FAT path, SHA-256, and FAT package receipt.
- Final rebuilt `samurai-mp2650.ko` path, size, SHA-256, and matching vermagic.
- Confirmation that `Module.symvers` contains exactly one
  `bq27xxx_battery_set_status_override` row owned by `vmlinux` and exported with
  `EXPORT_SYMBOL_GPL`.
- Current main-manifest hash for the exact install order.

The new Image, kernel label, boot, logdump/FAT, and primary module must differ
from the current rollback values. The script rejects a different USB wake module
hash because `226041...` is already the tested wake module.

## Safe invocation

Default execution is read-only and prints the deterministic plan:

```powershell
python -B prepare-trial-517-r8.py --self-check
python -B prepare-trial-517-r8.py `
  --image '/home/cy122/charging-management-20261023/.../Image' `
  --image-file '\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023\...\Image' `
  --image-sha256 '<64 hex>' `
  --image-bytes <bytes> `
  --kernel-version '#518 SMP PREEMPT ...' `
  --kernel-release '7.3.0-rc6-rmx1931-samurai-k363+' `
  --build-root '\\wsl.localhost\Ubuntu\home\cy122\...' `
  --boot 'E:\edk2-samurai-out\...\boot-r8.img' `
  --boot-sha256 '<64 hex>' `
  --boot-receipt 'E:\edk2-samurai-out\...\result.json' `
  --fat-receipt 'E:\edk2-samurai-out\...\result.json' `
  --logdump 'E:\edk2-samurai-out\...\logdump-r8.img' `
  --logdump-sha256 '<64 hex>' `
  --mp2650-module '\\wsl.localhost\Ubuntu\home\cy122\...\samurai-mp2650.ko' `
  --mp2650-module-sha256 '<64 hex>' `
  --main-manifest-sha256 '<b07f... or d9f231...>'
```

Only after every pin is final and the target is still absent:

```powershell
python -B prepare-trial-517-r8.py <same arguments> --materialize
```

`--materialize` refuses an existing target. It copies into a private sibling
directory, validates and hashes the result, then renames it. It never overwrites
an existing trial or package.

## Remaining execution gates

1. Run the copied Windows and WSL test suites and refresh test evidence.
2. Run stage read-only preflight on the phone; no carrier write may occur.
3. Require the exact live kernel version and main-manifest old hash.
4. Execute the stage, then run the fastboot operator; one reboot only.
5. On the new boot, prove accepted state, both modules, new main manifest,
   protection Good, Type-C/TCPM/NCM, and MP2650 telemetry.
6. Start a fresh same-boot soak. Previous #517 soak evidence is not reusable.
7. Physically test low-battery precharge, CC/CV, Full hold, recharge, thermal
   bands, and USB insertion/removal wake before declaring the trial daily-use
   ready.
