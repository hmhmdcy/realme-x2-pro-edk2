from pathlib import Path
import json,re
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126'
tpg=json.loads((ref/'tpg-runtime-validation.json').read_text());health=json.loads((ref/'final-health-validation.json').read_text());cleanup=json.loads((ref/'obsolete-object-cleanup-validation.json').read_text())
assert tpg['actual_native_kernel126_tpg_pass'] and health['final_health_pass'] and cleanup['recoverable_private_archives_verified']
session='sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md'
summary='阶段126已实际刷入#126及内嵌CAMSS设备树，live DT全节点/已有属性、boot/logdump/persist/GPT18/11来源/770模块验证通过。内部CSID0→VFE0 TPG三帧真实DMA通过：3个地址在原厂窗口、每帧96000字节覆盖预填充、raw10非恒定横向图案、IRQ和电源恢复核对；物理camera仍未验收。最终桌面进程/无线/音频恢复、taint0，50秒窗口无新增故障；启动仍DPU1、最终CRTC inactive，不能算显示长稳通过。完整126 rootfs已打包，但发现home UID1000与passwd10000不一致，127修正进行中，126 rootfs暂不应全量部署。清理3个obsolete构建的15189个生成ELF文件，实际分配2.49GiB，全部归档回读后删除，稳定镜像与源码保持。goal active。'
path=r/session;t=path.read_text();t+='''
## 已完成嵌入DT刷入与真实TPG

canonical固件审计通过，除DTB FFS外其他UEFI可执行模块/bootshim/兼容DTB保持；原源码/blob/FD/FV/boot逐字节恢复。第二次当前126 fresh preflash与排空/trace保留关闭/sync/fsfreeze/F1单次回执通过，只更新boot，logdump保持。boot SHA256 d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8；logdump5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2。新boot不同、live DT节点集合及每个预期属性精确匹配126 DTB，CAMSS自动绑定，22个media实体、8个video/14个subdev节点。

真实TPG3帧320×240/stride400/size96000，序列0/1/2、时间戳递增，三个不同预填充全部96000有效字节被覆盖，FNV64同为af89995da687f925，首帧SHA25658109bf2b6a4791284bc6299d99d1ed5011b3cc15516e580a31bad64233d0460。三个IOVA dffa0000/dffc0000/dffe0000及完整96000-byte plane均在原厂窗口内；bufinit和bufprepare两次核验共6条trace。VFE0 IRQ+8、CSID0+1，PHY/VFE1/CSID1 IRQ无变化；三个CAMSS domain前后suspended/user0，两路IFE off。STREAMOFF、REQBUFS0、图/format/control恢复调用均成功，dma_trace关闭、taint0，capture期间无新fault，SLPI和物理sensor供电保持关闭。

按照[官方packed Bayer布局](https://docs.kernel.org/userspace-api/media/v4l/pixfmt-srggb10p.html)解码76800样本，0/1020各38400，非恒定横向条纹、全部240行重复两行图案。不能仅凭覆盖预填充当成正常图像，已排除all-zero/恒定内容；Bayer颜色分量次序及完整10bit动态范围未证明。CPAS成功路径通过100/101版本守卫和十项QoS读回，接受此版本族属于从实际成功路径推断，精确revision未单独记入硬件日志。此结果不代表外部PHY/sensor/物理摄像头可用。

最终同boot的6次10秒间隔采样50.19秒：Phosh/Phoc保持、wlan up、MPSS/ADSP运行、hci0存在，PCM closed/双amp off/muted/failed0，zram证据已采。NV6/source4/vendor1及770模块、boot/logdump/persist保持；trace完整私有保存后关闭。采样期间0新增DPU/GPU/SMMU/WARN/BUG/Oops，整个boot仍DPU1/GPU0，最终CRTC active0。因此只能认定有限窗口恢复和内部数据通路，不认定持续绘制或休眠长稳。Bluetooth sysfs没有name属性的采集错误已改为hci0目录/uevent核验，并同boot续采；没有伪造缺失属性。

## rootfs语义检查与清理

126镜像完整导出内容/metadata无差异，但语义审计发现账户UID/GID10000，home及145条目仍1000；实机相同路径为10000/10000，当前桌面没有该问题。系统20978条目root-owned，所有usr特权文件root-owned，问题限定用户home。126 rootfs镜像保留为诊断/重现，暂不全量刷入；127副本只修正这145条目的属主并保持内容/mode/xattr，验证真实降权创建/读写/删除从EACCES变为成功，随后重建完整镜像。系统目标尚未完成。

按用户要求清理obsolete110/112/114生成ELF对象。逐一核对旧Image/DTB/cpio与E导出，排除tracked/symlink，只选有Kbuild .cmd证明、Git ignored的生成ELF；归档全部候选并逐成员SHA回读，再逐file当前hash核对后删除。共4072+5552+5565=15189文件，allocated2677497856 bytes，3个可恢复私有gzip archive总800763433 bytes。tracked diff/源码/.config/Module.symvers/Image/DTB/cpio/.ko保持；稳定109/111/113/115的Image hash未变，118卷和115/118回退套件保留。WSL根实际free增加2677428224 bytes，宿主C最终约16.06GB free；未resize/compact VHD，不把guest释放量等同hostfree增长。其它工作目录如MediaCrawler/telegram/angr不属于此任务，未动。

127首个WSL启动请求曾返回WSAETIMEDOUT；检查WSL已停止，E126无loop，readonly e2fsck=0，随后检查rootfs127尚不存在，故修正尚未执行，没有半成品副本。重新启动后使用cp -a保留设备节点/hardlinks/ownership，不用普通copyfile复制/dev/null。后续必须等待terminal再运行依赖脚本。
''';path.write_text(t)
for name in ['README.md','FLYWHEEL.md']:
 p=r/name;t=p.read_text();t=t.replace('[阶段125]',f'[阶段126]({session})，[阶段125]',1);t=t.replace('\n阶段125完成','\n'+summary+'\n\n阶段125完成',1);p.write_text(t)
