current: actual failed gadget/recovery errno swallowed; active resources and pending tail retained
rejected: direct runtime errno leaves core powered, PM suspended, exact pending-event ref and IRQ depth held
rejected: actual system caller marks suspended after negative gadget path with powered resources
rejected: HALT unknown skips event cleanup yet core_exit releases PHY; queued actual recovery work accesses after exit
rejected: even HALT-confirmed event cleanup plus IRQ join does not drain separately queued recovery work
API gap: the same negative primary can accompany successful final reconnect; core needs an outcome, not just errno
control: original init-for-resume failure uses its existing clock/reset unwind before gadget starts
{"passed":true,"cases":7,"safe_gadget_failure_unwind_proved":false,"deployable_patch":false}
