# 221：GNSS星座配置与卫星黑名单只读核对

2026-10-16。保持boot219/Image183/e49前摄模块和完整libcamera r7/config-r2。本轮没有启动GNSS引擎、拍摄、重启、刷写、修改NV或校准。**新增只读诊断工具，缩小GNSS排查范围；尚未修复真实fix/正CNR。**

当前USB邻居经原公钥认证，建立`k221-baseline`启动guard。初版基线因`apk info -v`输出格式断言退出；保存已完成查询，随后直接解析已安装数据库完成核对，没有重放状态切换。[基线](baseline-validation.json)

## 新取得的接收机配置

参考高通维护的[location-apis-qcom](https://github.com/qualcomm-linux/location-apis-qcom/tree/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948)，固定提交及头文件、IDL编码表、调用实现三个文件的哈希。[源码记录](qualcomm-loc-source-validation.json)。以公开IDL的GET消息制作[独立诊断程序](loc-readonly.c)，不包含SET、START、位置注入、master注册或NV写入。

| 查询 | 本机实际返回 | 解释范围 |
| --- | --- | --- |
| 当前操作模式0x004b | standalone，ACK及indication成功 | 用已有类型化查询交叉核对原始消息路径 |
| 星座控制0x00bf | GPS=0；GLONASS/BDS/QZSS/Galileo=1；NavIC未返回 | 0为强制启用，1为系统内部启用；不支持“上述星座被整体禁用”的猜测，不证明已经RF跟踪 |
| 卫星黑名单0x00b7 | GLO/BDS/QZSS/Galileo四个掩码均0 | 仅这些已返回字段无屏蔽；SBAS/NavIC/GPS字段未返回，不能把缺省当零 |
| 多频配置0x00e1 | ACK result1/error57，无成功indication | 本机库的错误枚举名为WmsInvalidMessageId；该GET不被当前接口接受，不能由此断定硬件没有多频能力 |

当前普通查询的engine lock为mt，NMEA掩码63，DMS为shutting-down/MM PowerState1。mt针对网络发起定位，不等于锁住本机发起会话。191与201已有普通ON/online对照，仍无正CNR，本轮没有重复开启电源或把该状态直接认定为GNSS根因。

原生工具复用190隔离签名包SDK，在独立目录编译，通过系统运行库解析，未改已安装包数据库。[构建](loc-readonly-build-validation.json)。首次编译被SDK兼容头的deprecated声明和-Werror阻止，未运行；第二版成功完成四查询。[第二版](loc-configuration-r2-validation.json)。

审查后进一步明确等待阶段：提前indication仅缓存，不能结束尚在等ACK的循环；验证ACK服务/CID/事务号/消息号，不把畸形或传输失败响应算查询完成。最终版重编译、四查询复核一致，实测操作模式和黑名单的indication先于ACK；CID释放、设备关闭均成功。第二版没有观测到运行失败，不能把这次健壮性修改宣称为手机固件缺陷。[最终结果](loc-configuration-validation.json)

## 蜂窝状态与保留结论

两个UIM Card Status为no-atr-received；Slot Status均absent/active、逻辑槽1/2，MM failed/原因2、SIM对象无、bearer0。[UIM查询](uim-readonly-validation.json)、[完整槽位状态摘要](final-health-validation.json)。这与[191电源前后对照](../kernel191/uim-power-comparison-validation.json)相同，是本次启动复核，没有建立新的UIM根因，也不能反推物理未插卡。未切槽、供电循环或改卡锁。

## 最终状态与后续

[最终健康](final-health-validation.json)：同boot219、r7/r2的49条相机payload与e49模块保持，相机/CCI/CAMSS休眠、两前摄电源关闭且用户0、实验完整模式N。GPS0/Signalsfalse/刷新30，辅助服务空闲且未新增worker，chrony Normal；三DSP running，BT关闭无连接，taint及五fault0，NV源校验通过。两轮诊断都完整释放/关闭。[37成员私人原生归档](final-evidence-validation.json)已逐一核对，归档指纹及设备身份不公开。

用户仍在关灯的室内窗边；没有新的天空接收或Android射频基线。星座配置读取通过不证明天线、LNA、RF时钟或完整OEM初始化正常；不能用较新SDK的未返回字段或错误名猜测本机硬件。继续对照[realme/一加/OPPO材料](../kernel205/GNSS-RELATED-DEVICES.md)，保留209时间不确定度负结果，不盲写NV或猜GPIO。

相机手动曝光API、真实几何/CFA/颜色/延迟、后置四路及GPU ISP，蜂窝真实业务与其余[完整硬件目标](../../linux-port/docs/HARDWARE-STATUS.md)仍开放。室内暗场仍以RAW噪声、帧间变化和TPG区分暗光与传输故障；没有场景图像保存或照明动作。
