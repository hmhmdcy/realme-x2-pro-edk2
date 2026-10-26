# 阶段收尾与 Wi-Fi 启动依赖（2026-10-10）

按用户要求，本阶段充电排查收尾，下一项硬件适配优先 Wi-Fi。充电接口、控制及保护仍有
待办，不作为继续无线工作的前置验收。本轮没有刷机、重启、开关屏或充电控制操作。

## 已确认的进展与未解决项

触摸基本输入、USB NCM/自动密钥 SSH/SCP、原生 60Hz 显示及 A640/Turnip 真实渲染已有
实机数据流证据。session75 的非连续 DSI 时钟修正解决了用户确认的静止彩色噪点；
随后捕获的 DRM frame-done timeout 是另外的稳定性问题，尚未解决。

电量计能读取电量、电压、温度等标准属性。session86 纠正 MP2650 输入有效位解释，
实测 ONLINE=1/Full；但 ADC 一致性读返回 EAGAIN，三份 uevent 为空，完整观测接口失败。
修正版最多三次一致性尝试，用 ENODATA 保留其它属性；已进入宿主源码，未实机验收。
手机没有 MP2650 客户端或持久设备树节点。此前 99%/8.636V/31.5°C/平均 0mA 是近满电
观测，不能据此认定慢充。2719 器件映射、保护、热敏校准、输入预算及失联行为仍待核实。
Android R/cyborg 来源与单位边界见 [session83](83-androidr-and-cyborg-charging-source-comparison.md)、
[session85](85-oem-chemistry-and-short-ic-observations.md)、[session86](86-mp2650-input-status-and-real-display-timeout-snapshot.md)。

本轮 USB SSH 复核：手机仍为 #86，boot ID
`32bf2d8f-8dde-47dc-9b88-e87db9e95198`，采集时 uptime 2140.55 秒，taint=0，
frame_done_cnt=2、underrun=0。display 实例 on=0、snapshot:count=0；快照 SHA256 仍为
`550d76908bd09bb280f57a5937fce7ec0101e4c167fed850b42834085e53f2f2`，与 session86 一致。
没有清空或重新武装跟踪，没有新的光学确认。原始 state/dmesg 和设备端摘要保存在
[reference/kernel87](../reference/kernel87/README.md)。boot/logdump 保持 session86 的部署版本；
本轮未重新读取整分区摘要，不将旧摘要称为本轮实测。

## 保存的显示修正候选

审阅发现原来的 timeout trace 位于 printk 和寄存器快照之后，session86 的
378.497165 秒事件不能代表计时器开始处理超时的时刻，因此先前 done/idle/timeout
时间关系不能直接证明根因。候选把真正的超时判定事件移到日志/快照之前，并增加
arm/expire_check/expire_stale/expire_claim 跟踪。

