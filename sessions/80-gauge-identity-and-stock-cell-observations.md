# Session80：电量计身份差异与原厂双电芯读取

日期：2026-10-10。目的：补充本机充电安全依据，回答权限是否限制排查。
手机保持 session79 boot，本轮未刷分区、重启或开关屏；没有改变充电配置。
原始数据、工具和校验见 reference/kernel80；可执行文件、镜像和完整手册留在私人输出目录。

## 结果

权限足够，没有工具审批或文件/联网权限阻挡。原厂双电芯接口实测成功：
两节均为4321mV，相加8642mV，与同次标准电池包电压8642mV一致。
这是一份静态测量，不能证明均衡动作、过压/过温保护阈值或实际充电控制通过。

身份查询有新的差异：旧式 DeviceType 为0xFFA5，符合原厂驱动；扩展 DeviceType
两次均为0x2719，命令回显、长度和校验和一致。TI 官方确认的 BQ28Z610 型号号是
[0x2610](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/979612/bq28z610-device-type)。
本轮未建立0x2719到确切器件/固件的映射，不能据此断定是假电池、替代芯片或某个TI型号。
设备树名称和主线驱动的固定Manufacturer字符串也不是芯片身份测量。

FirmwareVersion 0x0002 的11字节有效负载为2719000400060003850200，长度15、校验29，
校验通过；保留原始字节，不在版本兼容性未核实前猜测字段字节序和版本含义。
005x保护/制造状态和DAStatus2/0072独立温度没有查询，没有假定TI全部接口都适用。

## 请求边界及工具验证

核对 [TI SLUUA65E](https://www.ti.com/lit/pdf/sluua65) 的12.1.28–31、12.2、
Table12-2与12.2.37，以及
[本机原厂电量计源码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/gauge_ic/oppo_bq27541.c)。
手册允许封存状态下读取多种R命令；本机身份差异出现后，执行范围限于原厂也使用的身份、
固件和双电芯查询。原厂get_2cell_voltage采用3E 71 00、等待1ms、从40读4字节。

这些请求帧本身包含I2C写，改变命令响应缓冲区；不是“完全没有I2C写”。本轮共5个固定
查询请求：DeviceType三次、FirmwareVersion一次、原厂电芯查询一次。没有参数数据、
checksum/length、NVM/OTP、解封、复位、标定、保护/FET/OTG切换或快充MCU操作。

read-bq28-status.c检查QUP15 of_node、55地址客户端、ti,bq28z610兼容串及实际bq27xxx
驱动。主线BQ28路径的dm_regs=NULL、unseal_key=0、NVM更新配置关闭，且没有MAC查询，
因此普通轮询不会替换本轮MAC响应。I2C_RDWR并不自动遵守O_RDONLY/地址占用限制；
本轮依据已审查的绑定驱动操作，不使用FORCE、不解除绑定。

初始工具遇到非2610立即停止，未发送FirmwareVersion或后续状态请求。之后分别用固定
原厂身份/固件工具取数；电芯工具先当场确认旧式FFA5，再执行唯一0071请求。原厂4字节
结果与额外36字节块的前两节一致，块回显0071、长度36、校验f5通过。

所有工具以aarch64-linux-gnu-gcc -Wall -Wextra -Werror -O2 -static构建；源文件/设备
二进制SHA对应。解析器自测通过有效32/2字节、错误回显、非法长度和错误校验；触摸、
MP2650适配器均拒绝并返回2。没有自动重试或任意地址/寄存器/命令参数。
read-gauge-device-type.c等包含共享解析/guard实现，实际入口仍仅固定请求；这些工具
是本轮诊断记录，不能绕过身份门槛直接重放全量status模式。

单独Control字读取发生在前一查询约286秒后，返回620b；它不是当场DeviceType响应。
配对查询等待1ms后当场旧式返回FFA5，扩展仍2719；不能把延迟读取误判为另一型号。

## USB输入路径来源

核对固定原厂源码及session76摘要：
[SMB5适配](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/charger_ic/oppo_battery_msm8150_pro.c)
在vbatt_num!=1时选择外部oppo_get_chg_ops，
[MP2650操作表](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/charger_ic/oppo_mp2650.c)
提供该表的充电电流/输入限流/电压/启停接口，同时借助SMB5侧识别供电和充电类型。
set_sdp_current、smblib_set_icl_current包含SDP电流档、Type-C/APSD、覆盖和suspend逻辑。
不能把MP2650当前标称900mA限流字段当作USB供电预算已验证。

实际主线qcom_smbx只匹配PMI8998/PM660；当前SMBB/SMB2配置关闭。
PM8150b Type-C与VBUS regulator模块的存在不等于MP2650充电控制已实现。
本轮没有载入这些模块、切换USB角色或访问SPMI充电寄存器。

## 保留状态与下一步

boot_id仍87753933-4992-45d2-aaf5-d9db9c11d1a3、内核#76，最终uptime1772.71秒、taint0。
最终标准读数8.641V、SOC99%、30.0°C、平均电流0、Not charging；采样时差导致与电芯
测试略有变化。MP2650十二个字段与session79一致，NTC/watchdog仍关闭、终止/12小时
安全计时器开启；这些是继承配置，不是建议设定。

完整dmesg未匹配到DSI错误/下溢、Oops、BUG、SMMU或I2C/GENI错误。KMS快照显示
underrun0；没有新的光学、pageflip或GPU压力测试，session77间歇性显示故障仍开放。
Image/config和既有显示源摘要保留；手机分区没有写入，本轮没有新固件候选。

下一步优先建立本机2719/固件响应的兼容性依据，核对独立温度和保护链、USB输入预算、
故障读取语义及失联状态。电池更换记录已向用户询问，截至记录时未获得答复；不预设结果。
有充分依据的原厂固定测量可以继续，不能把身份未定等同权限不足，也不能因增加授权
直接跳过硬件验证。全硬件自动任务继续active，其它外设仍按优先级推进。
