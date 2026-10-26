# RX41: SM8150 AHB2PHY wait state and native RX

The first repeatable native ABC/DEFG result was obtained by setting SM8150
SOUTH AHB2PHY TOP_CFG at **0x088ee010 to 0x11**, with readback verification.
The unchanged RX39 adjacent DAT-read loop then advances through the payload.
Only the low eight bits of each COM field are interpreted; upper lanes need
not be identical when the FIFO advances. This is board evidence, not a claim
about all Qualcomm SoCs or an undocumented COM flag handshake.

RX43 audited the unchanged raw files and corrected the earlier missing-output
claims: native id, echo and console responses are present. verify.py now checks
those responses as well. See [session 43](../../sessions/43-native-terminal-evidence-audit.md).

## Fixed primary sources

* [Stock RMX1931 DALSYSDxe](https://github.com/Project-Aloha/binaries_extracted/blob/adf853e45436bfcfd4274fa5d51b921c8b66e9f2/sm8150/realme/rmx1931/BOOT.XF.3.0-00501-SM8150LZB-1/QcomPkg/Drivers/DALSYSDxe/DALSYSDxe.efi):
  323584 bytes; Git blob `84bfffc312cb91fbfd99c36ed20f5050dfd9ef31`;
  SHA256 `32548b494ffc1f4f111d81928b440a911ca44c2b86fb84625254c5a20a667a88`.
* [DAL HWIO structure layout](https://github.com/tansuozhey/qcom-edk2/blob/main/QcomPkg/Drivers/HWIODxe/DalHWIO.h),
  verified blob `b69fba4dbe5543373018834019789cf8208bf272`:
  physical-region entries are 40 bytes, module entries 24 bytes on AArch64.
* [The matching Realme vendor dwc3-msm.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/usb/dwc3/dwc3-msm.c),
  blob `f89b2e0e9e974bd0269b2be76a346767e6bade0c`:
  TOP_CFG offset 0x10; ONE_READ_WRITE_WAIT 0x11. Its optional ahb2phy path
  reads the configuration, writes 0x11 if needed, and completes the write
  before PHY use. This alone was not proof that the present device needed it.
* Stock ClockDxe was also statically inspected; blob
  `4d30ac2443f9381e896be5799d081e6c19d61c94`, 294912 bytes,
  SHA256 `931a2fb597f33317e8b51f2259b8697ba9579c8d7ea806215b9c05998ebbca52`.
  No clock register was changed in this experiment.

## Minimal stock-map facts

DALSYSDxe has PE ImageBase zero; pointers were converted from RVAs through
the PE sections. Module offset plus length was checked against the region.

| File offset | Entry | Physical base / offset |
|---|---|---|
| 0x2c858 | AHB2PHY_SOUTH region, size 0x10000 | 0x088e0000 |
| 0x23b28 | SOUTH SWMAN module, size 0x400 | +0xe000 = 0x088ee000 |
| 0x23e10 | EUD_EUD module, size 0x2000 | +0 = 0x088e0000 |
| 0x2c240 | PERIPH_SS_AHB2PHY_NORTH region | 0x00ff0000 |

The currently used local DALSys.efi has a different blob
`6e7d8232689d8213e3683a5be9d6ebe1fb7d8652` but the same decoded map.
It was not replaced. Full stock binaries and full map output stay in the
external output directory, not this repository.

## UEFI hardware evidence

EudSnapshot reads TOP_CFG exactly twice before its first EUD TX and replays
the cached pair five times. Both reads were zero. No configuration write.
EudWaitProbe changes only TOP_CFG relative to the retained RX39 loop:
original zero, write 0x11, two matching readbacks, ABC/DEFG, restore zero and
verify it, then chainload the original Linux. Original Kernel and DTB were
compared byte for byte when each diagnostic logdump was packaged.

| Boot | Native ABC, low bytes | Native DEFG, low bytes | Config restore |
|---|---|---|---|
| wait-native | 41 42 43 | 44 45 46 47 | 0 verified |
| wait-native-repeat | 41 42 43 | 44 45 46 47 | 0 verified |

Each payload needed two host OUT attempts. The first capture has eight stray
bytes, the second zero; neither fact establishes lossless USB/TX delivery.
Only accepted complete result lines count as payload evidence. F1 reached
independently confirmed fastboot between boots. All serial owners close and
dispose in finally; see the session record for the premature, unsuccessful
second-open attempt, which sent no bytes.

Linux verification and final retained artifact are recorded in
[session 41](../../sessions/41-rx-ahb2phy-wait-state-fix.md).