现有代码中，帧完成可能发生在 post-kickoff 计时器 arm 之前；已经开始执行的旧
timer callback 也可能遇到下一帧重新 arm。候选在 enc_spinlock 下同步忙位、截止时间和
arm/disarm，忙位为空时不 arm，旧回调遇到未来截止时间时不消耗新帧的超时状态。
disable 清理 timer 后，在锁外同步等待正在执行的回调。真正超时的错误、快照及 CRTC
事件仍保留。相关 API 行为见 [Linux timer 文档](https://docs.kernel.org/driver-api/basics.html)。

只改动 dpu_encoder.c/dpu_trace.h；现有显示、EUD、触摸、电量计及 MP 观测修正保持。
使用实际三个函数体的宿主回归测试：旧函数在“完成早于 arm”场景失败，候选的六个场景
通过，包括旧回调/新帧重叠、真正超时、多个物理 encoder、jiffies 回绕和无 CRTC。
这是确定性 timer/IRQ 桩测试，不是实际 SMP 或硬件验证；桩测试编译有类型/未使用函数
警告，真实内核构建没有 warning。增量 patch 的反向应用检查通过。

#88 内核 Image 构建退出码 0，36719104 字节，SHA256
`7def19605ac17482528049a6956144abc075a9727d3da2e771cce6a4fcab9e89`。
完整配置摘要仍为 `a19260711d578f1c348091b205476cf56d9878a4fd5b57c2dd7068b648ad0881`，
CPIO 仍为 `74052b3e705e5af1c2268590206da264a339cf4e042e5ed601c54f56ad66b102`。
30 个既有源文件的内容/模式、14 个 initramfs 文件和 308 个链接均核对；除上述两个 DPU
源文件外保持。本地源码 HEAD 是 e42788e，不称为已推送主线版本。
**#88 尚未部署，不能称显示故障已修复；#87 的 MP 候选同样未验收。**

## 已开始的下一项：Wi-Fi

当前 `.config` 关闭 WLAN，CFG80211/MAC80211/QRTR/QMI/PAS/PD mapper 等为模块；
宿主 initramfs 和实机均没有 `/lib/modules`，实机 `/proc/modules`、remoteproc class 为空，
网络只有 lo/usb0。设备树 Wi-Fi/MPSS 均 disabled。这是具体的启动依赖缺口，不是权限阻挡。

本机四路 Wi-Fi 供电已由 MTP 继承，wlan 保留区 `0x9b000000+0x180000` 已核对，不能
重复补供电或将原厂 MSA 请求大小当成保留区大小。session81 私人归档的 wlanmdsp.mbn
及 34 项 bdwlan.* 共 35 个文件重新逐项校验，通过；未安装或加载。

新增 `wifi-prerequisites.config`：内建 ath10k SNOC、网络栈、RFKILL、QRTR/GLINK、QMI、
PAS/SYSMON 和 PD mapper；其它厂商/总线及测试/DFS 认证选项关闭。私人候选配置已用
实际 Kconfig 解析，最终 27 个符号改变，所有请求值匹配，配置解析无警告。
初次解析暴露 RFKILL/SYSMON 模块约束及工具环境导致的 RELR 变化；已补足依赖和
交叉工具环境，最终 RELR/工具能力及原有配置/Image/DT/CPIO 均保持。
完整 Wi-Fi 候选配置留在私人目录，公开最小增量片段和解析/保留审计。
**该配置尚未构建 Image、部署或实机测试。#88 不包含这个 Wi-Fi 配置。**

当前 ath10k QMI 按远端返回的 chip/board ID 选择板数据，并在 MSA permission/ready
之后获取能力；SNOC 的 `firmware-name` 在当前源码中用于板文件名，不能直接当作
wlanmdsp 加载器。板文件的精确名称和来源要求见
[Linux Wireless 文档](https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath10k/boardfiles.html)。
实际本机 QMI ID、WLFW/PD/TFTP 顺序还未知，不挑任意 bdwlan 文件或通用板数据顶替。

[tqftpserv 固定源码](https://github.com/linux-msm/tqftpserv/tree/128cd6e0a39734fefd0f0bf0aad5e997c29e2445)
支持读/写请求；private session81 文件摘要已核验，WRQ 路径使用 O_WRONLY|O_CREAT，
不能直接称只读服务。下一步先构建隔离的诊断依赖候选，准备明确拒绝 WRQ/存储写的
固件服务及服务日志，再按本机签名固件和返回 ID 验证无线启动。MPSS 的 PAS 默认
auto_boot=false，当前节点仍禁用；没有启动 modem、rmtfs 或其它持久存储服务。

## 后续顺序

Wi-Fi 的依赖镜像与受限固件服务 → 本机 chip/board ID 和板数据 → 无线接口/扫描 →
连接和实际流量，再推进蓝牙/音频等硬件。显示候选及充电未解决项保留在待办，避免
继续围绕充电重复查询；出现新故障先保存现场。全硬件目标继续，不标为完成。
安全边界保持：不写充电配置、NVM/OTP、FET/OTG/GPIO/MCU；保留 Android、数据、GPT、
密钥及固件。未来部署只使用新会话的新守卫，旧 kernel86/flash-final.ps1 的停止保护保持。
