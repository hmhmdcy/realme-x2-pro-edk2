# Session83：Android R 官方源码与 cyborgdc2000 充电实现对照

日期2026-10-10。用户补充：此前Android16第三方固件使用cyborgdc2000的内核和设备树，
该固件与Realme UI2.0均使用Android11底包。本轮据此重新定位主要参考源码。
没有访问手机、刷写分区、重启、开关屏或修改充电/保护配置；实机最新记录仍是session82。

## 来源定位和适用范围

| 来源 | 本轮固定分支/提交 | 核对结果 |
|---|---|---|
| [官方Android R内核](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/tree/23172a1571bd91156032cc9fef16284a82b63d2c) | master / 23172a1571bd91156032cc9fef16284a82b63d2c | Makefile版本4.14.190；板级DTS在19781目录 |
| [cyborgdc2000内核](https://github.com/cyborgdc2000/kernel_realme_sm8150/tree/1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1) | lineage-23.0 / 1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1 | Makefile版本4.14.356-openela-rc1；板级DTS在qcom目录 |
| [cyborgdc2000设备仓库](https://github.com/cyborgdc2000/android_device_realme_samurai/tree/af8af4614d5ab0c7e6c47bd8742a2e8c90a00f5f) | lineage-23.0 / af8af4614d5ab0c7e6c47bd8742a2e8c90a00f5f | BoardConfig使用samurai_defconfig及vendor/debugfs.config，内核路径kernel/realme/sm8150 |

这是当前分支的固定快照。用户确认了使用的作者和Android11底包，但没有提供历史构建
提交；不能据此声称上述提交就是回滚boot的精确源码。session82备份版本中的DroidSpaces/
KernelSU后缀继续保留，文件名stock仍不能证明OEM来源。

早期4.14.83官方仓库保留作历史参考。它的短路保护占位实现不能代表Android R官方实现，
也不能作为当前硬件保护缺失的依据。Android上层版本与底层vendor/内核版本需要分开记录。

## 板级设备树与本机Android存档

两套mtp-overlay均标记oppo,dtsi_no=19781，经mtp.dtsi包含pmic-overlay。相应节点为：

| 节点 | 两套源码的总线/地址 | 进一步核对 |
|---|---|---|
| MP2650充电器 | QUP1 / 0x5c | 本机主线已启用此总线，仍未绑定充电器驱动 |
| 电量计 | QUP15 / 0x55 | 两套都有batt_bq28z610属性；该属性不等于实际芯片身份已验证 |
| 短路保护 | QUP15 / 0x58 | 有启用节点，本轮未做实际I2C查询或初始化 |

14项选定策略属性，包括8项温区、双串数量、总充电时间、USB输入策略及3项电压属性，
在两套源码中均与2026-10-05同一手机Android DT归档的原始u32完全一致。
归档SHA256为e3329db4f3568252286489abd2ae27b9cbd0c711a2c5d790ebfba80fffc5b56b。
这里只核对选定属性，不代表所有DTS/DTBO字节相同或整个运行配置已复原。

两套普通温控解析器均对removed/cold幅值显式取负，得到−19/−2°C；温度单位0.1°C。
均保留HIGH_TEMP_AGING运行时特殊分支，因此不能仅凭defconfig没有HIGH_TEMP_VERSION
就断言该分支从不生效。电量计双串路径返回最高单节电压，主线接口仍为电池包µV。
session82的单位、失效处理和输入预算边界继续适用。

cyborg DT的compatible前缀是oppo，驱动OF表为oplus；Android R官方DT则为oplus。
本机Android归档的三个compatible与cyborg DT一致，短路节点后缀为oplus_short-ic。
核对同一cyborg内核的OF与I2C核心后，发现OF生成的I2C名称去掉逗号前的vendor，
I2C匹配在OF未命中后还尝试id_table；三个后缀均命中各自驱动的I2C ID。
这是根据源码判断可能正常绑定的依据，不能据前缀差异认定驱动没生效；也没有获得
此前Android运行时的实际绑定/初始化成功日志。

## 驱动、配置和有实质影响的差异

两个固定提交的oplus_bq27541.c完全相同，SHA256为
0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87。
oplus_short_ic.c完全相同，SHA256为
fea6f381755e0491ce4f3667cca427ec2b03ab1b1e817f294cdbb2906d72fadf；对应头文件也相同。
Android R官方提供了实际保护读写实现，不能沿用早期占位源码的结论。

cyborg的samurai_defconfig启用OPLUS_SM8150R_CHARGER和四项SHORT保护选项，与session82
备份中的选定配置一致。其charger_ic/Makefile直接包含msm8150Q、MP2650和short对象；
官方Makefile的SM8150R分支选择msm8150Q/MP2650。不能因仓库同时包含PRO等其它版本，
就把其它平台的配置当成本机实际路径。

MP2650源码不同：cyborg的hardware_init删去了官方实现中的5项WPC默认设置，涉及浮充、
预充电流、快速充电电流、终止电流和再充偏移。两套仍会复位充电器、设置其它参数并
关闭MP2650硬件安全计时器。主控充电策略和msm8150Q文件也不同，不能把整个充电栈
称为完全一致，不能直接运行任一初始化来恢复所谓“原厂默认”。

## 安全状态和后续

本轮把参考范围收敛到用户确认的Android11底包谱系，完成54项固定来源文件的哈希、
选定DT属性、对象选择及名称匹配核对。reference/kernel83保存来源摘要和离线审计工具；
完整下载源码、设备树归档、内核配置、镜像和私人MP差异保留在私人目录。

尚未确定2719/FW的精确器件映射、短路IC型号/当前阈值、热敏接线/均衡温度补偿、USB
实际预算和控制失联后的安全行为。源码和编译配置只能证明有相应实现，不能证明本机
独立保护已经验证。充电控制仍未验收，没有权限或自动审批阻挡。

接下来以这两套固定源码和本机存档为依据核对保护/测温/输入链，先完成必要的观测与
故障语义设计，再考虑受限普通充电控制。不得解封、写NVM/OTP、切FET/OTG或刷快充MCU。
显示77首次接管失败和80两次超时继续开放，可准备保留既有修复的FTRACE诊断内核；
Wi-Fi/MPSS仍禁用。全硬件目标保持active。
