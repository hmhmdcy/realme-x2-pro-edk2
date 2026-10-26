# EUD (Embedded USB Debug) on the realme X2 Pro

用途：设备寄存器、CTL/COM与固件日志环的技术历史。文档整理：2026-10-14；以下“下一步”和设备/工具状态按各节日期解释。当前部署见[检查点](NEXT-SESSION.md)，操作规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)，后续RX与协议验收见[RX-CONSOLE](RX-CONSOLE.md)及[测试飞轮](FLYWHEEL.md)。

EUD is a debug hub built into almost every Qualcomm SoC since ~2018. When it is
enabled it hijacks the USB port and exposes a small USB hub (VID 0x05C6) with
debug devices the host can drive: CTL (control), JTAG, SWD, TRACE and COM.
The CTL channel alone is enough to enable/attach the other peripherals.

## Device facts (verified on this unit)

| Item | Value |
|---|---|
| Device tree node | qcom,msm-eud@88e0000, compatible qcom,msm-eud |
| Base / size | 0x088E0000 / 0x2000 (inside PERIPH_SS) |
| Interrupt | GIC SPI 492 |
| Kernel driver | eud, bound to 88e0000.qcom,msm-eud |
| Kernel enable knob | /sys/module/eud/parameters/enable (root only), default 0 |
| Fuses | not disabled - EUD works on this retail unit |

## Enable from Android (verified 2026-10-06)

    adb shell
    su
    echo 1 > /sys/module/eud/parameters/enable

The host then sees a Qualcomm hub (VID_05C6&PID_9500) plus the EUD control
device (VID_05C6&PID_9501). EUD takes over the port: adb / fastboot / USB mass
storage stop working. A full power cycle (hold Power ~15 s) restores normal USB;
a warm reboot can keep EUD on and hide fastboot.

## Register writes (what the kernel does)

    writel(BIT(0),             eud_base + 0x1014);  /* EUD_REG_CSR_EUD_EN */
    writel(BIT2 | BIT3 | BIT4, eud_base + 0x0024);  /* INT1_EN_MASK */

This node has no qcom,secure-eud-en, so plain non-secure MMIO is enough - which
is exactly why EDK2 can do the same.

## EDK2 firmware enable (VERIFIED on hardware 2026-10-06)

Implemented in PlatformBm.c under #ifdef SAMURAI_ENABLE_EUD (set in
samurai.dsc). In PlatformBootManagerAfterConsole the firmware writes the two
registers ten times, 200 ms apart, and prints to the framebuffer console:

    [SAMURAI-EUD] CSR_EUD_EN=0x00000001 INT1_EN_MASK=0x0000001c

Test image: E:\edk2-samurai-out\boot-samurai-eudtest.img
sha256 a2819fbafe2e2eb4774fcdd22c4cb7ac2c1d718b463e30c8638835575e8b1ce8
(= release3 + EUD; release3 already carried the three-button fix.)

Host-side result after flashing and rebooting (2026-10-06 17:19):

    9500 hub + 9501 control device appear immediately
    eudtool probe -> opcode 0x01 => 00 00 05 00
                     opcode 0x02 => A1 28 BC 62
                     opcode 0x03 => 04 00 00 00

Do not try to verify this by grepping the boot image: SM8150_UEFI.fd contains a
compressed FVMAIN_COMPACT, so the marker is not visible. Check the uncompressed
build products instead:

    Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv      (strings -el | grep SAMURAI-EUD)
    Build/samurai/RELEASE_GCC5/AARCH64/Platform/RenegadePkg/Library/
        PlatformBootManagerLib/PlatformBootManagerLib/OUTPUT/PlatformBm.obj

## Host access from Windows (verified; no Zadig, no usbipd, no WSL)

The Qualcomm QDSS driver that is already installed on this PC (qdbusb.sys via
oem58.inf) binds the EUD control device and creates a DOS device name:

    QueryDosDeviceA(NULL, ...)  ->  "Qualcomm EUD Control Device 9501"

