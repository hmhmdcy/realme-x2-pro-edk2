# Type-C 固定受电分支：507 试运行准备

2026-10-25。补齐当前 qcom PM8150B TCPM port 对 `power-role="sink"` 的处理；已完成对象、Image507、BDS 和两个启动载体，已上传独立暂存目录，**尚未安装或重启**。手机仍为506，继续原低电预充实测。

**R1禁止stage**：[收尾复核](trial-readiness.json)确认普通full-TCPM shutdown没有协议关闭动作，原pdphy_stop只清TX/filter并放共享供电引用，未明确清EN/BIST。现stage另要求匹配实际两载体的full-pd-shutdown-ready文件；当前没有该文件。先补IRQ/work/TCPM实际join和最终控制读回，再生成R2载体/独立暂存，不得对现有R1补一份虚假的ready。

当前 [506](../eud-route-pm-candidate/README.md) 的专用 PD-disabled 分支没有注册 TCPM/Type-C class。本候选针对正常 TCPM 分支：原 port probe 要求 VBUS 输出 regulator，启动先写 TRY_SNK，set_cc 只更新源电流/缓存，没有执行固定受电端需要的 OPEN/Rd 模式写。这里按实际 connector 的标准 `power-role` 选择分支，未增加机型私有开关或虚假电源。

## 改动与验证

[源码和基线](source.json)、[补丁](sink-only-port.patch)：仅明确 sink 的 connector 可缺少 VBUS 输出电源；真实 defer/I/O 错误保留。拒绝 VBUS/VCONN 源使能、Rp 和 DRP；从第一条模式写即为 SNK_ONLY，OPEN 写 DISABLE，Rd 写 SNK_ONLY，模式写失败不更新 CC 缓存。其它角色保留原控制路径。新增 helper 在所有取得 connector 的路径释放该引用。

[四组测试](test-result.json)直接抽取七个完整真实函数，OS/设备/I/O 边界建模，覆盖输出电源缺失及错误、引用、源使能拒绝、OPEN/Rd、原 Rp/输出路径、启动与中途写失败；ASan/UBSan、Werror 通过。初次测试框架存在 puts 命名冲突及遗漏日志宏，修正框架后通过，运行源码未因此改变。[对象编译](build-result.json) W=1 零诊断；[Image507](image-build-result.json)保持配置、电量计对象、initramfs、builtin 元数据与全部 builtin 导出逐字相同，原506和共享构建未改。

[试运行 DT](dtb-result.json)只请求5V/500mA，固定受电/USB device，不含 source 或高压 PDO。保留 peripheral DWC、原 USB IRQ/PM 绑定和电芯参数。去除两个 PD5V opt-in，并暂时禁用 EUD-route/APSD borrower，避免两种控制方式并行。**这会停用当前 APSD 支路，所以本配置只供短时试运行，不能直接取代正式506。** 完整 TCPM 与 APSD 共同工作、PD 合同预算接入及原厂9V策略仍需后续实现和验证。

[BDS](firmware-build-result.json)只编译一个对象，复用其余40库；[boot](boot-package-result.json)只换 BDS 和 native DT 两个 FFS，其余99个 FFS、SEC、shim/兼容段/ramdisk及原绝对尾部保持。[FAT](logdump-package-result.json)只替换已有 Image 文件数据，目录、分配、slack 和另一个 DTB 保持，fsck -n通过。

| 试运行产物 | SHA256 |
| --- | --- |
| Image507 | a41469c71f43688360f7d8d318a40b663e05eb5afd203c80db8d2c4e818984a6 |
| boot | e48dddfc2ae0beda4a128f878cabb54c63dbaad7e9d4ad0cab9500fc9bc2c100 |
| logdump/FAT | 2c26ffd18c7088a9c0f93695a02cc3039a7ff3b6d4019f17a2b61196bad73f18 |

## 启动与恢复

手机独立暂存 `tcpm507-trial-20261025-01`、host private `image507-sink-trial-private-01`，载体及旧/新文件已校验；live 文件/分区未改。trial manifest 为7db574…1720，guard 为21e937…5f38。

[guard](boot-guard.py)算法与已验506相同，仅三处身份字面量改变；若 Linux 用户态能运行，未接纳时300秒恢复原 boot5c8d、FATb29e 和原文件后重启，不能恢复用户态之前的硬挂。此配置应短测不写accepted，等待300秒guard自行恢复原506，不并发调用第二份restore，也不接纳为正式基线。[stage](trial-stage.py)另要求原预充实测成功、监督器已 join/AUTO 恢复、六个原进程消失、SOC≥20%、两芯均≥3.70V；当前这些条件尚未满足，**未运行 stage**。装入顺序先 FAT 后 boot，逆向先 boot 后 FAT。

后续先完成当前真实预充→fast/CC 阶段并恢复 AUTO、补回启动电量，再进行一次有界 TCPM 注册/CC/原USB500预算及连接恢复检查，短测后还原506。现连接由 Windows 报告非 Type-C 且无独立断电路径，不能在此证明 PD 适配器合同、真实 VBUS 断开/APSD 或 USB 物理唤醒。软件 OPEN、重绑和 adapter reset 均不计作物理拔插。

未改桌面、充电电压、保护/FET/OTP/NV；没有因候选准备重跑 MAC 诊断。原厂高功率、完整PD/QC/VOOC、2719精确语义/TCA、温界和长计时仍未完成。

[audit-phone.py](audit-phone.py)是仅查询的507验收入口：同时检查真实watchdog PID/startticks、cmdline与所持锁、绑定与Type-C角色、实际TCPM供电属性、两次原服务健康/原USB500预算和可选载体读回，不写accepted或充电控制。已在实际506验证会于身份检查拒绝，未冒称507实机通过；新启动的正向验收仍待执行。此脚本不依据Type-C class或USB_TYPE声称PD合同生效：固定源TCPM在选PDO时先置USB_TYPE_PD（4444行），PS_RDY接收分支才设current_limit及explicit_contract（3775–3782行）。后续真实预算接入必须处理这个先后关系及重置/待机限流，不能仅消费PD类型字段。

收尾缺项已在[507 R2](../tcpm-sink-shutdown-candidate/README.md)补齐并独立暂存，R1仍不可stage；当前506预充实验未切换。
