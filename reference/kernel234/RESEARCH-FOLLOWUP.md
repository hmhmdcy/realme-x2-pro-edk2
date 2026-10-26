# 234 后续实现依据

三路代理仅做资料/源码/产物只读审查，手机操作由主代理串行执行。以下研究不是实机修复验收。

IMX319：两家模组的136条global及1632×1224的171条WRITE8逐条相同，规范化addrBE16+value8的SHA256分别`5e8029f021b277c1dd551d481fba3303b0bb4da87e927a3be2eaba616e81e85e`、`e31586a739b52f00f6e61804d7dae24ff492c53f495497fe74fc02cf4134ea5e`。已有完整vendor XML仅IMX471；IMX319只有192的电源前缀XML，需由主流程在独立分析副本用ParameterParser取得完整模式XML，并逐条核表。

19.2MHz、RAW10/四lane/VC0、行长2080/帧长3350以及PLL/MIPI寄存器可由两家BIN交叉核实。BIN的outputPixelClock177.6MHz与frameRate30不能直接作为同一时序：177.6M/(2080×3350)=25.4879fps。按现有主线使用的同类VT公式推得209.066667MHz/30.0044fps，OP/MIPI/数据率候选link222MHz；这些仍是参数推导，未经测量或独立XML时钟语义确认。pixel_rate与link_freq应独立，首次SOF可区分约30和25.49fps，不能盲改PLL试探。[V4L2控制定义](https://docs.kernel.org/userspace-api/media/v4l/ext-ctrls-image-process.html)

主线IMX319仍无可直接套用的OF电源实现；[047119e3](https://github.com/torvalds/linux/commit/047119e3cd631624e04cf251cbafe13bef3f6373)仅时钟helper。需保留ACPI行为，新增三真实supply/reset/MCLK/runtime PM和OEM单模式。真实电源顺序及P/Q隔离沿[233依据](../kernel233/RESEARCH-FOLLOWUP.md)。P profile额外要求：固定掩码0x09，任何secondary读之前验证opt-in/身份/仅L1、L4节点，循环在读取前skip其余五路；仅L1=1.104V/L4=2.8V，VSET写前确认本路关闭、两字节写后回读匹配。任何I2C错误锁存fault，直到P reset/reprobe前仅允许关闭/必要状态读。

置primary0x0950 bit0全局开关前读七路enable且要求全关。写enable即使返回错误也可能部分生效，必须先记attempted并在失败时清位。READY轮询和回滚在实验.enable自身完成：regulator core在.enable错误时不替本路调用.disable。disable失败时core保留enable_count，sensor不能清成功flag或继续重试。regulator_unregister不清电源、不恢复VSET；按sensor→child→P MFD退出，最后使用233已验P-only reset，保留Q暖态。这里只是下一实现约束，本轮未写P电压/enable。

GNSS：未找到同SM8150真实零CNR恢复的可直接套用修复。[Hotdog会话修正](https://github.com/Sr-0w/hotdog-linux-bringup/commit/255d3e282d063351102f6b51e96f73181a2ea9f6)仍明确无卫星；[IPA提交](https://github.com/Sr-0w/hotdog-linux-bringup/commit/c21305c457668aad6c3ddd7a72db0a7c889887d9)解决MM网络端口。本机226已越过接入前提。[RMX1931包名](https://github.com/HyperTeam/android_device_realme_samurai/commit/e7792fcf23783db11f1a28aee9bf27fe9bd01734)及[launcher权限](https://github.com/HyperTeam/android_device_realme_samurai/commit/2dffaa08a0d2f8408879c373f09d79e440c8f1a2)属Android入口，不能当当前原始QMI零CNR修复。

新差异是R GPL的[QMI MEMSHARE服务](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/soc/qcom/memshare/msm_memshare.h#L17)：service52/version1/instance1，GPS client0，alloc0x22。19781 DTS的GPS client预分配size0；原Android归档启用该驱动，但内核实为第三方，来源限制仍在。当前主线无实现，仅形成具体差异；没有MPSS lookup52/client0请求证据，不能认定GNSS依赖。现有QRTR trace不含lookup服务参数，不能从qrtr-lookup未列52推断modem在等待它。下一判别应只观察真实lookup/请求，不注册伪服务或盲分配内存，且不需要户外。本轮没有因此启GNSS/重启服务。
