# 208：取得原厂 GNSS 接收器诊断，核对时间、ADC 与 XTRA

本轮在当前 207 第二次启动上，临时开启并恢复原厂 DEBUG NMEA，取得真实接收器状态。**GNSS 仍没有有效 fix 或正 CNR，完整适配目标继续开放。** 没有重启、刷写、修改 RF/供电或替换原厂 NV；产品程序保持 207 状态。

## 原厂接口与本机入口

固定提交的 [SM8150 SystemStatus](https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/57ced1dc07cd15aaedbee0f98a3384ac837c4ce5/core/SystemStatus.cpp) 定义了 `PQWM1` 的时间、时钟、ADC、增益与干扰字段，以及 `PQWP3/4/5` 的 XTRA、星历和健康掩码。[GnssAdapter](https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/57ced1dc07cd15aaedbee0f98a3384ac837c4ce5/gnss/GnssAdapter.cpp) 根据基带能力请求 DEBUG NMEA；本机当前 libqmi 已有 `DEBUG=0x20000`，不能用先前保存的旧 SDK 判断接口缺失。[固定源码收据](receiver-source-validation.json)

先只读取得原 NMEA 掩码 63，ACK、indication、CID 释放及设备关闭均完成。首个脚本误用当前库没有的 `fix-session-state` 信号，在开启 GPS 前退出；原失败保留，掩码 63/GPS0/客户端关闭确认。随后按实际信号列表改为 NMEA 和 engine-state，使用新 marker 提交一次 120 秒诊断。[原掩码](query-nmea-mask-validation.json)、[首次失败及清理](debug-nmea-validation.json)、[修正后会话](debug-nmea-r2-validation.json)

本次临时掩码为 131135，MM 启动后仍保持。旁路 LOC 客户端收到引擎 ON/OFF，但没有 NMEA；在同一会话中读取 MM 的 GetLocation，20.35 秒取得 147 条不同 NMEA，包括 20 条 PQWM1、各 20 条 PQWP2—6、20 条 GGA、4 条 GSV。因而本次旁路空流不能作为“基带没有输出”的证据。全部句子校验通过；GGA/RMC 有效定位、正 CNR 和 raw 坐标字典仍为零。[MM 观察](observe-mm-debug-validation.json)、[独立 NMEA 分析](analyze-mm-nmea-validation.json)

## 实际诊断结果

| 项目 | 20 组 PQWM1 的观察 | 证据边界 |
| --- | --- | --- |
| 时间 | TimeValid 始终 1，TimeSource 始终 3；TimeUncNs 约 6.0004 秒 | 历史公开 LOC IDL 将 source3 定义为外部注入，不能当作卫星导航时间已解码 |
| 接收器数据 | PGA −6 至 −4，ADC I 142—174、Q 134—164；GPS AGC 0.21—1.55 | 这些字段有变化，尚无本机正常接收基线，不能据此宣布天线、LNA 或 RF 接收正常 |
| 干扰与恢复 | GPS jammer 字段 64—65，恢复错误字段均 0 | 尚未确认该固件 jammer 值的正常区间，不将其直接判为干扰过高 |
| 辅助数据 | PQWP3 有效掩码 31；GPS/GLO/BDS/GAL/QZSS 有效预测数据分别覆盖 30/21/13/26/3 颗卫星 | 是接收器内部对 XTRA 的报告，比仅查询 168 小时窗口更直接；仍不等于真实跟踪这些卫星 |
| 星历 | PQWP4 对这五类星座的接收星历掩码均为 0 | 与当前无真实接收证据一致，不能单凭此定位 RF 故障位置 |

[时钟/ADC 分析](analyze-mm-debug-validation.json)、[XTRA/星历/健康分析](analyze-aiding-debug-validation.json)。PQWP2 含位置字段，原始内容及所有 NMEA 都只保存在私人目录，不公开或拿来冒充当前定位。

独立解析器保留缺省值，不把空字段或 NaN 当成零；负数、小数、64 位整数、可选后缀、校验和和截断用例已核对。[解析器检查](parser-validation.json)

## 清理与部署状态

120.29 秒诊断完成后，掩码读回 63、GPS0、CID 释放及设备关闭完成，引擎状态为 ON→OFF。2177.49 秒独立健康检查再次读回掩码 63，Signals=false/rate30，无需再次归一化；watch 累计 2/2，本轮新增一个正常 GPS 会话。三个 DSP running，taint 与五类内核故障均零，NV 源校验保持，原 185 蓝牙模块及 207 产品程序哈希保持，辅助窗口独立查询仍有效。[最终健康](final-health-validation.json)

本轮 57 份原生文件私人归档并逐成员核对，包含失败、原始 MM 数据和诊断脚本；归档指纹不公开。[归档](evidence-export-validation.json)。本轮没有修改或安装产品程序；采集脚本位于手机私有 `k208-loc-tools`，不存在待确认的 worker 或重启。

## 下一步

先依据实际时钟误差核对 UTC 注入精度：当前服务固定填 1000ms，公开 LOC IDL 定义该字段单位为毫秒；接收器报告约 6 秒的不确定度，二者的具体处理关系尚未验证，不把它写成定位根因。[IDL 收据](loc-idl-source-validation.json)。chrony 给出的误差界限包含系统偏差、root dispersion 和一半 root delay；未来调整应基于实测界限与传输余量，不能盲目填写极小误差。[chrony 定义](https://chrony-project.org/doc/4.6/chronyc.html#tracking)

原厂接收初始化、RF/天线与真实天空条件继续排查；MCFG、XTRA 和时间有效不代表这些已验收。相机常态 sensor 图/PLDO 冷启、真实蜂窝业务、传感器精度/SSR、BT phase5、Wi-Fi/USB PM、radio APK 与完整 rootfs 整合等仍属于完整目标。[当前检查点](../../NEXT-SESSION.md)、[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)
