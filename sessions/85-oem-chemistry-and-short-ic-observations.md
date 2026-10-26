# Session85：原厂化学类型查询、短路 IC 无应答与 Android 温补分支

日期2026-10-10。用户已允许实机测试并要求注意充电安全。本轮沿用session83固定的
官方Android R与cyborgdc2000 Android16参考，完成固定查询和离线来源审计。
没有更新内核/设备树/initramfs、重启、开关屏或写分区，没有修改充电/保护参数。

## 实机结果

| 项目 | 本轮直接证据 | 边界 |
|---|---|---|
| 短路 IC | QUP15、0x58、SMBus READ BYTE DATA寄存器00首次身份查询返回ENXIO，退出1 | 没有读到身份；未继续02阈值/03模式；不能证明器件不存在或保护失效 |
| 化学类型 | 固定MAC004b，3e请求、等待1ms、40读4字节为4c494f4e，即LION | 化学标签不是唯一器件/标定ID，不建立2719的保护阈值映射 |
| 均衡状态 | 原厂0054的4字节为86030000；整块echo/长度/checksum通过且与4字节读一致 | OEM位28为0；不据此解码其它未核实保护位 |
| 身份门槛 | 旧式FFA5、扩展2719和11字节FW2719000400060003850200精确匹配 | 只有原厂已核实字段可查询，未放宽通用TI状态工具的2610门槛 |
| 测温/电流 | 标准06=3043、28=3032，暂按0.1K换算为31.15/30.05°C；0c瞬时−2mA、14平均0mA | 不能由两温度不同证明独立热敏接线/校准正确 |
| MP2650 | 三次各12个固定配置读，36读与session84末次原始值完全一致 | 没有查询故障REG14、启ADC、复位或改变配置 |
| 显示 | 1289.30/1289.33、1859.17/1859.27、2477.32秒采集均taint0、帧超时0/下溢0 | 77首次接管、80两次超时仍开放；没有新增光学/休眠/90Hz验收 |

最终电量计报告99%、8.638V、31.2°C、平均0mA和Not charging。主线目前只有电池
power_supply，未接入充电器侧输入/故障/控制接口。接近满电的0mA不能证明充电慢，
电量计HEALTH=Good也不是整个充电保护链通过验收的证据。

当前#85 boot ID仍为f02d218a-cc7d-4b92-8858-c8eeaeab5777。display实例on1、nop/mono、
2051KiB/CPU，snapshot:count=1仍待真实故障触发。没有清除快照或自动恢复显示。
长时间空闲的环形缓冲可自然覆盖旧事件，不据此称完整空闲跟踪无损。

两次分区哈希与session84保持一致：

| 范围 | SHA256 |
|---|---|
| boot前6682624字节 | 08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 |
| logdump完整64MiB | 60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b |

## Android16参考怎样处理，主线可以怎样参考

