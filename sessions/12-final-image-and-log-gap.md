---
<!-- from HANDOVER-NEXT.md, section 12 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 12. Final image verified, why boot logs are still missed, and the two fixes (2026-10-07 01:0x)

### Verification of the final image

* Image: boot-samurai-eudcom.img
  sha256 A8891194EE35023CB6BDAE7F22C2ABEF983735F841262D8EA574AF507187E44C
  flashed via fastboot, booted to the UEFI boot menu: display, UFS, all three
  side buttons normal.
* EUD control channel while running the final image:
      0x01 -> 00 00 05 00
      0x02 -> A1 28 BC 62
      0x03 -> 04 00 00 00
* EUD COM: "Qualcomm EUD Port 9505 (COM14)" Status OK.
* comlog.exe COM14 60 -> 0 bytes captured.

### Why 0 bytes (a timing gap, not a bug)

    firmware: BDS enables EUD, then immediately emits the single marker line
    host:     sees the 9501 only after the EUD hub enumerates, then runs
              eudtool com-up, which is what sets COM_PERIPH_EN + VBUS_ATTACH,
              so COM14 appears about 1-2 s later

The marker is written before the COM channel exists and is dropped; the BDS
boot menu is idle afterwards, so nothing else arrives.  The earlier 30-second
test loop was captured precisely because it was still sending while the host
brought the port up.

### Consequence for the log channel design

Every DEBUG line emitted before the host runs com-up is lost - that includes
all of PEI/DXE and the start of BDS, i.e. the most interesting boot logs.
Two complementary fixes:

1. Firmware enables the COM peripheral itself (small, nice-to-have)

   In the BDS EUD block, after CSR_EUD_EN, also write the CTL_OUT bits
   directly instead of waiting for the host:
       CTL_OUT_1 register = 0x088E0074
       set bit5  (COM_PERIPH_EN) and bit12 (VBUS_ATTACH)
   Those are the same bits eudtool com-up sets through the CTL USB channel.
   The EUD COM device then exists before the first log line and the host only
   has to open the port.  Verify the write semantics on hardware (the register
   behaves like a set/clear register; the host uses CTLOUT_SET/CLR commands).
   This alone does not help if the host is slow to open the port - which is
   what fix 2 solves.

2. Non-blocking SerialPortLib with a ring buffer (the real fix)

   * SerialPortWrite() only appends bytes to a RAM ring buffer: no MMIO, no
     delays, no gBS dependency; count the dropped bytes when the buffer is full;
   * a periodic event (or the BDS wait callback / a platform timer) drains the
     ring buffer into the EUD COM TX FIFO in 6-byte frames with the known-good
     timing (200 us per byte, 2 ms per frame);
   * the drain only runs once CSR_EUD_EN is set, and - with fix 1 - once the
     firmware has enabled COM;
   * expose the drop counter (an on-screen line or a CTL scratch register).

   With both fixes in place, DEBUG from DXE onwards is buffered and replayed as
   soon as the host is ready, which also removes the need for the
   PcdDebugPrintErrorLevel workaround and its crash risk (section 5, pitfall 3).

### Suggested order for the next session

1. Final image is flashed and verified (this section) - nothing to redo.
2. Implement fix 2 (ring buffer + drain) in EudSerialPortLib; that is the main
   remaining task and it unblocks full DEBUG logging.
3. Optional: fix 1 (firmware-side COM enable) to shorten the gap further.
4. Re-test with comlog.exe and PcdDebugPrintErrorLevel set to 0x800B05C7,
   keeping the SerialPortLib scoping unchanged (never DXE_CORE).
---
