from pathlib import Path
w=Path('/mnt/e/RealmeX2Pro edk2')
p=w/'HANDOVER-NEXT.md';s=p.read_text()
start=s.index('6. While EUD is enabled');end=s.index('\n7. ',start)
s=s[:start]+'''6. F1 explicitly releases EUD before restarting to bootloader. This is verified
   on this handset. EUD being enumerated does not establish that ordinary Linux
   USB must be exclusive; the actual gadget/role path is still untested.
'''+s[end:]
start=s.index('## 7. ');end=s.index('## History index',start)
s=s[:start]+'''## 7. Open questions

* Which ordinary USB gadget function/configuration will provide reliable
  network/SSH on this Windows host, and how will actual USB/EUD role signaling
  behave? UDC exists; configured functions and real traffic are missing.
* Does the new touch input retain correct physical contact count, orientation,
  edge accuracy and suspend/resume behavior? Basic recorded input now works.
* What board-native panel/DSI/DSC, GPU firmware and power descriptions are
  needed to replace the inherited framebuffer with accelerated native display?
* How can a full persistent rootfs be provided while preserving Android and all
  data? The current logdump FAT only has about34.91MiB free; userdata FBE/ICE
  access and a safe large layout have not been established.
* CPU high-frequency load, battery/charging and the remaining functional groups
  still need board-specific implementation and acceptance; see HARDWARE-STATUS.

The EUD console reaches Linux userspace and F1 returns to independently
enumerated fastboot. Native RX advancement and RX53 console/IRQ are verified;
intermittent TX loss remains documented in session65. The deferred EUD/Windows
driver work is background evidence, not the next hardware implementation task.
Historical SWD/JTAG evidence and its unresolved AP DAP response stay in SWD-JTAG.md.

---

'''+s[end:];p.write_text(s)
replacements={
 'README.md':[('Current kernel audit: [session70]','Previous kernel audit: [session70]'),
 ('Latest kernel fix: [session68]','Previous kernel fix: [session68]')],
 'linux-port/README.md':[('当前只读诊断：[session70]','前次只读诊断：[session70]')],
 'RX-CONSOLE.md':[('当前日志入口：[session70]','前次日志入口：[session70]')],
 'FLYWHEEL.md':[('最新只读日志/供电/触摸前提审查看 [session70]','前次只读日志/供电/触摸前提审查看 [session70]')]
}
for name,changes in replacements.items():
 p=w/name;s=p.read_text()
 for old,new in changes:
  assert old in s,old;s=s.replace(old,new)
 p.write_text(s)
print('Stale current labels and USB exclusivity claim corrected; open questions now match hardware goal.')
