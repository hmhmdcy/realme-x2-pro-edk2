

---

## 26. Real-hardware review: console works, two real culprits, panic loop (2026-10-07)

### 26.0 What happened

1. console=eud is verified on hardware: with keep_bootcon removed the log no
   longer stops at 1.2 s.
2. But the kernel never reached userspace; it has been a panic loop all along.
   Two independent causes:
   - RPMh read regression (new in 7.3): on SM8150 the AOSS never answers
     rpmh_read().  The request occupies an ACTIVE TCS and blocks every later
     write.  The first read was issued at 0.16 s and timed out exactly 10 s
     later (rpmh.c: RPMH_TIMEOUT_MS = msecs_to_jiffies(10000)).  The log shows
     "failed to read VOLTAGE ret = -110" plus rpmh_write WARNs and
     "dwc3 ... failed to get clocks" as secondary damage.
   - initramfs dead links: build-image.sh ran "busybox --install -s" with an
     absolute path, so all 305 applet symlinks in initramfs/bin point at
     /home/cy122/x2pro-linux/initramfs/bin/busybox.  Inside the initramfs they
     dangle, so /init (a #!/bin/sh script) cannot exec, and the kernel panics
     with "No working init found" -> panic=15 -> reboot loop.  The screen stuck
     on repeated firmware DXE dispatch output ("stuck at EDK2") is the symptom,
     not the cause.

### 26.1 Evidence from the two boots

Boot 1 (console=eud firmware + old Image):

    0.000-0.15 s   earlycon output (garbled head, then clean)
    0.15-10.2 s    hole: fbcon registered at 0.118 s and the kernel unregisters
                   all boot consoles automatically; our real console only
                   appears at device_initcall
    10.2 s         "console [eud0] enabled" and the log RESUMES - hard evidence
                   that console=eud works (without it nothing would follow)
    10.22 s        failed to read VOLTAGE ret = -110, rpmh_write WARN,
                   dwc3 -ETIMEDOUT
    78.86 s        random: crng init done (kernel still alive)
    next 5 min     0 bytes captured: it had already panicked and rebooted, and
                   the EUD CTL state resets on reboot (the host did not re-run
                   com-up)

Boot 2 (keep_bootcon firmware + RPMh patch): ret = -110 becomes ret = -95
(-EOPNOTSUPP, the read is never sent), the 10 s hole is gone, and then the
kernel panics with "No working init found".
### 26.2 Fix 1: RPMh read (drivers/soc/qcom/rpmh.c)

At the top of rpmh_read():

    if (rpmh_read_unsupported())
        return -EOPNOTSUPP;

where rpmh_read_unsupported() caches

    of_machine_is_compatible("qcom,sm8150") || of_machine_is_compatible("qcom,sc8180x")

once.  sm8150-samurai.dts carries "qcom,sm8150" in its compatible list, so the
check matches.  Same idea as the upstream "skip read commands on sm8150 and
sc8180x" thread.  It sits in rpmh_read() rather than in the regulator driver
because there are three call sites (qcom-rpmh-regulator.c:265/377/598) and the
TCS is an RPMh-level resource.

### 26.3 Fix 2: initramfs symlinks (the build-image.sh trap)

    ls -l initramfs/bin/sh
    sh -> /home/cy122/x2pro-linux/initramfs/bin/busybox      <- host absolute path
    find initramfs -type l -lname /home/* | wc -l
    305

build-image.sh calls "busybox --install -s" with an absolute directory, so all
305 applet symlinks point at the host tree.  The cpio keeps the target verbatim,
so inside the initramfs /bin/sh, /bin/ls, ... are dangling and the #!/bin/sh
/init cannot run.  Fix (now scripted): relink every non-busybox symlink in
initramfs/bin to the relative target "busybox", delete linux/usr/
initramfs_data.cpio* to force a rebuild, then make Image.  Verified: the Image
no longer contains /home/cy122/ and /bin/sh points at busybox.

### 26.4 Artifacts and state (2026-10-07 18:45)

    Image-rmx1931-samurai-rpmhfix    d25be955...  RPMh patch, verified in hardware (-95)
    Image-rmx1931-samurai-initfix    4a4463c3...  RPMh + initramfs fix, NOT yet in the FAT
    boot-samurai-eudconsole.img      ea4a8f4e...  console=eud, no keep_bootcon (production)
    boot-samurai-eudlogfull.img      7bc3d6e1...  keep_bootcon debug build (complete but slow)
    rollback: boot-samurai-linux-console.img (16:01), backup/boot_stock_RMX1931.img

Phone state at that moment: panic loop, screen showing firmware DEBUG output,
USB not enumerating at all (neither fastboot nor adb).  Recovery: hold Power
for 15 s, Vol-Down + Power into fastboot, flash stock boot, boot Android, write
Image-rmx1931-samurai-initfix into the logdump FAT, flash
boot-samurai-eudconsole.img.

### 26.5 TODO

1. Flash the initfix image and confirm "rmx1931-mainline initramfs reached
   userspace" appears on screen.
2. Emit the rpmh patch and the initramfs fix as linux-port/patches/0003, 0004.
3. Back to section 20.6: panel SOFEF03F_M, touch S3706, WCN3990, charger, sensors.