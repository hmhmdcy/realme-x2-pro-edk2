from pathlib import Path

w = Path('/mnt/e/RealmeX2Pro edk2')
session = '73-native-sofef03f-dsi-dsc-display.md'
state = '''SOFEF03F原生DSI/DSC面板已部署到#64，1080×2400@60自动接管msmdrmfb。
两次启动的彩条—白屏—彩条硬件CRC一致，每次三次关闭/开启与60次vblank等待通过。
亮度120/256/400写入成功；面板DCS电源状态0x9c。没有人工光学验收或亮度硬件读回。
最终boot_id=fc4fe164-1e90-402a-b841-ce870ba9ddfb、taint0，59284字节完整dmesg和
5492字节facts通过设备SHA/gzip CRC/长度；触摸、CPU、六UFS、NCM/SSH与EUD保留。
启动显示接管阶段记录10条SMMU fault，后续测试未复现，仍须修复；GPU/90Hz/休眠待验。
本轮一次boot和两次logdump部署，Android/全部数据保留。下一项显示交接与GPU/GMU。
'''
for name in ('README.md','RX-CONSOLE.md','FLYWHEEL.md','linux-port/README.md'):
    p=w/name
    text=p.read_text()
    start=text.index('当前硬件接入：')
    end=text.index('\n\n',start)
    prefix='../' if name.startswith('linux-port/') else ''
    text=text[:start]+f'当前硬件接入：[session73]({prefix}sessions/{session})。\n'+state.rstrip()+text[end:]
    if name=='README.md':
        text=text.replace('the built-in mass-storage kernel runs; a full distro needs a mainline DTB + rootfs',
            'native touch, 60 Hz DSC panel and USB NCM/SSH verified; GPU and other hardware pending')
    p.write_text(text)
p=w/'HANDOVER-NEXT.md'
text=p.read_text()
start=text.index('## 0. ')
end=text.index('## 2. ',start)
text=text[:start]+'''## 0. TL;DR - where the project stands (2026-10-10, session73)

'''+state+'''
原生显示驱动、binding、板级DT和内建依赖已实现。原厂live DT的51条初始化命令、
GPIO6/25/152/TE8、L14A1.8V/L17A3V、DSI L3C1.2V/PHY L5A0.88V逐项核对。
DSC PPS在真机生成后与原厂128字节比较通过。屏幕仍是诊断控制台，没有完整GUI/rootfs。
完整代码/构建/FFS与实际分区哈希、失败记录见sessions/73与reference/kernel73。
首版#63因REFGEN为模块及10秒defer时限失效，#64内建REFGEN并延长到60秒后自动绑定。
启动SMMU故障位于旧splash缓冲区，仅出现在首次接管时；不能据此称全日志无错误。

旧CPU/温度、触摸基本输入和自动密钥NCM/SSH保持。客户端/手机主机私钥均未入Git；
COM14回Windows/Shared/未Attached，无host连接owner。EUD原生命令与三次F1均有回执。
立即回退需成对恢复kernel73/boot-before.img和logdump-before.img（session72状态）；
当前boot-k73-display.img与logdump-k73-display-deps.img是已验的原生显示基线。
logdump仍只有约33.5MiB空闲，未确定安全的大持久rootfs位置。

## 1. What to do next, in order

直接交接见NEXT-SESSION.md，复制提示词见NEXT-SESSION-PROMPT.md。

1. 从169.254.42.1密钥SSH取得新boot_id/taint/完整日志。先查显示接管SMMU故障：
   旧splash地址0x9dxxxxxx、SID0x800/0xc20，停止旧DPU路径或保留映射需源码与真机验证。
   不套用其它DPU代际的CTL_FETCH_ACTIVE补丁或通过关闭IOMMU隐藏问题。
2. 接入本机Adreno640/GMU并验证真实渲染。vendor仅以ro,noload临时挂载获取本机固件，
   已卸载；固件在本地kernel73/gpu-firmware-stock.tar，哈希/ELF几何已归档，未入Git。
   GPU/GMU DT仍disabled；renderD128存在来自MSM注册，不证明GPU可用。
3. 随后电池/充电、无线/音频等。显示90Hz/休眠/光学输出、触摸精度和USB OTG/USB3
   仍需单独验收；当前60Hz模式成功不等于整个硬件组完成。

执行边界：保留Android/全部数据；部署仅boot/logdump；保留既有TOP_CFG0x11/整帧/
RX53/F1/两终端，串口/对应USB接口单owner并finally释放。实际源码在
/home/cy122/x2pro-linux/linux，initramfs在/home/cy122/x2pro-linux/initramfs。
不要运行旧build-image.sh覆盖真实init。DT变化必须更新实际UEFI固件，FAT-only不会
激活；源码/证据仅推fork/master。读分区先按PARTNAME核对，不能猜sde编号。

'''+text[end:]
text=text.replace('    master = 964362e  samurai: enable native S3706 touch and record hardware handover',
    '    master = bd23aaa  samurai: enable automatic USB NCM and public-key SSH\n'
    '             964362e  samurai: enable native S3706 touch and record hardware handover')
