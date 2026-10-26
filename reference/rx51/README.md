# RX51: bounded console-overlap failure and one missing issued TX frame

Current mirror: unchanged RX48 B. See [session 51](../../sessions/51-console-overlap-and-issued-frame-loss.md).

One manual Windows owner armed a single `R51H=1\n` native frame after the
kernel-prefixed `R51LOCK:` marker began arriving. The 1009-byte `/dev/kmsg`
write contains 990 zero digits and is below this kernel's 1024-byte limit.
Marker/end host observations are 54079/54867 ms; the probe was submitted once
at 54231 ms. The entire log arrived, but the probe had no receipt after 4 s.
Accepted RX/tty counters and the empty shell variable exclude it from accepted
input. Host write completion/overlap do not prove physical OUT delivery.

A separate recovery owner used two bounded startup Ctrl-U attempts, then
captured an immutable 3120-byte journal before fetching status. Its 512 records,
seq 11397..11908, CRC 621cfafd, have this direct comparison:

| Journal records | Raw observation |
|---|---|
| First 336 | Exact suffix of `console-overlap-01.raw` |
| Seq 11733, source console, `90 04 5b 20 35 38` | Absent; payload `[ 58` |
| Last 175 | Exact prefix of `post-fault-01.raw` |

The unique recovery prefix anchors the comparison; every other frame is
compared directly. No gap filling, edit-distance result, or decoded stdout
filter is used. The recovery raw begins `63.839589]`, whereas the issued record
includes `[ 5863.839589]`. Both owners opened files/port before their startup
inputs, logged actual reads, and closed/disposed in finally. The failure owner
exited with the seven-byte input pending; the recovery owner exited cleanly.
Maximum sampled queues were 174/165 bytes; no serial errors were observed.

Local unchanged core/source audit confirms the legacy console holds the UART
lock over the whole record, and non-RT printk additionally disables local IRQs
around its callback. The IRQ counter is incremented only after taking the lock;
the watchdog also samples under that lock. Zero waits therefore does not measure
the blocked interval. PREEMPT=y; a nonpreempt worker premise does not apply.
The [kernel printk documentation](https://docs.kernel.org/core-api/printk-basics.html)
describes synchronous legacy-console blocking. The
[console API](https://docs.kernel.org/driver-api/tty/console.html) describes nbcon
thread/atomic ownership rules. These support investigation, not a proven cause.
The [QUIC EUD source](https://github.com/quic/eud) still does not establish the
physical delivery/timeout or TX-ready behavior needed to assign either loss.

`eud-console-overlap.ps1` is a separate executed diagnostic copy of RX50.
Ctrl-O arms only once after pending input drains; a kernel-prefixed marker
prevents triggering on shell echo. The probe is queued through the existing
single-attempt native sender, retaining length-2 F1 reservation and ACK bounds.
`eud-terminal-rx-audit.ps1` and `EudRxAudit.cs` are exact recovery helper copies.
The installed ordinary terminal is unchanged.

Run `python3 verify.py` for raw/read accounting, submitted/accepted input,
CRC/direct comparison, source identity and final state. `inspect-source.py`
rederives local core/config facts. `exports.json` records original/export hashes:
raw/bin/self tools and executed helpers remain byte-identical; derived text is
UTF-8 LF, and preflight exports only target USB rows. Full kernel sources and
driver binaries are not copied here.
The executed overlap helper has mixed LF/CRLF endings; its per-file whitespace
attribute preserves those exact bytes while retaining other whitespace checks.

No flash, reboot, new elevation/capture, driver/PHY/reset/fuse change, or installed
terminal replacement. TOP_CFG=0x11 whole-frame RX, console/F1 and compatibility
are retained. An extra empty IRQ and a missed first reopened Ctrl-U cannot be
assigned to the overlap versus session reset. RX grace is still unexercised.
Next useful control is the same trigger with target USB IN/OUT evidence, rather
than ordinary passing echo/numbered-output loops. Stability remains unresolved.
