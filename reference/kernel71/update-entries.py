from pathlib import Path
w=Path('/mnt/e/RealmeX2Pro edk2')
intro='''当前硬件接入：[session71](sessions/71-native-s3706-touch-bringup.md)。
已实现并部署GENI/GPI DMA/RMI4内建、本机触摸供电/DTS及可选reset GPIO；只刷
boot/logdump。新#61/taint0，54413字节完整dmesg校验通过，S3706A/fw3078696、
F01/F12/event2注册。真实输入事件验收见session71；其它硬件仍按清单推进。
Android/全部数据、TOP_CFG0x11/整帧/RX53/F1/两终端保留，无新EUD实验。
'''
p=w/'HANDOVER-NEXT.md';s=p.read_text();needle='Current kernel handoff: sessions/70'
assert s.count(needle)==1
block='''Current kernel handoff: sessions/71-native-s3706-touch-bringup.md,
reference/kernel71. Implemented native S3706 touch DTS/power/reset and built-in
GENI/GPI DMA/RMI4; one boot/logdump deployment. #61, new boot_id a31c1158-fbca-
4515-83ac-1a3b40ee808e, taint0, complete 54413-byte dmesg SHA/gzip CRC/lengths
verified. S3706A/fw3078696 and F01/F12/event2 bound. Physical event validation
is recorded in session71. Existing warnings retain session70 priorities;
Android/all data preserved, immutable EUD/init/core and rollback retained.
See linux-port/docs/HARDWARE-STATUS.md for the remaining functional groups.
No new EUD experiments or Windows driver/reset/timing/mask changes.

Previous kernel handoff: sessions/70'''
s=s.replace(needle,block);p.write_text(s)
for name in ('README.md','RX-CONSOLE.md','FLYWHEEL.md'):
 p=w/name;s=p.read_text();assert 'session71' not in s.split('\n',12)[0:12]
 pos=s.index('\n')+1;s=s[:pos]+'\n'+intro+'\n'+s[pos:];p.write_text(s)
for name in ('linux-port/README.md','linux-port/docs/00-INDEX.md'):
 p=w/name;s=p.read_text();pos=s.index('\n')+1
 entry=intro.replace('(sessions/71','(../sessions/71' if name.endswith('README.md') else '(../../sessions/71')
 s=s[:pos]+'\n'+entry+'\n硬件功能清单：[HARDWARE-STATUS]('+('docs/' if name.endswith('README.md') else '')+'HARDWARE-STATUS.md)。\n\n'+s[pos:];p.write_text(s)
p=w/'DOCS-INDEX.md';s=p.read_text();needle='| HANDOVER-NEXT.md |'
assert s.count(needle)==1
s=s.replace(needle,'| sessions/71-native-s3706-touch-bringup.md、reference/kernel71/ | 原生S3706触摸代码/供电/总线接入、boot/logdump部署、完整日志与输入事件校验 |\n| linux-port/docs/HARDWARE-STATUS.md | 按用户功能分组的14类硬件接入/验收状态与优先级 |\n'+needle);p.write_text(s)
p=w/'linux-port/docs/ROOTFS-PRESERVE-ANDROID.md';s=p.read_text();pos=s.index('\n')+1
s=s[:pos]+'''\nSession71只刷boot/logdump接入触摸，Android/全部userdata保留；没有安装rootfs。
新64MiB logdump镜像内Image30317056/DTB95933字节，FAT空闲36605952字节
（约34.91MiB），旧session70的36737024字节是其保留旧镜像容量，仍然有效。
两者均不足以证明完整、可持久更新的postmarketOS布局。\n\n'''+s[pos:];p.write_text(s)
print('Living entries and hardware/rootfs scope updated.')