text=text.replace('    101 commits ahead of upstream origin/master','    102 commits ahead of upstream origin/master')
p.write_text(text)

(w/'NEXT-SESSION.md').write_text('''# 下一阶段交接：显示接管与GPU（2026-10-10，session73）

手机#64，boot_id=fc4fe164-1e90-402a-b841-ce870ba9ddfb、taint0。SOFEF03F原生
1080×2400@60 DSC已自动接管；两次启动各完成彩条—白屏—彩条硬件CRC、三次显示
关闭/开启及60次vblank等待（约0.99秒）。面板DCS状态0x9c，120/256/400亮度写入
通过；亮度硬件读回/实际光学图像没有验收，90Hz/休眠与GPU渲染也未验收。
最终59284字节dmesg、5492字节facts均按设备SHA/gzip CRC/长度通过。

显示接管时有10条SMMU context fault，地址在旧splash 0x9dxxxxxx、SID0x800/0xc20，
后续KMS/电源循环未再记录故障。先排查旧DPU/CTL路径与IOMMU映射切换。维护者2022
讨论的CTL_FETCH_ACTIVE方案对应较新DPU，不能不核对就套SM8150 DPU5。
原生驱动/DSC输出工作不等于启动交接已修好；完整失败/限制见sessions/73。

GPU/GMU DT仍disabled，renderD128不能当GPU成功证据。已从本机vendor只读ro,noload
复制a640_gmu.bin、a630_sqe.fw和a640_zap ELF/mdt/b00..02，随后卸载vendor。
本地E:\\edk2-samurai-out\\kernel73\\gpu-firmware-stock.tar（SHA83df98ec…），固件
未入Git；reference/kernel73/gpu-firmware-manifest.json有全部哈希/ELF header。
zap.elf是完整ELF32，LOAD offset0x3000、paddr0x5000、memsz1968、reloc标记；
须核对主线PIL/MDT loader和本机gpu_mem0x99515000+0x2000再打包，不猜其它板的固件。
GPU后推进电池/充电、无线/音频等14组功能；保留各项验收边界。

SSH用reference/kernel72/usb-ssh.ps1，169.254.42.1/16；SCP用scp-usb.ps1（-O）。
本地私钥/known_hosts在E:\\edk2-samurai-out\\kernel72，手机独有主机身份跨重启保留。
Windows系统UsbNcm自动APIPA，别改默认路由；真实SSH认证才代表服务就绪。
COM14最后Windows/Shared/未Attached，五个相关PnP节点OK，终端与USB owner均释放。
重启后原生命令K73_REBOOT_EUD_OK通过（两帧ACK，无重试），前三次F1回执也保留。

实际内核/home/cy122/x2pro-linux/linux，v7.3-rc6+a90ee430；实际initramfs在
/home/cy122/x2pro-linux/initramfs，保留EUD/USB hook/本地SSH身份，别覆盖为旧快照。
native代码增量linux-port/patches/0009、kernel73-builtins.config及dts源码；
面板binding dt-doc-validate/目标dtbs_check、checkpatch和两次Image构建通过。
CONFIG_REGULATOR_QCOM_REFGEN=y、defer60秒不可遗漏；显示时钟用SM8250共享驱动，
不存在SM_DISPCC_8150选项。#63手动reprobe仅用于定位；#64必须自动绑定。

已部署boot-k73-display.img（57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999）
和logdump-k73-display-deps.img（c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7）。
两者实际分区哈希见final-facts；旧cycled-facts的/dev/sde9是dsp，不能当logdump证据。
save-facts.sh已改按PARTNAME查找（本轮logdump=/dev/sde32，boot=/dev/sde11）。
立即回退成对刷kernel73/boot-before.img与logdump-before.img；不混用旧DTB/新Image。
一共一次boot、两次logdump写入；同镜像复测只reboot。Android/全部数据/GPT保留。
仅允许部署boot/logdump，只推fork/master，保留TOP_CFG0x11/整帧/RX53/F1/两终端。
''')
(w/'NEXT-SESSION-PROMPT.md').write_text('''继续无人硬件接入目标。先读NEXT-SESSION.md、sessions/73和reference/kernel73/README.md。
当前#64原生SOFEF03F 1080×2400@60 DSC/硬件CRC/两次启动各三次显示电源循环通过，
NCM SSH169.254.42.1、触摸/CPU/UFS/EUD保留，taint0。先用新完整日志排查首次接管
SMMU fault（旧splash0x9dxxxxxx，SID0x800/0xc20），再接入本机Adreno640/GMU并验证
真实渲染，随后电池/充电、无线/音频等。GPU仍disabled，renderD128不能当成功证据。
本机GPU固件只读提取保留在kernel73/gpu-firmware-stock.tar，manifest有哈希/ELF几何；
不发布专有blob。实际WSL Linux/initramfs保留，不运行旧build-image.sh。DSI REFGEN
内建/defer60秒保留，DT变更要进入实际UEFI固件；按PARTNAME核对分区，别猜sde号。
只写boot/logdump，保留Android/全部数据、TOP_CFG0x11/整帧/RX53/F1/两终端，owner
finally释放，只推fork/master。90Hz/休眠/光学图像、亮度硬件读回及其它硬件仍待验。
''')
p=w/'DOCS-INDEX.md'
text=p.read_text().replace('| sessions/72-usb-ncm-and-autonomous-ssh.md、reference/kernel72/ |',
    '| sessions/73-native-sofef03f-dsi-dsc-display.md、reference/kernel73/ | 原生SOFEF03F/DSI/DSC、60Hz/CRC/电源循环、固件依赖与启动SMMU交接限制 |\n'
    '| sessions/72-usb-ncm-and-autonomous-ssh.md、reference/kernel72/ |',1)