Open it at:

    \\.\Qualcomm EUD Control Device 9501\DEBUG

There is no "(0003)" instance suffix on this unit - the "(NNNN)" names quoted in
older Qualcomm documents do not exist here, and brute-forcing them fails with
ERROR_PATH_NOT_FOUND.

### CTL protocol

One request = one opcode byte plus an optional little-endian payload; the
response is read from the same handle. Opcodes (ctl_eud.h):

| Opcode | Name | Send bytes | Recv bytes |
|---|---|---|---|
| 0x01 | EUD_VERSION_READ | 1 | 4 |
| 0x02 | DEVICE_ID_READ | 1 | 4 |
| 0x03 | EUD_STATUS_READ | 1 | 4 |
| 0x07 | CTLOUT_SET | 5 (opcode + LE u32 mask) | 0 |
| 0x08 | CTLOUT_CLR | 5 | 0 |

CTLOUT bit positions: bit2 SWD_PERIPH_EN, bit3 TRACE_PERIPH_EN,
bit4 JTAG_PERIPH_EN, bit5 COM_PERIPH_EN, bit12 VBUS_ATTACH, bit13 VBUS_INT.

IMPORTANT: CTLOUT_SET / CTLOUT_CLR return no data. Reading after them blocks
forever on a synchronous handle; write only, or use overlapped I/O with a
timeout.

### Bringing up the COM peripheral (verified)

    CTLOUT_CLR 0x00000000
    CTLOUT_SET 0x00000020   # COM_PERIPH_EN
    CTLOUT_SET 0x00001000   # VBUS_ATTACH
    CTLOUT_SET 0x00002000   # VBUS_INT
    sleep ~100-200 ms
    CTLOUT_CLR 0x00002000   # clear VBUS_INT

Result: the hub then reports USB\VID_05C6&PID_9505. Without the VBUS attach step
it only reported USB\VID_0000&PID_0002 ("device descriptor request failed"), so
the attach step is required.

### Known gap: no Windows driver for 9505

After the sequence above the 9505 device enumerates correctly
(HardwareIds USB\VID_05C6&PID_9505&REV_0100, compatible Class_FF) but has
ProblemCode = 28 ("the drivers for this device are not installed"), empty Class
and no COM port.

Reason: Qualcomm's own C:\Windows\INF\oem69.inf has the 9505 entry commented
out:

    ;%QcomDevice9505%   = QportInstall00, USB\VID_05C6&PID_9505
    QcomDevice9505      = "Qualcomm EUD Port 9505"

The public qualcomm/qcom-usb-userspace-drivers repo has no INF for 9505 and no
signed catalog either (only qcusbfilter.sys), so the serial driver cannot simply
be installed from there.

Options for getting EUD COM data to the host:

    A. Bind WinUSB to 9505 (Zadig, admin once), then read it with libusb.
       quic/eud's libeud.dll is already built on this machine (see below).
    B. usbipd bind 9505 -> attach to WSL, then use linux-msm/openocd or the
       Linux build of quic/eud.
    C. Supply a signed serial INF for VID_05C6&PID_9505 (qcusbser).

SWD (9504) and JTAG (9503) are listed, not commented out, in oem58.inf, but
CTLOUT_SET 0x645 (SWD payload) + attach did not make 9504 appear on this unit.

## Host tools built for this project (Windows)

Everything lives in E:\eud-host\ :

| File | What it does |
|---|---|
| eudtool.exe / eudtool.cpp | probe / attach / detach / com-up / com-off / raw / list |
| eudraw.exe / eudraw.cpp | first raw opcode test (0x01 / 0x02 / 0x03) |
| dosdev.exe / dosdev.cpp | enumerate DOS device names via QueryDosDevice |
| opentest.exe / opentest.cpp | CreateFile variant matrix for the CTL node |
| quic-eud/ | quic/eud clone, libeud.dll built with MSYS2 UCRT64 |
| eud-probe.exe | probe linked against libeud.dll (the library uses libusb on
  Windows, so it cannot see the device while qdbusb is bound - use eudtool) |

