# Daily charging progress

## 2026-10-28 completion window

- Cold boot binds `samurai-mp2650` and starts the service automatically.
- The kernel initializes fail-safe: no AUTO, 500 mA input cap, 500 mA CC cap,
  and a verified stop request.
- The service removes a stale/shadow managed module before binding, resolves
  the real providers, requests 900 mA input, 500 mA CC, then enables AUTO.
- No-provider operation is no longer a charging error in shadow mode. Optional
  provider `ERR_PTR` values are rejected instead of used as valid supplies.
- The runtime handles an already-managed start without first rebinding the
  generic driver, avoiding the previous EBUSY recovery trap.
- `gauge-protection` is loaded with only its declared `register_board`
  parameter. The nonexistent `observed_2719_diagnostic` parameter was removed
  from the daily path.
- The install script checks a complete rollback snapshot. The backup includes
  all three modules, service files, and the prior manifest.
- Added `samurai-charging hashes`, a read-only installed-file hash report that
  works even when the charger is stopped.
- Added `verify.py` offline handling: with no source it accepts `online=0`
  while still requiring a valid managed sample and no faults.
- First-bind test passed: removing the service-owned module and loading the
  module with `runtime_board=1 control=1` reports
  `charge_behaviour=auto [inhibit-charge]`, 500 mA input, 500 mA CC,
  `desired_enable=0`, and no stop/latch/fault error. The service start then
  transitions to AUTO.

## Verified behavior

- Repeated source-present cold boots: managed driver bound, service started,
  `valid=1`, `online=1`, `protection_ok=1`, no fault/latch/stop error.
- Full hold: `logical_full=1`, `full_holding=1`, `hold_requested=1`,
  `desired_enable=0`.
- Stop/start round trip: service stop returns the client to generic `mp2650`;
  service start removes the generic binding and returns to managed charging.
- Effective input is 500000 uA because the USB/TCPM source budget is 500000;
  the requested 900000 uA is retained as the policy cap.
- Constant charge current is 500000 uA and active behavior is `auto`.
- Taint 4096 is solely the out-of-tree module load in this build. No new
  warning/Oops was observed in the successful cold-boot windows.
- Final active state after the last cold boot is full hold: the kernel keeps
  `logical_full=1`, `full_holding=1`, `hold_requested=1`, and
  `desired_enable=0`; the service and verifier both remain healthy.

## Open limitation

The current host reaches the phone over the same USB cable. A true no-VBUS
cold boot therefore cannot be automated without physically disconnecting the
cable. The service logic supports `online=0` and stays inhibited, but this file
does not claim that path as measured.

Final live evidence is stored in
`E:/edk2-samurai-out/charging-management-20261023/daily-final-20261028/`.
The final boot was `9e519b0a-3e38-4d67-b3ad-2e476b0a790d`; the last verifier
run returned 0 with `input=500000`, `cc=500000`, and
`valid=online=protection_ok=1`.

The rollback snapshot is `/root/charging-daily-20261028-02-before`. The
installed package is `/root/charging-daily-20261028-03`.