text=text.replace('session72结束状态、自动USB SSH通道、后续原生显示/GPU实作与短提示词',
    'session73当前原生显示状态、启动SMMU与GPU接入、自动USB SSH通道与短提示词')
p.write_text(text)
p=w/'linux-port/docs/HARDWARE-STATUS.md'
text=p.read_text()
start=text.index('按用户能使用的功能')
end=text.index('| 功能组',start)
text=text[:start]+'''按用户能使用的功能分组共14类。触摸基本输入、普通USB NCM/SSH/SCP与原生60Hz
DSI/DSC显示输出已经通过实际数据流验证；每组的精度、休眠或其它模式仍待验。
本轮#64/taint0、两次启动各三次显示电源循环和A—B—A硬件CRC通过；59284字节
完整日志与5492字节facts校验通过。启动显示交接仍有SMMU fault，GPU尚未启用。
详见sessions/73/reference/kernel73；此前触摸/USB功能证据见sessions/71、72。

'''+text[end:]
text=text.replace('（2026-10-10，session72）','（2026-10-10，session73）')
text=text.replace('| 原生显示面板 | UEFI遗留帧缓冲/simpledrm能显示 | SOFEF03F面板、电源、DSI/DSC、背光/亮度及刷新率 |',
    '| 原生显示面板 | SOFEF03F 1080×2400@60 DSC、DCS状态0x9c、硬件CRC、两启动各三次电源循环及亮度写入通过 | 首次接管SMMU fault、90Hz、亮度硬件读回/光学输出及休眠恢复 |')
text=text.replace('三路PMIC温度、simpledrm屏幕、EUD交互和F1。','三路PMIC温度、原生60Hz显示输出、EUD交互和F1。')
text=text.replace('触摸基本输入、普通USB NCM/自动SSH与文件传输已通过；接下来优先原生显示/GPU、',
    '触摸基本输入、普通USB NCM/自动SSH与文件传输、原生60Hz显示输出已通过；优先显示交接/GPU、')
p.write_text(text)
print('Updated living handovers; historical sections remain unchanged.')