MSYS2 lives at E:\msys64 (UCRT64 environment). Rebuild eudtool with:

    export MSYSTEM=UCRT64
    E:\msys64\usr\bin\bash.exe --login
    cd /e/eud-host && g++ -o eudtool.exe eudtool.cpp

Typical use with the phone already in EUD mode:

    E:\eud-host\eudtool.exe probe
    E:\eud-host\eudtool.exe com-up

## OpenOCD (host debugger, still the plan for JTAG/SWD)

    git clone https://github.com/linux-msm/openocd
    cd openocd && git submodule update --init
    ./bootstrap
    ./configure --enable-eud --disable-linuxgpiod
    make -j"$(nproc)"
    ./src/openocd -d -f tcl/interface/eud.cfg -f tcl/target/qualcomm/<target>.cfg

On this Windows machine prefer the native CTL path above for enable/attach and
use OpenOCD only once a JTAG/SWD device is reachable (WSL + usbipd, or a native
Linux host).

## Caveats

* While EUD is enabled the USB port is unavailable (no fastboot / UMS) until the
  next power cycle.
* EUD grants full JTAG/SWD access (halt, breakpoints, arbitrary memory access).
  Treat it as a debug tool, do not leave it enabled on a device with sensitive
  data.
* On fused-off SoCs, or where the mode manager is secure-only, the writes
  silently do nothing. Not this unit.

## Windows COM driver for 9505 (installed 2026-10-06)

The EUD COM device enumerates as USB\VID_05C6&PID_9505 but Windows has no
in-box driver, and Qualcomm's current INFs comment the EUD product IDs out
(qcom-usb-kernel-drivers RELEASES.md: "Remove EUD product IDs from INFs").
A working WHQL-signed package still ships inside the older QUD.WIN.1.1
installer 10057.4:

    source : https://mirrors.lolinet.com/software/windows/Qualcomm/QUD/
             qud.win.1.1_installer_10057.4.zip
    sha256 : 5ADE2447F8CA75CED0EE61C7B5641DB76CF6D1B8A85C423C1F1EC2D0ECEF2B9A
    inside : Setup.exe -> MSI -> Data1.cab -> qcser.inf (DriverVer 12/17/2018,
             2.1.3.5), qcser.cat, qcusbser.sys
    signing: qcser.cat and qcusbser.sys are Valid WHQL
             (CN=Microsoft Windows Hardware Compatibility Publisher)
    local  : E:\eud-host\qud_10057.4.zip and unpacked E:\eud-host\qud_cab\

qcser.inf carries the 9505 model line for every architecture:

    %QcomDevice9505% = QportInstall00, USB\VID_05C6&PID_9505

Install (admin). The INF expects the driver binary under serial\<arch>\, so if
you unpack the cab yourself you must recreate that layout first:

    mkdir E:\eud-host\qud_cab\serial\amd64
    copy E:\eud-host\qud_cab\qcusbser.sys E:\eud-host\qud_cab\serial\amd64\
    pnputil /add-driver "E:\eud-host\qud_cab\qcser.inf" /install
    pnputil /scan-devices

Result on this machine (2026-10-06 17:4x):

    published name : oem102.inf
    device         : USB\VID_05C6&PID_9505\8&5580DC5&0&5
    status         : OK, Class=Ports, service=qcusbser, problem=0
    friendly name  : Qualcomm EUD Port 9505 (COM14)
    open test      : COM14 opens at 115200; ReadByte times out (expected -
                     the firmware does not write COM output yet)

Notes:
* Only qcser.inf is needed. Do NOT install qdbusb.inf / qcfilter.inf from the
  same package - the working QDSS CTL binding (oem58.inf) must stay.
* The 9505 device must exist first: enable EUD, then run eudtool com-up.
* Full log chain: firmware writes the EUD COM TX FIFO, Windows reads COM14.

## Firmware side: EUD COM TX (next step)

