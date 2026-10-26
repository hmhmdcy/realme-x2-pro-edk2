# Optional EUD COM software quiet window

Review candidate only. `0001-eud-optional-software-window.patch` implements a returning software quiet/restore foundation in the exact Image-linked COM driver. There is no consumer, exported symbol, userspace switch or automatic activation. The window never writes CSR_EUD_EN or AHB2PHY and does not claim electrical handoff, bypass, USB enumeration, APSD or USB500 success. Hardware CSR disable/restore remains a separate, unimplemented stage.

## Scope and source

The selected COM source is the cached `apsd-integration/current-r7/snapshots/drivers--tty--serial--eud.c`, SHA `16670a85501bf1bb1d8ae5bd856d991a73ac199028e33275f34f1774991c7bfd`. Existing [Image linkage](../../charging-oem-audit-20261023/apsd-integration/current-r7/image-source-linkage.json) proves it matches commit `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`, original Image SHA `15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468`. The [source manifest and integration boundaries](../../charging-oem-audit-20261023/apsd-integration/current-r7/README.md) and [working boundaries](../../../WORKING-BOUNDARIES.md) were read before changes.

The exact cached DTB instantiates `qcom,sm8150-eud-com`, rather than the SCM/role-switch-managed full `qcom,eud` device. Existing [OEM EUD/SDP material](../../charging-oem-audit-20261023/eud-sdp500/README.md) was reused. No new sources were downloaded, and no hub descriptor, OTP, strap, charger protection, R8 source or main tree was changed.

Short quiet periods deliberately allow console output and an already-dequeued in-flight debug frame to be discarded. Kernel printk records stay in the kernel ring subject to its ordinary capacity. A host ACK or lossless FIFO state is not required or fabricated. Undequeued TTY data is paused and scheduled again on explicit end; a normal TTY close still owns its normal queue lifetime. Neither the kernel ring nor the existing TX journal guarantees indefinite retention or host delivery.

## Implemented contract

`eud-com-window.h` is an internal built-in interface. Calls require process context outside EUD callbacks, with no UART, TX or console lock held. No EUD lock remains held on return. A future owner must bound its own session; this component does not time out by silently resuming producers under another hardware phase.

| Call/result | Behavior |
| --- | --- |
| `eud_com_quiet_begin(result)` | Requires an initialized RX session, no current quiet owner, no PM transition, and no TX/RX stopping or accepted F1/reboot. Rejects calls from its own TX/RX work with EDEADLK. Returns a fresh cookie after gating producers and joining IRQ/work activity. |
| `eud_com_quiet_cancel(cookie,result)` | Exact cookie required. Marks CANCELLED and keeps software quiet. It does not resume anything or clear an old fault. |
| `eud_com_quiet_end(cookie,result)` | Exact cookie required. Restores the saved Linux IRQ-enable intent and schedules existing TTY/RX work. It does not enable an originally disabled diagnostic IRQ or clear its old fault. Restored refers only to this software pause. |
| Missing IRQ while restore requires it | ENXIO with `restore_error`, quiet and cookie retained. No implicit retry or default enable. The owner may explicitly retry after resolving the inconsistency. |
| System PM | prepare rejects quiet with EBUSY. Successful prepare blocks new begin until complete, covering the prepare-to-suspend interval. No sleep/reset/clock action is added. |
| Runtime PM | suspend rejects quiet with EBUSY; a completed runtime suspend blocks begin until resume. The patch does not enable runtime PM or invent a clock/PHY reference. |
| Remove during quiet | Marks REMOVED, joins activity, destroys the endpoint and invalidates its token. It leaves the current AHB2PHY value alone instead of imposing probe history during an external session. A tombstone cookie blocks reprobe before MMIO. After its other components are cleaned up, only exact `end(old_cookie)` acknowledges removal and releases the reprobe interlock; it still returns ENODEV and never claims restored. |

The result reports `cookie`, `state`, `software_quiet`, `cancelled`, `restored`, `error` and `restore_error`. `csr_touched` and `ahb2phy_touched` remain false for this window. They describe this component's writes, not proof that other firmware or drivers never changed a register. Successful end after cancel can return zero for restoration while retaining `cancelled=true,error=-ECANCELED`; that is not a successful detection result. REMOVED or failed end is never restored.

## Actual synchronization

A new global window mutex serializes API calls, probe, remove and PM against the global COM pointer's lifetime. It is released on every return and is not used by RX dispatch. Short flag/IRQ operations reuse the existing UART lock. Quiet first gates all FIFO access, saves only the current software IRQ-enable intent, clears stale watchdog waiting/credit and disables that Linux IRQ without synchronously waiting under the spinlock. In process context it then synchronizes IRQ, cancels RX/TX work and joins the TX mutex. The existing interrupt mask is not rewritten by begin/end.

