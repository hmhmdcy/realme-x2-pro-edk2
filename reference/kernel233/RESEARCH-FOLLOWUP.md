# 233 后续只读研究收敛

这些是下一步源码工作依据，不能替代本机上电/出图或GNSS、BT修复证据。

后摄：OEM R固定提交`23172a1571bd91156032cc9fef16284a82b63d2c`的19781板源声明L7P为指纹AVDD 3.3V，不能把P七路统配相机2.8V。IMX319使用L1P（请求1.10V、8mV档位为1.104V）/L4P2.8V；3M5使用L2P1.056V/L6P2.8V；GW1主要使用Q侧L1/L3/L7。两家本机IMX319 BIN共136条init及前五模式表一致，低负载1632×1224为171条WRITE8/RAW10/四lane/VC0；还需vendor XML独立核对。现有ACPI主线表不等同本机表，226/227的OF/runtime内容仅设计，没有实现文件。

P输入父网：当前233 P@8没有VIN属性，S8C只在Q@4。另有独立OEM声明：19781/pm8008.dtsi将P的regulators置于@9；sm8150-mtp.dtsi:1067–1073分别给P/Q的NLDO输入指定S8C。不能把OEM声明说成233实际连接或物理测量。P的PLDO输入仍无可靠父连接。后续可硬限制只注册L1/L4（掩码0x09），不注册全部七路再禁用；只用已知输出和OEM序列，不编造未知输入。core会对真实父电源按dropout投票，必须核固定S8C约束/操作权限；未解析输入得到dummy只表示软件占位，不证明物理VIN。七路注册也不等于必然改写全部七路：无init_data且regulator_ignore_unused时通常没有VSET写入，但隔离掩码仍有必要。

120的stock-camera-contract-validation还独立记录原机overlay @9/P（GPIO1）的NLDO输入为S8C，@5/Q（GPIO4）亦然；此为DT声明证据，当前233 P仍未添加。下一实验可用特殊MFD cell/固定driver_data掩码0x09，在任何读/注册前跳过五路，Q沿用原cell；P身份模式与新供电模式互斥、默认拒绝。只声明ldo1 1.10–1.104V/ldo4 2.8V，不加boot-on/always-on，不修改带电VSET。OEM还操作primary 0x0950 bit0全局enable并轮询base+0x08 bit7 READY，不能沿用192旧采样假定当前bit0状态；应先读再确认必要动作，失败的LDO enable必须由驱动自身清位后返回。IMX319三个供电引用必须是真实phandle，不能让缺供电被dummy掩盖。此处均为后续候选要求，未在233操作或验收。

首次写前只读七路enable并要求全关闭，否则置全局位可能点亮未选输出；未选五路不注册、不写。regulator_unregister不负责清enable或恢复VSET，不能当电源回收。失败必须按已完成步骤退出；若I2C关闭失败无法证明off，停止重试，按sensor→child→P MFD解绑，最后走已验P-only reset，Q保持暖。IMX319设计序列为保持reset，L4P→1ms→L1P→1ms→真实VIO1.8V→MCLK1 19.2MHz→TLMM30释放→18ms，再在CCI0 master1/0x10读0x0016=0x0319；退出按OEM顺序，不能bulk启停或猜缺失VIO引用。

GNSS：R板源的单GPIO26线缆监控将状态写SMEM136，未证明GNSS消费它。下载R OTA的DTBO有该consumer，102原机分区两份DTBO没有；不能跨版本拼配置。82会话已明确名为stock的Android回滚boot实际是第三方内核，226所谓基础DTB没有可追溯来源，不能当OEM依据。MPSS的XO/CX/MSS/PAS4/AOP已有对应；RF_CLK3命中的是禁用WiGig，不能据此补GNSS时钟票。本轮没有为这些未成立差异操作手机。[来源纠正](../../sessions/82-charging-policy-units-and-android-backup-provenance.md)

BT phase5：`partial=0`不能区分NULL skb与已消费H4包类型但len0的skb；`first=ff`是chunk首字节，不是解析器错误位置。不能据此吞FF或补04。下一诊断可在既有32B/固定预算/限定phase5日志上补had_skb、pkt_type、expect、padding及RX序号，保留解析行为并与GENI切速/RTS/IRQ关联。TTY返回速率不是硬件实测速率，应结合时钟/分频。205 RTS模型实际停在TIOCM_LOOP未定义，未形成16例通过；应先补模型真实UAPI常量并执行实际函数/负对照，再评估set_termios后同步RFR。OEM Realme/OPPO有对应模式维护，但成功trace也已有正常RFR切换，不能直接解释历史错误；本地主线已包含零长度DMA重装，不能重复应用当修复。

固定源码入口：[Realme板源](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/arch/arm64/boot/dts/19781/sm8150-mtp.dtsi)、[Realme GENI](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/tty/serial/msm_geni_serial.c)、[OPPO GENI](https://github.com/oppo-source/android_kernel_oppo_sm8150/blob/66cbe4bd056bf032063026ce24a7159449c00f6e/drivers/tty/serial/msm_geni_serial.c)。