The host side is now complete. What is still missing is on the target:

    TX_ID   0x088E0000   (execution environment id, APPS = 0x81)
    TX_LEN  0x088E0004
    TX_DATA 0x088E0008

Planned: a minimal TX-only write from the BDS EUD block (fixed string), then a
proper SerialPortLib so DEBUG() output goes out over COM14.

## EDK2 side: DEBUG over EUD COM (verified 2026-10-07)

EudSerialPortLib (Platform/Realme/sm8150/Library/EudSerialPortLib) implements
SerialPortLib by writing DEBUG() output into the EUD COM TX FIFO.

Wiring (samurai.dsc): SerialPortLib is overridden only for the module-type
scopes DXE_DRIVER, DXE_RUNTIME_DRIVER, UEFI_DRIVER and UEFI_APPLICATION.
PrePI/PEI/SEC and DXE_CORE keep FrameBufferSerialPortLib.  That matters:

  * PrePI/PEI run before the EUD block is enabled;
  * DxeCore owns the page tables and must not run extra MMIO/delay code early.

Frame format (verified on hardware):

    [ID=0x90][LEN][DATA...]

  * TX_ID   0x088E0000 <- 0x90 (UART_ID)
  * TX_LEN  0x088E0004 <- payload length of this frame
  * TX_DAT  0x088E0008 <- payload byte

A whole string written in one go is truncated by the TX FIFO after ~7 payload
bytes, so the library sends it in 6-byte frames (200 us between bytes, 2 ms
between frames).  The host must reassemble the frames.

Gate: SerialPortWrite() only transmits once CSR_EUD_EN (0x1014) low byte is 1,
i.e. after the BDS block enabled EUD.  It re-checks the gate every 256 calls so
the pre-BDS cost stays at zero.

Host-side capture (verified):

    E:\eud-host\eudtool.exe com-up
    E:\eud-host\comlog.exe COM14 600 E:\eud-host\eud-com.log

Result: "[SAMURAI-EUD-COM] SerialPortLib test 29" was reassembled from COM14,
proving EDK2 -> EUD COM 9505 -> qcusbser -> COMx -> host log.

### Crash lesson (2026-10-06, build with PcdDebugPrintErrorLevel=0x800B05C7)

Enabling full DEBUG globally while the library was also assigned to DXE_CORE
crashed the boot in DxeCore/CpuDxe:

    ReplaceTableEntry: splitting block entry with MMU disabled
    Synchronous Exception at ArmCpuDxe.dll+0x34B8
    (ELR 0x...F4B8, LR 0x...F518, ESR 0x02000000, stack corrupted)

Fix: keep the platform default PcdDebugPrintErrorLevel (0x80000000, ERROR only)
and never override SerialPortLib for DXE_CORE.  To get INFO-level logs later,
raise the level per module (component <PcdsFixedAtBuild>) rather than globally,
or make the library non-blocking (ring buffer drained by a timer event).

## Firmware log ring buffer over EUD COM (2026-10-07)

Problem: the host cannot open the EUD COM port until it has run eudtool com-up,
so every DEBUG() line printed before that (all of PEI, DXE and the start of BDS)
was lost.

Solution: a fixed-address RAM ring buffer that the firmware fills, plus a single
drainer that replays it once the host is listening.

  shared ring   Platform/Realme/sm8150/Library/EudSerialPortLib/EudLog.h
  producer      Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c
  consumer      Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c

Design points (do not undo them casually):

* SerialPortWrite() must never touch EUD MMIO.  The library is a BASE library
  linked into about 160 modules, so every module gets its own copy of the
  library variables; a per-module buffer plus a per-module drainer cannot work.
  The ring therefore lives at a fixed address shared by all copies: 0x9FFE3000,
  80 KB, the platform memory map entry that used to be called RSRV2 and is now
  called "EUD Log" (EfiReservedMemoryType: not given to the pool and not handed
  to the OS as free memory).
* Producers reserve space with InterlockedCompareExchange32 (SynchronizationLib).
  GCC lowers both __atomic_* and __sync_* to out-of-line __aarch64_cas* helpers
  which EDK2 does not link, so the raw builtins cannot be used here.
