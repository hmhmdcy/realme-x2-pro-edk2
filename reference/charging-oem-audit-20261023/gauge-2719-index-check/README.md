# Existing pack-descriptor indexes: limited check

No matching descriptor was found in these **six existing selected indexes or
summaries**. This is not a search of full vendor/odm/OTA contents. Exact source
paths, hashes, sizes and scope are in `result.json`.

| Existing cache/index | Actual scope |
| --- | --- |
| `reference/kernel73/gpu-firmware-manifest.json` | 7 selected same-handset vendor GPU files |
| `reference/kernel81/firmware-inventory.txt` | Existing depth2 Wi-Fi-name candidate list from vendor/firmware and modem/image |
| `reference/kernel81/wifi-firmware-manifest.json` | 35 selected same-handset wireless files |
| `reference/kernel88/mpss-inventory.txt` | Existing depth2 MPSS-name candidate list from modem/image |
| Private `kernel88/mpss-firmware-manifest.json` | 33 selected MPSS files |
| `reference/kernel207/stock-mcfg-inventory-validation.json` | Summary of173MCFG files; not its original path index |

The exact MCFG host-side path-index filename named by the existing producer,
`E:/edk2-samurai-out/kernel207/mcfg-source-manifest-private.json`, is unavailable.
The existing producer was read as source only and was not executed. Its173file
summary must not be represented as173searched file paths.

Literal searches for `.bqz`, `.bqfs`, `.df.fs`, `.srec`, standalone `2719`/`0x2719`
and `2719000400060003850200` found zero matching lines in those six inputs.
No full vendor, odm or OTA member index was identified in the limited metadata
discovery scope. Workspace archive/out manifests found there were camera,
documentation or mirror records; the kernel source/build cache index is also
outside ROM membership scope.

No archive or ROM image was opened, no payload was extracted, no new inventory or
full-drive scan was made, and no firmware download, device/SSH/USB/SDK/build/Git
action occurred. No binary candidate was identified, so no new binary parsing
was warranted. The exact2719 firmware mapping and new-MAC semantics remain open;
there is no new query permission or production change. This check ends here.
