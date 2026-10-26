

---

## 28. Button-free fastboot and a hands-off flywheel: PON reboot-mode, EUD COM RX, fastboot flash logdump (2026-10-08)

### 28.0 Summary

Three findings, each verified in source or on hardware:

1. The phone can reboot into fastboot by itself.  The vendor DTB already carries the
   magic (mode-bootloader = <0x02> on the PMIC PON), mainline's qcom-pon.c speaks the
   generic reboot-mode framework, and only two DT lines are missing on this board.
2. The EUD COM channel is full duplex.  The official QUIC host library documents
   COM_RX_ID/LEN/DAT at 0x088E000C/0x10/0x14, i.e. host -> device.  This project only
   implemented the TX half, so "control the phone like adb" is a software task, not a
   hardware limit.
3. fastboot can write the logdump partition: "fastboot flash logdump" works and is
   byte-exact, 64 MiB in 1.8 s.  That removes the Android step from the iteration
   loop.

### 28.1 Button-free fastboot (PMIC PON reboot-mode)

Evidence:

* Vendor decompiled DT, linux-port/artifacts/sm8150-samurai.dts.decompiled:3917:

      pon@800 {
              compatible = "qcom,pm8998-pon";
              reg = <0x800>;
              mode-bootloader = <0x02>;
              mode-recovery   = <0x01>;
      };

  So the stock Android "reboot bootloader" writes 0x02 into the PMIC PON reason
  field and resets; ABL reads it and enters fastboot.  That is why every
  "adb reboot bootloader" in this project worked.

* mainline drivers/power/reset/qcom-pon.c matches qcom,pm8998-pon with
  GEN2_REASON_SHIFT, writes magic << reason_shift into the PON register and
  registers itself with the generic reboot-mode framework
  (devm_reboot_mode_register).  reboot-mode.c takes the magics from DT properties
  prefixed "mode-" (define PREFIX "mode-").

* .config already has POWER_RESET_QCOM_PON=y, POWER_RESET_MSM=y, REBOOT_MODE=y,
  POWER_RESET_SYSCON=y, SYSCON_REBOOT_MODE=y.

* mainline pm8150.dtsi's pon@800 has the right compatible and reg, but not the two
  mode- properties - that is the only missing piece.

Patch (two lines in sm8150-samurai.dts):

    &pon {
            mode-bootloader = <0x02>;
            mode-recovery   = <0x01>;
    };

Trigger: busybox's reboot cannot pass a reason string, so a ~15 line static helper
is needed:

    sync();
    syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2, "bootloader");

Caveat: the magic is written by the reboot notifier at reset time, so the mode has
to be requested on the reboot that matters.  A panic reboot passes cmd = NULL and
therefore does NOT carry the bootloader reason; for that case the next boot's
initramfs should read pstore, notice the previous panic, and itself call
reboot2 bootloader.

### 28.2 EUD COM is full duplex (host -> device)

From the official QUIC library, E:\eud-host\quic-eud\com_api.cpp:127-132:

    HWIO_PERIPH_SS_EUD_COM_RX_ID_ADDR : 0x088E000C
    HWIO_PERIPH_SS_EUD_COM_RX_LEN_ADDR: 0x088E0010
    PERIPH_SS_EUD_COM_RX_DATA         : 0x088E0014

  TX (device -> host, what this project uses): 0x088E0000 / 0x04 / 0x08
  RX (host -> device, unimplemented here):     0x088E000C / 0x10 / 0x14

So a command channel is purely a software task:

* device side: poll RX_LEN, read RX_DAT, interpret a small command set
  (reboot2 bootloader / recovery / edl / heartbeat);
* host side: write to the COM port, or add an eudtool opcode;
* the same polling can be added to EDK2 with a timer event, so a PC can rescue a
  device that is stuck before BDS finishes - the situation seen twice today, when
  neither fastboot nor adb existed.

