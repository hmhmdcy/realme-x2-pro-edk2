# DWC resume unwind: current call-chain audit, changes required

This leaf audits the exact frozen **core 5331ae94…**, **gadget aabfc928…**, **header 9a8dc48a…**. It is not a deployable patch, Image or physical PM result. It does not alter those inputs, older rejected drafts, #501/#502 transactions or any device. No 284 storage guard, shared tree, object/Image build, SDK or Git action was used. Seventeen exact functions were composed in seven new native GCC ASan/UBSan/Werror cases; old 13/20/24/126 suites were not rerun.

The current DEVICE branch calls `dwc3_core_init_for_resume()` and then ignores `dwc3_gadget_resume()`. Its initialized core/PHY, event buffer allocation and registered gadget IRQ remain live. The new composed control reproduces the real failure return being ignored after both initial connect and recovery fail. It also reproduces a distinct case: initial start fails but synchronous recovery reconnects successfully, while the gadget still returns the same initial errno. A bare `int primary` is therefore insufficient to classify final service state.

## Exact calls and resource owners

| Source / function | Proven state and ownership |
| --- | --- |
| core 2516 `dwc3_core_init_for_resume` | Deassert reset, enable optional clocks, call core init. Its own init error path pairs clocks/reset. A later gadget failure does not enter that unwind. |
| core 1383 / 1413 / 1417 `dwc3_core_init` | Initializes PHYs, powers them on, programs event buffers. The fixture models these hardware APIs; exact surrounding init-for-resume and exit bodies are extracted. This board's legacy child optional core clock/reset handles are NULL; the parent owns its separate clocks. No five-child-clock leak is claimed. |
| gadget 2801 `dwc3_gadget_soft_connect` | Soft reset, event-buffer setup, endpoint start, RUN_STOP. Start failure masks/stops EP0 but retains core/event/IRQ resources. RUN_STOP failure has already set the software pullup flag; that flag is not physical HALT proof. |
| gadget 4816 `dwc3_gadget_recover_locked` | Holds `connect_mutex`, records IRQ generation, disconnects and may reconnect once. Its `dwc3_recovery_result` records stage/sequence/pending-at-publication; it is not an IRQ-depth or teardown owner. A late real IRQ preserves RECOVERY and schedules work again. |
| gadget 5091 `dwc3_gadget_resume` | Logs primary/recovery separately but returns primary even after successful recovery. It does not expose the recovery result to core. |
| gadget 4895 `dwc3_err_recovery_work` | Takes connect mutex and calls the same recovery helper. It obtains no PM/core lifetime reference. `synchronize_irq()` is not a join of this separate work item. |
| gadget 4699 `dwc3_check_event_buf` | In runtime suspended state, sets pending_events, takes `pm_runtime_get` and disables gadget IRQ. The current successful runtime-resume tail owns the corresponding put/enable. |
| core 2802 `dwc3_runtime_resume` | Any negative common result returns before the pending-events put/clear/enable tail. The new actual-function sequence retains exactly the modeled entry's reference and disable depth. |
| core 2884 `dwc3_pm_resume` | Disables runtime PM, sets ACTIVE, calls common; negative result sets SUSPENDED, then re-enables PM. Keeping powered core and returning negative is not a consistent failure result. |
| cached `drivers/base/power/runtime.c` 934–945 | The actual generic runtime caller sets RESUMING before callback and SUSPENDED/cancels pending requests after negative callback. Its state transition is a documented adapter in the test, not a simulation of the whole runtime PM engine. |
| core 581 `dwc3_event_buffers_cleanup` / 994 `dwc3_core_exit` | Cleanup returns early without DEVCTRLHLT. Core exit nevertheless powers off/exits PHY and clocks/reset. It does **not** free the event-buffer allocation or unregister gadget IRQ. |
| gadget 3057 / 3091 start/stop; core 2477 remove | IRQ request/free is attached to gadget bind/unbind. Event-buffer memory is freed later by core remove, not by core exit. It is invalid to invent an unconditional free or an IRQ-depth release on the resume error path. |

