# 163：在早期显示初始化期间保持面板复位

160用户确认剩余白屏花屏位于edk2画面消失后、首个Linux命令行出现前，启动速度已变快、手动唤醒无闪屏。161改SMMU空RMR路径未通过新boot软件验收，162已恢复原版158。

163在SM8150 TLMM成功就绪后，仅对realme,samurai及启用的samsung,sofef03f-m面板读取其reset-gpios；严格核对本控制器、GPIO6、active-low。随后把复位设为逻辑1（物理低），释放GPIO占用供原生面板驱动重新获取。实际日志中TLMM复位在13.270700秒，晚于SMMU13.178408/13.180918秒，早于native DSI停机14.513072秒。arch_initcall注册顺序不能保证实际probe顺序，不能声称本版先于SMMU关闭面板。原生prepare及首帧门控保持。[候选补丁](early-panel-reset.patch)、[实际顺序](startup-order-validation.json)

14个真实函数场景普通/ASAN/UBSAN通过，验证平台和面板过滤、控制器初始化成功前不请求GPIO、错误pin/极性不操作、所有节点/GPIO引用释放、原生面板可重新获取GPIO，以及GPIO失败时保留控制器正常probe。旧probe负对照无法保持面板复位，测试拒绝它。[函数验证](actual-function-test-validation.json)

完整W=1/Image/770模块/DTB/checkpatch/FAT通过，只刷logdump163。新boot Phoc17.91/Phosh19.39秒，关键显示错误/WARN/audio DMA prepare0、taint0，分区/NV/模块/Mesa核验通过。[运行结果](runtime-validation.json)

两轮共48次标准DPMS无新增错误。首轮最终恢复亮屏后立即关闭trace，只观察到11次完整门控；保留原始档案，工具增加0.4秒最终恢复等待再复测，第二轮12次门控完整位于真实PP TX done及ret0等待之后，trace无丢失，未修改驱动。[第二轮结果](dpms-restoration-validation.json)

601.11秒/21次观察到uptime1499.87，同boot、桌面PID保持，显示/WARN/UFS UIC错误0、taint0；稍后到uptime3269.73仍同boot，Phoc/Phosh启动时间17.91/19.39不变。临时启动记录器已停并退出runlevel。实体白屏效果未观察；164进一步在UEFI离开Boot Services前保持面板复位，仍需实体验收。[稳态结果](steady-validation.json)

使用的是内核GPIO描述符接口，logical1对active-low线路驱动物理低；参见[GPIO官方文档](https://docs.kernel.org/driver-api/gpio/consumer.html)。本机MSM pinmux没有gpio_disable_free硬件回调，释放占用保留输出电平；实机仍需核对日志顺序和原生恢复。