This is the "control it like adb" path.  It is cheaper and more useful than
SWD/JTAG for boot-mode control; SWD remains the only way to halt or single-step a
core, and on this unit the 9504 SWD endpoint has not been seen at all.
### 28.3 fastboot can write the logdump partition (verified)

Tests run on hardware:

| test | result |
|---|---|
| fastboot getvar partition-type:logdump | `raw` |
| fastboot getvar partition-size:logdump | `0x4000000` = 64 MiB |
| fastboot fetch logdump ... | not supported by this ABL |
| fastboot flash logdump logdump.img | OKAY, 64 MiB in 1.78 s |
| re-read with dd and compare sha256 | identical (`63e83d3e...` before and after) |

FAT layout of the template (parsed from the dump):

    FAT16 / label KERNEL / 4096 B per sector / 1 sector per cluster / 2 FATs
      \Image       30,116,352 B   start cluster 3
                   clusters 3..7355 contiguous, data offset 90112 (0x16000)
      \samurai.dtb     94,739 B   start cluster 7356

Because the Image size is always exactly 30,116,352 bytes and its cluster chain is
contiguous, an in-place update is a single contiguous write and touches neither the
FAT nor the directory entry:

    d = bytearray(open('logdump.img','rb').read())
    img = open(new_image,'rb').read()
    assert len(img) == 30116352
    d[90112:90112+30116352] = img
    open('logdump-new.img','wb').write(d)

Template kept at E:\edk2-samurai-out\logdump.img (sha256 63e83d3e...).

Side benefit: a corrupted logdump FAT is no longer a trip through Android - the
template can be flashed back in 1.8 s from fastboot.

### 28.4 The flywheel

    [PC]  edit code, make Image                                     ~2.5 min
    [PC]  python: patch logdump.img in place                        ~1 s
    [PC]  fastboot flash logdump (64 MiB)                          ~1.8 s
          fastboot flash boot, only when the firmware changed      ~0.3 s
    [phone] firmware -> Linux: dump logs, then reboot2 bootloader -> fastboot
    [PC]  capture daemon: waits for 9501, com-up, finds the COM port, records
          one log file per boot - no operator needed
    [PC]  new log -> panic/WARN extraction -> next fix

Prerequisites, in order:

1. DT: the two mode- lines (28.1).
2. initramfs: read the previous boot's pstore; if it shows a panic, go straight to
   fastboot; pet the hardware watchdog (CONFIG_QCOM_WDT=y) so a hang also resets;
   after the banner and diagnostics, call reboot2 bootloader.
3. PC side: the capture daemon above (the pieces exist: eudtool, comlog2).
4. PC side: the logdump patch script, landed in linux-port/scripts/.

### 28.5 Deltas to the shortcuts / proper-goals split (section 27.3, 27.4)

* S5 (kernel stored in a FAT inside logdump) is much less of a shortcut now: the
  fastboot write path is verified, the file offset and size are fixed, and a
  corrupted FAT is recoverable in 1.8 s.  It is still not the standard shape (goal
  4: ESP + GRUB), but it is no longer fragile.
* New item S14: reboot2 needs a static helper binary because busybox cannot pass a
  reboot reason.  The proper fix is a small tool in the image, or a future
  userspace that can call the reboot syscall properly.
* New proper goal (8): a host -> device command channel over EUD COM RX, wired into
  both the kernel driver and EDK2, so the PC can control boot modes and rescue a
  firmware that is stuck before BDS.  Replaces nothing; it makes S3/S6 unnecessary
  and gives the same convenience adb has, without Android.
* SWD/JTAG (section 4) stays where it was: the only tool for halt/step/memory, not
  for boot mode, and its endpoint has not appeared on this unit.

### 28.6 TODO, in order

1. Land the two DT lines and the reboot2 helper; rebuild the Image.
2. initramfs logic: previous-panic check via pstore, watchdog pet, reboot2 at the end.
3. PC capture daemon and the logdump patch script.
4. Then the flywheel runs unattended; use it to finish the real work of section 20.6.
5. Optional, later: the EUD COM RX command channel (kernel + EDK2), and the ESP/GRUB
   end state.