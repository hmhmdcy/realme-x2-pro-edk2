# Session82：充电策略单位、保护源码与 Android 备份来源

日期2026-10-10。延续全硬件目标，本轮核对本机充电安全链。手机保持session79 boot、
#76内核和相同boot_id。没有分区写入、重启、开关屏、充电参数修改或实际故障注入。
用户确认电池从未更换；扩展2719身份仍不用于判断电池真伪或确切芯片型号。

## 已取得的实机记录

5373.89至5598.76秒的固定观察均为taint0、8.639V、99%、平均电流0，温度约30.7至30.8°C。
标准温度字3038/3039，内部温度字3027；初次瞬时电流−4mA，后次0mA。12项MP2650字段
保持79/80/81读数。电量计仅五项标准字组合读取，无MAC请求；MP仅既有固定12项读取。
selector写帧不含配置数据，不应表述为完全没有I2C写帧。

USB gadget为configured/high-speed，实际MaxPower为100mA、bmAttributes为0x80。
当前power_supply仅电量计，Type-C类没有设备。MaxPower是USB描述符的声明，不能证明
供电端可用预算、已经协商的电流或实际总输入电流。Android存档DT的USB策略值500mA和
MP寄存器按未核实采样电阻解出的标称900mA是不同依据，不能混作一个输入预算。

两次既有DRM超时仍为1545.683499/1775.069790秒，encoder超时计数前后均2、underrun0。
新日志是原日志的后续追加，未新增同类超时。这不是显示稳定性验收；81的600翻转测试及
77的首次接管故障继续保留，下一阶段仍需定位空闲/控制台路径。

## 不能直接套用的单位和错误处理

从同一手机2026-10-05 Android DT归档提取原始属性，再核对
[Realme公开解析代码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/oppo_charger.c#L1633)。
下表是普通解析分支的重建结果，属于参考策略，不是本轮选定的充电参数。

| DT属性 | 原始u32 | 普通解析后的温度 |
|---|---:|---:|
| removed_bat_decidegc | 190 | −19°C |
| cold_bat_decidegc | 20 | −2°C |
| little_cold_bat_decidegc | 0 | 0°C |
| cool_bat_decidegc | 50 | 5°C |
| little_cool_bat_decidegc | 120 | 12°C |
| normal_bat_decidegc | 160 | 16°C |
| warm_bat_decidegc | 440 | 44°C |
| hot_bat_decidegc | 530 | 53°C |

removed/cold是以正整数编码的负温度幅值，解析器显式取负；所有字段均为0.1°C。
原始DT还给出vbatt_num=2、max_chg_time_sec=36000，以及按单节语境使用的浮充/保护值。
不能把这些值直接应用到另一单位或另一电池电压接口。

[旧电量计实现](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/gauge_ic/oppo_bq27541.c#L338)
在双串路径返回最高单节电压；主线VOLTAGE_NOW报告电池包总电压，且单位为µV。
后续控制必须分别保留总电压与最高/最低单节电压，不能用总电压直接比较单节阈值，也不能
仅把总电压除以二代替电芯不平衡检查。

旧驱动温度读取第一次失败返回缓存，第二次连续失败返回−400，即−40°C。当前主线TEMP
接口直接读温度寄存器并传播错误码；其360秒常规轮询周期不等于TEMP样本年龄。
后续控制需要先检查返回码，并对采样失败采取经过验证的停止策略。不能把未更新的输出
当作有效温度；不能把errno直接当成负温度。

离线工具提取并编译了上述两个温度读取函数及旧分类函数的原始实现，模拟两种I2C错误、
恢复、旧缓存路径和25个边界温度。结果符合源代码；只验证这些函数和普通解析分支，
没有测试完整控制器、防抖、独立温控或实机故障处置。

## 保护源码及备份来源的纠正

[早期官方短路保护源码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/charger_ic/oppo_short_ic.c)
是占位实现，otp_check直接返回true；oppo_short.c的检查也是占位。不能据此认定实际硬件
保护已启用，也不能据此认定手机缺少保护。

私人回滚文件boot_stock_RMX1931.img仍为100663296字节、SHA256
dfe18875661164e7cb64eba7942b856e80ffe20abb537aec815da4bf43995cdd，与早期备份记录一致。
本轮仅离线提取其IKCONFIG和内核版本，未改动备份。内嵌版本为
4.14.356-openela-rc1-perf-droidspaces-lr2-ksu3-ext-a16pf，带第三方内核标记。
文件名中的stock不能证明它是OEM出厂镜像；它应称为此前Android环境的回滚备份。
早期记录中的“原厂boot”称呼在本轮纠正，原始归档/历史采集保持。

该备份实际配置启用OPLUS_SM8150R_CHARGER、OPLUS_SHORT_C_BATT_CHECK、
OPLUS_SHORT_HW_CHECK、OPLUS_SHORT_IC_CHECK和OPLUS_SHORT_USERSPACE；OPPO旧选项关闭。
配置不能证明对应保护器件已初始化或实际阈值。HIGH_TEMP_VERSION未在配置中出现也不能
证明所有运行时分支；维护源码已将低温特殊分支改为get_eng_version()==HIGH_TEMP_AGING。

[HyperTeam维护实现](https://github.com/HyperTeam/android_kernel_realme_sm8150/blob/20950ce50e3496b98d497370c730460e7e3dd75b/drivers/power/oppo/charger_ic/oplus_short_ic.c)
与[crDroid实现](https://github.com/crdroidandroid/android_kernel_realme_sm8150/blob/ae9e1cfb6b1d4ed1b02ab5f9448b6320daece944/drivers/power/oppo/charger_ic/oplus_short_ic.c)
包含实际读写，文件SHA相同。初始化会写阈值和工作模式，OTP错误处理也包含缓存/多次确认。
其compatible与旧Android存档命名不同，尚未证明它与备份中的精确代码或本机保护芯片一致。
本轮未读取0x58或执行初始化，未把通用同系列实现直接绑定到设备。

维护电量计源码还包含均衡状态和化学类型相关温度补偿，说明不能把旧读取实现当成完整
当前Android策略。相关条件和2719固件的兼容性仍需核实；本轮未查询化学配置、保护状态
或任何NVM，未启用均衡/FET/OTG/快充MCU。

## 验证与后续工作

reference/kernel82保留两轮原始字节、设备端SHA、USB声明、来源摘要、离线测试结果和
固定观察脚本；完整镜像、配置、下载源码及生成的测试二进制保持私人存储。
日志核验把Oops/BUG限定为完整词，避免误报ramoops和debug；实际两次DRM超时单独计数。

本轮把保护调查从早期占位源码推进到Android备份配置及同机型OPLUS完整实现，并查实
单位/缓存处理的移植差异。接下来继续核实精确保护实现、热敏接线/补偿、USB预算及失联
行为，同时准备显示帧完成超时的诊断。充电控制和全硬件目标仍未完成，目标保持active。
