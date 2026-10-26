# Optional APSD DWC lifetime owner — offline candidate

This leaf implements a real power-supply notifier and delayed-work consumer,
not a standalone protocol mock. It binds only after successful gadget init,
with the new default-off `USB_DWC3_SAMURAI_APSD_OWNER` option **and** explicit
`samurai,apsd-owner` property. Neither is enabled on the phone. Normal paths
with no option/property keep the existing behavior.

The DWC copies are based on frozen `apsd-dwc-window-candidate-r2`. The new
consumer joins work before runtime/system PM, UDC stop, gadget exit and core
exit. The worker never acquires the registry mutex that lifecycle callbacks
hold while joining. Notifier enqueue checks the blocked state under the same
short spinlock that sets the fence, so a late notification cannot restart
work after the join. System/runtime/core/UDC fences are independent. Only a
fresh physical off/on sample can start a new once-core epoch: logical UDC
stop/rebind preserves the attempt history.

`samurai-apsd-backend.h` is the frozen transport contract (`00d5659e…cee94`):
`read_sample(ctx, sample)` returns two new equal R7 physical reads and a new
serial; `rerun_once(ctx, epoch)` consumes its epoch before one physical masked
1341 transfer, including failures. Registration/unregistration are outside
the provider's lock. Unregistration synchronously withdraws and joins the
consumer before provider regmap/devres teardown. The two GPL registration
exports allow the existing module provider to register with a built-in
owner; no new EUD/PHY exports or userspace interface are introduced. Their
option-disabled stubs keep an absent owner from enabling a backend.

The source contains the sequential EUD → verified DWC HALT → PHY entry and
PHY → DWC → EUD restore path, plus the original once-core claim/write/clear
→ new DONE handling. An additional active-only DWC PM reference lasts through
EUD restoration. UDC retirement cancels/parks DWC, lets the original
`window_shutdown` consume that token, then releases EUD; it never briefly
calls reconnecting `window_end` during UDC removal. Restore errors remain
separate from the protocol/primary error. A failed PHY restore retains the
remaining quiet tokens. Remove after failed restoration keeps an orphan
tombstone and blocks rebind; it does **not** report restored or access the
removed controller later. No resume, PHY reset, CSR/AHB write, current policy,
descriptor, role or PD change was added.

**Every actual hardware attempt is currently refused at `owner_entry_gate`,
even with a registered PMIC backend.** There is no audited PD/sink/route
generation lease, nor EUD/PHY pre-remove cancel/join coverage. Callback
presence is not permission. The actual optimized arm64 owner object therefore
contains no begin or 1341-call path. The direct component functions are
exercised only by explicit fake-boundary tests. This is the requested first
DWC lifecycle closure, not an enabled cross-driver APSD solution. The gate
must not simply be removed: real PD/route acquisition, pre-write validation,
invalidation, EUD/PHY withdrawal and restore-failure power lifetime must be
reviewed together. The OEM contract `apsd-tcpm-owner-candidate` remains
implemented=false. The gate cannot grant permission to a future provider.

The fixed actual config has DWC, `SERIAL_EUD_CONSOLE` and the SNPS PHY built
in; `USB_QCOM_EUD=m` is a different full USB EUD driver. The Kconfig fragment
requires the three relevant drivers and power-supply core built in. Actual
`nm` checks resolve this candidate's component references against the frozen
DWC/EUD R2 and existing PHY private objects, with no full USB EUD references.
This is not a final vmlinux link.

Validation completed:

- 13 new actual-function cases passed host ASan/UBSan and Werror. They include
  the extracted actual DWC `gadget_stop`, `core_exit` and `pm_prepare`, late
  notifier fencing, inverse error recovery, cancellation, source withdrawal,
  rebind/physical-epoch separation and failed-remove tombstone behavior.
- Only `core.o`, `gadget.o` and `samurai-apsd-owner.o` were privately compiled
  with the fixed Image's saved W=1 command plus Werror; all passed with zero
  diagnostics. Source/config/generated files/original objects/saved commands
  were identical before/after. No make, SDK, Image or module link was run.
- The first private compile exposed `ep0.h` loading the original core layout;
  its failure and `objects-01` are retained. The successful `objects-02` run
  force-included the private candidate `core.h` after cached compiler/config
  includes, making all three objects use the same layout. No source defect
  was hidden by weakening warnings.
- Existing once-core, DWC R2, EUD R2 and PHY test suites were reused, not rerun.

`dwc-lifecycle.patch` modifies only the three copied DWC files. Integration
also needs the two new owner files, the backend header at
`include/linux/usb/samurai-apsd-backend.h`, the two build fragments, and verbatim
copies of the frozen once/EUD/PHY headers beside the owner (the private build
uses equivalent pinned include copies). No integration is applied here.
`object-build-result.json`, `test-result.json`, `linkage-result.json` and
`delivery.json` bind the exact reviewed bytes and scope. The build runner
refuses reuse of its private output directory; it is evidence, not an update
or deployment launcher. Hardware/route/APSD/USB500, PM physical recovery and
the separate Image363 boot experiment are untested and unchanged.
