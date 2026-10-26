# PHY publication and withdrawal candidate

This is an offline, same-Image integration candidate for the frozen femto-v2
window and PD5V DWC client. It does not change Image501, a device, configuration,
or any shared source. It grants no route, PD, budget or APSD permission. The
actual `owner_entry_gate()` still returns `-EOPNOTSUPP` with a valid bus backend.

The implementation changes the actual femto platform probe/remove/shutdown/PM
callbacks and the actual DWC owner bind/unbind and restore calls. It is not a
standalone state model. `lifetime.patch` is incremental against the two frozen
component candidates in `source-inputs.json`; it is not a patch against the
currently deployed Image501. No symbol is exported and there is no UAPI or new
automatic consumer. The existing default-n owner Kconfig and device-property
opt-in remain required. The unchanged default property-return prefix is bound
in `scope-result.json`.

## Entry and ownership

`qcom_snps_hsphy_window_client_register()` accepts the actual generic PHY object
only while its platform provider is published. Its binding contains a global
nonzero provider identity, per-provider nonzero client identity and client
context. Registration holds a real `kref_get_unless_zero`/`put` reference to the
DWC owner. Every dispatched cancel or complete callback has another real ref.
Neither `get_device()` nor an active PM ref is treated as a devres lifetime pin.

Begin/end now take that binding. The registry compares the old pointer value
and all identities before dereferencing a provider or PHY. An admitted operation
has an inflight count until after the original function and PM put finish.
An old binding after removal or a new provider instance returns `-ESHUTDOWN`
without MMIO; a successful re-probe never inherits the old provider identity.

The unchanged active PHY algorithm still requires initialized device mode and
`pm_runtime_get_if_active`, saves every original masked value before the first
write, enters in the OEM order, and restores in reverse with exact readback.
It does not init, reset or request a resume to obtain a window. Caller ownership
of a real active DWC HALT is still necessary and not established by this API.

## Withdrawal and locks

The order is:

1. Block new entry in the registry.
2. On remove/shutdown/final devres withdrawal, synchronously disable runtime PM
   and join its callbacks before generic PHY devres can disappear.
3. Finish an already-dispatched complete notification, then call the client's
   cancel/join with no registry or PHY lock held. An existing end is allowed
   during that join while MMIO is still valid.
4. Close end as well, drain admitted operations, and mark the provider terminal
   under the generic PHY mutex. Unpublish before releasing client refs/resources.

System prepare and runtime suspend perform steps 1/3/4 without terminal removal;
an actual restoration/join error refuses PM and keeps entry blocked. Successful
complete/resume clears only its matching reason and sends a metadata callback.
Shutdown is terminal: later complete/resume cannot republish it. A failed
restore retains the old enter/restore errno and sets independent lifecycle
revocation information; forced remove is never called successful restoration.
Any retained window PM reference is dropped without another MMIO operation.

The original `devm_pm_runtime_enable()` action precedes generic PHY creation,
so its normal reverse cleanup is too late to serve as this new lifetime fence.
The candidate expands that exact enable/managed cleanup into an idempotent local
wrapper: one enable, one disable and the original dont-use-autosuspend cleanup.
The final withdrawal action stops PM earlier; the older cleanup does not add a
second disable depth. Kernel `pm_runtime_disable()` may service an already
pending resume as in the original cleanup; the owner issues no new resume request.
New window entry is already blocked before that barrier, then the actual join
cancels any work queued by an already-running completion.

The withdrawal action is registered **last**, after MMIO, clocks, reset,
regulators, managed PM, generic PHY and PHY provider. Fixed-source devres LIFO
therefore runs it before those releases. If action allocation fails,
`devm_add_action_or_reset()` executes the same withdrawal immediately. Probe
failure cleanup, explicit remove and shutdown use the same terminal fence.

