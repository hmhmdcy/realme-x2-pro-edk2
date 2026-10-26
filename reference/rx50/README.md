# RX50: Windows receive observation and exact installed-driver audit

See [session 50](../../sessions/50-windows-receive-and-driver-buffer-audit.md)
and [source audit](source-audit.md). The current connection works; no old
receipt/output fault was reproduced. No phone flash/reboot, new elevation,
driver change or installed-terminal change occurred.

A diagnostic copy of RX47's terminal records the Windows receive queue,
ClearCommError flags, asynchronous error notifications and read/display
timing. It keeps the existing raw/text capture and native receipt boundaries.
The one manual owner returned 1508 frames / 8996 raw bytes, with no observed
serial errors and a maximum reported receive queue of 150 bytes. The 287
journal records overlapping this capture match exactly, including rx_stats.
The other 225 journal records preceded the owner and are excluded.

The locally supplied PDB matches the installed qcusbser binary by GUID/age
and section headers. Selected type offsets identify its real receive-buffer
overflow branch and the status flags cleared by a status query. This closes
a source-version uncertainty; it does not show that overflow caused RX47.

`python3 verify.py` checks hashes, exact read/raw accounting, actual commands
and receipts, resource closure, journal CRC/direct frame equality and the
retained image/terminal state. Executed source/raw/bin exports are unchanged;
derived text is normalized with original/exported hashes in exports.json.
The driver, PDB, complete symbol/type dumps, disassemblies and downloaded
Microsoft source remain local under E:\edk2-samurai-out\rx50 or E:\eud-host.

Diagnostic use, on .NET Framework Windows PowerShell only:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\eud-terminal-rx-audit.ps1 -Native -RxAudit -Port COM14 -LogBase E:\edk2-samurai-out\rx50\fresh-name
```

Check ownership first; choose a new log name. Ctrl-] exits. The audit deadline
is checked between loop iterations; it is not a hard deadline if console I/O
blocks. Both normal and exceptional exits close/dispose the port in finally.
Keep the installed compatible/native terminal as the ordinary entry point.
