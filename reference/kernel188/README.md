# 188：自动SSC服务、桌面访问通过与休眠崩溃回退

2026-10-15。完整外设goal active；当前kernel183、boot/DTB172、modules132且仅hci_uart185覆盖。承接[187本机A.11三轴实测](../kernel187/README.md)，本轮实现并实际验证自动启动及桌面用户接口，但休眠恢复发生SLPI崩溃，已回退自动服务，不能称完整传感器适配完成。

## 自动启动与真实桌面接口

[服务实现](../../linux-port/ssc/samurai-ssc.py)每次开机建立私有RAM注册表，仅用本机只读配置、校准和A.11固件；核验303个来源文件、24个固件文件及固定文件服务/兼容库。持有文件服务直到DSP先停，PID与启动ticks/可执行文件/参数匹配才发TERM，DSP未离线时保留服务及供电。每boot只允许一次启动，失败或停机后明确拒绝重复启动，避免掩盖186尚未解决的共享池问题。15项实际生命周期函数检查通过，覆盖错误顺序、陈旧身份、PID复用与重复启动等。[策略检查](service-policy-validation.json)

原rootfs文件完整备份后，临时安装独立libssc目录、固定hexagonrpcd和OpenRC依赖；系统`/usr/lib/libssc.so.2`及APK数据库保持。当前已用过SLPI的旧boot调用start被明确拒绝，未启动DSP。[安装](service-installation-validation.json)

一次当前身份/分区/模块/资源排空门控的受控热重启，各只发一次RESTART2与fastboot reboot，未刷分区。**新boot204.12秒实际自动启动成功**：SLPI/ADSP/modem running，SensorProxy由OpenRC启动并从maps确认加载独立兼容库；HasAccelerometer/HasAmbientLight/HasProximity均1。Phosh、声卡、Wi-Fi5180、taint0、0秒日志及九类所列启动故障0；hci_uart185加载build-id匹配、BlueZ原配置/配对密钥保持、关/未连接。[开机验证](reboot-runtime-validation.json)

普通SSH下`su cy122`发Claim被原Polkit策略拒绝。检查确认策略仅允许active本地会话，不能因此修改策略放开后台访问。第二试验只把一个新建、即将退出的测试子进程加入已激活Wayland会话的cgroup，再降为UID10000；通过elogind GetSessionByPID核对Active/seat0/wayland/UID后，实际三项Claim/Release全部成功，策略文件未变。没有迁移既有桌面进程或打开应用窗口。

[实际桌面客户端](persistent-client-r2-validation.json)：UID10000访问通过；默认持久服务下原装CLI陀螺仪90、磁力计14、罗盘17条，退出/disable均0，daemon身份与RAM状态保持、九项所列故障增量0。手机平放方向undefined、光照0 lux，人工运动/旋转、亮暗响应及绝对精度仍未验收。

## 休眠失败，不能以PM回调通过替代传感器恢复

保持默认SSC及SensorProxy运行、蓝牙关/未连接，RTC预检后只提交一次`s2idle`。Linux suspend_stats在失败后为success1/fail0，trace记录2422个PM callback end、err均0；**恢复后约31ms收到SLPI fatal**：`err_qdi.c:964:EX:sensor_process:0x1:frpc_dsp:0x6e:PC=0xb2065188`，remoteproc进入crashed。恢复后的SSC健康检查失败，四项测量未执行。整轮明确失败，未重试start或注入其它crash。[实机失败](persistent-suspend-failure-validation.json)

实际执行的[r1脚本](test-persistent-suspend-r1.py)存在证据采集缺陷：per-CPU字典键误用共同父目录，最终仅保留一个CPU统计；返回后先检查健康，尚未持久化驻留时长就异常退出。因此不宣称全部CPU overrun为0，也不宣称实际休眠45秒。原脚本、失败现场与有限证据全部保留。[追踪范围](failed-pm-trace-scope-validation.json)。修正后的[脚本](test-persistent-suspend.py)保存各CPU及早期时长/统计，但尚未另跑一次，不把源码修正称作硬件PM通过。

该fatal是Linux恢复后发生的真实DSP故障，不能从err_qdi文本直接断言电源、VMID或文件服务冻结就是根因。后续应结合FastRPC、GLINK、IOMMU及userspace freezer时序定位；186共享池停启−22也仍独立开放。没有试遍未知权限mask或忽略SCM错误。

## 回退与最终现场

先停SensorProxy，再对crashed SLPI执行正常shutdown；DSP离线后才停文件服务/关闭供电，恢复原firmware指针与recovery，完整封存RAM注册表和尝试的部署。随后删除本轮自动启动项并原子恢复原rootfs文件，原始系统库/APK数据库仍保持。[回退](rollback-validation.json)。清醒状态通过结果继续保留，但这个自动方案不作为默认已验收修复。

[755.26秒最终检查](final-validation.json)：SLPI offline/供电0，ADSP/modem running，Phosh与Wi-Fi5180正常；临时proxy/daemon已停，自动服务已回退，taint0。全boot保留SLPI fatal/crash各1，所列WARN/Oops/GPU/ASoC/蓝牙重组/SCM错误0；原来源/NV保持。失败后没有额外重启或刷写。

本次Windows新USB NCM接口丢失原IPv4地址，首次SSH不可达；添加临时地址被系统拒绝，未强行提权。改用USB链路IPv6和相同严格HostKeyAlias/原主机公钥核验恢复连接。初次IPv6候选缺zone的格式检查失败保留，补齐当前已核对接口scope后连接成功；实际endpoint只存私人目录，重启后必须重新枚举。公开脚本不包含设备IPv6/MAC。

完整私人归档SHA核验见[导出](evidence-export-validation.json)，原始材料在`E:/edk2-samurai-out/kernel188`及手机k188目录。继续处理SLPI/FastRPC PM与生命周期，再推进GPS UTC/aiding及桌面定位、实体camera PM8008/CCI/C-PHY和蜂窝SIM/IPA业务；蓝牙185修复保持，不把扫描当成连接或音频验收。
