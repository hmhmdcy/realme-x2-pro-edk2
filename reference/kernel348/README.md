# 348：原厂 Gamma 已经由 VFE175 硬件生效

2026-10-20。347提取的原厂IFE Gamma已通过新的原生参数块在真实VFE175成像链中生效，完成临时模块实测。尚未接入IPA/默认配置，试验后已恢复338模块及现有服务；手机安装文件保持344基线。完整多摄/ISP目标继续，不能把内部图案结果当作正常照明画质标定。

来源优先复用原厂包：65节点曲线及模式对应沿用347，VFE175寄存器/DMI布局复用286/289已核原厂HAL和296寄存器资料。没有重新下载固件、读取EEPROM或启动Android HAL。原厂曲线只在私有运行数据中，公共驱动不包含模组调校值。

本轮分层变化：

- 公共typed params新增 `CAMSS_PARAMS_IFE_GAMMA=7`，776字节：RGB各64段，每段独立U10 base和signed10 delta。与旧OPE的256项直接表分别表达，旧type4在本机仍拒绝。
- VFE175后端支持enable、无标志更新时保留开关、仅头部disable。开流仍按输出格式初始化标准曲线，停止清开关状态。最大参数容量相应增加，旧参数包仍有效。
- Gamma和LSC复用同一output_lock，分别写各自非活动bank，保存/恢复共享DMI与时钟状态，再沿既有参数队列和PIX RUP报告生效SOF。没有私有ioctl、板级DT、传感器或主线框架改动。

[完整补丁](ife-gamma-driver.patch)、[源状态](source-state.json)。源码在既有E盘ext4的 `/mnt/samurai-full282/source348`，从338干净提交创建。第一次准备在核对UAPI注释文本时停止，尚未修改文件；核对原文本后复用同一干净树继续，没有重建或覆盖原338。主机测试最初缺挂载和LSC声明，修正测试封装；实际驱动功能未因此变化。初次checkpatch的一条屏障注释提示已补齐，最终0错误0警告。

实际Gamma和LSC函数在主机/AArch64各完成24组开关/bank场景，192个字段位置的576项越界拒绝、所有八种bank组合、保护页后的header-only disable、格式初始化及两种DMI交错顺序均通过。DMI模型检查Gamma时钟及只写非活动bank，保留其它寄存器位。[函数测试](register-validation.json)。CAMSS及其现有依赖闭包W=1/KCFLAGS=-Werror构建成功、无诊断，共享构建输出已恢复；末次耗时29.84秒。[构建](kernel-build-validation.json)。

实机使用主摄ShadeColorBars，经实际CSI/VFE175/NV12输出，10阶段观察28帧、保存10图，按参数ACK和图像稳定条件结束。阶段含显式709、线性、R半增益线性、原厂曲线、关闭、关闭期间上传、再次开启、Gamma+单位LSC、Gamma+1.5倍LSC及恢复709/关闭LSC。四项非法包被QBUF拒绝；QBUF后破坏用户缓冲不影响内核快照。

原厂曲线重新启用与首次结果逐字一致；搭配单位LSC也逐字一致；关闭期间上传不影响图像；线性曲线与Gamma旁路相同；末次709与初始709逐字一致。原厂/分通道曲线及非单位LSC都产生实际像素变化，10张保存图的SOF均不早于参数报告的首个生效帧。[采集](pattern-r1-capture-validation.json)、[图像与帧对应](pattern-r1-image-validation.json)。

从线性NV12基准反推RGB的近似模型，原厂Gamma均值误差0.333、p99 1.419/255；Gamma+1.5LSC均值0.504、p99 2.378/255。模型仍含Bayer/缩放/量化/截断误差，不是RAW逐像素参考或光学色彩精度。试验显式替换曲线，未按格式中广告的sRGB传递函数反推输入。

临时模块下已安装r27/r22栈四摄GStreamer各取得12帧，全部无总线错误并恢复媒体状态。试验共76帧，相关故障增量0、taint0，CAMSS/两CCI休眠、九路相机电源disabled/users0。已加载note恢复为原338，PipeWire/WirePlumber各一个uid10000进程30772/30836。[最终状态](final-state-validation.json)。没有安装模块或包、刷写、重启、写NV/OTP/EEPROM/persist；worker已终态。

下一步把Gamma编码及可选静态曲线配置接入IPA，和现有WB/LSC/CCM共用参数revision与SOF上下文，再部署已测内核及用户空间组合。当前默认曲线仍是原有输出传递函数，不能把本轮临时硬件验证写成默认原厂Gamma已经启用。随后继续真实曝光表、防频闪、其它模式、光学、多摄几何/同步与连续AF。
