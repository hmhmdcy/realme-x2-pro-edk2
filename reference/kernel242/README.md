# 242：ROM 对照、modem 文件一致性与 GNSS 时钟关联采集

2026-10-16。用户要求采集 Android 厂商 HAL 的实际初始化报文，随后提供 crDroid 12.4 Android 16 ZIP，并询问是否必须刷回 Android。**不必把恢复 Android 作为适配前提。本轮保持 Linux，完成文件对照及新的 Linux 原生采集；尚未取得 Android 运行时报文，也未证明零 CNR 根因。**

## 本机与提供的 ROM

严格原 SSH 密钥确认仍为236启动、boot235；根目录是物理 userdata 上的 F2FS，当前没有运行 Android、ADB 设备或 Android init/getprop。[现状](baseline-validation.json)

用户提供的 ZIP 约1.75GB，metadata支持 samurai/RMX1931/RMX1931L1，BLOCK OTA包含 system/vendor/odm、boot、recovery、dtbo和vbmeta，没有 modem 分区镜像或 userdata 备份。离线重建三个 ext4 镜像，检查 Brotli 完整结束、ZIP成员CRC、块范围和写入字节数；未执行安装器。boot为v1、4096页、legacy LZ4 ramdisk，18个CPIO成员；与旧stock备份的boot整体不相同，不能把两者视为相同内核。[包检查](android-rom-validation.json)、[分区重建](rom-partition-unpack-validation.json)

包中的7个关键文件——GNSS服务、libgnss、libloc_core、libloc_api_v02、libgps.utils、liblbs_core、libqmi_cci——与238从本机只读提取的文件逐字节相同；ODM gps.conf也与239实际来源相同。这个包适合做匹配版本的离线分析及未来运行对照，不代表已验证Android能正常定位。[比较](rom-comparison-validation.json)

ramdisk fstab包含直接指向物理userdata的ext4/f2fs `/data` 项，带FBE/metadata密钥目录及f2fs formattable；metadata也可格式化。安装器另明确覆盖system/vendor/odm/boot/dtbo/vbmeta。直接运行安装器或只刷原boot，都不能作为保留当前Linux的已验证方案。本轮没有进行刷写、重启、数据分区转换或制作可启动的隔离Android候选。

## modem 与 MCFG 对照

找到既有本机TWRP modem备份并核对其SHA256侧车，识别路径和摘要仅保存在私人目录。[备份核验](android-backup-validation.json)

起初仅按 `/lib/firmware/<sysfs firmware>` 查找，modem MDT不存在；继续核对发现实际firmware_class搜索路径为RAM中的自定义目录。那里34个文件全部存在且匹配部署清单，不能把初次默认路径检查的false解释为固件缺失。[完整搜索路径](resolve-firmware-validation.json)

这34个modem文件与原Android modem备份对应文件全部逐字节相同；当前文件服务记录的173个MCFG源文件也全部与该备份相同。[modem比较](rom-comparison-validation.json)、[MCFG比较](mcfg-comparison-validation.json)。因此“Linux用了另一套MPSS/MCFG源文件”目前没有支持证据，但这**不等于**验证了Android运行时选择的active MBN、RAM中的完整固件状态或RF/NV配置相同。本轮未执行PDC load/select/activate，也未读取或覆盖NV内容。

## Linux 搜星期间的实际记录

复用已验证226-r3同CID原生探针，逐一核源码/程序摘要及GET/REGISTER/START/STOP消息白名单。standalone=4、HIGH=3，90秒观察；本轮没有重放241 master/AFW/RESUME组合，也未重注入辅助数据。另建独立trace实例，在Start之前开启32个时钟/调压器事件，采集前、5/30/75秒及停止后的状态。[生命周期](clock-session-validation.json)

- 89次SV事件，29次带列表，累计946个有效SNR字段均0/SEARCH；60次缺列表，不计零CNR。普通/扩展格式同时报告时重复累计，不是946颗唯一卫星。
- 90条PQWM1：PGA −2至0，ADC I125—154/Q118—146，GPS AGC −0.78至0.37；错误恢复字段0，XO状态数值11。数据变化不是天线/LNA正常证据，尚无该固件XO枚举的充分解释。
- TimeValid1、TimeSource原值7，TimeUncNs约8.4975—8.4979秒。不能把有效时间或source7当作本次获得fix。历史IDL含NAV_SOLUTION=7的定义，但不是当前固件调试NMEA枚举的充分证明；本次原始位置状态没有成功报告。[历史定义](https://android.googlesource.com/platform/hardware/qcom/gps/+/android-4.2.2_r1/loc_api/loc_api_v02/location_service_v02.h#525)
- 筛选的XO/RF/MSS时钟没有AP侧trace转换，采到17条regulator事件，名称均为ldo10。快照中存在两个同名ldo10，不能仅凭事件名认定是GNSS/LNA电源。AP无转换也不等于modem未投RF票。

[解码与范围](clock-analysis-validation.json)。PQWM1字段依据固定[SM8150 SystemStatus](https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/57ced1dc07cd15aaedbee0f98a3384ac837c4ce5/core/SystemStatus.cpp)，沿用208校验和、截断、缺字段及NaN检查。原NMEA、卫星标识、位置及完整硬件快照保持私人。

实际运行内核对应源码确认：`clk_rpmh_ops`只有prepare/unprepare/recalc_rate，没有硬件is_enabled回调；通用clk_summary在没有enable回调时直接显示Y。RPMH频率由静态父频率除分频计算。因此这个Y和19.2/38.4MHz标称值都不是物理XO开关、锁定或频率测量。[源码核验](clock-source-validation.json)

探针完成Stop、CID释放、close，独立trace实例删除，8核trace均无overrun/dropped；MM属性、辅助worker计数及包数据库保持，三DSP运行、taint0，本轮WARN/Oops/GPU/DSP fatal增量0。14份原生归档成员已逐一核验。[导出](clock-export-validation.json)、[最终健康](final-health-validation.json)

最终只读检查首版误把watch.running当作数据worker运行，断言退出。核对实际为watch守护进程running=true、active=false、数据worker starts/completions均0、time_prepared=true后修正判断，未停止或重启该服务，失败收据保留私人。

## 保留 Linux 的续作路线

可以继续从当前Linux抓取LOC/接收器诊断，核对可观测的modem电源/时钟/文件请求及配置差异，再用有界单变量实验验证有依据的候选。室内窗边负结果仍混有接收条件；同一Linux程序移至无遮挡天空也是有区分力的对照，并不需要刷机。

Android的额外价值是同机正常接收基线和实际初始化顺序。只有真实运行Android才能称为Android运行报文；从ZIP反汇编、Linux重放或在Linux上运行厂商库均不能替代该证据。目前没有依据指定LNA GPIO、强持RF时钟票或修改校准/NV。后续优先寻找能区分故障层的证据，不把重复零CNR会话当修复。

私人产物在 `E:/edk2-samurai-out/kernel242`。本阶段没有变更生产驱动、MM或GNSS辅助配置；其它外设仍沿用240检查点。原241初始化差异与630秒测试见[241](../kernel241/README.md)。
