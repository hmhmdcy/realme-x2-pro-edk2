# 306：长焦原厂黑电平、控制时序与硬件 AE

2026-10-19。在同一305启动 guard 下完成 S5K3M5 的1200帧硬件实验：延迟测量240帧、联合控制480帧、隔离IPA自动曝光480帧。复用300测量后端与303通用控制／AGC后端，只增加测试应用和独立模组配置；内核、DT、固件、SDK候选源码和产品软件包保持。产品仍为RAW＋CPU ISP，完整多摄／ISP校准目标active、未完成。

## 原厂资料与实际采用范围

从本机原厂vendor分区以ro／noload／noexec只读提取 qtech_s5k3m5sx 调校，26248608字节，SHA256 a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b，传回主机哈希一致并卸载；没有执行该调校文件或写EEPROM／OTP／NV。[来源与单位](factory-source-validation.json)

有界类型表解码与保留的原厂解析器分别遍历19个IFE根、152个区域，均启用且offset为960 U14、阈值0。另独立解码11个BPS根、48区域，其中有960／990，BPS没有用原厂解析器交叉验证，也没有用于本次在线IFE。[直接解码](tele-bls-direct-validation.json)、[19模式交叉核对](tele-bls-export-validation.json)

显式实验profile将IFE960映射为U16共同减偏移3840，归一化参考2175 Q11经公共WB共同增益量化为136 Q7。SoC BLS scale保持unity，没有把这些参考值塞进DT、传感器驱动或软件ISP的SensorBlackLevels。各测试WB为unity，不采用广角的临时场景WB，且没有实现AWB。厂商文件名不证明本机个体模组供应商；完整原厂模式选择、个体暗场和整条IQ链未重建。

## 真实控制与统计

当前长焦模式为GRBG10 2104×1560，pixel rate481930000、line9648、最小frame1663；曝光1—1659行，原生模拟gain code32—512（gain=code/32）。305几何修复仍在，活动阵列4208×3120。[当前基线](preflight-validation.json)

测量程序在SOF后经标准V4L2写入500／1200／800行曝光及64／128增益码，不预先假定延迟。240帧／240配对、233个SOF和9次写入全部完成；其中7次达到预定信噪比条件，首变化与三帧平台均为写入SOF＋2。后两次较小曝光变化没有足够信噪比，不计作时序证明。仅覆盖本模式和及时SOF回调，不是逐像素／嵌入式锁存或严重延迟证明。[采集](delay-capture-r1-validation.json)、[独立时序分析](delay-analysis-r1-validation.json)

[手动配置](s5k3m5-manual.yaml)据此明确限定模式、时钟与两帧延迟；驱动和公共延迟属性没有改变。复用303同一套CameraSensorHelper／DelayedControls／IPA后端，无传感器分支补丁。普通低照度场景中采用20000µs×8与10000µs×16的恒EV切换：两个epoch共480帧、18次双控、36次真实写入，均在元数据生效SOF前2帧写入。BHIST和四个Y分区的90个域稳定，未检出混合EV瞬态；小幅曝光量化差异保留。这不是逐像素无撕裂或完整校准证明。[独立联合核对](joint-physical-validation.json)

[自动配置](s5k3m5-ae.yaml)复用通用libipa AGC，目标仍0.16。真实隔离IPA跑两个240帧epoch，启动值分别5ms×2、30ms×16；3次有效revision、6次实际写入，15个可辨响应域与有效元数据同帧。写入到生效为2 SOF；提议到生效观察为5 SOF，包含统计／IPC／排队，不能把5当作传感器延迟。[AE帧关联](ae-r1-association-validation.json)

**目标亮度收敛仍为false。** 当前场景下，两轮尾部稳定在接近当前模式／策略曝光上限（量化允许差2行）及16倍增益，仍低于目标；报告passed仅表示“达到目标或正确受限”的既定边界检查。高低两个起点不等同验证了变光或双向收敛。WB固定；RGB AWB、动态帧长、防频闪和正式IQ仍待实现。

每个包均从手机读回核对文件哈希，应用／IPA进程来源分别检查，图、格式、裁剪、控制及video状态由305带明确恢复返回值的fixture恢复。三个worker与子进程均终态，无匹配活进程；五sensor／lens、两CCI、CAMSS休眠，9供电关闭用户0，MCLK／CCI clocks0，fault／CCI错误／pstore／taint均0。10个关键模块加载note和磁盘哈希与305一致，APK数据库／world及桌面／PW／WP身份保持；全778模块和产品四摄回归沿用305，未重复声称本阶段重测。[最终检查](final-health-validation.json)

## 分层与下一步

内核仍为298 Image加305长焦模块，源码samurai-geometry305／18b0a5a753e9363594f682049bf131169488c644。SDK内仍是303源码。本阶段新增的是模组profile与独立测量程序，通用IPA／pipeline／参数接口字节保持，候选没有装入系统软件包。[应用](control-applications-validation.json)、[联合包](bundle-joint-validation.json)、[AE包](bundle-ae-validation.json)

已取得并固定8份原厂AWB BG主来源：Realme Android R内核与CamX Titan17x。确认AWB BG使用DMA client15，BHIST为16；常规区域为24字节，包含R／B／Gr／Gb求和与计数。寄存器位域、阈值、区域限制及多统计DMA生命周期还须核对，**尚未实现或上机验证RGB统计／AWB**。[固定来源与待办](awb-primary-source-validation.json)

继续在公共SoC统计／参数接口实现RGB网格与同SOF配对，再接用户空间AWB；补主摄／前摄／其它模式、AE变光和错误恢复、正式暗场／色彩／阴影调校。304的EEPROM完整校验、模组绑定、LSC几何及golden合成仍开放。用户延期纯色／遮光保持，不阻碍其它适配。

私人根 E:/edk2-samurai-out/kernel306，传输继承305原密钥USB与新guard。delay-r1、joint-r1、ae-r1均终态，勿重放。准备阶段首次查找包收据文件名错误在打包前拒绝，修正后才上传；未将准备失败当作手机失败。现有四摄产品路径、NV和工厂备份保持，未刷写或重启。