The registry does not span MMIO, PM calls, a PHY mutex acquisition in an active
operation, or client callbacks/joins. Unregister checks idle under registry +
PHY mutex but never waits for a callback. Thus an owner may unregister while
holding `owner_registry` even if a provider callback is waiting for that mutex;
the callback's extra real kref prevents use-after-free. DWC unbind joins its
worker before unregistering. Failed token restoration retains its existing
quarantined tombstone instead of freeing an outstanding owner.

For REMOVE/SHUTDOWN the actual client invokes the existing retiring join:
restore PHY, cancel DWC while keeping HALT, and retain downstream quiet state.
It does not reconnect DWC just before a supplier is released. Ordinary PM uses
the existing non-retiring restoration. Main and restoration errors remain
independent, and teardown failure cannot be relabeled restored.

## Actual caller evidence

`lifecycle-source-evidence.json` binds the fixed ba61/Image363 source cache:

- `device_prepare()` holds the device mutex around prepare, after taking its
  noresume PM hold; it does not acquire the generic PHY mutex or runtime PM
  spinlock for that callback.
- `__rpm_callback()` releases `dev->power.lock` before invoking driver runtime
  callbacks; `__pm_runtime_disable()` disables and executes the runtime barrier.
  The barrier releases that lock while waiting for pending/running work.
- The new terminal helper holds only its dedicated stop mutex across disable.
  No runtime or owner callback takes that mutex. The registry is released first.
- The original end uses asynchronous `pm_runtime_put_autosuspend`; the owner
  restoration also uses asynchronous PM puts. The cancel/join chain does not
  synchronously resume or lock the provider device while prepare holds its lock.
- Driver remove precedes `device_unbind_cleanup()`/`devres_release_all()`.
  `release_nodes()` executes the reversed devres list outside its list spinlock.
  `__devm_add_action_or_reset()` calls the action on registration error.
- Generic `phy_get()` only supplies a device/module reference and a stateless
  link. Those references alone are explicitly not this component's lifetime
  guarantee. This candidate fences its actual window client and platform PM;
  it does not claim to redesign all unrelated generic PHY consumers.

## Verification and limits

`test-result.json` records nine new ASan/UBSan/Werror pthread groups using 27
complete functions extracted from the actual sources plus the actual full
`phy-lifetime.inc`. The fake boundaries are PM/MMIO/devres/OS primitives and the
previously tested owner-join algorithm. New actual DWC kref/cancel/complete and
registration functions run directly. The cases cover registration/refusal,
restore error and old-token zero MMIO after free/rebind, PM failure, shutdown,
inflight begin drain, complete-before-cancel ordering, unregister/callback ref
races, probe LIFO/action-reset failure, runtime callback barrier, and the final
unconditional policy refusal. These are not kernel lockdep or physical tests.

The old PHY eight-group and PD bridge fourteen-group suites are reused by hash,
not rerun. `scope-result.json` checks unchanged original masked function bodies,
owner worker/join/notifier/PD observation and opt-in prefix. `history/` preserves
the initial eight-group result and the first private object attempt, including
source bytes bound to its receipt. That attempt compiled PHY but failed the
owner because an older `core.h` included its sibling old owner header first.
The final private include layout must copy that core header and the new owner
header together; it is not a production source fix.

The affected saved-command W1/Werror object build passed at native exec session
90767, exit 0: PHY, owner with the current module Type-C configuration, and
owner with the private future-builtin header view. All three had zero diagnostic
bytes. `build-result.json` binds actual commands, outputs and unchanged shared
source/config/command/symvers hashes. The command-only builtin view is not a
configuration change or a successful whole-Image link. No make,
modules_prepare, Image, module link, DTB, package or installation is performed.

Still absent: a trusted EUD-off route contract and write-time atomic lease/
physical-generation fence. PD5V ownership is not a physical attach epoch and
does not authorize 1341. Existing EUD-off COM absence still cannot be treated
as quiet success. This PHY revision does not remove any of those refusals.
No hardware or deployment success is claimed.
