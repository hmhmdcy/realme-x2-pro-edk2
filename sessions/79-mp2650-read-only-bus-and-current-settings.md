# Session79：MP2650 总线接入与当前配置只读核验

用户要求继续搜索相关机型充电设备树和内核，并注意安全。当前权限足够；
本轮 gh API 成功，Realme 官方 master 仍为 session76 固定提交
9668fcdc6ec15be7a10d66f7b93c347829e0fdb6。检查的主线目录仍只有 MP2629，
没有 MP2650。相关机型和原厂策略对照继续见 session76。

本轮已完成总线接入和实际读取，充电控制尚未验收。只写 boot；Image、config、
logdump、充电芯片配置数据、PMIC OTG GPIO、电量计 NVM、快充 MCU 均未写入。

## 接入范围与依据

[本机官方设备树](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-mtp.dtsi)
及本机 Android 存档指向 QUP1 0x884000、MP2650 0x5c、400kHz。
存档引脚为 GPIO114/115、qup1、2mA、bias-disable，与实际主线 SM8150 定义一致。
此前两个引脚未被占用。补丁0014只启用 GPI0、QUP0 wrapper、I2C1，并设置400kHz；
DT语义仅四项属性改变，没有新增充电器子节点或充电参数。

原厂 MP2650 probe 会复位、写参数、启用充电并关闭安全计时器，未绑定该驱动。
[官方 MPS 数据手册 Rev1.0（2022-04-22）](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/)
第29页 Figure16 明确单寄存器读取：地址指针、重复 START、读一字节。
据该时序和原厂 SMBus byte-data 读取实现，采用有限的标准读取；这不是配置数据写入。
“any write”与host mode的文字仍不能作为失联保护保证，未测试模式切换或看门狗超时。
第44页列出故障位，但本次未找到明确的读后清除/锁存行为说明，REG14排除。
没有芯片ID寄存器证据；0x5c响应、配置结构和原厂DT对应，不能声称唯一硅片身份认证。

read-mp2650 固定地址0x5c、12个寄存器、一次失败立即停止，无任意寄存器/地址参数。
访问前验证 sysfs of_node 为 QUP1，并用非 FORCE 的 I2C_SLAVE 检查地址占用；
O_RDONLY本身不能限制 I2C_RDWR，实际每个写消息只有一个指针字节。
不读故障寄存器，不启用ADC，不复位/喂狗，不改充电/OTG/BATTFET或GPIO。
编译启用-Wall/-Wextra/-Werror，旧触摸和电量计总线的拒绝路径实测返回2。

## 实测当前配置

新启动 boot_id=87753933-4992-45d2-aaf5-d9db9c11d1a3，仍为 #76 内核，taint0。
实际适配器重新编号：I2C1/QUP1是/dev/i2c-0；触摸为1-0020，BQ28Z610为2-0055。
必须按of_node寻找总线，不能再照用session77中硬编码/dev/i2c-1的电量计采样脚本。

三次快照共36次组合读，约88.90/135.40/137.45秒，12个返回值完全一致：
08=16、09=4c、0a=36、07=14、00=12、01=2d、02=06、03=a2、04=68、
0f=12、0b=00、13=0f（均为十六进制）。这是继承的当前配置，未确认其来自OTP还是固件。
按照官方字段及原厂头文件交叉解码：

| 当前字段 | 解码 | 验收边界 |
|---|---|---|
| 电池串数 | 2S | 与存档及电量计包电压对应 |
| CHG_EN / OTG_EN / BATTFET_EN | 1 / 0 / 1 | 原有值，未由本轮启用充电 |
| NTC_CTRL / watchdog | disabled / disabled | 未核实热敏电阻接线和独立温控，不能直接开展充电控制 |
| 终止 / 安全计时器 | 开启 / 开启，12小时 | 配置位存在不等于保护行为已实测 |
| 充电电流 / 终止电流设置 | 300 / 200mA | 设置值，非正在流动的电流 |
| 两个输入限流设置 | 标称900mA | 官方换算假定10mΩ，板上电阻和USB输入预算未验证 |
| 浮充设置 | 4362.5mV/节，8725mV/包 | 当前设置，不是推荐的新参数或实测电芯电压 |
| 状态 | 输入power-good，charge termination | gauge三次为Not charging、电流0，不能作充电测试通过 |

BQ28Z610标准读数与sysfs相符：包8.643V、SOC99%、29.9–30.0°C。
初次及后续sysfs偶见-2mA；尚无经过校准的负电流/放电验收。Good不是电池健康鉴定。
REG14未读，因此本轮不证明故障位清零、没有历史故障或整个充电链安全。

## 部署与回归

候选由实际UEFI DTB构建；FV/FFS校验、嵌入DTB、兼容附加DTB和Android header通过。
三个可执行模块只有版本字符串136157b→3dd07f4，其他代码字节不变。
fastboot独立核对62bc28a1/msmnile及boot容量96MiB；写前Linux确认PARTNAME。
6682624字节boot sha08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405，
已设备端回读。logdump仍为607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0。
回退kernel79/boot-before.img为session77 boot，sha3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e。
Image/config及此前显示/GPU/EUD/init/USB身份源码哈希保持。

首次启动至约196秒DSI错误0，600双缓冲翻转、完成事件及CRC均通过，20.034903秒。
没有请求开关屏，panel enable日志仍1；没有新取得用户光学观察、GPU压力或休眠验收。
session77间歇性首次接管故障仍开放。初次debugfs未挂载产生的空快照不作为证据；
补挂后kms/state/clk_summary已完整取得。F1一次回执后设备转为fastboot导致读断开，
独立枚举成功；COM被动采集35秒、sent0，句柄与WSL USB owner均释放。

## 下一步

依据本机保护链建立控制方案：确认热敏电阻及电量计温度可信度、两串保护/均衡，
核实PM8150b/SMB5输入路径、USB供电识别与电流预算；查明当前/默认参数来源、
故障读后语义、终止与超时，以及失联/重启时保持的状态。不会以软件温度轮询
自动替代缺失的独立温控，也不能把看门狗恢复默认等同于关闭充电。
继续从受限普通供电设计验证；高压/快充、MCU固件及OTP/NVM编程不纳入此阶段。

完整来源、工具、原始日志哈希、候选和观察校验见reference/kernel79/README.md。
全硬件目标保持active；授权足够，无权限或自动审批阻挡。
