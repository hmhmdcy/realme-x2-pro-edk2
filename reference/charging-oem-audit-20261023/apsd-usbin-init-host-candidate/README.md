# One USBIN initialization transaction, offline candidate

This is an inert host controller and a bounded read-only observer for the frozen
`apsd-usbin-init-candidate` helper. No phone, SSH, USB, SDK, kernel deployment or
permanent startup changes were performed to prepare or test it. Use from WSL
Ubuntu so the pinned strict IPv6/original-key R7 transport is used unchanged.

The helper's only possible configuration write is its independently reviewed
masked clear of `0x1358 & 0x80`, after a new physical-off stable window. The
controller never writes other PMIC registers, I2C, CMD_APSD, PD, PHY, role or
budgets. It does not automatically restore, retry, unload, or reboot. The helper
protocol and already compiled module are byte-pinned; no build is necessary.

## Coordinated sequence

The root session owns the phone/window and user questions. Check local inputs,
confirm the user is available **now**, then select a never-used transaction name.
The following commands are examples for that explicitly coordinated window;
they have not been executed against a phone.

```sh
cd '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/apsd-usbin-init-host-candidate'
python3 -B controller.py check-local
python3 -B controller.py launch --transaction usbin-init-r8-001 --execute --window-confirmed
python3 -B controller.py status --transaction usbin-init-r8-001 --execute --window-confirmed
```

`launch` creates a unique private host/remote transaction, uploads and checks the
frozen bytes, starts one detached observer, and loads the helper once with
`register_board=1`. Loading performs one observe read and no configuration write.
`status` must report `ready_to_arm=true`: two new ticks, exact PID/start ticks and
argv, same instance/boot/guard/R8 manifest/three notes, fresh healthy protected
charging/CV/temperature/budget and current idle camera/session. Service PIDs are
discovered fresh. The capture has a 180-second bound and is never restarted.

After that gate, root obtains a new ready reply from the user, then:

```sh
python3 -B controller.py arm --transaction usbin-init-r8-001 --execute --window-confirmed --user-ready-confirmed
python3 -B controller.py status --transaction usbin-init-r8-001 --execute --window-confirmed
```

Only a fresh `may_prompt_user=true` authorizes root to immediately prompt one
physical unplug for about 10 seconds and reconnect to the same port. The gate
requires at least 45 seconds of the actual helper's 60-second arm window left,
two new observer ticks and known waiting state. Recheck if root has not prompted
within three seconds. No old ready reply or old card may authorize another arm.
The helper arm and controller intents are one-shot. Arm expiry starts no retry.

The observer survives SSH disconnect and records 1 Hz raw seven PMIC fields plus
configuration, source/ACOK, cached protection/raw flags, standard Battery
status/current, budgets/CV and native netlink/UPower events. It waits for a real
offline/online cycle, then at least 60 seconds after the online edge, within the
original bound. Logical UDC `configured` is never physical-off evidence. Fetch
after reconnect, or wait for observer terminal without killing/restarting it:

```sh
python3 -B controller.py fetch --transaction usbin-init-r8-001 --execute --window-confirmed
```

Fetch retains all raw regular files, current process identities, cached helper
state and clock brackets. It performs no module/control/cleanup action. A status
or fetch transport/read error is retained as a read error and permits a later
read of the same transaction. It cannot repeat `arm`.

Inspect observer terminal and full raw/results before explicit completion:

```sh
python3 -B controller.py finish --transaction usbin-init-r8-001 --execute --window-confirmed --terminal-state-confirmed
```

This requires complete physical/init/monitor-cleanup/identity/environment and
current protection/CV evidence. It explicitly commits an exact verified helper
state (zero register writes), checks same-instance `can_unload`, then unloads
only this helper and proves absence. If already committed, commit is skipped.
The old-bit-zero no-op correctly has no self-reference and still requires the
explicit commit record. Initialization verified, physical cycle, source type/
budget, UPower State timing, and screen observation remain separate results.
No State event means unknown latency; Discharging can remain valid at a low
budget. A bit clear proves neither source upgrade causality nor Charging.

## No user action / zero-write expiry

If the user becomes unavailable before arm, or the actual arm expires with
proven zero writes, review the terminal helper state and use:

```sh
python3 -B controller.py close-expired --transaction usbin-init-r8-001 --execute --window-confirmed --terminal-state-confirmed
```

The same entry accepts only exact unarmed `observed` or a proven zero-write
`timeout`. It stops/joins the owned observer, checks its event cleanup and current
same-instance unload predicate, then removes only the helper. A saved
`old_valid=true` alone is not a write: the actual blocked-config deadline fixture
has that value but no attempted write, pending restore or reference.

## Unknown mutating outcome

Only launch/arm/finish/close-expired failures quarantine further mutations. Keep
all markers and fetch first; never delete `unknown-private.json` to escape.
No automatic retry, kill, restore or unload follows uncertainty.

Once root has reviewed the retained originals and all original mutating children
and the observer are terminal, an explicit qualification is available:

```sh
python3 -B controller.py qualify --transaction usbin-init-r8-001 --execute --window-confirmed --terminal-state-confirmed
```

It freshly checks identity, owner, exact retained helper instance, original
PID/start-tick/argv identities, monitor cleanup and current environment. Active,
reused or unknown processes refuse qualification. Verified/committed plus full
capture/current health evidence qualifies `finish`; observed/zero-write expiry
qualifies `close-expired`. A removed module also needs its exact retained commit
or zero-write-close receipt and original terminal unload child evidence. The
proof binds both host unknown bytes and remote uncertain bytes and expires in
30 seconds. Only its named action may then run with terminal confirmation.
Committed states skip commit; an already absent module skips rmmod. Another
uncertain mutation invalidates the old qualification. If no exact retained
instance or sufficient evidence exists, this controller cannot qualify it and
remains fetch-only for a separate reviewed recovery.

## Offline evidence

`test-result.json` binds the actual runtime bytes. The 35 new targeted assertions
execute actual parser, aggregation, readiness, host runner and process gate;
the SSH/OS boundary is fake. Six JSON states come from the frozen helper's real
`state_show`, core and complete control/work functions under ASan/UBSan/Werror,
including blocked-config timeout with `old_valid=true` and the no-op clear.
The helper's old 12 groups, icon matrices, PM and USB500 tests were not rerun.
`session_persistence` independently reviews terminal recovery boundaries. These
are software receipts, not physical-off or UI acceptance on a phone.