`source-result.json` supplies exact source lines/function hashes; these supersede abbreviated table line hints. The previous fixed-source PM/glue manifest is rechecked. The actual selected `qcom,dwc3` legacy parent resumes its own clocks/interconnect/state and separately populates the child; it does not unwind the child's initialized PHY/core on this error. HOST/OTG behavior is outside the proposed DEVICE consumer change.

## Seven new composed controls

1. Current ignored errno after initial RUN_STOP and recovery-stop failures: common returns zero, powered resources remain, existing successful runtime pending tail runs. This documents existing behavior, not a fix.
2. Test-only direct propagation through the actual runtime callback: negative result leaves powered/initialized core, pending_events, its get reference and IRQ disable depth. The separately sourced generic runtime transition marks SUSPENDED.
3. The same direct propagation through the actual system callback: it sets SUSPENDED while initialized PHY/core remain on.
4. Test-only IRQ-join/core-exit after unproven HALT: event-buffer hardware cleanup is skipped, PHY is still released, and a separately queued actual recovery worker later accesses after modeled core exit.
5. Even when DSTS indicates HALT and event-buffer programming is cleared, IRQ join does not drain the separately queued recovery work; that actual worker can still reach a core-access boundary after exit.
6. Current gadget primary `-EIO` with recovery `0`, final RUN_STOP success and error state NONE. This is distinct from failed recovery even though the legacy return is the same primary errno.
7. Original core-init failure control uses its own existing clock/reset unwind before gadget startup.

The late-IRQ controls inject the event only after the existing spinlock is released, while the modeled IRQ is enabled; they use the actual schedule/publication/work functions. They prove an unclosed interleaving, not that it occurred on this phone. MMIO offsets/values, PHY/init/endpoint commands, IRQ/work scheduling and PM APIs are explicitly fake. No DMA drain, physical HALT, enumeration or real interrupt timing is certified. In particular, the after-exit counter means access after the modeled resource release; it does not assert a measured bus fault or UAF of event-buffer memory.

The two rejected variants in `rejected-diagnostic-functions.inc` are **test-only controls** generated from these exact callers. They are not patches and must not be applied, compiled into a kernel or deployed. No prior permanent-poison/IRQ-parking WIP was reused.

## Result and next implementable cut

Safe total failure unwind is **not proved**. Neither direct errno with powered resources nor direct core exit is a valid repair. A HALT-unknown failure still lacks an authority that can safely establish hardware quiescence. Also missing is a resume-abort owner that blocks future recovery producers, drains the separate work outside its mutex, serializes bind/free IRQ, and pairs only its own pending IRQ/reference ownership. A Boolean pending flag or a one-time HALT read does not supply that lifecycle.

The concrete next source cut is in [OUTCOME-API.md](OUTCOME-API.md): expose the existing actual recovery result as a stack-only DEVICE resume outcome while retaining the legacy wrapper's ABI and primary-return behavior. This lets the new core consumer distinguish a genuinely completed reconnect from failure/pending work. Its failure consumer must remain gated on a separately proved abort receipt and correct runtime/system PM state handling. Returning zero merely because resources were retained is explicitly not proposed as a fix. No new source patch or single-object build is warranted until that failed-HALT/producer/PM ownership boundary is settled.

The native fixture ran once in its unique `/home` output: compiler PID762 and fixture PID773 both terminal 0 on original exec session32135. The first invocation stopped in source-hash preflight because Windows relative paths contained backslashes; no output/compiler existed then. `history/preflight-01.json` preserves it. Normalizing only metadata paths fixed the preflight; extracted source/policy bytes did not change.

Archive revision 2 only adapts the selected-file layout: the original audit bytes remain in `history/revision-1-audit-result.json`, and the identical 837-byte stdout is mirrored as `test-output.txt.inc`. `archive-layout.json` records the old/new names and equal SHA256 values. The workspace-only `test-output.txt` remains outside the current file list. Source, tests, original test receipt and outcome API are unchanged; none of the seven cases was rerun.
