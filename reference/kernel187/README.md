# 187：本机A.11 SLPI惯性流与标准客户端实测

2026-10-15。当前仍kernel183、boot/DTB172、modules132且仅hci_uart185覆盖；完整外设goal active。本阶段首次证明本机加速度计、陀螺仪和磁力计通过SSC实际出数，尚未部署自动开机服务。

## 固件与实际采样

使用[186提取的官方同机型A.11](../kernel186/README.md)，独立只读路径`qcom/sm8150/realme/samurai-a11-r187`，保留原00121文件。没有刷写modem或其它分区，不导入外机校准。原厂配置与校准只复制到RAM；磁力计配置继续使用113已校验的转义修正。原FastRPC模块保持，186失败的生命周期候选未恢复。

首次新固件启动返回0，全量查询51个实例，accel/gyro/mag各一个；wise_light仍存在、ambient_light为空。原始光线探针72个测量、可靠72、非法帧0、五个QMI操作成功且disable ACK通过，lux为0至1。[首启](a11-first-validation.json)。隔离SCM/GLINK追踪8核overrun均0，但请求与完成事件不是一一配对，也不包含真实owner mask，不能据此宣称共享池生命周期已修复。[追踪范围](trace-first-validation.json)

DSP先停、文件服务后停、供电关闭，恢复原firmware指针。随后根据当前身份做一次受控热重启，未刷分区；新boot的89.32秒原生桌面/声卡、Wi-Fi5180、ADSP/modem running、taint0及九类所列错误0。所有784模块树文件中仅hci_uart185覆盖。

新boot完整[用户态实测](a11-userspace-validation.json)：

| 通路 | 结果 |
| --- | --- |
| accel原始流，25Hz请求 | 204测量、可靠201，模长均值9.8025 |
| gyro原始流，25Hz请求 | 202测量、可靠197；启动瞬态保留，未验收绝对精度 |
| mag原始流，25Hz请求 | 197测量、可靠197；模长约91.23，未验收绝对精度/当地磁场 |
| 三种原始流共同检查 | 时间戳严格递增、非法帧0、四次QMI操作成功、disable ACK通过 |
| 原装ssccli | 加速度129、陀螺仪120、磁力24、罗盘27、光线24条；五项退出0并正常disable |
| 原装SensorProxy 3.9 | HasAccelerometer/HasAmbientLight/HasProximity均1；同一D-Bus连接三项Claim/Release成功，TERM退出0，LightLevel为2 lux |

SensorProxy和CLI使用184候选库的独立`LD_LIBRARY_PATH`及`LIBSSC_LIGHT_DATA_TYPE=wise_light`，系统库和APK数据库未改变。原始三轴探针独立于libssc，协议测试覆盖packed/unpacked、非法长度/维度/状态及非有限数值，见[线协议检查](vector-wire-validation.json)。

手机平放时加速度均值Z约9.80，XY接近0，SensorProxy方向为undefined；未做人工运动、屏幕方向/自动旋转、亮暗变化或准确度验收。不能把这些短流测试称作完整日用传感器适配。默认CLI的gyroscope帮助列表和单位文字也不能作为实际协议单位依据。

## 当前现场与失败记录

完整试验start/采样/stop均0，临时SensorProxy已退出，SLPI offline、供电0、原firmware指针恢复、taint0；源码/NV核验保持，九类所列错误增量0。当前boot已用过一次SLPI首启，继续启动前需处理生命周期缺陷或有门控的重新启动整机，不能盲目重复start。

运行态采集尚未结束时，首个用户态准备调用因boot检查文件未就绪而被拒绝，DSP没有启动。确认采集完成后才实际启动一次。错误的`/usr/sbin/iio-sensor-proxy`只读查询失败保留，实际路径为`/usr/libexec`。首次未压缩SCP退出非零，保留部分下载；随后压缩归档独立下载并核对SHA256 `7ca7575f5ae1974e077c7ad444e5d7c8fb7c0077e7b750359a1ba5954755fedb`，完整检查成功，不重复运行试验。

私人证据在`E:/edk2-samurai-out/kernel187`和手机`/var/lib/samurai/k187*`。下一步是持续文件服务、正确OpenRC依赖与开机接入，同时继续FastRPC停启/PM、GPS真实fix、实体摄像头与蜂窝业务；不将这些待办标为完成。