p=r/'DOCS-INDEX.md';t=p.read_text();t=t.replace('\n',f'\n\n- [阶段126：内部TPG实机DMA、嵌入DT修正和完整rootfs语义检查]({session})：已刷入126、3帧数据/IRQ/power验收；rootfs home权限待127修正，保留稳定回退。\n',1);p.write_text(t)
p=r/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('阶段125）','阶段126）',1);a=t.index('\n\n')+2;b=t.index('\n\n',a);t=t[:a]+'15组硬件保持。 '+summary+t[b:]
row='| 摄像头 | #126已刷入匹配内嵌DT/Image/770模块，CSID0→VFE0内部TPG3帧真实DMA/IOVA窗口/IRQ/非恒定raw10内容/电源恢复通过；C-PHY与共享L3原厂配置保留 | 外部PHY/sensor/PM8008四输入与enable、HAL settle及物理stream、颜色次序/10bit范围/多模式及用户态应用仍待办 |'
t,n=re.subn(r'^\| 摄像头 \|.*$',row,t,flags=re.M);assert n==1;t+='\n阶段126：当前运行内嵌126 DTB的#126，最新boot有限窗口taint0/DPU1/GPU0，但旧GPU像素失败和最终CRTC inactive不能因未重跑测试判为修复。126完整rootfs home属主缺口由127继续，未擦除userdata。\n';p.write_text(t)
(r/'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro 继续检查点（阶段126，2026-10-12）

{summary}

先读[阶段126]({session})、[硬件15组](linux-port/docs/HARDWARE-STATUS.md)。用户授权静态补丁检查后实际刷入与日志核验，无人值守、无人工观察；长难项留档换项。清理已验证obsolete构建，保留稳定版本。

## 当前真实设备和产物

手机运行#126、release 7.3.0-rc6-rmx1931-samurai-k126+，boot内嵌126 DTB已生效；flash先只logdump，再纠正嵌入DT只boot。最新post-firmware boot私有身份在E:/edk2-samurai-out/kernel126/embedded-boot-id-private.txt及phone /var/lib/samurai/k126-embedded-runtime/boot-id-private.txt。旧current/source boot-id均属于先前启动，不能用于当前重启。115/118回退完整保留，旧118模块仍在。

当前boot分区hash d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8，logdump5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2；FAT DTB不能决定内嵌UEFI设备树。以后任何DT改动必须canonical UEFI audit/源码恢复和live DT逐节点属性核验。

阶段126完整4件包已验证匹配，但rootfs账户10000/home1000是新发现的语义缺陷，126 rootfs暂不全量部署。127代码在reference/kernel127，副本rootfs127在E126 ext4卷/home/cy122/pmos-samurai-build126，优先完成145项ownership修正、实际降权读写和F2FS双fsck/逐块稀疏/全量反向content+metadata/encoded passwd-home一致性。镜像复制用cp -a，保留/dev/null等类型/hardlinks。

## 执行纪律与下一项

所有WSL ensure helper用-u root，同卷mount/unmount串行flock，不在上一步仍有session_id时启动依赖操作。126新卷有24GiB；118/122/126都放E，C旧VHD不resize。127第一次WSL请求超时未实际创建副本，readonly fsck=0；不要凭超时盲重跑一次性脚本，先检查目标是否存在与report。

126 prepare/build/stage/preflash/quiesce/freezeroot/F1/flash脚本均已执行，是历史一次性工具，当前不能重放。新刷入需要最新boot身份、当前分区备份、完整GUI/DRM/audio/radio排空、trace保留关闭、11来源核验、sync+fsfreeze回执，单次9002 F1后独立fastboot身份/geometry，失败先捕获状态不盲reset。

TPG证明内部数据通路，不解决物理sensor/PM8008四输入/全芯片enable/HAL settle。完成127软件镜像后优先推进一项有自动真实验收的缺失功能；5GHz Wi-Fi、充电ADC事件或有界sensor电源线索均可，长难错先留档再换项。旧GPU故障/显示持续绘制、GNSS fix、指纹、休眠等仍开放。所有手机dump/IDs/固件/密钥/镜像留E:/edk2-samurai-out私有目录，公共仅代码/统计/hash。goal active，不标完整可用。
''')
print('K126_REAL_TPG_DEPLOYMENT_CLEANUP_CHECKPOINT_WRITTEN_ROOTFS127_NEXT')
