# R6 USB500 host orchestration — frozen offline candidate

Status: archived R6 candidate, **do not execute now**. The root session is preparing R7 USB source handling and a normal reboot. The observed FLOAT/native-100 source produced a controlled INHIBIT on R6; that is not an eligible healthy baseline for this experiment. This candidate deliberately requires the exact R6 manifest and retained R6 boot/guard. It must reject R7 or a changed boot. Changing version strings or manifest hashes does not transfer the validation below to R7. A later R7 port requires actual baseline/boot/guard validation, directed profile changes and the affected worker boundary tests.

No new USB500 trial was run. The earlier R6 100mA host baseline retained 26 sweeps / 182 GET responses over about 5.1 seconds; its offline re-decode does not turn it into a full 30-second or 500mA capture.

## Candidate behavior

`host-parent.ps1` requires explicit `--WindowConfirmed`, which records the root operator's actual camera/Bluetooth handback. The flag and a lease do not establish that those sessions have released the phone. The parent starts the frozen read-only host reader hidden for 140 seconds and retains its actual Windows Process object, PID, handle, start time and executable.

Before the single dispatch, the parent requires that process to remain alive with its original fingerprint, exact collector/decoder hashes, the latest newline-complete armed sweep no older than three seconds, a complete fresh error-free port set, one 0525:a4a1 target at configuration 1, and at least 110 seconds on the conservative parent stopwatch. An incomplete trailing JSON line cannot become a completed sweep. The gate contains the requested `host_ready`, trigger UTC and owned-process evidence. `ready_at_utc` identifies the latest complete sweep; the launcher explicitly copies it to the frozen worker's `armed_utc` field without changing the original field or frozen worker.

`host-launcher.py` imports inertly and stages only the four exact reviewed device files. Before staging, its remote program checks the actual root/boot/guard, R6 manifest, fixed SoC serial interface and compatible, an absent ownership lease and the old worker list. It launches the worker as `python3 -B` so import cache directories cannot obscure the retained file set. The device worker performs its own actual manager, loaded-note, health, identity, shared service-lock and window checks. Neither host tool edits the USB source provider or power_supply policy.

The parent and launcher each create a durable one-dispatch marker before dispatch. An SSH timeout leaves the same nonce fetch-only; neither restarts the worker. The reader stays independent of network loss until it exits or its 160-second watchdog expires. Only that owned read-only Windows reader can be killed by the parent. Phone workers and unknown launch/fetch children are never killed or replayed. After collection, fetch addresses only the retained nonce. Original stdout/stderr envelopes and per-fetch file bytes are preserved before attestation; files, config, process start ticks/argv, execution marker and result must agree.

`terminal_verified` proves the recorded original worker reached a known process terminal state with the required evidence. It does not mean `passed`, `restore100_verified` or healthy charging. Those result fields and retained phase/clock anchors require separate review. A fresh reader at dispatch is not proof that every later device phase was captured. Equal whole-ring log counts cannot prove that no new fault occurred or that the ring covered the interval.

## Offline verification and pins

The final local run used Windows Python and pwsh only. The Python suite passed 11 grouped tests of the actual host functions with fake transport, including remote Python syntax and the actual config mapping assignments, durable unknown-launch refusal and fetch evidence boundaries. The 12 PowerShell tests extract and exercise the actual gate/file functions with synthetic capture files and owned hidden local sleep processes; they never run the coordinator's main body. The PowerShell result is bound to the tested parent and test-script hashes before the combined receipt is produced.

No USB reader, WSL, SSH, phone, SDK or network was used for this final verification. The prior 67-case updater, 51-case device worker and 62-case decoder suites were not rerun. Their frozen bytes were only hash-checked. This is not an end-to-end experiment or hardware validation.

| File | SHA-256 |
| --- | --- |
| `host-launcher.py` | `911021dd92b756f8d94f11dea5b250d4cb51c620db1fcb9b702d584001fdd4d1` |
| `host-parent.ps1` | `9e5c39bb80d36e0c300bbbed05461d6aa61334e86d9242f69ed1e4b391c66348` |
| `test-orchestration.py` | `2f6541370610728534dd2b66bcdeab7f248130195ec73a189d3976da8c8cc01a` |
| `test-host-parent.ps1` | `abf0da9d61e2eb0dec1c663d91bf19daf454774dbb71a113d69085c13045b21d` |
| `parent-gate-test-result.json` | `0e198a5c56fc6221559e7345a8ea9744aab8bb6034e0661634b510b53492657b` |
| `orchestration-test-result.json` | `0302a1e89aa06c9952bf3595c7684532ab73befe35a9053c874af3f3a4f9d4eb` |
| Frozen device `worker.py` | `b9f7cc4c741ca85608ec769640b920e0783d76e383ad0c36c7c8e3c912e81f21` |
| Frozen device 51-case receipt | `faf128cf133e0c91127d1d7cef466a402abdc23c93f02d46d1a9bc5910d42348` |
| Frozen decoder 62-case receipt | `4c1984e557dfd6fff70d0adcb6202f91912302c9aa0cb4f2137a838cb9a25338` |

The exact R6 manifest is `944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d`. The collector is `31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5`; the decoder is `9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716`. Main sources, frozen device helpers, updater and device state remain unchanged by this orchestration work.
