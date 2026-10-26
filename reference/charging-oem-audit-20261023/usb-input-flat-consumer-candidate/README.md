# R8 USB input: legacy and flat native-consumer retention

This candidate changes only `samurai_usb_retain_for_native_consumer()`. It fixes
the hardcoded legacy-node lookup identified in
[the parent/reset investigation](../../charging-session-20261023/dwc-parent-reset-investigation/README.md).
No module was installed or loaded. The first planned现场 transaction remains the
original prepared502 transaction; this leaf is a later topology prerequisite.

## Exact baseline and delta

The source is the actual R8 integration copy, SHA
`b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098`.
The decoder is **exactly**
`a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd`, copied
from the same `r8-source-integration/kernel-sources/drivers/power/supply` directory.
The old main-directory adjacent decoder is not used. The candidate source SHA is
`ee0f0806c5a51576f10b299aca173c61ab2b4764a5954c1039d1c73327878a88`.

`source-result.json` proves that every byte outside the retain function and the
entire existing legacy prefix are unchanged. `flat-consumer.patch` is the complete
source delta. The decoder, ordinary source/UDC budget calculation, PMIC reads,
1000ms fallback poll, PM callbacks, probe, module parameters and
`suppress_bind_attrs` remain unchanged. No future IRQ source is incorporated.

The old lookup `/soc@0/usb@a6f8800/usb@a600000` executes first with its existing
semantics. If it establishes `native_retained`, no flat lookup or additional
module reference occurs. Otherwise the new exact path `/soc@0/usb@a600000` must:

- exist and pass `of_device_is_available()`;
- contain compatible `qcom,snps-dwc3`;
- return exactly `samurai-usb-input` from `usb-psy-name`.

Only then does the existing `__module_get(THIS_MODULE)`/`native_retained=true`
policy retain this provider until the next boot. Every acquired OF-node reference
is released. Repeated calls do not add a second module reference. The original
user-settable `native_retained` parameter behavior is preserved; its boolean alone
is not newly promoted into independent proof that a module reference was taken.

This retains the existing lifetime contract for a selected native consumer. It
does not infer an accepted USB current, prove successful controller probing or
authorize hot-unload. The current native provider remains non-unloadable in the
established way; no force-unload or teardown path is added.

## Flat DT alignment

The session agent's separate `dwc-flat-board-candidate` derives from actual
native9271. It reports the real generated DTB
`3c66a954d94ee4e9f59aac8190272dac0f247e592aac254772b043bd9cded9ae`,115816B,
with the unique controller `/soc@0/usb@a600000`, compatible
`qcom,sm8150-dwc3` plus `qcom,snps-dwc3`, status`okay` and the unchanged raw
`usb-psy-name="samurai-usb-input"`. Those fields match this new branch. The old
wrapper/child is removed by that DT candidate, not by this module.

That DT and this ko are independent offline candidates. No actual boot or flat
controller was exercised. The existing#502 already links both Qualcomm drivers;
this module does not require or build a new Image. It does not merge the future
IRQ DT/provider or alter PHY/PD/EUD resources.

## Tests and real module build

`run-tests.py` compiles and directly includes the actual extracted production
function in `actual-retain.inc`. Eleven cases passed ASan/UBSan and Werror:
no nodes; legacy behavior unchanged even for legacy availability/compatible
fields that the old branch did not inspect; valid flat; repeated call; legacy
nonmatch falling through to valid flat; disabled flat; wrong compatible; missing
supply; nonexact supply; legacy priority; and premarked native-retained behavior.
OF lookup/availability/compatible/property/ref operations, module-get and logging
are explicit fake boundaries. These are not full-probe, device-reference or
hardware lifetime tests. No old IRQ/FLOAT/budget matrices were rerun.

`build-ko.py` reused the frozen USB board builder's actual in-tree method, the
original `kernel284/storage.py` helper SHA`5cddb34d…7d42c`, fixed32GiB backing
guard and existing actual Image502 source/config/export material. Only a new
private source view/build directory was written. `modules_prepare` PID970 and
the sole `samurai-usb-input.ko` target PID2806 were each actually waited to rc0;
W1 plus `KCFLAGS=-Werror` reported no diagnostics. The original exec session80399
then exited0. All tracked shared/R7/Image502/author inputs were identical before
and after. No new anchor, unmount, lock modification, SDK, Image link, device or
Git operation occurred; the284 window has been returned.

The actual new module is AArch64, intree`Y`, same release and vermagic as#502.
All40 strong imports resolve in the actual Image502 builtin export map, with no
unresolved strong imports or module-provider fallback. Actual config and generated
autoconf are exact Image502 matches. This is static build/import consistency,
rather than runtime/type-ABI or physical validation.

| Artifact | Actual identity |
| --- | --- |
| Private ko | `E:/edk2-samurai-out/charging-management-20261023/usb-input-flat-consumer-private-01/samurai-usb-input-flat-private.ko` |
| ko SHA / size | `c70a2ef09c48af4c51c60bf4081c63229464587ac3f5ad47f9c121209d1d2c17` /83944B |
| loaded-note bytes SHA | `77caf790c9eb71eb1d7fdf2ee4f053abde01fccbb64c85a86fdd6913d13a1bce` |
| GNU build-id | `fdebb13b3adc8d8f03599a9a45bd347935fb124a` |

`module-identity.json` and `ko-result.json` carry the full source/import/config and
actual child terminal receipts. New module/note identities must not be presented
as old R8 identities. No manifest/cohort/deployment/reboot tool was added. Any
future use needs its own consistent module/manifest/boot verification.
