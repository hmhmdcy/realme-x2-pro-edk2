# Typec IRQ probe (diagnostic only)

`typec_irq_probe.c` performs one controlled PM8150B Type-C mode change
without touching the boot image, DTB, or root filesystem:

1. Find `c440000.spmi:pmic@2:typec@1500`.
2. Borrow the parent SPMI regmap and read the Type-C register base.
3. Write `TYPEC_DISABLE_CMD` to `TYPEC_MODE_CFG_REG` (`0x44`).
4. Wait `off_ms`.
5. Restore the previous mode value.

The `run` parameter executes the cycle immediately.  The early `armed`
kthread attempt failed because its timer is frozen with `s2idle`; do not
repeat that method.

`typec_wake_near.c` is the successful boundary probe.  It links a dummy
supplier after the Type-C device and changes the Type-C mode from
`suspend_late`, after the driver has armed its wake IRQs.  A 15-second
RTC safety window returned in 4–5 seconds with a Type-C IRQ delta and
TCPM wake events, while unarmed and `power/wakeup=disabled` controls
slept the full window.  This proves the PM8150B IRQ -> SPMI -> PDC path,
but it is not a physical cable event.

Both modules are diagnostic-only.  They must not be shipped or added to
boot, DTB, or `samurai-platform`.  See `RESULTS-20261112.md` for the
evidence and control table, and
`HOST-VBUS-AUTOMATION-20261112.md` for the host-side VBUS automation
probe.

`typec-transition-observer.sh` is a non-persistent userspace logger for
later physical-cable correlation.  It records changes in VBUS/UDC/
carrier, Type-C role/orientation, suspend counters and Type-C IRQ counts.
It cannot identify the wake source by itself; use
`test-usb-typec-wake.sh` for the actual wake PASS/FAIL test.  On the
current device it is running as:

```text
/root/samurai-tests/typec-transition-observer.sh
/var/log/samurai/typec-transitions-20261112-observer.log
```

Stop it with `pkill -f '[t]ypec-transition-observer.sh'` when the
transition capture is no longer needed.
