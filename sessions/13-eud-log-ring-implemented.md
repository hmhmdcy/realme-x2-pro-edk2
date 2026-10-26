---
<!-- from HANDOVER-NEXT.md, section 13 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 13. EUD log ring buffer implemented (2026-10-07 02:0x)

The main task from section 12 (fix 2) is DONE in code and builds clean.  It is
NOT flashed yet.

New image (built, not flashed):
    E:\edk2-samurai-out\boot-samurai-eudlog.img
    sha256 d2fce824f9e3ac0495b85c4775f5448a917ebec4e8deeb8150d9ab55de46ae72
    (plus SM8150_UEFI-samurai-eudlog.fd)

Changed in ~/edk2-samurai/repo (all uncommitted):

    Platform/Realme/sm8150/Library/EudSerialPortLib/EudLog.h            new
    Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c  rewritten: producer only, no MMIO, no delays
    Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf  SynchronizationLib in, IoLib/TimerLib out
    Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c                        new (single drainer)
    Platform/Realme/sm8150/EudLogDxe/EudLogDxe.inf                      new
    Platform/Realme/sm8150/samurai.dsc                                  [Components.common] entry
    Platform/Realme/sm8150/samurai.fdf.inc                              INF entry
    Silicon/Qualcomm/sm8150/Library/PlatformMemoryMapLib/PlatformMemoryMapLib.c
                                "RSRV2" renamed to "EUD Log" (address and size unchanged)
    Platform/Realme/sm8150/EUD.md                                       new section

Why the section 12 design had to change: EudSerialPortLib is linked into 162 of
the 177 built modules (verified from the .map files), so a library-static ring
buffer would exist 162 times and no single drainer could see all of them.  The
ring is therefore at a fixed address shared by every copy.

Why RSRV2 and not Log Buffer: realme own uefiplat.cfg (in
uefifw/realme-rmx1931/Binaries/RawFiles) contains no RSRV1/2/3 at all; the vendor
map simply leaves 0x9FFD0000 up to 0x9FFF7000 empty and the port filled that hole
with reference names from other SoCs.  "Log Buffer" by contrast is a real vendor
region (RtData, and the stock XBL references it), so overwriting it would destroy
the vendor boot log.

Build verification (no hardware involved):
  * EudSerialPortLib.obj undefined symbols: InterlockedCompareExchange32 and
    MemoryFence only; zero references to 0x088E0000 (the blocking path is gone).
  * EudLogDxe disassembly contains both movk #0x9ffe (ring) and #0x88e0000 (EUD).
  * FVMAIN.Fv: "RSRV2" 0 occurrences, "EUD Log" 1, 0x9FFE3000 1, EudLogDxe FFS
    file present (GUID 2E6C5B41-9A73-4C0E-8B27-1F5D3A6E9C04).

Still to do next session:
  1. flash and verify on hardware: look for the "[EUD-LOG] host COM attach seen"
     line, then the full DEBUG stream, and check the Drops counter.
  2. measure the replay rate and tune (see the follow-ups in EUD.md).
  3. optional fix 1 (firmware side COM enable) is still not done; it would remove
     the dependence on the CTL_OUT gate.
---
