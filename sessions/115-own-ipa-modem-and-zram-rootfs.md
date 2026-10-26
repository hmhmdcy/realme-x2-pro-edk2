# 阶段115：本机IPA、ModemManager与完整zram rootfs

2026-10-12。完整系统 goal active；无人值守调试，不要求人工检查。

2026-10-12，完整系统目标仍 active，继续无人值守自动化适配。当前已部署 #115，USB SSH/F2FS rw、Wi-Fi 自动连接、IPA 初始化、ModemManager 检出 qcom-soc modem、zram 自动启动通过；taint 0。ModemManager 为 sim-missing，移动数据/通话未验收。首个 #115 启动有桌面，随后两次启动出现 RCU stall 和 DPU CTL reset -22，当前无 DRM/Phosh/Phoc。不能把无帧超时/GPU fault 当作显示正常。

本机专用 rootfs 已更新到 #115 完整 764 个模块、936 个签名包、同机 IPA 固件和服务修复。修正 IPA TX delay 后的 sparse 镜像为 1,817,970,276 字节，逐块展开比对及源/重建两次 fsck 通过；尚未刷入，手机采用增量安装保持 userdata。SLPI offline/供电 0、空闲 PCM closed/双功放静音、NV6/source4/persist 保持。启动 trace 已保存后停止。长时间无进展问题保留证据后转项，不要求画面、触摸、听音或转动检查。

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
