# Future host launcher

Prepared and tested offline only. No phone, SSH, SDK, deployment or PM command was executed. The frozen `worker.py`, `audit.py` and original 32-case `test-result.json` are unchanged. The new launcher has its own 13-case host-only test receipt; it does not repeat the collector suite. Tests exercise the actual host scheduling/retention and readiness functions with fake transport, and compile the embedded remote RPC. They do not execute the remote filesystem/process boundary.

All commands below are **future commands**, only after the root coordinator has explicitly received the phone window from camera/Bluetooth. The launcher never asks the user to unplug and never borrows/releases a phone window. Imports do not load SSH transport or read local files.

From the shared Windows PowerShell workspace, use the established Ubuntu host environment:

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-candidate/launcher.py' launch --transaction charging-icon-r6-20261023-01 --window-confirmed --max-seconds 300
```

`launch` requires the explicit handback flag. It validates exact reviewed collector/receipt hashes and the reviewed pm-r5-recovery snapshot, adopts that snapshot's boot, and requires the existing original-key/baseline adoption flags. It then creates an exclusive host transaction directory/marker **before** loading `device-window.py` and dispatching its established strict original-key SSH path. Host evidence is under `/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture/<transaction>/`.

The remote RPC checks the same adopted guard against the current boot and r6 manifest `944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d`; it repeats that identity check immediately before the detached Popen and before returning. It refuses existing output and bundle directories, uploads the frozen worker/auditor/32-case receipt, validates every byte hash plus receipt contents, and uses `start_new_session=True` with private output and DEVNULL input. Launch output identifies the detached PID/start_ticks and whether the launch receipt matches the host marker. **Launch output always has `may_prompt_user=false`.**

Unknown SSH/Popen outcomes leave the host marker in place and make the same transaction status/fetch only. A second `launch` for that transaction is refused. Do not remove the marker or choose a new transaction to bypass an unknown worker. There is no automatic retry, recovery, service action or USB action.

Run the readiness gate immediately before the user instruction:

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-candidate/launcher.py' status --transaction charging-icon-r6-20261023-01
```

Only `may_prompt_user=true` permits the coordinator to send the one unplug/replug instruction. The check reads two remote observations 2.2 seconds apart; both require current active ready status, matching live PID/start_ticks/cmdline and host launch receipt, increasing tick/sample monotonic time, and status age at most three seconds. It independently checks the deadline from the worker's recorded start BOOTTIME and subtracts the complete host roundtrip from remaining time; at least 45 seconds must still remain. A roundtrip over eight seconds, missing/invalid timing, PID reuse, terminal/settling status, absent marker, changed identity or receipt mismatch fails closed. **If more than three seconds pass before prompting, rerun `status` manually.** A saved positive result is not reusable permission. SSH failure is not a request to send the user an action.

After the one cycle and collector termination, fetch all originals:

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-candidate/launcher.py' fetch --transaction charging-icon-r6-20261023-01
```

Every fetch creates a new local `fetch-<time_ns>/` directory containing byte-exact remote bundle and capture files with verified SHA256 values and the full response receipt. It also retains the original SSH stdout/stderr. It does not truncate logs; a file exceeding the explicit 16 MiB bound produces a retained failure rather than silent omission. Partial/unknown launch output can still be fetched. Repeated fetches are read-only against the same worker and preserve earlier copies.

`cleanup_state` reports that worker's exact process state and retained terminal/monitor/DBus cleanup evidence. `cleanup_confirmed=true` requires that the original worker is absent, zombie or definitively replaced by a different start time, plus terminal inactive status, a started clean monitor and a recorded DBus subprocess return code. An alive or unknown process, missing terminal status, monitor cleanup error or missing return code remains unconfirmed. Fetch does not stop any process, clean a shared lease, delete remote evidence or infer camera/Bluetooth handback. The root coordinator decides when the window can be returned using this evidence.

To audit a terminal fetched copy locally, use the already frozen auditor:

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/icon-capture-candidate/audit.py' --directory '/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture/charging-icon-r6-20261023-01/fetch-REPLACE_WITH_ACTUAL/capture'
```

The printed fetch result gives the exact retained directory. The frozen collector's physical-cycle qualifier remains separate from screen/UI acceptance: no State means no measured State latency, and net discharge is never rewritten Charging. This launcher never runs the unsafe old r5 PM acceptance auditor.