* The drainer gates on CTL_OUT_1 bit5 (COM_PERIPH_EN) or bit12 (VBUS_ATTACH),
  which is exactly what eudtool com-up sets.  Replaying before that would only
  throw away the oldest and most interesting lines.  If the readback cannot be
  trusted on this unit the gate opens after 15 s (EUD_HOST_WAIT_MS).
* The drain is rate limited: EUD_DRAIN_FRAMES_TICK frames of EUD_COM_CHUNK (6)
  bytes per EUD_DRAIN_TICK_MS (10 ms) tick, using the hardware-proven timing of
  200 us between bytes and 2 ms between frames.  That is about 1.2 KB/s, so a
  full 80 KB ring needs roughly a minute to replay while the boot menu stays
  usable, because each tick blocks for at most a few milliseconds.

Testing: flash boot-samurai-eudlog.img, let the phone reach the boot menu, then
on the PC run eudtool.exe com-up and comlog.exe COM14 600 eud-com.log.

The Drops and DropEvents counters are reported once, on screen and in the log,
if the ring overflows.

Known follow-ups:

* Measure the real replay rate.  If it is too slow, replace the fixed 2 ms frame
  gap with the TX flow control the stock kernel driver uses (EUD_INT_STATUS_1
  bit1, eud_tx_empty()), and/or raise EUD_COM_CHUNK towards the 14 byte FIFO
  depth.  Both need a hardware measurement first.
* A producer that is preempted between its reservation and its copy can leave a
  partially written region at the very end of the ring.  The drainer is far
  behind whenever there is real traffic, so this is accepted for a best-effort
  debug log.

## Log ring verified on hardware (2026-10-07)

Image boot-samurai-eudlog2.img (sha256 cf2364723022b2491bf763d5359547fc6226518829c119539b2d5153ec0e71a8)
was flashed and verified:

  * EUD CTL 9501 appears about 3.5 s after reboot (BDS enables EUD in the boot).
  * eudtool com-up -> "Qualcomm EUD Port 9505 (COM14)" appears immediately.
  * comlog.exe COM14 30 -> raw 12523 bytes, 1571 frames, 12 complete passes.
  * The capture contains DEBUG lines produced long before the host attached
    ("SimpleFbDxe: Retrieve MIPI FrameBuffer parameters from PCD"), which is
    exactly what used to be lost.  No drops (no overflow marker) at ERROR level.

Design change made after the first hardware test: the drainer no longer gates on
CTL_OUT_1.  That readback proved not dependable, and the 15 s fallback fired long
before a human runs com-up, so the buffer was replayed into the void and the host
captured 0 bytes ("no host attach seen, replaying anyway" was on the screen).

The drainer now loops instead: it rewinds the consumer tail to the oldest byte
still in the ring and replays everything, pausing EUD_REPLAY_PAUSE_MS (2 s)
between passes, for EUD_REPLAY_WINDOW_MS (120 s) after EUD is first seen enabled.
After that it switches to plain pass-through so a long-lived boot menu does not
keep busy waiting in a timer callback.  A host that attaches at any time inside
the window receives a complete copy, and no guess about host state is needed.

Consequences and follow-ups:

  * The capture holds several complete copies (a pass every ~2.5 s at the
    default ERROR level).  That is intended; a per-pass marker line would make
    the boundaries easier to read.
  * With PcdDebugPrintErrorLevel raised to full DEBUG the ring fills up, so a
    pass takes about 68 s at the current ~1.2 KB/s drain rate.  The loop still
    guarantees a complete copy, but the timer callback would then be busy for
    most of each pass, which is worth tuning (TX flow control polling or larger
    frames) before raising the level.
  * The first capture already shows a real firmware error that was invisible
    before: "ERROR: C40000002:V03051003/V03051002 I0 6D33944A-EC75-4855-A54D-809C75241F6C 9FFCF718"
    (BdsDxe GUID, reported 9-11 times per pass).  Worth investigating next.

