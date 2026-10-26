# Off-only USBIN start-on-CC initialization candidate

This is an offline, temporary in-tree helper for one initialization difference: clear **0x1358 bit 7** with `regmap_update_bits(map, 0x1358, 0x80, 0)`. It is not loaded or tested on the phone. No Image, existing provider, charger, service, SDK or shared source/build was changed. The successful software tests and private module build do not establish electrical behavior or fix the charging icon.

## Source basis and boundary

The fixed OEM commit is `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6`. The complete source functions and their hashes are in [the separate scope receipt](../apsd-lifecycle/start-on-cc-scope-r8/result.json), SHA-256 `7c39fcbadb22dd1e6678506bd4cbd6b5a8b8f3e68fd365620699521bcc0b96ea`.

- `qpnp-smb5.c:6061` calls `smb5_init_hw`; its Type-C branch at 3816 calls `smb5_configure_typec`. That function enables APSD at 3324, disables HVDCP detection at 3325, then clears this configuration bit at 3327–3328.
- Later, probe at 6182 calls `smb5_determine_initial_status`; its plugin handler call at 4273 reaches `smb5-lib.c:5255`, then `smblib_usb_plugin_locked:5080` and `smblib_request_dpdm(true):5113`. The initializer therefore precedes this initial-status/plugin DPDM request. The rerun in init_hw at 3832 is specific to PMI632.
- `smb5-reg.h:282–283` defines `USBIN_BASE + 0x58`, bit 7; 349–350 supplies the vendor alias. `smblib_masked_write` at `smb5-lib.c:144–147` only calls `regmap_update_bits`.

This supports a standalone initialization bit write; the exact operation does not issue APSD CMD, PHY, PD, role or budget writes. It does **not** prove that an online VBUS write cannot indirectly trigger detection. This candidate only attempts the write after a new stable physical-detach observation. It does not rerun APSD, retry the old 500mA experiment, promise CDP recognition, or establish that retained bootloader state is otherwise inactive.

## Module and board binding

The ko name is `samurai-usbin-init.ko`; the kernel module name is `samurai_usbin_init`. Its sole load parameter is `register_board` (bool, mode 0444, default false). With the explicit value `register_board=1`, it creates the fixed platform device `samurai-usbin-init` (`PLATFORM_DEVID_NONE`). With the default false it only registers the driver and creates no device.

The board locator follows the already verified provider pattern: machine `realme,samurai`, parent compatible `qcom,pm8150b`, node name `pmic`, parent DT `reg=2`, child software `reg=0x1300`, and the parent's existing regmap. There is no arbitrary address/base parameter. The driver suppresses manual bind/unbind attributes. A successful module load alone does not prove probe success; the controller must verify the actual state node and identities.

Probe takes one read-only snapshot. There is no default polling, timer or write. There is no power-supply registration, budget provider or MP2650/I2C access. The only register-write call is the masked bit operation above. Reads are the seven fixed PMIC status registers followed by 0x1358.

## Sysfs protocol, schema 1

The machine-readable [protocol.json](protocol.json) enumerates the fields. Actual paths are:

```
/sys/bus/platform/devices/samurai-usbin-init/state
/sys/bus/platform/devices/samurai-usbin-init/control
```

`state` is mode 0444 and returns one cached JSON line. Reading it performs no bus access, schedule, write or status refresh. `now_boottime_ms` is sampled immediately before taking the state mutex, so a controller should bracket the read with BOOTTIME and reject stale/slow observations. `instance` is a random, nonzero 16-character hex value for this probe. It is an instance discriminator, not a substitute for the controller's boot/guard/transaction identity.

`control` is mode 0200. Its only exact commands (optional terminal newline) are:

| Command | Accepted condition and effect |
| --- | --- |
| `arm` | At most once per module instance. Acquire `try_module_get` before scheduling; wait for stable off, then attempt clear. No user-supplied old value. |
| `restore_saved` | Only with `pending_restore && old_valid`; use this instance's saved actual bit after a **new** complete off gate. It never restores a default byte. |
| `commit` | Only successful `clear_verified`, `commit_allowed`, and no current errors/unknown. Record adoption and release the retained reference, with **zero register IO**. |
| `cancel` | Only while running. Stop work, join outside the mutex, release the reference only if no pending restoration/unknown write. It never automatically restores. |
| `observe` | Only when not running and without pending restoration; one new read-only snapshot, no polling. It changes phase, so do not call it between `clear_verified` and the intended `commit`. |

Controls are rejected while paused or joining a worker. PM suspend cancels/join work, resume merely unpauses; it does not rearm. Exit joins work without holding the worker mutex and performs no restore. Normal unload is prevented by a retained module reference after an attempted write until successful commit or saved-bit restoration. Force unload is outside the protocol.

