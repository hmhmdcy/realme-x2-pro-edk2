# 209：UTC 精度单变量对照未改善接收器报告，核对常态相机缺口

在同一个 GNSS 会话内，将 UTC 注入不确定度从 1000ms 改为实测时钟界限加余量的 418ms。调用成功，但接收器仍报告约 6 秒不确定度，fix/正 CNR 均无改善。因此本轮没有修改或安装产品 helper，也没有将候选算法当作已验证的 GNSS 修复。当前仍为 207 第二次启动，209 没有重启、刷写或 RF/供电/NV 操作。

## 对照方法与结果

先重新核对设备身份和空闲状态：三个 DSP running、taint/五类 fault0、GPS0、Signals=false/rate30、BT 关闭且无连接。首次 chrony 观察为 Normal/Stratum3，按照 `abs(system_offset)+root_dispersion+root_delay/2` 得到约 178.67ms 界限。[基线](baseline-validation.json)、[时钟观察](inspect-clock-bound-validation.json)、[chrony 定义](https://chrony-project.org/doc/4.6/chronyc.html#tracking)

临时 DEBUG NMEA 掩码开启后，由 MM 启动一个连续定位会话，等待自动 helper 本轮 worker 完成，再采集原策略 25 秒。随后重新读取 chrony，当时界限约 167.87ms，加 250ms 传输余量、向上取整为 418ms，经独立 LOC client 注入当前 UTC，静置 3 秒后采集 60 秒。RF、固件、电源策略及辅助文件均未变；自动 helper 确认当前 XTRA 有效，下载和注入次数均 0。[辅助数据对照](assistance-control-validation.json)

| 观察窗口 | UTC 不确定度输入 | PQWM1 组数 | 接收器 TimeUncNs 范围 | 有效定位 / 正 CNR |
| --- | --- | --- | --- | --- |
| 原策略 25 秒 | 1000ms | 25 | 6.000016896—6.000134144 秒 | 0 / 0 |
| 候选后 60 秒 | 418ms | 60 | 6.000022016—6.000314880 秒 | 0 / 0 |

两阶段分别收到 184 和 427 条不同 NMEA，校验错误均 0，TimeValid=1、source3、恢复错误字段 0。418ms 请求 ACK 与完成 indication 均成功，往返约 23.15ms，小于预留的 250ms；这只证明 API 调用完成，不能证明基带采用了更小的输入误差。当前观测不支持把固定 1000ms 判为造成本机约 6 秒报告或零 CNR 的根因。[完整对照](utc-comparison-validation.json)

本机 SDK 将较新的时间来源字段称为 coarse time origin，枚举 UNKNOWN/AP/NTP/NTS=0/1/2/3，标注 since1.37。这里只核对库侧接口，没有证明 SM8150 基带使用该可选字段，也没有据此更换产品中的 UNKNOWN。[接口收据](inspect-utc-enum-validation.json)

纯候选算法核对了毫秒向上取整、正负偏差、样本年龄和频偏，以及无同步、本地时钟、非有限值、负误差和过期样本拒绝。候选仅保存在本目录，没有进入产品 helper/APK。[边界检查](clock-bound-validation.json)

## 恢复与当前健康

比较结束后，发送一次原 1000ms 输入策略的当前 UTC，ACK/完成约 23.44ms；关闭 GPS，恢复原 NMEA mask63、Signals/rate、释放 CID 并关闭设备。此动作恢复输入策略，没有将系统时钟倒退，也没有强制写入接收器内部估计值。唯一 worker 91.88 秒终态，引擎 ON→OFF，错误和内核故障增量均 0。

3301.29 秒独立检查再次确认 mask63/GPS0/Signalsfalse/rate30、无 GeoClue owner、BT 关闭无连接；watch 累计3/3，辅助窗口仍当前168h，三个DSP running、taint/五类fault0，NV源与原185模块/全部产品程序保持。[最终健康](final-health-validation.json)。48份本轮原生文件私人归档并逐成员核对，原始NMEA/时间服务器身份及归档指纹不公开。[归档](evidence-export-validation.json)

## 常态摄像头的具体缺口

同一 boot 做了只读设备树、媒体图、模块和源码核对，没有上电相机或采新图像：

- CAMSS 正常绑定，media0 有22个内部实体，缺少 IMX471。
- CCI0/CCI1 均 disabled；活动设备树没有 PM8008 或 IMX471 节点。
- 已安装模块树没有 imx471 和 v4l2-cci；当前配置没有启用 VIDEO_IMX471/V4L2_CCI，modules.order 不含 IMX471。已安装的 PM8008 仍是原模块，不能把200临时加载的开发模块当作已持久化。
- PM8150L S8C 为1.352V/users3；VIO LDO1 为1.8V/users0/state unknown，且无 phandle。unknown 是 provider 初始状态，不能写成已关闭或故障。

[实机图与供电状态](inspect-camera-normal-validation.json)、[安装模块](inspect-camera-installed-modules-validation.json)、[配置与源码](camera-source-inventory-validation.json)。

下一步按200已经取得实体RAW帧的前摄拓扑，补齐可持久构建/安装的传感器和CCI库、匹配PM8008模块及正常DTS资源，再验证正常启动的媒体图和取流。新DTS应从204部署的基线核对，不能拿旧canonical DTB22c1作当前板级树。PLDO四路输入网仍未知，不虚构供电父节点，完整冷启仍需验收。

GNSS 实际天空条件已向用户异步询问，尚未得到答复；不据此假定室内或室外，不阻塞其它适配工作。真实定位/RF、摄像头其它镜头与用户态、蜂窝真实业务、传感器精度/SSR、BT phase5、Wi-Fi/USB PM、完整充电及APK/rootfs整合继续属于完整目标。[当前检查点](../../NEXT-SESSION.md)
