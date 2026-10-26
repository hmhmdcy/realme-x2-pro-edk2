# 239：实际 ISP 首参修复、r15 默认部署与近机型核对

2026-10-16。已完成r15/config-r10完整构建、七包默认部署和真实两次start验参，补齐当前ODM配置来源、S5K3M5全模式离线解码，并重新搜索近机型Linux实现。**首参同步修复已验证；后摄光学成像、颜色与GNSS fix仍开放，完整适配goal active。** [机型、传感器和Linux使用路线](RELATED-LINUX-SOLUTIONS.md)。

## 为什么黑帧不能按白天或夜晚直接归类

[固定12帧r14](fixed-rgb-validation.json)程序成功、严格非零失败；完整FIFO实际Debayer日志显示BLC依次0→16→12，首帧gamma1，之后1/2.2。IPA回报的元数据比实际处理参数更早变化，不能当作同帧实参。

[同request十二组RAW/RGB](paired-validation.json)的源sequence/timestamp精确相等，均为真实sensor且测试图案关。RAW有效区每帧1,997,568像素，值63–72、均值约63.965，仍很接近黑电平。BLC16时RGB均值约0.0017、最大28；BLC12后约37。[全直方图重算和LUT边界](paired-lut-analysis.json)一致，但RAW宽1632、RGB裁掉两边至1624，不声称逐像素等价。接收数据含噪声并不能独立证明正常光学成像，尚待用户后摄朝向信息；没有要求纯色物体或新增照明。

## r15 的修复及实际验收

[0022补丁](0022-soft-initial-parameters.patch)在同步IPA start成功后立即`saveIspParams()`，IPA start补发布combinedMatrix；CPU处理日志加入frame/sequence/timestamp。保留238的IMX319 gain helper和原20补丁，不改黑电平、调校、控制延迟或异步逐帧API。

- [完整构建](r15-package-build-validation.json)13包，34个AArch64 ELF、5个IPA签名、Qt/Python/GStreamer等全部保留；[完整QA](r15-complete-host-qa-validation.json)通过，原214的2254文件/链接/模式恢复，r14缓存2269项不变。
- [候选同相机两次start](r15-startup-analysis.json)和[安装后默认路径两次start](r15-installed-startup-analysis.json)各24帧，实际处理身份逐帧对应回调；两轮首帧BLC16、gamma1/2.2、gains1、identity matrix，旧默认值和上轮残留问题修复。非identity CCM运行场景未测。
- 零帧严格失败保留：候选run0 q0–1、run1 q0–3；系统默认run0 q0–3、run1 q0–2。参数同步修复不等于近黑场或颜色验收。程序exit0和`diagnostic_capture_completed=true`与`passed=false`分别记录。
- 前摄候选[RAW六帧](front-raw-validation.json)/[CPU RGB六帧](front-rgb-validation.json)通过，仅RAM统计。纯色测试按用户延期。
- [实际七包安装](r15-package-install-validation.json)升级到libcamera/IPA/tools/GStreamer/V4L2 `99990.7.2-r15`、config/stack `0.1.0-r10`；944包总数不变，937无关记录不变，49个payload记录含模式/链接/hash核对。该安装收据中的pending字段是安装当时状态，后续默认验参与[WirePlumber重载](wireplumber-reload-validation.json)均已完成。
- WirePlumber平滑停止后手动按原环境启动，已映射新库且无deleted旧库；PipeWire和桌面身份保持，蓝牙既有连接集合不变，没有pair/connect/disconnect调用。

r13/config-r8实际七包仍在设备`k225-r13-package-candidates/forward`，事务前world/repositories/配置/包库保留于`k239-r15-package-transaction`，原生七包降级模拟通过，未执行完整往返。当前持久仓库索引指向`k239-r15-package-candidates/forward/packages.adb`。主配方与部署锁已同步，完整kernel/rootfs整合仍未完成。

## S5K3M5 与 GNSS 来源

[S5K3M5验证](s5k3m5-crosscheck-validation.json)以原始qtech BIN两种schema投影加独立有界decoder交叉核对：917条初始化、4×53=212条模式写入相同，保留重复写、最后WRITE8及5µs延迟，原BIN未改。投影追加偏移以EOF计算，保留原section2的24B尾。reader以UID/GID1000及CPU/内存/文件/墙钟限制运行，修改XML层级验证后复用已生成结果，没有重跑reader。首次XML层级错误与Span `.at()`编译错误均保留。

模式包括4208×3120、4000×3000、4208×2368、2104×1560；前两项另有PDAF VC1，模式3无该流。OEM时钟元数据不是实测PLL。硬件仍须本机19.2MHz、CCI1/master0/0x2d、reset23/MCLK3/CSIPHY3与严格P L2/L6 mask0x22/shared lease；不复制Hotdog 24MHz或猜VIN。没有本轮实体S5K3M5 probe/capture。

[当前ODM只读采集](odm-validation.json)核PARTNAME/几何/ext，ro/noload/noexec挂载且前后分区摘要相同，正常卸载，仅复制gps.conf与build.prop两文件。[配置比较](odm-gps-comparison-validation.json)确认实际gps.conf逐字节等于205 HyperTeam固定源；39启用键/34数值键。AOSP差异含DEBUG、XTRA_VERSION_CHECK、NMEA分组及10个RF_LOSS键，缺省不当作运行值0。

真实libloc_core的35项表、APS2重定位及readConfig默认已只读分析：GPS_LOCK默认3、LPP_PROFILE0、CAPABILITIES7、MODEM_TYPE2；ODM分别未写/2/23/1。这不是运行时modem配置。实际libgps.utils固定`/vendor/etc/gps.conf`、失败无ODM回退，尚不能认定ODM配置已使用。RF_LOSS日志在SV报告处理分支，没有RF/LNA供电证据。本轮无GNSS SET/搜星，不读写NV/persist，真实正CNR/fix仍未解决。

## 清理与续作

[最终实机健康](final-health-validation.json)确认仍236启动/235 boot，775ko/789文件及已加载build notes与237清单一致；仅相机七包按新manifest改变，其余旧用户态和loader校验保持。两sensor/CCI/CAMSS suspended、四camera rails OFF/users0、MCLK1/2关；三DSP、SensorProxy三Has、Wi-Fi/chrony正常，taint/fault0。GNSS idle、无新数据worker；MM处于无SIM背景，蓝牙状态只观察。

[153项原生证据](evidence-validation.json)已分48KiB导出且逐成员验证，保留失败、参数、统计、trace、安装和清理；ODM原文另行私有导出，没有场景像素、私钥、设备指纹或坐标公开。canonical仍after228，旧相机内核输出不能整刷。

后续优先基于本机OEM表准备S5K3M5，继续独立判断IMX319光学响应；GNSS可研究匹配厂商HAL初始化与当前原生QMI差异，但尚无可部署RF修复。其它后摄、蜂窝业务、传感器/蓝牙长稳及全机整合保持待办。
