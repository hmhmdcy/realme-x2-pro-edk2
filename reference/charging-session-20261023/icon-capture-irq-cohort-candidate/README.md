# IRQ cohort icon capture profile

This profile targets a future **actually adopted IRQ/protection cohort** on Image502, boot `eddadec…f6e06`, logdump `ace2e261…3ed1` and manifest `5fca8e5a…9417`. The current original502 adoption is insufficient. No runtime pins, boot UUID, guard, endpoint or request are supplied by this source package. Default entry points only check sources.

`adoption-review.py::review_adoption(context, camera, probe_directory, capture_directory)` reuses the fixed compressed postboot/adoption profile. It first calls the original adoption review and then checks the actual adoption request, exact executed input, one dispatch, original child birth and terminal receipts, reply, result, retained predecessor, saved pointer/endpoint and current global pointer. The guard comes only from the authenticated `usb-irq-protection-activate-*` transaction. Runtime notes are taken from the fully audited postboot raw data, including new USB/protection, unchanged charger, camera481 and sensor468. The returned expected guard hash is the real reply's readback digest, not a host assertion that the device was queried again.

The worker, audit and historical32-case receipt are byte-identical to the previous502 package. Source/ACOK, battery current/current_avg, kernel/DBus timing, finite300-second lifecycle, 130-second ready minimum, advancing two-heartbeat gate, 90-second reconnect observation and original cleanup/fetch remain. The entry changes only guard selection/namespace; the host transport keeps the original key/peer and fixes `-C` for potentially large returned originals. Neither desktop nor UPower is changed. Registration, ready status and static tests do not prove physical IRQ delivery or icon latency.

Run from WSL with actual `/mnt/e/...` paths only after stage, activation, boot-only flash/reboot, compressed full postboot and compressed IRQ adoption have completed with original receipts:

```text
python3 -B bind-identity.py --context <activation>/host-context-private.json --camera <actual481wrapper> --probe-directory <original-compressed-probe> --capture-directory <original-compressed-capture> --execute-bind
python3 -B launcher.py check-local
python3 -B launcher.py launch --transaction charging-icon-irq-001 --window-confirmed
python3 -B launcher.py status --transaction charging-icon-irq-001
python3 -B launcher.py fetch --transaction charging-icon-irq-001
```

Bind validates all actual inputs before creating its private directory. It publishes only a checked pins file; an existing pins/next file is retained and never replayed. Host originals live under `/mnt/e/edk2-samurai-out/charging-session-20261023/icon-capture-irq-cohort/`, remote originals under `/root/charging-session-20261023/icon-capture-irq-cohort/`.

Root may prompt immediately only after `may_prompt_user=true` from fresh status; recheck if the prompt is delayed beyond3seconds. Five minutes is the total deadline from launch. It is not five additional minutes after prompting. On unknown launch/transport outcome retain the transaction and use status/fetch only. Fetch is read-only retrieval, not a stop action. Require the original finite worker terminal, same-child monitor cleanup and `cleanup_confirmed`; preserve all failure/raw files. No physical cycle or latency has been measured by this leaf.

All21 new profile/receipt, missing/mixed adoption, bind, guard, compression and ready boundaries passed in the original local execution `337a6b` (exit0). The two default entry points then returned0 in `80180b`, reporting runtime identity/pins absent. The fixed compression profile is `bd533c9f…b904` with delivery `fb8a62a1…5813`. The old32/12/14 suites and device procedures were reused, not rerun. These fixtures use temporary synthetic receipt boundaries; they do not authenticate an actual future adoption. No real pointer, device, SSH, USB, SDK, storage guard, build or Git was accessed. Exact source hashes and unchanged-body evidence are in the local receipts and delivery.
