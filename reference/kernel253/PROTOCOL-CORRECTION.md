# 253协议更正：0x7D是Wi-Fi AP数据，0x38才是UTC

2026-10-17，对照高通官方固定提交的`location_service_v02.h/.c`，发现250—252的文字说明把消息`0x7D`误标为UTC时间注入。正确对应如下：

| ID | 官方定义 | 本次验证 |
| --- | --- | --- |
| `0x38` | `QMI_LOC_INJECT_UTC_TIME_REQ_V02` | 必填TLV1为u64毫秒UTC，TLV2为u32毫秒不确定度；253专门构造该标准请求，ACK与完成均成功 |
| `0x7D` | `QMI_LOC_INJECT_WIFI_AP_DATA_REQ_V02` | 252原报文TLV1长1177/1226字节，并含AP附加数组，不是UTC所需的8字节时间 |
| `0x39` | `QMI_LOC_INJECT_POSITION_REQ_V02` | 某些位置注入也可携带时间字段，不能因没看到0x38就推断整个系统没有任何时间来源 |

250—252的原始包、数值统计、C/N₀、TRACK和无fix结果没有修改；更正的是消息名称及由它引出的“已经成功UTC注入”结论。252重新逐包统计，辅助窗口和HAL+DIAG窗口都没有0x38请求；0x39带有timestampUtc，但没有可选gpsTime/timeUnc。253另做真实UTC注入后，接收器时间来源7→3、不确定度约6.71→6.00秒，随后仍无正C/N₀或fix。

来源：[高通官方头文件](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/location_service_v02.h)、[对应IDL编码表](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/location_service_v02.c)。文件哈希沿用[221锁定记录](../kernel221/qualcomm-loc-source-validation.json)，实际构造器见[loc-time-probe.c](loc-time-probe.c)。这项更正已同步修改250/251/252当前说明，不以错误标注继续排除时间链路。
