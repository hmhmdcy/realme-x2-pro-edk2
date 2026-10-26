# Native USB PM: completed offline two-file cohort

The private forward payload contains only USB-input module2691 and the updated
manifest. The backward payload contains the exact original R8 USB module7d4 and
raw manifest3203. These are host-side archives, with no installer, stage worker,
activation request, live guard or phone identity.

| Artifact | SHA256 | Bytes |
| --- | --- | --- |
| Forward archive | `2e1320e9940539eaf3fe6c485970124c1836ead4ba67389f6659f324b9070bc6` | 25692 |
| Original-R8 rollback archive | `4575cdabf2b780fd0afdf6d81e731a44dfbd528c430e82588dcf3d6a4b0c3579` | 24010 |
| New manifest | `f74a702a1f86515235820ee89c0f9cb057b30674c6be13decbed6be0ef2716b9` | 1868 |

The sole materialization and its subsequent read-only audit returned0.
Private output is
`E:/edk2-samurai-out/charging-management-20261023/native-usb-pm-budget504-cohort-private-01/`.
Each archive has exactly two regular root-owned members, mode0600 and mtime0:
the original USB module path under the k363 charging extra directory and
`/usr/share/samurai-charging/manifest.json`. Extra, duplicate, symlink, metadata
and byte changes are rejected. No archive extraction or phone write occurred.

Only adapter_revision (`usb-native-pm-order-01`), modules.USB.sha256 and its
installed_files hash change. The six other installed file hashes, original
charger10ec/protection75b, manager61451/OpenRC and control/live dependencies stay
exact. Original startup500 is separately pinned. Input request900mA/CC250mA,
source-budget enforcement, thermal/Full/protection logic and original CV policy
are retained. This cohort cannot authorize a new USB allowance.

## Exact kernel and carrier pair

The required consistent Image is actual504 f647, carried by the independently
completed [64MiB logdump4453](../../charging-oem-audit-20261023/image504-budget-logdump-candidate/BUILD.md).
Original boot97811 and native9271 topology stay unchanged. The module's43 strong
imports reuse its actual502 link receipt, because actual504 public headers,
config and all15097 builtin export rows/names match502. This is scoped export
and build compatibility, not type-ABI or runtime-load acceptance. No IRQ/flat-DT,
new protection observer, fast-charge, desktop or rootfs rebuild is included.

`carrier-input.json` pins the actual completed carrier receipt. The final
validator compares that receipt's written/read-back Image504 row, saved502 ace2
base, candidate bytes and all10 completion facts. An independent504 label is
insufficient. The first1938 source missed this cross-binding; its original
10-case receipt remains intact and `carrier-binding-delta.patch` reconstructs
that source. Six actual packaging functions are unchanged, so those10 cases
are reused. Four new binding cases cover the actual completed carrier, old502
relabel, wrong base and incomplete readback. The
[limited follow-up](../native-usb-pm-pair-integration-review/CARRIER-BINDING.md)
resolves that finding for source911d. Old module/kernel matrices were not rerun.

## Future stage and complete rollback

The current phone is still recorded as501, with prepared502 awaiting its own
onsite step. The first physical transaction remains502. Neither that guard nor
any completed transaction is reusable for this future cohort.

The original manager accepts this independent revision and checks disk hashes.
After a future stage, new2691 disk versus old7d4 resident note must reject the
ordinary start/resume path. The provider selfpins until next boot; do not hot
unload, force replacement or restart the old service to manufacture acceptance.
A new stage-aware transaction must first obtain normal INHIBIT/register08 proof,
retain original live-note evidence and replace only these two files. Before
reboot this can mean only staged/runtime_pending.

After genuine502 adoption, coherent rollback comprises both exact original R8
rootfs files plus the saved502 ace2 carrier, followed by normal restart to align
disk and loaded notes. Returning only logdump, or the manager's configuration
rollback, does not restore this cohort. Unknown mutations or child states need
their original evidence reconciled; this package grants no automatic retry.

Actual new boot, provider/link probe, provider-first callbacks, fresh allowance
after controlled PM, USB data recovery and cable/icon timing remain unverified.
Reviewed scope is native DEVICE/runtime-on-active. Synchronous zero-budget
failure remains an explicit warning; auto/direct_complete and full UDC/DMA
recovery are not accepted. No device, SDK, storage helper or Git was used.

Default `python -B cohort.py` only checks existing inputs. `build --execute`
created the one fixed private output and refuses replay while it exists.
`audit` reads the saved artifacts. Neither action is a deployment interface.
