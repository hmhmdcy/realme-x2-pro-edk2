# Authorized object-build supplement

The source/test delivery remains frozen at
`8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa`.
Its README and `kernel_object_or_Image_build_run=false` describe the earlier
source-only stage. This supplement records the subsequent authorized private
object build; none of those frozen source/test files was edited.

All eight objects that depend on `core.h` were compiled using the same candidate
header, not a mixed layout: core, trace, gadget, ep0, debugfs, dwc3-qcom,
dwc3-qcom-legacy and dwc3-generic-plat. Each is AArch64 relocatable with return0
and no W1/Werror diagnostic. This is interface/build validation, not a linked or
bootable Image or PM hardware acceptance.

`object-build/derive.py` reuses the established eight-object builder method but
pins the actual **#502** base:
`/home/cy122/charging-management-20261023/gauge-image502-notify-01`.
The original core/gadget/header must be exactly bd8a/9eec/525c. The actual #502
build receipt, full Image/vmlinux hashes, config, and each of the eight original
source/object/saved-command hashes are checked before compiling. No503,
outcome/exit/HALT source is selected. Only the three local candidate files are
copied into a unique private source view. All other inputs remain references to
the fixed base. No shared file is written.

Each invocation comes from its actual saved `.o.cmd`, retains the W1 flags and
adds `-Werror`. There is no make, link, module, Image, initramfs or carrier build.
The #502 config is unchanged:
`23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed`.
The original284 helper SHA is checked and its normal Ubuntu/root
`mounted_build()` guard is used. It restored the normal named mount in this
session; no format, unmount, lock/permission change or new anchor was performed.
The mountinfo after that original helper is unchanged across compilation.

Original host session52441 exited0. Original GCC PIDs795,805,816,825,834,839,844,851
were each waited by their same `Popen` owner and returned0. All shared, #502,
original command/source/object and author inputs match before/after. The284
window has been explicitly returned; this run owns no live compiler, guard or
anchor.

Private outputs and raw stdout/stderr stay at
`/home/cy122/charging-management-20261023/dwc-vbus-budget-fence-objects-01`.
`object-build/build-result.json` binds all object SHA/size/PID/argv evidence;
`object-build/delivery.json` binds this supplement and the unchanged source
delivery. Future use still requires a coherent Image build and review, paired
with provider-first ordering where fresh resume allowances must be accepted.
No phone, SSH, USB, SDK, Git, installation, activation binding or request occurred.

The source scope remains runtime-on/active native DEVICE with an initialized PSY
interface. Auto/direct-complete remains unsupported. The join is for this one
software budget work only; DMA/IRQ/UDC resource quiescence, full PM recovery and
the r5/icon root cause remain unproven.
