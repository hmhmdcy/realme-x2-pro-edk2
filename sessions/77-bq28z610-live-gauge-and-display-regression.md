# Session77：BQ28Z610 真实读数接入与显示启动回归

用途：记录本机电量计接入、仅 boot 部署、连续读数及出现的显示回归。
日期：2026-10-10。来源：session76 原厂研究、实际源码/固件、手机完整日志和
标准寄存器读数。证据在 reference/kernel77；大镜像和 SSH 身份留在本地输出目录。

## 当前结果

BQ28Z610 已在本机主线 Linux 上提供电量、电池包电压、温度、电流、容量和循环次数。
两个启动、45 次连续样本均与标准寄存器对应。充电控制仍未接入；驱动返回的
Charging/Good 是电量计状态解读，不是本轮充电安全或电池健康的验收。

两次新启动都出现 DSI FIFO/MDP FIFO 下溢，完整开关屏后停止；数字彩条和一次
A640 渲染回归通过。首次显示接管回归仍开放，不能把本次结果称为全部硬件通过，
也不能将 session75 的光学验收自动套给这两次新启动。

当前：内核仍为 #76，Image/config/logdump 原样；boot_id 为
aada8705-14a3-4012-bf84-eeb0f7987b96，taint0。最终采样电池包 8.649V、
电量100%、温度29.3°C、电流0；DSI worker 累计194条，开关屏后的观察期间不再增加。

## 1. 改动和安全边界

只在实际 Linux DTS 中增加 &i2c15，clock-frequency=100000、status=okay，
子节点 fuel-gauge@55 使用 ti,bq28z610 / reg=0x55。主线默认 pinctrl 与原厂
GPIO27/28、qup15、2mA、bias-disable 一致；已有 QUP2/GPI2 来自触摸接入，无需改动。
上机实际 Linux 总线号为1，器件1-0055；触摸仍0-0020。DT 标签不等于运行时总线号。

电量计驱动/config 已内建，未改 Image。逐项审查了 probe、setup、settings、
标准读取及所有写接口：NVM 更新配置关闭，BQ28Z610 dm_regs=NULL，未增加
monitored-battery 或编程数据。未解封、复位、标定电量计，未清除保护/故障状态。

验证程序 read-gauge.c 只对固定地址0x55读取12个已知标准字，每个事务是一个
一字节寄存器选择器加两字节读取。没有写寄存器数据，没有使用 Control/MAC 命令，
没有扫描总线，也没有访问 MP2650、DA9313、short IC 或快充 MCU。