The gates cover TTY work before dequeue, start_tx, startup, shutdown drain, send_frame, legacy/atomic console FIFO access, threaded-console RX kicks, IRQ collection, RX work/requeue and the reboot decision. Console registration and nbcon allocation/sequence are left intact. The atomic console callback does not take the TX mutex, so its UART-locked FIFO gate is essential; a late no-op work kick is harmless because its work entry rechecks quiet. Any already running work completes before begin returns. No wait, console registration operation or PM operation runs under the UART spinlock.

An accepted F1 header remains a distinct pending restart and causes begin to reject. The irreversible restart decision and quiet gate share the UART critical section, so begin cannot race a newly committed reboot. The candidate does not call the restart tail to obtain quiet and never clears F1/reboot history on end.

Default operation without a consumer keeps existing TX pacing, RX initialization delay, console behavior, CSR/AHB writes and ordinary remove restoration. The extra state gates are false; PM callbacks perform only software interlocking. During a borrowed remove, the original IRQ teardown still restores its owned interrupt mask before freeing IRQ; CSR/AHB quiet fields are not a claim that removal performs no other register access.

## Future coordination with DWC

The separate DWC foundation owns controller HALT and active-only PM handling. The tentative owner order is EUD software begin, DWC begin, separately authorized hardware stages, explicit hardware cleanup, DWC end, EUD end. Components do not call or take each other's locks. Begin failure is handled through the already acquired component's explicit cancel/end, not an implicit resume. Both tokens and all independent errors must remain valid before accepting an overall result.

The owner must keep its own cross-component power/PM and lifecycle cancellation constraint until EUD end completes. DWC end may release its active PM reference; its return alone is not proof that COM's bridge will remain powered. The COM node has no PHY/clock resources from which this candidate can truthfully acquire that reference. Remove can make either token terminal; the owner must cancel/join its session before acknowledging the EUD orphan and must never label a removed component restored.

No automatic owner is supplied. In particular, software quiet does not authorize a BC1.2 operation: it does not disable the EUD hub or prove analog DP/DM high-Z, PD inactivity, DWC data route or restored host configuration.

## Separate hardware stage still missing

Existing `eud_reboot_cmd` is a useful stop-order reference but ends with `kernel_restart`; it is not returning recovery. Its AHB helper writes a probe-era snapshot with no comparison, and its CSR path writes zero without a saved runtime value. The full OEM driver also uses optional secure EUD_EN2 and extcon/role state unavailable to this COM binding. Neither defines a normal-OS CSR-off/on route-completion receipt or a reversible failure state.

A later CSR stage must save the actual borrowed state, own the powered MMIO lifetime, compare documented state on every transition, and report hardware restoration separately. It must reject unsupported old states instead of writing a default 1 or a probe-era AHB value. Hardware routing and USB enumeration need a separately coordinated validation with an independent recovery channel. Nothing here modifies descriptors, OTP/straps or supply authorization to manufacture that result.

## Verification and artifacts

- `prepare-candidate.py` generates private `eud.c`, header and patch from the exact base hash. The patch was applied to an independent private source copy and reproduced candidate/header bytes exactly (`patch-check-result.json`).
- `candidate-test-result.json`: 9 groups exercise the actual candidate functions with fake OS/MMIO: unchanged no-consumer TX; quiet gates and joins; exact-token restoration; cancel with an old IRQ fault; F1/reboot/startup/self-work rejection; system/runtime PM interlocks; rejected IRQ restoration and explicit retry; quiet/ordinary remove and orphan acknowledgement; and a real pthread begin-join/remove lifetime race. ASan, UBSan and Werror passed. The actual full RX-work body is included; unrelated delivery/GIC helpers are fake test boundaries. This is not a proof of every kernel interleaving.
- `object-build-result.json`: the entire private arm64 EUD object compiled with the original build's saved W=1 command plus Werror, no diagnostics. Only output/dependency/temp paths were redirected. There was no make/config regeneration, SDK call or shared output write; selected original config/generated headers/object/command hashes were checked unchanged. This proves compilation, not link or hardware behavior.
- `test-result.json` preserves the earlier 7-group audit of 15 unchanged callbacks, explaining why old UART stop and reboot helpers alone were insufficient. It was not rerun to attest this candidate.

Candidate SHA `8cdd661b7834a7ccba46bd7577be84bd3bb81f6a00fb512d2b70e9d7c4c1231c`; header SHA `8003aa9619d2f9d1a15d4ff97460b8f106dc54defc841f31670e98d48e2d8c46`; patch SHA `838cb462b1ff1535185b82fee980ef7f368585ba975aaf3f394e07f5e93f4929`. Private object SHA `ea5fd9fd2b869dd9abfa8915254646c490f9cd70e4d6e7a925dfa435e0268bd3`.

All work was offline. The original verified storage helper was reused only to access the existing build and compile a private object; its binding was not changed. No phone, SSH, USB handle, SDK, deployment, reboot or physical acceptance occurred. Main, R8 and shared kernel sources remain untouched.
