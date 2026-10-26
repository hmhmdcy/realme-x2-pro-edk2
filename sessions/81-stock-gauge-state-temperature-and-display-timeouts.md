# Session81：原厂电量计状态、温度及显示超时复查

日期2026-10-10。用户确认电池从未更换；后续以本机原厂固件兼容性为重点，不根据
扩展身份编号推断更换、真伪或确切芯片。手机保持session79 boot，内核Image/config不变。
本轮没有手机分区写入、重启、开关屏或充电参数修改。全硬件目标继续active。

## 充电相关的新实测

[原厂电量计代码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/gauge_ic/oppo_bq27541.c)
的bq8z610_sealed()与bq8z610_check_gauge_enable()分别使用固定0054/0057请求。
新工具先核实本机旧式FFA5、扩展2719及与session80一致的11字节FirmwareVersion负载，
再只读这两项；没有调用原厂随后解封、启用计量或改数据闪存的整套函数。

| 项目 | 实际返回 | 本机原厂代码支持的结论 |
|---|---|---|
| 0054 | payload 86030000，即0x00000386；length8/checksum22 | 封存位=3，仍处于sealed |
| 0057 | payload 1800，即0x0018；length6/checksum90 | GAUGE_EN位=1，计量启用 |
| 标准06 | 原始3037，按0.1K约30.6°C | 与原厂及主线电池温度读取地址一致 |
| 标准28 | 原始3025，按0.1K约29.4°C | 原厂头文件和TI手册均定义为内部温度 |

两项MAC块均通过回显、长度、checksum与原厂四字节读取一致性核验。固定MAC请求共4帧：
身份1、固件1、状态2；这些帧包含I2C写，但只选择响应缓冲，不改配置。后续温度工具是
五项标准字的组合读取，没有MAC请求或寄存器数据写。错误的MP2650和触摸适配器都拒绝。

[TI SLUUA65E](https://www.ti.com/lit/pdf/sluua65)的12.1.4、12.1.21及12.2.30/33
提供标准温度和状态定义。两个温度读数不同，有助于排除简单地把内部原始字直接当作
当前电池温度的判断；这仍不能验证TS1接线、温度选择配置、偏移校准或独立温控阈值。
其它TI状态位映射对2719固件仍属待核实的解释，不能因0018中的某个位而宣称全部保护关闭。
0051 SafetyStatus、0053 PFStatus和0072 DAStatus2未查询；80完整status原型的身份门槛未放宽。

3608.23秒采样：taint0、8.639V、99%、30.6°C、平均电流0、Not charging。先前标准字
同次总电压8.638V、瞬时-3mA、平均0mA。MP2650十二字段与79/80一致，现有NTC/watchdog
关闭、终止与12小时安全计时器开启仍是继承值，不是建议设定。权限足够，缺项仍是保护链、
USB预算、故障/默认/失联行为的本机验证；没有充电控制验收。

## 显示日志检查的纠正

复查发现[session80原始日志](../reference/kernel80/final-dmesg.txt)已有1545.683499秒、
1775.069790秒两次enc35 frame done timeout，其encoder计数也为2。此前检查关注DSI、
下溢、Oops、SMMU和I2C/GENI，漏掉了这类DRM超时。本轮保留旧封存文件，新增检查与说明。
它们在81状态/温度操作之前已存在，不能归因于本轮的新查询或只读固件提取。

运行源码dpu_encoder.c把该timer超时累计到frame_done_timeout_cnt，debugfs显示名为
frame_done_cnt；它不是完成了多少帧。当前下溢仍为0，DSI错误匹配为0，但显示稳定性没有
因此通过。先保存现有KMS/state/clk_summary，再复用78的事件/CRC工具，无显式CRTC disable
或开关屏。600个完成事件与600项请求图案CRC均通过，1199条CRC行只出现两个已知完整缓冲，
耗时20.044934秒，工具返回0；超时计数前后均2，没有新增同类错误。

持续刷新通过不能关闭空闲/控制台更新路径的超时问题；根因尚未建立。保存的寄存器是
故障后的对照快照，不能冒充当时瞬间现场。本轮没有新光学观察或GPU压力测试，77的
首次接管间歇故障也仍开放。当前CONFIG_FTRACE关闭，后续可准备保留现有修复的诊断内核，
追踪空闲后kickoff/IRQ/电源恢复，不通过自动开关屏掩盖错误。

## 无线的安全准备

本机Android存档DT的icnss供电为PM8150 L1 752mV、L7 1.8V、PM8150L L2 1.304V、
L11 3.0–3.312V。核对实际编译DTB后发现，这四项已经由sm8150-mtp.dts继承，不能只看
samurai局部wifi节点就认定供电属性缺失。wlan保留区为9b000000+180000，原厂ICNSS请求
MSA大小100000；保留区和请求大小是不同参数，未自动改小。当前wifi与MPSS仍禁用。

按实际PARTNAME/容量/UFS型号/boot_id守卫只读挂载vendor(ro,noload)与modem(vfat ro)，
定位无线文件后解除挂载。前后整个vendor/modem分区SHA均一致。再仅从modem/image归档
wlanmdsp.mbn和34项bdwlan.*，35项均存私人目录，未安装或加载。mdsp为4069824字节ELF32、
machine164；记录ELF布局不等于安全认证或运行验收。完整固件不发布，公开metadata/摘要。

核对[原厂ICNSS](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/icnss.c)、
实际ath10k snoc/qmi、Q6V5 PAS与PD mapper源码：现有SNOC路径等待WLFW QMI服务，
没有在这两份文件发现直接request_firmware加载wlanmdsp；PD mapper列出msm/modem/wlan_pd
的kernel/elf_loader和wlan/fw服务，SM8150 MPSS PAS为auto_boot=false。
[tqftpserv固定源码](https://github.com/linux-msm/tqftpserv/tree/128cd6e0a39734fefd0f0bf0aad5e997c29e2445)
展示通过QRTR向远端提供固件文件的方式。这支持继续核对远端加载链，而不是仅打开Wi-Fi
status就认定能工作；本机具体加载顺序、chip/board ID和板数据选择仍未实测。tqftpserv
没有构建、运行或安装；未启动modem、未开启无线、未接入rmtfs或其它存储写服务。

## 可复核记录及下一步

reference/kernel81的设备端SHA、状态块、标准字、源文件/二进制摘要和两分区前后摘要
均通过独立核验。Image/config/既有显示源及DTB保持，EUD、USB hook、init和SSH身份未修改。
所有原始日志按字节保存；SHA256SUMS封存后不修改历史采集。

下一步先保存并定位显示空闲后帧完成超时，同时继续原厂2719固件的温度/保护链依据。
无线已有本机固件和板级映射，可继续准备独立且受限的远端服务测试。仍禁止试写充电参数、
解封、NVM/OTP、FET/OTG或快充MCU；Android、userdata、GPT和校准/身份数据保持。
