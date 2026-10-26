

---

## 27. Userspace reached; console moved to /dev/kmsg; shortcuts vs proper goals (2026-10-08)

### 27.0 Where we are

* The kernel boots to userspace and stays there: "Run /init as init process",
  all six UFS LUNs enumerate, no "No working init found", no panic.  This is
  the first time the port gets past the kernel/initramfs handover at all.
* The initramfs banner and the diagnostic dump now reach EUD, but only
  partially: the dump floods the console (measured throughput ~3 KB/s), the
  captured stream breaks up, and the phone reboots shortly afterwards (cause
  not yet proven; panic=15 turns a panic into a reboot).
* Neither blocker was the port itself: (a) the 7.3 RPMh read regression,
  (b) the initramfs absolute symlinks.  Both are fixed.

### 27.1 What was fixed, in order

1. initramfs symlinks: build-image.sh ran "busybox --install -s" with an
   absolute directory, so all 305 applet links pointed at
   /home/cy122/x2pro-linux/initramfs/bin/busybox.  Inside the initramfs /bin/sh
   was dangling, /init could not exec, and the kernel panicked with
   "No working init found" -> panic=15 -> reboot loop.  Fixed by relinking to
   the relative target "busybox" and forcing a cpio rebuild
   (rm -f usr/initramfs_data.cpio*).
2. The kernel could not open an initial console ("Warning: unable to open an
   initial console.", the initramfs /dev is empty), so init's stdout went
   nowhere.  First attempt - redirect the script to /dev/console after mounting
   devtmpfs - still did not reach EUD, because opening /dev/console resolves
   through console_device() = the preferred console's .device callback, and the
   console-only driver has none, so the writes land on the VT (screen only).
   Second attempt (current): redirect to /dev/kmsg.  That goes through printk
   and therefore reaches every registered console, EUD included.  Banner
   confirmed in the EUD capture.
3. The RPMh read regression workaround (rpmh_read() returns -EOPNOTSUPP on
   qcom,sm8150 / qcom,sc8180x) is in and verified: the 10 s stall is gone and
   the log now shows "failed to read VOLTAGE ret = -95" instead of -110.

### 27.2 The reboot after the dump (open)

Not explained yet.  The last EUD bytes are at kernel time ~0.30 s, right after
the banner, and the tail looks like a crash dump cut into pieces by dropped
frames.  Candidates:

  (a) the flood of /dev/kmsg writes saturates printk/console and something in
      that path stalls or dies;
  (b) init exits (exec sleep 100000 fails, or the shell dies) ->
      "Attempted to kill init!" -> panic=15 -> reboot.

Next step: read /sys/fs/pstore/console-ramoops from Android.  The DTB already
carries ramoops@0xb7e00000 and PSTORE_CONSOLE is enabled, so the panic text
should be there in full - this is the one channel where we get an unbroken log.
### 27.3 Shortcuts taken to get information (temporary by definition)

Every row below exists only because we needed facts from a board that has no
UART.  None of them is the shape the port should keep.

| # | Shortcut | Why it exists | Proper replacement |
|---|---|---|---|
| S1 | initramfs writes its diagnostics to /dev/kmsg | our console has no tty, /dev/console writes never reach EUD | implement the tty layer (uart_driver + .device = uart_console_device): /dev/console and /dev/ttyEUD0 then work for userspace too |
| S2 | the whole diagnostic dump runs on every boot (iomem 40 lines, dmesg 30 lines, device lists) | collecting bring-up facts in one shot | opt-in only (cmdline flag or a file on the ESP); never unconditional |
| S3 | "exec sleep 100000" at the end of initramfs init | keep the box in userspace so the screen keeps its text | a real root filesystem and switch_root; the debug initramfs is a bring-up tool |
| S4 | rpmh_read() SoC quirk via of_machine_is_compatible | 7.3 RPMh read regression on sm8150/sc8180x | upstream's own proposal is the same skip; the cleaner form is a DT capability/quirk or an RSC version check |
| S5 | kernel Image + DTB stored in a FAT partition created inside the factory logdump partition | the kernel cannot fit in the FV (FFS 16 MiB limit; PrePi pool) | a real ESP (shrink userdata) + GRUB, i.e. the section 8 deferred plan |
| S6 | reading the previous panic through Android's pstore | the Linux bring-up has no shell | the initramfs can read /sys/fs/pstore itself and print the previous boot's panic; or OpenOCD |
| S7 | console=eud firmware carrying the command line in firmware code | the firmware is the only place we control the cmdline | the same command line, but as a documented boot option/chosen node with a reproducible build recipe |
| S8 | keep_bootcon (older builds, and boot-samurai-eudlogfull.img) | keep the early console alive to catch early logs | console=eud (done); the debug build stays debug-only |
| S9 | CONFIG_CMDLINE_FORCE experiment | test without flashing a new firmware | abandoned; .config reverted |
| S10 | kernel console pacing still consults INT_STATUS_1 when it reads back | it usually answers | the firmware side already learned this lesson: never trust INT_STATUS_1; use the proven fixed timing (200 us/byte, 2 ms/frame) or a real tty with flow control |
| S11 | panic=15, loglevel=7, ignore_loglevel in the cmdline | debug convenience | production defaults once the port is stable |
| S12 | local DT compatible qcom,sm8150-eud-com with no binding | bind the COM FIFO | an upstream binding, or reuse the qcom,eud node once the role-switch/SCM path is available on this unit |
| S13 | logdump repurposed at all | factory-unused, all-zero partition | keep it as the emergency/rescue area; user data belongs in a real partition scheme |

### 27.4 Proper goals (the standard shape of this work)

1. Console and tty.  A real console for the EUD COM FIFO, selected with
   console=eud, plus a real tty so userspace can write to /dev/console and
   /dev/ttyEUD0.  Pacing must not depend on readbacks that this block does not
   return reliably.  Replaces S1, S2, S10.
2. Device tree.  A reviewable samurai DTS with no borrowed MTP or vendor
   scaffolding: correct PMIC resources ("could not find RPMh address for
   resource ldof2" is a real mismatch), the missing supplies (vdd-hba-supply),
   interconnect paths for qcom-cpufreq-hw, and the temp-alarm dependencies.
3. USB.  Decide explicitly whether dwc3 coexists with EUD or is disabled while
   debugging; the end goal is a working USB gadget/UDC.
4. Boot chain.  ESP + GRUB (or SimpleInit BOOT_LINUX) with kernel, initrd and
   DTB, replacing S5; the firmware's job becomes "load an EFI application",
   nothing else.
5. Root filesystem.  A real distribution (postmarketOS/Debian) with a
   documented install path, replacing S3 and S6.
6. Logging.  Two channels with clear roles: pstore/ramoops for durable records
   across a crash, EUD COM for the live view.  Nothing debug-only on by default
   (S11).
7. Upstream.  The RPMh quirk (S4) and the EUD console with a proper binding
   (S12), plus commit messages that explain the hardware, and no bring-up
   scaffolding in the shipped configuration.

### 27.5 Order I would do it in

1. Read the panic from pstore (S6) and fix the reboot.
2. Trim the initramfs dump to the banner plus a handful of lines and throttle
   it (S2); make it opt-in.
3. Land the tty half of the EUD driver (S1, S10): that is already written and
   waiting in the un-landed eud.c.
4. Then the real work of section 20.6: panel SOFEF03F_M, touch S3706, WCN3990,
   charger, sensors - plus the DT items listed in goal 2.
5. Only after that: the ESP/GRUB/distro work (goals 4, 5), with a GPT backup
   and a verified 9008 rescue path in hand first.