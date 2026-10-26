# RX60 no-admin even reversal — before execution

The originally planned joint logger/ETW Arm stayed at Windows desktop UAC.
After approximately 489 seconds it was cancelled. The late-Arm control-directory
guard was set before stopping the exact launcher; no helper or backup started.
No logging values, PnP reload, or ETW change occurred.

Use the same frozen diagnostic and the same pre-defined even-IN prediction.
Two sequential owners with 60/100-second bounds, total <=180 seconds; startup
Ctrl-U only may retry. Owner 1 must accept its first Ctrl-U, then send abc once
if startup IN count is even or abcd once if odd; inspect actual final even IN,
two short OUT only, manually drain and close around 40 seconds. Owner 2 opens
normally, measures the first status via raw/counter, freezes one 3120-byte CPU
journal and exports base64. Data sends are once only. Finally Close/Dispose/Detach.

This is a reversal of the RX59 forced-odd transition. Differences are explicit:
no initial full PnP reload, driver raw logging, or new ETW. It can test whether
the predicted first-frame loss reverses; it cannot establish physical DATA0/1
or reproduce the full logger/ETW boundary. No firmware or installed terminal
change, flash, phone reboot, driver install, fuse/PHY/clock changes.
