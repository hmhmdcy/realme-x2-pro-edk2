# Three-file rollback connected adapter

This is an offline implementation in `rollback-connected-candidate`. It connects
the frozen rollback binder and restore worker to the existing once-owner path.
No actual identity, request, lease, bind, SSH child, device operation, restart,
module operation or carrier write was performed. The phone and the prepared502
transaction are unchanged.

The default entry is `python -B host.py`. It verifies source pins and exits without
creating a runtime directory. `remote.py` and `supervisor.py` also have source-only
defaults. The three actual local default children were waited to return code0 in
`local-checks.json`. Connected actions require the original WSL `/proc` process
identity path and the fixed original key/known-hosts/IPv6 peer. There is no address
or key fallback.

## Reuse and interfaces

`prepare.py` verifies the frozen stage-hostR2 input bytes, specializes only this
new leaf, and retains seven host helper functions verbatim. `source-reuse.json`
records their exact extracted-source hashes. `supervisor.py` retains the original
regular request-FD and same-Popen `finally wait` algorithm; filename, argv,
documentation and request schema are the only changes. `owner-delta.patch`
records the remote/supervisor changes against stage-hostR2. The original leaves
and their receipts were not edited or rerun.

The actual frozen binder is
`../usb-irq-protection-rollback-host-candidate/bind.py` (`6537bd2c…9b50`, delivery
`c8f53b57…3745`). Its `review_current` and `bind` are called directly. Its original
authenticated current probe must already have exact original-key child/input,
output and terminal receipts. Current identity comes from that actual probe,
including the double identity bracket, complete carriers and actual resident
notes. Old adoption/pointer values cannot fill current identity. The connected
adapter adds no whole-postboot-passed requirement.

The restore worker remains exactly `f0767ce2…4142`, delivery
`8ac46475…dfad`. Its safe-stopped, protection, limits, original flock and atomic
USB→protection→manifest restore algorithms are unchanged. The existing saved
source/profile reviewer remains `3c16d34b…0092`. The three explicit profiles are:

| Profile | Actual current boot and resident modules |
| --- | --- |
| `staged_same_boot_old_resident` | Original502 source boot, boot97811/logdumpace2, original live notes |
| `booted_irq_new_resident` | New UUID, IRQbootedd/logdumpace2, new live notes |
| `booted_original_new_resident` | New UUID, explicitly restored boot97811/logdumpace2, new live notes |

All profiles require actual#502, the same board/rootfs, complete saved source-stage
terminal evidence and the selected saved activation action pair where applicable.
The binder rejects missing or inconsistent evidence before creating the runtime
transaction or request. It is callable as:

```python
bind(transaction, profile, stage_directory, stage_fetch_directory,
     probe_directory, context=None)
```

`transfer(action, transaction, window_confirmed=False)` supports only `launch`,
`status` and `fetch`. Launch re-audits the original saved evidence, validates the
retained exact request, then persists its once intent before starting transport.
Missing, failed or unknown launch outcome consumes that intent; it never causes
another launch. The explicit current coordinated window is the existing charging
window, rather than a new approval flow.

## Ownership and result qualification

The detached local owner records its own PID/startticks/argv and retains the exact
SSH Popen. Both SSH child/terminal receipts bind the exact stdin SHA. A receipt
failure before sending leaves the stateful payload unsent, closes that owned
stdin to EOF, and waits that same child. Partial communicate failure also closes
owned stdin and waits. All owned log flush/fsync/close attempts finish before the
transport terminal is published; a close error is retained and prevents a clean
terminal. No kill, timeout kill, second child or retry substitutes for that wait.

The initial parent waits at most35s. Timeout means pending: the same detached
owner continues. It does not imply terminal or failure and does not extend the
device window. Runtime lease is exactly120 BOOTTIME seconds with the original
transaction/boot/token/exclusive/camera/bluetooth fields. No status/fetch renews it.

The device supervisor receives DEVNULL; its actual worker receives the fsynced
request through a regular file FD. It retains that worker Popen and always waits,
including after launch-receipt failure. Its final receipt is absent if its own
log close fails. The device restore algorithm is not copied into the adapter.

`status` and `fetch` authenticate the original request/claim/source bytes even
after the source boot ends. A different boot records `source_boot_ended` and does
not inspect a current process with the old PID. Missing or malformed receipts stay
unknown; their raw bytes can still be fetched. No new guard or restored identity
is inferred from a different boot.

Fetch first saves the bounded raw files. A successful file-restore qualification
requires all original device worker/supervisor PID, birth, argv, request and
source relationships, their actual worker-wait return code0, a clean supervisor
terminal, exact three old file hashes/modes and absent temporary files. It also
requires the original launch SSH terminal0, exact launch-intent input/action,
original launch response transaction/request, and the same original supervisor
receipt. A later successful fetch transport cannot repair an unknown or nonzero
original launch transport. Raw evidence is retained without promotion.

The strongest result is only `rollback_staged_original=true`, corresponding to
the worker's `staged_original/runtime_pending`. `runtime_validation_accepted`
remains false. Actual restart, old-R8 residency and postboot health require their
own later verification. This tool never restarts, loads/unloads modules, enables
AUTO, changes USB policy, alters a carrier or claims physical acceptance.

## Future use order — not executed

1. Obtain the actual selected saved source/profile evidence and an authenticated
   current read-only probe using the original owned-Popen sender path. Retain its
   exact stdin/output/child/terminal raw receipts.
2. Run `host.py --action bind --transaction <new-rollback-tx> --profile <one-profile>
   --stage-directory <original-stage> --stage-fetch-directory <original-fetch>
   --probe-directory <actual-current-probe> [--context <selected-activation>]`.
   Only complete actual evidence may create a request; this round did not do so.
3. In the current coordinated exclusive window, call `--action launch` with the
   same transaction and `--window-confirmed` once. A pending or broken response
   permits only `--action status` / `--action fetch` for the original transaction.
4. Fetch and review actual original terminals and file states. Handoff is pending
   runtime verification, even when all three disk files are restored. Do not use
   this result as restart or loaded-module verification.

## Verification scope

`test-result.json` records29 new actual wrapper/reviewer cases. Authentication,
Linux filesystem/clock and process IO are explicit fake boundaries, except that
missing actual source evidence is rejected through the real binder before mkdir.
The cases cover all three profile envelopes,120s lease, once-only launch,
crossboot raw fetch without PID attribution, regular request FD, same-child waits,
receipt/input/close failures,35s parent pending, local owner identity, exact input,
original launch rc/action/request/supervisor and device terminal qualification.
`test-transfer-result.json` adds three actual transfer branches: absent window
zero intent, original-key exact launch wire with no replay, and a successful
fetch that cannot promote an unproved original launch. No old12/21/6/20/31 suites
were run. These are software boundary tests, not device or charging validation.

`delivery.json` uses an explicit source/text/JSON whitelist. No executable test
binary, pyc, cache, runtime transaction or unbounded recursive file scan is
included. No test text log alias is needed because receipts are JSON.
