---
<!-- from HANDOVER-NEXT.md, section 30 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 30. Current artifacts and how to drive the phone

Images (E:\edk2-samurai-out):

* boot-samurai-console.img   EDK2 firmware whose command line carries
                             "console=tty0 console=eud" and no keep_bootcon
                             sha256 8351b782b090f16355fc8019c2701579217ecd581961da20db52a6f568890f52
* logdump-tty6.img           last verified-good kernel: clean console,
                             /dev/ttyEUD0, header command channel
* logdump-payload.img        payload protocol; wedges the EUD (section 29.5)
* logdump-regprobe2.img      the register-window probe that found 0x14
* Image-rmx1931-samurai-*    the kernel Images themselves
* boot_stock_RMX1931.img     Android boot backup, sha256 dfe18875..., byte
                             identical to the phone's boot partition

Host tools (E:\edk2-samurai-out):

* eud-parse.py            reassemble a capture ([0x90][len][data], with resync)
* patch-logdump.py        put an Image into the logdump FAT (about 1 s)
* flash-and-test-rx.ps1   flash boot + logdump, wait for EUD, capture;
                          -RestoreAndroid puts the Android boot image back
* eud-type.ps1            type a string into /dev/ttyEUD0
* eud-run.ps1, eud-run2.ps1  run a command with output verification and retry
* eud-cmd-test.ps1        exercise the [0x81] command channel
* eud-regprobe-host.ps1   write [0x90][0x08]"PAYLOAD!" every 5 s (the 0x14 hunt)
* comlog2.cpp            tight-loop reader used earlier in the project

Workflow for every cycle:

    hold Power ~15 s        full power cycle: EUD keeps the port otherwise and a
                            wedged EUD block only clears this way
    Vol-Down + Power        -> fastboot
    fastboot flash boot  boot-samurai-console.img    only when firmware changed
    fastboot flash logdump logdump-<version>.img     1.8 s
    fastboot reboot
    E:\eud-host\eudtool.exe com-up                   enable COM + VBUS attach
    then eud-type.ps1 / eud-cmd-test.ps1 / comlog2 and read the capture

Build trees:

* kernel:  ~/x2pro-linux/linux   (Linux 7.3-rc6, samurai DTS, eud.c,
           eud_earlycon.c).  make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
           Image, then patch-logdump.py.
* firmware: ~/edk2-samurai/repo  (build.sh -d samurai --toolchain GCC5),
           produces boot-samurai.img.

Repositories to push to when the work is settled: the EDK2 tree (hmhmdcy fork)
and the kernel branch created in sections 22-24.