按 [TI BQ28Z610 TRM，第12章](https://www.ti.com/lit/ug/sluua65e/sluua65e.pdf)
核对温度0.1K、电池包总电压mV、有符号电流mA、容量mAh及时间min；内核接口使用
0.1°C、µV、µA、µAh、秒。不将串联包电压除2写回驱动，不用宣传容量覆盖设计容量。
负电流/实际放电、外部温度校准和完整充放电周期尚未实测。

## 2. 构建、部署及回读

0013-arm64-dts-qcom-samurai-bq28z610.patch 对 session75 的 DTS 精确应用后与
实际源码一致；checkpatch 为0错误/0警告。仅构建 DTB 和 EDK2 固件，保留 init、
USB hook、SSH 身份、显示/GPU/EUD/触摸/CPU代码与配置。没有运行旧 build-image.sh。

固件审查覆盖 Android header/gzip、bootshim、FV/FFS 校验、LZMA、DTB raw section
及兼容 DTB。DTB 语义仅改变 I2C15 状态/频率和新增 gauge 节点；其它模块只更新
固件版本字符串20a1d60→136157b，执行代码不变。解析和摘要见 firmware-validation.json。

部署前手机 PARTNAME 核对 boot=/dev/sde11、logdump=/dev/sde32，并回读旧镜像哈希。
F1 收到真实回执，独立 fastboot 核对 serial/product/分区容量后只刷 boot。
第二次测试只重启，无分区写入。Android/用户数据/GPT均保留。

| 产物 | SHA256 |
|---|---|
| 当前 boot-k77-gauge.img，6680576字节 | 3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e |
| 原样 logdump，67108864字节 | 607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0 |
| 原样 Image，31906304字节 | f90e6807bad34db3f3c88206ec952b0de78775272e407eb525ea2440ded476bb |
| 回退 boot-before.img（session75） | 43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b |

当前 boot 与 logdump 已在设备端回读核对。恢复 session75 无需改 logdump；若部署
其它候选仍必须重新核对 PARTNAME/身份及镜像摘要，不能仅照抄盘号。

## 3. 电量计数据与回归验证

| 采样 | 第一次启动 | 第二次启动 |
|---|---|---|
| boot_id | 37645400-925d-497d-99af-676ac4ff8e9c | aada8705-14a3-4012-bf84-eeb0f7987b96 |
| 连续样本/跨度 | 30 / 59.04秒 | 15 / 28.51秒 |
| 电池包电压 | 8.642–8.643V | 8.646–8.648V |
| 温度 | 28.9°C | 41.1–41.2°C |
| 电流 | 0 | +2–16mA；此前独立读取约+59mA |
| SOC | 99% | 100% |
| 电量计报告状态 | Not charging | Charging |

标准读取与 sysfs 按采样时差容差核对，设计容量1965mAh、满充容量1514mAh、
循环次数947也一致。这些是电量计报告值，不是实验室容量/健康测试。
不同启动期间温度读数发生明显变化，后续充电控制需进一步核对传感器、原厂策略和
实际热行为；目前只证明标准数据及单位转换。最终采样已降至29.3°C。

两个启动完整日志没有匹配到 Oops、SMMU context fault 或 I2C/GENI 访问错误，
taint0。日志原始长度/设备端SHA/压缩摘要与样本明细见 hardware-validation.json。

显示回归用原有 kms-smoke 测得60Hz vblank、固定彩条 CRC69961448/60af15f5，
两次完整 disable/unprepare→prepare/enable 通过。A640 Turnip 实际渲染12次，
4096像素交替红/绿读回与 fence 通过。USB SSH/SCP、触摸驱动和F1保持可用；
没有重新宣称触摸物理事件、90Hz、休眠等未执行项目已验收。

## 4. 显示回归和失败记录

两次首次启动日志分别已包含142/65条 DSI worker 消息；随后累计至435/194。
当前驱动中 status=c 对应 FIFO及MDP FIFO underflow。开关屏后分别连续采样59秒/
28秒不再增加，末次状态检查仍194条。这证明电源循环能恢复，不能证明首次启动修复。

本轮只增加 gauge DT，并且已验证 Image、显示代码及其它 DT 属性不变；尚不能
断言电量计造成回归。可能涉及初始化时序或继承的显示状态，需用基线/候选对照定位。
检索找到 [旧 MDP5 autorefresh/_START 冲突的维护者讨论](https://lists.openwall.net/linux-kernel/2019/11/11/591)，
它是定向线索，不是本机 DPU5 的直接补丁；其旧位定义也不能替代当前驱动定义。

首次 COM14/SSH 在枚举前打开失败；com-up后恢复。第二次 fastboot 首次枚举为空，
加入有界等待后正常；没有重复 F1 或刷机。F1 后 libusb 记录了断开错误，回执和独立
fastboot 枚举仍成立，原始错误保留。曾取错 kms-smoke 路径、未挂载 debugfs 导致
早期测试失败；后来使用找到的 kernel73 程序并挂载 debugfs，只有完整通过的两次
电源循环计入验收。日志分类器的 debug/BUG 子串误匹配已修正。

## 5. 下一步

优先定位两次新启动的 DSI 下溢，保持电量计只读接入和充电寄存器不变；不能用
自动开关屏隐藏首次启动问题。随后推进 MP2650 标准读事务、真实配置和故障行为
审查，再实现本机温控/输入预算/终止/超时策略。没有调整快充、OTG或电池保护参数。

全硬件目标仍 active。其他硬件和验收范围见 HANDOVER-NEXT、HARDWARE-STATUS；
电量计读取可用不等于充电、无线、音频、蜂窝、摄像头和传感器全部可用。
