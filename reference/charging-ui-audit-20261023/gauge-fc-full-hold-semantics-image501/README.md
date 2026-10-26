# Image501：gauge FC 与正常 Full 保持

当前证据没有建立 FC 位映射错误。Image501 的原 BQ28Z610 表仍读取 `0x0a` word，选用 `BQ27Z561_O_BITS`，因此 Full 判定位为 bit5／`0x0020`。这与已缓存的 TI SLUUA65E §12.1.6（69–70页）一致；通用 BQ27xxx 的 bit9 没有用于该 chip，MAC GaugingStatus0056 的 FC bit1 则属于另一份状态字，不能互换。501只改变显式 opt-in 时 NOW/STATUS 的电流来源，Full 掩码未变。

本轮保留原件的两份 telemetry 都是 flags192／`0x00c0`，即 INIT、DSG 为1，FC为0。标准 getter 的顺序是：FC为1先报Full，否则按有符号电流的正／负／零报Charging／Discharging／Not charging。对应本轮 NOW=0、AVG=0、capacity100、Not charging 是一致语义；顺序读取不等于一次原子 I2C 快照，但没有看到相矛盾的 FC 证据。

R8 `full_cause=3` 精确表示 `SM_FULL_HARDWARE`：完整安全采样时曾取得 MP2650 REG13 CHG_STAT终止事件，随后保留 Full 事实并置 `desired_enable=0`。它不是 gauge FC，也不是本轮由零电流触发的软件计数。正常充电器保持与 gauge FC未置位可以同时成立；软件保持不会改写 gauge flags。已缓存 OEM 源的 `set_battery_full()` 本身也是空操作，不能据其通用头里的 bit9 定义认定当前 BQ28 映射应改成 bit9。

TI §4.6–4.7（26–27页）把 RSOC 与 FC 分开配置。RSOCL关闭时，大于99%的分数允许显示为100%，不要求先完成有效终止。FC可以由启用的 VCT、电压或 RSOC条件设置，并受独立清除条件影响；容量100%与零电流都不能单独推得FC。

标准手册的有效终止同时要求处于充入状态、平均电流低于配置的 taper、电芯电压进入配置的充电目标窗口，并在连续两个40秒区间取得足够的正向累积电量。当前已停充／DSG为1的零电流时刻并不在新增这份 VCT证据。较低的继承CV可能使配置的电压条件无法达到，但 **4.3625V不必然阻止FC**：条件包含终止电压窗口；例如仅用手册默认75mV作说明，4.3625V相对4.4V仍可能处于窗口。默认值不是本机配置。

本机扩展身份为工厂族 `0x2719`，既有资料没有把它完全映射成标准 `0x2610` 固件。当前白名单也没有读取实际 FC/SOCFlagConfig、RSOCL、gauge ChargingVoltage、taper和终止窗口。因此本报告确认标准寄存器布局和现驱动语义相符，不能冒称已实测2719完整 FC设置／清除行为，更不能据手册默认值诊断其未置位原因。

来源与完整摘要见 `review.json`：缓存 TI PDF SHA `f62ec12b…e4139`，精确原363 BQ源码 `b2cd415a…aec69e`，501候选 `0aa3c533…88ffe`；R8两份 Full源码按冻结源码整合交付核对，现场原件按已公开健康收据摘要核对。未新增I2C、设备、网络、构建或旧测试。现阶段不建议修改FC掩码、抬CV、解除Full，或用capacity100强制Full／Charging。
