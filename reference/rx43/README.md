# RX43: full-output audit and remaining receipt boundary

2026-10-09. Hardware narrative and current device state:
[session 43](../../sessions/43-native-terminal-evidence-audit.md).
Source versions and chain audit: [source-audit.md](source-audit.md).

The RX41 .raw files remain unchanged. Their hashes pass; their native id,
echo and console outputs were hidden only in the decoder's previous stdout
filter. The enhanced RX41 verifier now asserts these actual responses.

This directory preserves RX43 raw/text/events, three libusb usbmon traces,
the bounded reboot/capture helper and the actual BusyBox PTY check. Full kernel
images and the downloaded official BusyBox archive remain outside the repo in
`E:\edk2-samurai-out\rx43`. There was no kernel change, build or flash.

Published derived `.txt` files use LF and remove line-end spaces for review;
original host text exports remain in the output directory. The authoritative
`.raw` and `.usbmon` bytes are unchanged and protected from Git newline conversion.

Run from WSL:

```sh
cd '/mnt/e/RealmeX2Pro edk2/reference/rx43'
sha256sum -c SHA256SUMS
python3 verify.py
```

Empty native-echo-a/libusb-stty captures are not accepted frames. The later
dmesg tail lacks the failed Windows echo A's RX receipt while retaining the
surrounding ones. Both USB paths still require retry. Completed virtual USB
URBs and zero-stray framing do not establish physical ACKs or lossless delivery.
