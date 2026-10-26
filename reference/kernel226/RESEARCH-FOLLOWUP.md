# 三路只读研究的后续结论

用户已授权并行研究；本轮子代理均未改文件或操作手机。用户明确未插SIM，因此缺卡/缺GW主会话与该条件一致，注册/数据/通话留待有卡验证。以下候选未部署，不替代实体功能验收。

## 后摄：补齐P provider前置，先准备IMX319

直接在内存解析本机stock boot基础DTB及两个DTBO：基础DTB没有PM8008节点；两份overlay的P/Q均只声明S8C到`vdd_l1_l2`、对应`pm8008_en`，没有四类PLDO父输入。基础DTB继承也不能填补L4P VIN，不能以BOB/VPH或固定电源占位。

原厂相机的`cam_bob-supply`路径只经`regulator_set_load()`请求功耗/PWM模式，并不enable BOB或建立PLDO供电关系。[生产相机helper](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/media/platform/msm/camera/cam_sensor_module/cam_sensor_utils/cam_sensor_util.c)

原厂LDO先启用`pm8008_en`的0x950 bit0，再操作DTS已声明的parent，最后enable LDO并等VREG_READY；未声明PLDO输入时原厂不获取该parent。192已有两芯片bit0=1采样，不能据此认定当前问题只是漏全局enable。[生产regulator驱动](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/regulator/qcom_pm8008-regulator.c)

当前MFD地址锁只保证串行，不保证Q先迁至4、P后释放到8。若普通P节点先probe解除reset，Q的默认地址8会被占用。应建立显式双芯片初始化依赖；Q失败时P保持复位，保留195失败重assert。原厂整体reset函数还涉及功放/指纹，不能搬进sensor runtime PM，也不能按DTS书写顺序假定probe顺序。

IMX319已有主线模式/控制实现，是优先离线候选；新增DT资源路径时保留ACPI D0行为，新增OF/绑定、VANA/VDIG/VIO/reset/clock及runtime失败反向回退。设备自身引用211已验TITAN_TOP域，不能只靠CCI父域。P父网络和双芯片依赖未解决前不安排上电；GW1的C-PHY新BIN解码仍待独立厂商XML核验。3M5缺CUSTOM_GPIO属性按原厂valid检查后的no-op处理，人像实物型号保持未知。[相机驱动规范](https://docs.kernel.org/driver-api/media/camera-sensor.html)

## FastRPC：原三补丁不能原样部署

Qualcomm的2026-10-07系列9个hunk在本地源码中唯一匹配，子代理仅在内存应用并检查189 freezer改动保持。经核实的Linus/char-misc相关分支当时均未包含该系列；不声称已合入或本机验证。[系列](https://lists.openwall.net/linux-kernel/2026/10/07/473)

1/3只提前kref，仍留下misc可见时channel锁、列表、idr、rpdev未初始化的open窗口。完整候选需要可见前初始化与ready发布，并处理第二节点注册失败时首节点已被open的生命周期。[1/3](https://lists.openwall.net/linux-kernel/2026/10/07/474)

2/3唤醒poll waiter是防御性修正；当前SM8150不在poll白名单，不能据此声称SSC已改善。[2/3](https://lists.openwall.net/linux-kernel/2026/10/07/475)

3/3仅排空invoke计数仍可能漏掉“计数已增加但尚未加入pending”的请求；调用线程退出后异步put_work还可能持有context/DMA。因此计数0不等于可拆context bank。须覆盖请求准入、所有退出、异步最后引用和DMA生命周期，再做隔离构建与SSR验收。没有证据说明它解释共享池reclaim−22。[3/3](https://lists.openwall.net/linux-kernel/2026/10/07/476)

## GNSS：扩展NMEA是兼容候选，不是零CNR修复

当前固定MM和libqmi读取旧NMEA字段；核对的libqmi main `d9e8af5c…`仍未定义expanded getter。Qualcomm定义扩展TLV0x10出现时普通字符串为空；本机226确实如此，但此次扩展内容仅PQWP7厂商debug，不能声称漏了标准定位句或解释无fix。[libqmi定义](https://github.com/linux-mobile-broadband/libqmi/blob/d9e8af5cae7fdf9749baf87606568d3af4d03082/data/qmi-service-loc.json#L335)、[Qualcomm定义](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/location_service_v02.h#L2435)

合适的兼容候选是在libqmi JSON增加可选TLV0x10字符串getter，最大4095字节，不加内容长度前缀；MM选非空expanded，否则legacy，并在MM层按CR/LF逐句更新GPS与cache。避免双字段重复分发，不跨回调保存借用指针。新MM依赖新getter，需匹配库/headers/GIR/包修订并成对回退；同SONAME不足以保证兼容。超长字符串可能被现有libqmi截断，不能把截断末句计作有效fix。

226已用原始QMI工具支持普通/扩展SV及NMEA，公开报告仅输出计数和范围。实际RF搜星仍未完成；HIGH会话参数对照、当前辅助数据有效期与接收条件分别验证。[正式对照](accuracy-ab-validation.json)、[接收器调试](receiver-debug-validation.json)。
