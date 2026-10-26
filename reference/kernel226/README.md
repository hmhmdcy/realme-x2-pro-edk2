# 226：GNSS原始测量与辅助数据四轮对照已完成

2026-10-16。当前仍boot219/Image183、e49/fae1、libcamera r13/config-r8，没有刷写或重启。用户确认无SIM、室内窗边且房间关灯；缺卡状态符合条件，蜂窝业务留待有卡。[基线](baseline-validation.json)、[完整结果](final-validation.json)。GNSS仍没有真实fix/正CNR，不能把本轮诊断写成已适配完成。

同一R3二进制和解析器分别做默认/HIGH×辅助前/辅助后四轮，每轮观察90秒。每次同CID注册、Start、收原始报文、同session Stop、释放CID并close；请求只在HIGH轮多水平精度TLV，其余固定。HIGH确实回读3，但未恢复接收。[原始精度对照](accuracy-ab-validation.json)。

| 条件 | 精度读回 | XTRA调试掩码 | 有效SNR字段（含双格式重复） | 正CNR / TRACK |
| --- | --- | --- | --- | --- |
| default | 1 | 0 | 748 | 0 / 0 |
| high | 3 | 0 | 748 | 0 / 0 |
| default-aided | 1 | 31 | 690 | 0 / 0 |
| high-aided | 3 | 31 | 746 | 0 / 0 |

四轮分别89/89/89/90次SV事件；每轮29次同时返回普通/扩展列表，余下60/60/60/61次未提供列表，后者不计有效0。报告的有效SNR均为0、状态均SEARCH；位置status4为USER_END（主动停止），不是TIMEOUT3，也未见PHONE_OFFLINE6或有效fix。固件同时返回两列表，所以累计字段数不代表唯一卫星数。session事件没有返回sessionId，不宣称已核对其匹配。

初两轮没有假定本次启动的辅助数据有效。扩展PQWP7解码表明只有本地almanac；PQWP3的XTRA掩码0、PQWP4星历位0。随后核对并运行现有helper一次：UTC ACK/完成通过，独立固件有效期0→168小时，一次HTTPS下载和标准MM注入。辅助后PQWP3掩码变31、GPS有效XTRA位数30，PQWP7来源从local4转为other-server3。这比“API成功”更进一步证明数据被接收器采用，但仍无正CNR/TRACK。[辅助刷新](assistance-refresh-validation.json)、[前后debug](receiver-debug-aided-validation.json)。XTRA轨道辅助和广播星历有效位分别记录，不由后者0反推注入失败。

GETcriteria在Stop后仍返回最后的HIGH，不代表活动会话；请求intermediate2与GET读回1不一致，分别记账，不把GET当即时活动状态。Start/Stop只有ACK，不等待不存在的成功indication。四轮均观察engine ON→OFF，MM owner/定位属性、watch空闲/0workers、包数据库保持，taint/fault0。[辅助后最终健康](post-aiding-health-validation.json)。

诊断解析已补普通/扩展SV和NMEA、有效位/有限值/严格数组长度。缺失字段保留missing，不当0；扩展NMEA此次仅PQWP7厂商debug，不能说漏了标准定位句并据此解释无fix。合成的expanded-only/invalid/NaN/长度反例与真实四轮均通过。接收器ADC/AGC在变化，不证明天线/RF硬件正常。

预检错误原样保留：首基线误把apk详细说明当版本；R1/R2把0x32服务版本95误标成NMEA掩码且早期standalone枚举假设错误。R3已按固定IDL使用Get NMEA0x3f/掩码63、typed standalone4，服务版本95另列；R2完成采集/清理但包装器因漏扩展NMEA拒绝，不是设备崩溃。离线debug首版不接受空值的失败也私人保留。[更正索引](preflight-corrections-validation.json)、[主来源](loc-layout-source-validation.json)。

首轮私人归档87成员只覆盖辅助前；最终117成员含四轮raw日志、清理状态、辅助payload与最终健康，归档及每成员哈希已核对。坐标、NMEA原文、卫星身份、端点和私人归档指纹不公开。没有保存相机场景、改变照明、写NV、改DMS电源或配对蓝牙。[最终归档](final-evidence-aided-validation.json)。

当前证据不支持把精度字段或缺轨道辅助单独当作零CNR根因。下一步核对RF/LNA/时钟与OEM初始化；室内因素仍未排除，开阔天空/同机Android对照仍有信息价值。191/201已做online负对照、209已做UTC精度负对照，不盲重复。后摄P provider依赖、IMX319、FastRPC初始化发布/退出生命周期、BT phase5与全部外设继续推进，完整goal保持active。[三路源码结论](RESEARCH-FOLLOWUP.md)、[全清单](../../linux-port/docs/HARDWARE-STATUS.md)。
