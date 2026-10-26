# Transport-independent restart tail: offline review only

This is a **future code improvement**, not the diagnosed cause of the current
incident. Root subsequently received the user's physical observation that the
screen displays fastboot. That proves this attempt reached the bootloader;
missing host fastboot enumeration must not be reclassified as “Python never
called reboot” on the basis of an absent second stdout message. No device,
SSH, EUD, CSR, restart, frozen payload or existing transaction was touched here.

The actual frozen `../r7-restart-review.py` has a reachable failure path. After
unbind and confirmed CSR_EUD_EN=0, it calls `phase.write_text` and then
`print(..., flush=True)` **before** constructing/calling syscall142. Both are
inside `except Exception: if frozen: FITHAW; raise`. If that print raises
BrokenPipeError, the worker thaws and exits without attempting RESTART2.
An ENOSPC/OSError from the post-retirement phase write has the same effect.
The old charging `usb-restart.py` has the same ordering. Previous successes do
not eliminate this code path.

The actual root `run-r7-restart.py` launches quiesce with detached Popen, but its
restart branch uses a foreground SSH Python/runpy invocation with inherited
stdout/stderr. These are not interchangeable launch modes. USB loss does not
guarantee an immediate EPIPE: sshd may still own the pipe, buffering can succeed,
and timing differs. It can also expose SIGHUP/transport-lifetime risks depending
on the remote session. None is established as the current incident's cause.

`test-tail.py` ran the local actual CPython interpreter with an actual anonymous
pipe whose only reader was closed. A `print(..., flush=True)` raised
BrokenPipeError(errno32), caught by Exception; CPython's SIGPIPE was ignored.
The exact interpreter version is in `test-result.json`. This is a controlled
interpreter/pipe experiment, not an observation of the phone's SSH pipe.

The same test extracts the actual top-level worker try block via AST; only
MMIO/sysfs/OS boundaries and native syscall are fake. Eight cases establish:

- Old post-CSR EPIPE:0 reboot syscalls,1 thaw, EUD already retired.
- Old post-CSR phase ENOSPC:0 reboot syscalls,1 thaw.
- New tail: injected post-CSR output/file failures cannot occur because those
  operations are removed; exactly1 native reboot call is reached before mmap
  closes.
- New pre-retirement output failure still aborts before unbind/CSR change.
- Failed CSR readback still blocks reboot; a returned reboot syscall still
  thaws and reports failure. There is no automatic retry or EUD rebind.

The unrun candidate is `r7-restart-transport-tail-review.py`, SHA256
`f7cfc985b0caf5694b59d24af3c5100942faa48c9a8b783e02a102abf87dc615`.
`transport-tail.patch` shows the narrow changes against the still-frozen
`1b246fce…93f0f` original. Native ctypes setup moves before retirement; all
necessary phase/output work precedes unbind. Following confirmed CSR0 readback,
the worker immediately calls the one RESTART2 while still inside mmap, with no
phase write, transport print, sleep or mmap close between them. The final
pre-retirement phase is deliberately called `filesystem_frozen_restart2_armed`:
it records intent/preparation, not evidence of a completed reboot.

For a future reviewed launcher, use a **new** transaction and exclusive launch
receipt, start a single detached Popen with stdin DEVNULL, stdout/stderr directed
to a unique **tmpfs /run log**, `start_new_session=True, close_fds=True`, then
record PID/startticks before acknowledging launch. Verify /run is tmpfs first.
Do not place the worker's live output on a rootfs log that FIFREEZE can block.
The worker's critical progress must never depend on an SSH channel. A receipt
still proves launch only; host fastboot/new-boot evidence proves the outcome.
This note is not an instruction or implementation to resubmit the current
already-claimed R7 restart. Root continues to own device recovery and host
enumeration. The candidate also does not fix or diagnose bootloader USB
enumeration, kernel console retirement waits, or the host EUD hub state.