[cyborg设备配置](https://github.com/cyborgdc2000/android_device_realme_samurai/blob/af8af4614d5ab0c7e6c47bd8742a2e8c90a00f5f/BoardConfig.mk)
选择samurai_defconfig及kernel/realme/sm8150。session83已核实其lineage-23.0固定提交
1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1的版本为4.14.356-openela-rc1；官方Android R
23172a1571bd91156032cc9fef16284a82b63d2c为4.14.190。用户确认作者和Android11底包，
但历史安装固件的精确构建提交仍未知，不能把当前固定提交称为当时精确源码。

这套Android参考使用MP2650、OPLUS电量计/温控/短路检测与快充MCU接口，系统上层
版本变化没有把它自动替换为主线充电实现。主线可参考寄存器协议、GPIO、双串最高
单节电压、温区、电流/电压限制及事件处理；需要适配Linux power_supply/regulator/
thermal等接口和本机失联安全行为。配置或源码存在不能证明此前Android的每项保护
实际生效，也不能证明当前Linux的保护已经通过验收。

本轮新增的两套oplus_bq27541.h完全相同，SHA256为
58c68c362fc031eb73884a59e121ba25918e6728b37572df4116f8e1277e270e。
它们定义BQ28Z610旧式类型FFA5；这与session80早期源码结论一致，并非新发现的身份
异常。扩展2719与TI文档2610的精确变体差异仍未解决，不查询0051/0053/0072。

两套gauge源码SHA256仍为0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87。
原厂化学类型查询是004b，不是另一个ChemID命令。温补布尔属性
qcom,bq28z610_need_balancing在两套选定gauge节点和同一手机最终Android DT归档中
均不存在。归档节点soc/i2c@0xc94000/bq27541-battery@55的batt_bq28z610存在，原始
归档SHA256为e3329db4f3568252286489abd2ae27b9cbd0c711a2c5d790ebfba80fffc5b56b。
因此按该归档和选定源码，OPLUS动态均衡温补分支没有被DT选中。不能推广成所有板型
都不需要温补，也没有因此修改温度、化学类型或标定数据。

原厂FFA5分支把reg_ai改为0c瞬时电流，本机主线bq28z610表则用14平均电流作为
CURRENT_NOW来源。本轮保留两种原始读数和语义差别，没有更改主线寄存器表。

[短路IC源码](https://github.com/cyborgdc2000/kernel_realme_sm8150/blob/1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1/drivers/power/oppo/charger_ic/oplus_short_ic.c)
会在初始化身份多次读取失败后将exist置false；OTP检查在未就绪或exist=false时返回
true。已声明存在后的持续OTP读失败又有不同处理，不能把所有错误路径混为一谈。
本机这次单次ENXIO没有执行其初始化，也没有执行OTP读。源码允许缺器件继续的行为
不能作为独立短路保护正常的证明。其阈值宏为44，错误日志里43是过时文案；没有写阈值。

[MP2650源码](https://github.com/cyborgdc2000/kernel_realme_sm8150/blob/1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1/drivers/power/oppo/charger_ic/oplus_mp2650.c)
与官方有5项WPC初始化差异，但两套仍复位并关闭硬件安全计时器，不能直接移植并执行。
当前继承CHG_EN=1、NTC/watchdog关闭、终止/12小时安全计时器开启；这不是推荐设置。
“未接入Linux充电控制”指没有主线策略接口，不代表硬件充电使能位为0。

## 查询与审计边界

read-short-ic.c守卫QUP15 of_node、SMBus能力和I2C_SLAVE地址所有权，仅允许00/02/03
READ操作；00失败立刻停止，没有FORCE/扫描/重试/初始化/解锁或OTP读取。
read-stock-chemistry.c复用session80已审计的客户端/驱动/单观察者守卫，精确核对旧式
类型、扩展类型和FW后仅执行004b/0054。错误适配器/dev/i2c-0在I2C访问前拒绝，退出2。
继承源码含有其它工具入口，但本工具argc与入口固定，未执行通用status列表。

I2C线路含寄存器选择和MAC请求写帧；配置数据写为0。O_RDONLY本身不限制ioctl，
安全范围来自固定入口、白名单、身份/FW守卫和失败即停。没有解封、NVM/OTP、FET/OTG、
MCU刷写、GPIO切换、充电参数写入或分区写入。

audit-observations.py离线验证3份tar/gzip、26原始成员中的23个设备生成哈希、响应
echo/长度/checksum、4字节与整块响应一致性、温度/有符号电流、MP前后/84基线和分区。
audit-sources.py验证两套头文件、gauge/short/DT来源哈希、最终归档布尔属性和错误分支。
最初日志审计把debug/ramoops字符串误判为BUG/Oops，已改为词边界匹配后通过，未删日志。
全部原始字节保留；公开dmesg以mtime=0 gzip存储，完整源码/头文件、归档、二进制工具、
镜像和配置留在E:/edk2-samurai-out/kernel85或原私人目录。

## 下一步

充电仍需精确2719保护映射、短路IC通信/独立保护依据、热敏校准、USB实际输入预算及
主控失联安全实现。不能把满电0mA当充电速率失败；不直接执行OPLUS硬件初始化。
先保留显示故障快照监测和现有数据，再逐项接入充电、无线/音频及其它未验收硬件。
全硬件目标active；本轮不是充电控制或快充验收。
