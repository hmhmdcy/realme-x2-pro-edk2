The offline forward package contains only charger ko`97c16c3d…ffdd` and manifest`18e8a104…3b4e5`. The rollback contains the exact original charger`10ec06fb…6297f` and current IRQ manifest`5fca8e5a…69417`, not the older3203 manifest. Both were materialized, reopened and checked. Paths, SHA256 and sizes are in `payload-result.json`; binaries remain in its named private output.

The manifest changes only the two charger hash spans (`modules` and `installed_files`). Replacing those spans back reproduces the entire5fca input byte for byte. USB7cbf, protection7848, their expected loaded notes, manager/service/startup entries, adapter_revision and all caps remain unchanged. The exact old10ec bytes were also compared with the frozen original R8 archive. Actual AArch64 ELF/name/intree/vermagic and old/new build-id notes were read with the existing frozen cohort function. New note is`fe15a2fc…472016`; no loaded-state claim is made.

The retained carrier profile is IRQ boot`eddadec3…f6e06`, Image502`085d0306…25955` in logdump`ace2e261…63ed1`, as fixed by the existing cohort. This package neither reads/writes a carrier nor creates a current identity, guard, lease or installation transaction. The new module's build receipt establishes Image502 config/import compatibility; runtime type ABI and actual load remain unproved here.

The frozen R8 single-charger updater cannot directly consume this package:

- `update-r8.py`19–30 and50–76 pin its ended R7 guard/transaction,5638→3203 manifests and original f2bc payload. Lines81–86 also force revision`r8`; the current IRQ revision and new two-hash delta differ.
- Its runtime gates at191–209 require the old manifest, old loaded module identity and SDP100 baseline; acceptance at247–252 requires those original limits/source to match exactly. Its preflight also excludes Full. This is not the current IRQ/500-or-CDP/healthy-Full contract.
- The old launcher’s local_inputs uses the original R7 adoption/endpoint and baseline440 evidence. A future reuse needs the actual current IRQ adoption/boot/SoC/rootfs/carriers, new payload/manifests/charger-note binding and a unique supervised transaction, with actual source/Full/fault continuity. No such adapter was generated here.

The old updater unloads only the charger, so its existing provider-retention principle remains usable. Future work must preserve the resident USB/protection instances and the already consumed MAC attempt; this payload is not permission to reload protection or repeat the batch.

Seven affected packaging checks passed, including deterministic two-member archives, exact rollback, refusal of extra/mis-moded members, unchanged entries, exclusive output and the actual old manifest_delta rejection. No old matrix/default test, SDK/284/build, phone/SSH, module reload or runtime change occurred.