## Off gate and one attempt

Snapshot arrays have this exact order: `0x1307`, `0x1308`, `0x1310`, `0x1506`, `0x1509`, `0x150b`, `0x150d`, then `0x1358`. Physical off requires independently `(0x1310 & 0x10)==0`, `(0x150b & 0x21)==0`, and `(0x1509 & 0x20)==0`. This reuses the current provider's physical-off predicates. It does not require a stale APSD result or every raw byte to be zero.

After arm, the worker samples on 250ms delayed-work intervals. At least two identical, off snapshots must span at least 500ms; the usual 250ms schedule uses three. The **first** off timestamp remains anchored across equal samples. Any of the seven raw bytes or the config byte changing resets evidence, as does physical on. Read errors terminate the attempt and cannot reuse old evidence. These timings and strict snapshot equality are conservative engineering choices for this candidate, not OEM timing requirements.

After stable off, the worker reads a new pre snapshot and config byte. Any difference/on state restarts accumulation. It saves the actual old masked bit, then checks a fresh actual BOOTTIME immediately before the sole possible write: no backward time, no start at/after the 60s deadline, and no more than 250ms since beginning the final pre snapshot. Thus delayed reads crossing the deadline cannot lead to a new write. A single regmap transfer or scheduling interval cannot be hard-interrupted; this is **not** a hard realtime 60s bound on completion. The gate-to-write interval and sequential hardware reads are not an atomic electrical-detach guarantee.

The worker writes only when the masked bit differs from the target. It then reads config and all status fields again, even if the write returned an error. It verifies the target bit, preservation of every other config bit, continued physical off, unchanged seven status bytes, and matching post config. A visible reattachment or other post mismatch records failure/uncertainty. `prewrite_boottime_ms` is the gate checkpoint for both real writes and no-op cases; `write_attempted` distinguishes them. `post_boottime_ms` may be after the deadline.

## Outcomes and reference ownership

`phase` is one of `observed`, `waiting`, `clear_verified`, `restored`, `committed`, `timeout`, `error`, `cancelled`. `op` is 0 observe, 1 clear, 2 restore. `armed` means the single clear arm was used; it is not a current-running indicator. Check `running`, `remaining_ms`, `instance`, boot identity and fresh read bracket to establish readiness.

Before a write, `pending_restore` is set **before** calling regmap: an error return does not prove the bus applied nothing. Failed/mismatched post-write results retain the reference and set `unknown_write`, including an ignored write, error-after-apply, changed unrelated bits, or observed reattachment. No automatic restore or successful commit follows an uncertain result. Restore has its own bounded off window, retains the original saved value, and cannot be enabled by supplying a new value. `clear_error`/`clear_write_return` preserve the initial clear outcome across a later restore.

Successful old-bit-1 clear normally has `pending_restore=true`, `held_ref=true`, `commit_allowed=true`; explicit commit adopts it and allows unload without another detach. If the actual old bit was already 0, successful `clear_verified` is a **zero-write** result: `pending_restore=false`, reference released, `can_unload=true`. It still permits explicit commit to record adoption. Never demand a held reference or manufacture restore-to-1 for this case. A timeout/cancel/read failure before any write can also be safely unloadable but is not a successful initialization.

`can_unload` means `!running && !pending_restore && !held_ref`. It is a kernel-state permission indicator, not proof of a successful change, worker/process identity, phone health, UI behavior, or safe unknown-host transport outcome. A controller must preserve raw receipts and use its own single-transaction/fetch-only handling for lost responses; it must not retry arm, blindly commit, restore or unload.

## Offline validation and delivery

[test-result.json](test-result.json) records 12 groups with ASan/UBSan and `-Werror`: seven actual core functions plus twelve byte-extracted module functions (worker/control/state/ref/stop and fixed regmap IO). Hardware/OS edges are fakes. Cases cover the retained first-off anchor, raw/on changes, delayed config reads across deadline, stale/backward clocks, no-off zero-write timeout, post-write uncertainty and exact saved restoration, old-bit-0 no-op, GOING rejection, cancel joining, cached zero-IO status and zero-write commit. This does not prove live concurrency or hardware behavior.

[build-result.json](build-result.json) binds these source hashes to a private in-tree `W=1` ko build with no diagnostic warnings, `intree=Y`, and k363 vermagic. Shared config/Makefile hashes were unchanged; no Image/package was built. [delivery.json](delivery.json) binds the protocol, docs, tests, receipts, source and private module SHA. All device operations and any future deployment remain with the root session under an exclusive coordinated window.