## Full DEBUG achieved; real cause of the +0x34B8 crash (2026-10-07)

The crash at ArmCpuDxe + 0x34B8 that killed every full DEBUG build (and that the
earlier handover blamed on the serial writer) is NOT caused by SerialPortLib.
The instruction at that offset, disassembled from the build, is

    34b8:  a94153f3   ldp  x19, x20, [sp, #16]

which is the epilogue of ReplaceTableEntry() in
ArmPkg/Library/ArmMmuLib/AArch64/ArmMmuLibCore.c.  It is a stack access fault:
the attribute update just performed (the live-block break-before-make path, with
the MMU temporarily disabled) leaves the stack page inaccessible, and the very
next stack access faults.

The message "splitting block entry with MMU disabled" is printed by that same
branch, which is why its text was found on the stack - it is a symptom, not the
cause.  The old MMIO writer and the new RAM ring writer crashed at the same
instruction because the crash happens after the serial write returns.

Fix applied: the DEBUG() call in that branch is removed, with a note in
ArmMmuLibCore.c.  Printing from a path that is about to disable the MMU is unsafe
on this platform.  With that change a full DEBUG build
(PcdDebugPrintErrorLevel = 0x800B05C7, set in samurai.dsc) boots to BDS in ~4 s.

Verified capture (boot-samurai-eudlog5.img, sha256
5a0aab582df3f1382b6b7cae6fd58568930a50b2a80dd5ab3013c265d8837d82):

  * EUD CTL 9501 appears 4 s after reboot with full DEBUG.
  * comlog.exe COM14 90 -> 138501 bytes, 2099 lines, 12 identical passes.
  * Pass marker: "--- pass N: 10214 byte(s) in 8510 ms ---" => about 1.2 KB/s.
  * No overflow: the complete boot log is only about 10 KB, far below the 80 KB
    ring, so full DEBUG does not need a bigger ring today.

Two previously invisible firmware bugs are now in the log:

  * "SetCPUFreqDxeMain: CPU 1 Now running at -1875767296 Hz" (CPU 2 likewise):
    negative/garbage frequency values.
  * "SetCPUFreqDxeMain: Failed to get the maximum performance level for CPU 4,
    Status: Protocol Error" and "This CPU may not exist on current platform":
    only CPUs 0-3 are set up on a platform that has 8.

The earlier BdsDxe status code error is explained by the boot option dump:
the auto enumerated "UEFI Misc Device 1-6" (the six UFS LUNs) and
"UEFI Non-Block Boot Device 1-2" are attempted and fail to load, which is exactly
EFI_SW_DXE_BS_EC_BOOT_OPTION_LOAD_ERROR (V03051002), plus one
BOOT_OPTION_FAILED (V03051003).  Benign noise from non-bootable devices, but it
is what made BDS report an error about nine times per boot.

### Where the ArmMmuLib fix lives

Common/edk2 is pinned to the fork https://github.com/hmhmdcy/edk2, branch
samurai-armmmulib, which carries exactly this one commit on top of the previous
revision, so a plain recursive clone gets the fix with no extra step.  The same
change is also kept as a patch for anyone building against the upstream
submodule URL:

    git -C Common/edk2 apply Platform/Realme/sm8150/patches/armmmulib-no-debug-in-mmu-off-path.patch

Without it a build with PcdDebugPrintErrorLevel = 0x800B05C7 dies at
ArmCpuDxe + 0x34B8 before reaching BDS.

## Where the rest went (split 2026-10-08)

The two hardware-verification topics that used to be the tail of this file now
live on their own: SWD-JTAG.md (EUD SWD 9504 / JTAG 9503 - the transport works,
the AP DAP is unreachable on this retail unit) and RX-CONSOLE.md (RX registers
0x0c/0x10/0x14, framing, the tty driver and the 0x14 wedge).  Everything above
stays here: device facts, registers, CTL/COM protocol, host tools, the firmware
log ring, the ArmMmuLib crash and the full-DEBUG story.
