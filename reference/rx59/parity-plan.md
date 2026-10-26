# RX59 parity experiment (before execution)

The human has granted continuing authorization for the same COM14 diagnostic scope.
One fresh UAC helper temporarily changes only QCDriverConfig and QCDriverLoggingDirectory,
reloading only the exact COM14 leaf once to enable and once to restore. It starts the
same bounded 64 MB USBXHCI/UCX/USBHUB3 trace and restores in finally, with a 300-second
helper deadline. No flash, phone reboot, driver installation, fuse/PHY/clock change.

Two sequential serial owners, 60/100 seconds maximum, final owner starts within 60
seconds; total capture <= 180 seconds. Both use the unchanged RX55 diagnostic.

1. Require a first-attempt fresh Ctrl-U receipt. Observe the actual startup IN frame
   count. Manually send exactly one unexecuted native frame: abc if startup count is
   odd (expected 20 more IN frames), abcd if startup count is even (expected 21 more).
   Drain, Ctrl-P, Ctrl-]. Assert the actual final count is odd, both submitted OUT
   frames are short, there is no pending input, and serial finally has closed.
2. Ordinary reopen with no PnP reload between the owners. Startup Ctrl-U clears the
   unexecuted text. Record whether its first timestamp frame is absent. Only sync
   may retry; no automatic data retransmission. Manually freeze a 3120-byte journal
   using dd bs=4096 count=1, base64 export, Ctrl-P, Ctrl-].

Hypothesis: reset 0x1e resets host DATA0/1, but device endpoint might preserve its
state. A preceding odd count could cause first IN loss after reopen. This experiment
forces odd IN while keeping preceding OUT count even. Software short completions
are a parity proxy, not a direct physical DATA0/1 measurement. If assumptions fail,
stop this single-use experiment and preserve its evidence.
