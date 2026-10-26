from pathlib import Path
import json,re,tarfile,hashlib
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel115'
out=Path('/mnt/e/edk2-samurai-out/kernel115')
with tarfile.open(out/'boot-traces-private.tar.gz') as tf:
    traces={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for row in traces['SHA256SUMS'].decode().splitlines():
    digest,name=row.split('  ',1)
    assert hashlib.sha256(traces[name.removeprefix('./')]).hexdigest()==digest
assert traces['taint.txt'].strip()==b'0'
assert traces['display-before.txt'].strip()==b'1' and traces['radio-before.txt'].strip()==b'1'
report=dict(kernel_build=115,boot_traces_preserved_then_stopped=True,taint_after=0,goal_complete=False)
(ref/'trace-stop-validation.json').write_text(json.dumps(report,indent=2)+'\n')
link='sessions/115-own-ipa-modem-and-zram-rootfs.md'
intro='''2026-10-12，完整系统目标仍 active，继续无人值守自动化适配。当前已部署 #115，USB SSH/F2FS rw、Wi-Fi 自动连接、IPA 初始化、ModemManager 检出 qcom-soc modem、zram 自动启动通过；taint 0。ModemManager 为 sim-missing，移动数据/通话未验收。首个 #115 启动有桌面，随后两次启动出现 RCU stall 和 DPU CTL reset -22，当前无 DRM/Phosh/Phoc。不能把无帧超时/GPU fault 当作显示正常。

本机专用 rootfs 已更新到 #115 完整 764 个模块、936 个签名包、同机 IPA 固件和服务修复。修正 IPA TX delay 后的 sparse 镜像为 1,817,970,276 字节，逐块展开比对及源/重建两次 fsck 通过；尚未刷入，手机采用增量安装保持 userdata。SLPI offline/供电 0、空闲 PCM closed/双功放静音、NV6/source4/persist 保持。启动 trace 已保存后停止。长时间无进展问题保留证据后转项，不要求画面、触摸、听音或转动检查。
'''
for name in ['README.md','FLYWHEEL.md']:
    p=root/name;t=p.read_text();start=t.index('[阶段114]');end=t.index('\nUnofficial EDK2',start) if name=='README.md' else t.index('\n> 2026-10-08',start)
    replacement=f'[阶段115]({link})，[继续检查点](NEXT-SESSION.md)。\n\n'+intro
    if name=='FLYWHEEL.md': replacement+='\nF1 前必须使用当前 boot 的 GUI/音频/功放/ADSP/无线/MPSS 排空、NV 核验、sync 与 fsfreeze 回执。阶段115首次刷入仅更新匹配的 boot+logdump；之后正常重启和 F1→fastboot reboot 恢复均没有再刷分区。旧阶段113/114守卫不可重放，新的尝试必须取得当前启动身份。不要用 erase userdata 的旧全量刷机脚本进行日常更新。\n'
    p.write_text(t[:start]+replacement+t[end:])
next_text='''# 继续检查点：阶段115（2026-10-12）

完整系统 goal active。继续无人值守自动化适配，不要求人工画面、触摸、遮挡、转动或听音检查；长时间未解决项更新文档后转项。

先读[阶段115](sessions/115-own-ipa-modem-and-zram-rootfs.md)、[15组状态](linux-port/docs/HARDWARE-STATUS.md)及 reference/kernel115/final-health-validation.json、trace-stop-validation.json、rootfs-fixed-image-validation.json。

当前手机是第三次 #115 启动，taint 0、USB SSH/F2FS rw、Wi-Fi 自动连接、IPA/rmnet_ipa0、ModemManager qcom-soc/QRTR+net、zram lzo-rle 已运行。ModemManager failed/sim-missing，无实际移动数据/通话。首个 #115 启动 Phosh/Phoc 存在，但 IPA 有两次 reg.h WARN；修正模块后两次启动都无 IPA WARN，却有 RCU stall 和 DPU 启动 CTL reset -22，无 /dev/dri，greetd crashed、Phosh/Phoc 不存在。后两次 display 0 次帧超时/GPU fault 不代表验收。不要重复同镜像重启当作修复。

SLPI offline、sensor-power vdd/vddio 0，原 selector 00121 不变；PCM closed、双功放 powered0/muted1；NV6/source4/persist 保持。display/radio 启动 trace 原来自动开启，现已在当前启动保存后关闭，不清除原证据。最终完整 native dmesg、启动身份、modem JSON 和 trace 私有；EUD 跨 NCM re-enumeration 早期 capture 不完整，不能代替 native 审计。

rootfs：E:/edk2-samurai-out/kernel115/samurai-rootfs-f2fs-delay-fixed.simg，1,817,970,276 字节，展开 119,033,245,696 字节，SHA256 d8fc01cea0187b5f1174a910dc01f4f566714716a78debf6061af37d1dd3f1f4。936包、764个完整 #115 模块、同机 IPA MDT/split 固件、elogind PID adoption、zram provide swap 冲突修复和 deviceinfo lzo-rle；源/重建 fsck、逐块展开验证通过。未刷入，不要覆盖当前 userdata 只为部署应用。阶段114基线及阶段115原 WARN 镜像保留私有。

隔离源码 /home/cy122/pmos-samurai-kernel115/{kernel,initramfs}。Image 已完整构建/部署；IPA TX delay 修正仅更新 ipa.ko，Image 不变。实际 stripped module SHA256 bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0。完整模块包初版仍包含修正前 IPA，后续打包必须使用修正后的 runtime/rootfs 树，不得回装初版。IPA_REG = own ipa-base 0x1e00000 + HAL offset 0x40000；IMEM 0x146bd000，GSI size 0x28000。loader self/PAS15 使用只读 vendor 提取的本机 IPA 固件。参考100MHz/ICC仍是 provisional，数据压力/SSR恢复未验收；GSI1000ms timeout尚未向所有void调用方传播错误。

显示下一步：dpu_hw_ctl_clear_boot_config 的首次 CTL_SW_RESET 轮询失败返回 EINVAL，在 INTF1 停止之后、清空 blend/outputs 之前失败。保留 IOMMU 接管前 quiescence guard，不可忽略 -22/删除 stalled mask 检查。检查为何 pending command frame 无法完成 reset；慢 EUD console/RCU starvation 是待验证假设，不是已证明根因。可在隔离下一候选中加阶段/寄存器日志或优化真实等待，不能再盲目重启。

摄像头转项：本机19781下13份摄像头 DTS 已做 hash/字段清单，当前 mainline 无 qcom,sm8150-camss match/共享节点。网络发现 Hotdog 仓库有 SM8150 CAMSS port（0055/0064等、C-PHY0089、stream unwind0114），已固定参考 commit 47087509c4289c2580c54f5433e55366b2e00445。先获取、核对并适配 SoC 支持；本机传感器/电源/CCI/时钟从自己的 DTS/stock 模组确认。不能复制 Hotdog 板级 pinmux、IMX586 身份或直接运行外国固件。

正常 reboot/F1 都需要当前启动守卫，先排空 GUI/用户音频/功放/ADSP/无线/MPSS、NV 核验、sync。F1必须当前 fsfreeze 成功；失败则不要强制reset。阶段115 boot/logdump是当前匹配套件，阶段113旧套件作为完整回退保留；回退也要重新取得当前身份与清理证据。UEFI构建后已恢复并字节核验baseline109原源码/blob/FD/FV/boot，不能凭FAT-onlyDTB认为固件更新。

没有 GPT/NV/persist 写入，没有 erase，没有发送消息/呼叫。所有身份、凭据、固件、原始 GNSS/无线/用户态日志和镜像保持私有。Windows静态USB IP操作因管理员权限被拒，脚本已修正不能虚报成功；当前APIPA/16可达SSH。不要请求睡眠用户操作或修改安全设置。文档只本地保存，不调用会推送的旧 sync-docs-to-repo.sh。
'''
(root/'NEXT-SESSION.md').write_text(next_text)
p=root/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text();a=t.index('| 功能组');b=t.index('\n已有基础能力',a);table=t[a:b]
changes={
'原生显示面板':('首个#115启动桌面存在；随后两次启动CTL reset -22，无DRM/Phosh/Phoc；RCU stall保留','修复命令帧/CTL reset接管，保留IOMMU前quiescence；休眠/长稳未验收'),
'GPU':('历史FD640硬件GLES2/故障保留；当前DPU bind失败未启动GPU桌面，0 fault不能算通过','先恢复DRM，然后GPU/压缩帧缓冲/应用压力/休眠/長稳'),
'普通USB与OTG':('当前#115 NCM/SSH/SCP可达；两次慢启动恢复SSH，F1 freeze/回执/fastboot reboot通过','RCU慢启动原因、OTG/USB3/休眠/长稳'),
'Wi-Fi':('当前#115 2.4GHz NetworkManager自动连接/up，早期认证重试后成功；历史HTTP/HTTPS保留','5GHz有界失败待修；冷启动/休眠/长稳'),
'蓝牙':('历史扫描通过；当前#115 UART启动phase2/phase5错误后retry setup完成','UART初始化错误/稳定性；不要求配对连接'),
'音频':('本机UCM/扬声器/DMIC0历史电气验收保留；当前ADSP/card0运行，PCM closed双功放静音','桌面恢复后自动音频回归；实际声音质量/耳机/DSM/校准/休眠未验收'),
'蜂窝网络/数据':('本机IPA v4.1/固件初始化和rmnet_ipa0通过，TX delay修正后0 WARN；MM检出qcom-soc/QRTR+net、sim-missing；NV6/source4保持','移动数据/通话未验收，100MHz/ICC参考值待压力验证；SSR/冷启动/休眠/长稳'),
'摄像头':('本机13份DTS已索引；当前无mainline SM8150 CAMSS；已找到固定版本Hotdog SoC port参考','适配SM8150 CAMSS/CCI，再核对本机模组、电源、ISP/图像数据流；物理未验收')}
rows=[]
for line in table.splitlines():
    if line.startswith('| '):
        key=line.split('|')[1].strip()
        if key in changes: line='| '+key+' | '+changes[key][0]+' | '+changes[key][1]+' |'
    rows.append(line)
tail=t[b:];pos=tail.index('下一项完成隔离#114');tail=tail[:pos]+'''下一项先记录并有界定位#115启动CTL reset/RCU回归，再转SM8150 CAMSS及本机摄像头资源核对。完整传感器、GNSS真实fix、充电、指纹、休眠等仍开放。每步区分构建、部署、限定功能验收；不用删除warning代替硬件接入。userdata增量保持，GPT/NV/persist及离线来源保持。
'''
p.write_text('# RMX1931 Linux 硬件接入清单（2026-10-12，阶段115）\n\n15组硬件保持。\n\n[阶段115](../../'+link+')，[继续检查点](../../NEXT-SESSION.md)。\n\n'+intro+'\n'+'\n'.join(rows)+'\n'+tail)
p=root/'DOCS-INDEX.md';t=p.read_text().replace('当前：[阶段114](sessions/114-complete-rootfs-and-qmi-ipa-foundation.md)','当前：[阶段115]('+link+')',1)
t=t.replace('> 本文件两边内容一致；改完文档跑一次 sync-docs-to-repo.sh 就会推上去。','> 当前任务只本地保存；旧 sync-docs-to-repo.sh 会推送，未经用户明确授权不要运行。',1)
t=t.replace('| 文件 | 内容 |\n|---|---|','| 文件 | 内容 |\n|---|---|\n| '+link+'、reference/kernel115/ | 本机IPA/固件与ModemManager、完整115 rootfs/zram服务、TX delay修正、RCU/CTL reset显示启动回归与当前边界 |',1)
p.write_text(t)
session='''# 阶段115：本机IPA、ModemManager与完整zram rootfs

2026-10-12。完整系统 goal active；无人值守调试，不要求人工检查。

'''+intro+'''
## 本机IPA资源、固件和部署

本机 Android R 19781/qcom SM8150 DTS 与 IPA HAL 形成一致地址证据：0x1e00000 基址加 HAL 0x40000，主线ipa-reg实际0x1e40000；GSI0x1e04000/0x28000，IMEM0x146bd000。Hotdog数据使用的估计IMEM0x146a8000已替换。自己的PAS15/PIL自加载与0x99500000/0x10000预留，MDT可加载段满足边界。vendor分区只读/noload提取本机IPA split firmware，整分区前后hash/NV6一致；modem分区未找到IPA文件的失败先保存后转vendor。100MHz核心及ICC参考配置仍 provisional，不因probe通过而验收数据带宽。

隔离 #115 Image/764模块/DTB 全量构建通过；实机完整模块树/同机固件增量安装，旧 bespoke /lib/modules/samurai 保留。部署前GPT18/NV6/source4/persist、实际#113 boot/logdump和回退镜像核验；排空GUI/音频/功放/ADSP/无线/MPSS、sync、F2FS freeze后F1 exact receipt，再核验fastboot产品和分区大小，仅刷匹配boot+logdump。userdata未擦除。UEFI构建后baseline109源码/blob/FD/FV/boot均字节恢复。

首次#115 IPA初始化成功、rmnet_ipa0出现，modem/adsp运行，但有两次reg.h:87 WARN/taint512。原因是导入4.1寄存器表缺 END P INIT CTRL（源码名ENDP_INIT_CTRL），而主线<4.2发送端会设置delay；本机HAL定义继承4.0 offset0x800/stride0x70，ENDP_DELAY bit1。补入该字段和表项，targeted模块构建/strip/depmod，实际ipa.ko SHA256 bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0；两次后续启动IPA成功，0寄存器WARN、taint0。Image不变。GSI commit_wait已加1000ms有界等待并保留completion引用，void调用方完整错误传播仍待办。

ModemManager曾与D-Bus自动启动争用；有界foreground诊断保留后恢复自动实例。最终qcom-soc plugin识别qrtr0(qmi)+rmnet_ipa0(net)，modem0为failed/sim-missing。Calls/Chatty等已安装；没有发出呼叫/短信，没有尝试移动数据连接，不能因modem出现认定通信完整。

## rootfs和服务

完整115固定镜像：E:/edk2-samurai-out/kernel115/samurai-rootfs-f2fs-delay-fixed.simg；1,817,970,276字节，展开119,033,245,696字节，SHA256 d8fc01cea0187b5f1174a910dc01f4f566714716a78debf6061af37d1dd3f1f4。936个签名包包含Calls/Chatty/Firefox/mobile-config/Megapixels/libcamera/QMI/诊断工具；764个115模块、同机IPA MDT/split固件、原Phosh/UCM和身份。源raw及稀疏重建fsck两次通过、block/hole逐块比对通过。没有全量刷入；包含身份/凭据/固件的镜像保持私有。

elogind已有D-Bus daemon但OpenRC failed：改为先核验PID存活+exe路径并adopt，再用默认start-stop-daemon；reload验证通过。去除zram脚本provide swap与OpenRC真实swap冲突，deviceinfo设置lzo-rle以匹配内核支持算法。两次115自动启动zram、10,900,996,096虚拟字节/priority300；虚拟大小不等于实际分配RAM。hwclock无RTC及iio-sensor-proxy缺SSC仍失败，没有抹去。

## 显示启动回归和自动恢复边界

首次115桌面Phosh/Phoc存在，DPU后续仍有超时。修正IPA模块后的正常reboot：F2FS72秒、RCU93秒、DPU CTL reset -22导致DRM/Phosh失败；SSH约180秒恢复。保存完整日志后用同次排空/freeze/F1、verified fastboot reboot重新启动同一镜像，未刷任何分区。第三次115也有RCU stall，INTF1停掉TE/autorefresh后，boot CTL0(top0x20000/layers0x100002d/intf0x2/dsc0x3)首次SW_RESET失败返回-22。当前USB SSH正常，taint0、Wi-Fi、IPA、MM、zram通过，但无/dev/dri、Phosh/Phoc缺失、greetd crashed。不继续无变化重复重启；不把0 GPU fault/0帧超时当验收。

原生final-health归档SHA256 7f1185f968c3a520227ce0336edb1b18050178a378f1f3549eb8abf8e7a6e6d4，全成员SHA/liveDT/boot/logdump/F2FS/NV6/source4/persist通过。SLPI offline、供电0、原selector00121，PCM closed/双功放powered0 muted1。发现启动display/radio trace自动为1后，将完整trace保存再关闭；未清除原记录。EUD早期capture因USB re-enumeration不完整；native完整dmesg是主要证据。曾有28MB部分SCP大归档，保留为不完整，完整68MB重传已校验，不能用部分包验收。

CTL reset位置已定位，后续候选必须保留IOMMU接管前quiescence及stalled-interface mask检查。慢console可能导致RCU starvation只是[内核RCU文档](https://docs.kernel.org/RCU/stallwarn.html)给出的解释方向，不能认定根因或隐藏warning。

## 转项和剩余功能

本机19781的13份摄像头DTS已保存来源hash/字段；当前mainline没有SM8150 CAMSS compatible/SoC节点。网络搜索找到[Hotdog源码仓库](https://github.com/Sr-0w/hotdog-linux-bringup)的SoC CAMSS补丁0055、CSIPHY0064、DMA/NOC0066等、C-PHY0089及stream unwind0114；固定参考commit47087509c4289c2580c54f5433e55366b2e00445。只借SoC驱动方案，本机传感器/pinmux/CCI/供电从自身源码和stock模组核对，不复制外国板级配置。[其摄像头报告](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-10-mainline616-camera-autofocus.md)提供参考路径，不能作为本机验收。

完整15组状态见[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。显示/GPU、摄像头、完整传感器、GNSS实际fix、蜂窝数据/通话、指纹、充电、休眠和长期稳定仍开放。阶段114 LOC事件只是IN_PROGRESS，未取得实际fix。长错误先记录，再推进其它功能，不宣布完整可用。

所有私有身份/固件/凭据/无线/定位及原始用户态日志保持E:/edk2-samurai-out，文档仅本地保存。无GPT/NV/persist写入、无erase、无消息/呼叫。旧docs sync会push，未执行。当前启动的freeze守卫必须重建，不复用前次boot。
'''
(root/link).write_text(session)
print('CHECKPOINT115_DOCUMENTS_SAVED_WITH_15_GROUPS')
