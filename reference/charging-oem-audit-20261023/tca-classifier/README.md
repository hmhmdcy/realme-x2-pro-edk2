# TCA分类：0050／0056报文与结束周期的证据门槛

2026-10-23，纯PC离线候选。没有实机查询、白名单变更、NVM／FET／解封操作，未改生产9d9或SDK。来源是本机已缓存官方TI SLUUA65E（June2023，PDF SHA `f62ec12bb5aa23631759e59a378f36d254f9b0e2b5b6b8523a0dd081a13e4139`）；不是从相近型号猜长度。

[tca-reference.h](tca-reference.h) 只解码调用者提供的保存字节并分类，完全没有总线接口。[23个报文／149个分类案例](test-result.json) 通过ASan/UBSan；均为合成包，不能称为0x2719实物新命令已验证。

## 精确帧长度与字节序

复用已有锁定MAC传输语义：向0x3E选择只读命令，等既有约1ms查询间隔，再从0x3E读取完整36字节。选择命令是低字节在前，例如0050为`50 00`，0056为`56 00`。不写0x60／0x61，不发送任何“command only”控制命令。

| 命令 | 内容 | 标准有效payload | 0x61长度字节 | 精确依据 |
| --- | --- | ---: | ---: | --- |
| 0050 | SafetyAlert | 4字节／32位 | 8 | §12.2.26，PDF80–82页；txt3552–3611位表31..0 |
| 0052 | PFAlert | 4字节／32位 | 8 | §12.2.28，PDF83–84页；txt3665–3700位表31..0 |
| 0056 | GaugingStatus | **4字节／32位** | **8** | §12.2.32，PDF88–89页；txt3911–3916明确第1byte是GaugingStatus、第2/3byte是ITStatus，**第4byte保留** |
| 0055，可选佐证 | ChargingStatus | 2字节／16位 | 6 | §12.2.31，PDF87–88页；txt3854–3909位表15..0 |

0056不是3字节，不接受长度7；PFAlert也不是凭低位信号个数缩成2字节／长度6。4字节保留空间属于payload，即使都是0也不能省略。

完整36字节的固定布局：0/1为命令回显，2..(1+payload)为状态小端值，34为checksum，35为length。逻辑length含命令2字节+payload+checksum1+length1，故4字节状态为8。checksum要求命令及有效payload之和加packet[34]低8位等于255；padding不参与求和。依据§12.1.28–31及§12.2读示例，PDF73–74页，txt3128–3191。

本候选解码器严格检查物理36字节、逻辑8／6、命令回显及checksum，再按LE32／LE16解码；不会因为“读到了36字节”就接受旧命令回显，也不会把checksum放在有效payload之后的可变位置。0056第4byte按标准为reserved；候选分类器发现该byte或其它标准保留位非零时按尚未映射处理，保留原包供兼容分析，不能静默截断成24位。

## TC、FC、CHG与TCA分别代表什么

| 字段 | bit／mask | 含义／证据 |
| --- | --- | --- |
| BatteryStatus 0x0A TCA | bit14／0x4000 | 终止充电请求，不能alone判电气坏或正常Full；PDF27页§4.8，70页§12.1.6 |
| BatteryStatus OCA | bit15／0x8000 | 过充告警；§4.8将其关联SafetyStatus.OC且CHARGE模式 |
| BatteryStatus FC | bit5／0x0020 | 电量计的Fully Charged；不是TC，也不是bit9 |
| BatteryStatus DSG | bit6／0x0040 | 为0时对应充电模式，1为放电／非充电模式 |
| 0056 TC | bit3／0x00000008 | Gauging算法发出的Terminate Charge状态；§12.2.32，txt3973–3975 |
| 0056 FC | bit1／0x00000002 | Gauging Fully Charged；与BatteryStatus FC的位置不同 |
| 0056 DSG | bit6／0x00000040 | 1表示未检测到充电（放电／relax），0表示检测到充电 |
| 0056 QEN | bit12／0x00001000 | Gauging已启用，作为兼容性和运行态佐证 |
| 0054 Operation CHG | bit2／0x00000004 | **CHG FET当前状态**，不是电量计充电模式，也不是MP2650 CHG_EN |
| 0054 XCHG | bit14／0x00004000 | 电量计禁止充电；不能仅因TC置位就放开此保护拒绝 |
| 0055 VCT | bit15／0x8000 | 有效充电终止，可选独立终止佐证，不能与0056 FC／TC混用 |

TI §4.6（PDF26页，txt1111–1139）允许在配置CHGFET选项且TC置位后关闭CHG FET，所以Operation.CHG=0可能正常。不能把它alone当fault，也不能要求它必须为1才能承认正常终止。XCHG、SS、PF等仍单独检查；本候选不放开现有保护函数对XCHG／低压关断／安全／PF模式的拒绝。

TC／FC可由电压、RSOC或有效终止条件配置而来（§4.7，txt1141–1182），因此“TC=1且FC=1”也不自动等价于本机完成了实际CV／taper过程。不要读取或修改DataFlash来迁就候选算法。

## 为什么SafetyStatus=0仍不能忽略TCA

§4.8给出的TCA置位来源是：

```text
SafetyAlert.OCC 或 SafetyAlert.COV 或 SafetyAlert.OTC
    或 (GaugingStatus.TC 且电量计处于CHARGE模式)
```

SafetyAlert可以在延时保护trip前已置位，随后才转入SafetyStatus；例如COV详表§2.3（txt466–524）将Alert与Trip分开。因此现有0051 SafetyStatus=0、0053 PFStatus=0并不能证明TCA来自正常TC。

0050里直接相关位：OCC bit2=0x4，COV bit1=0x2，OTC bit12=0x1000。首次兼容核对时建议完整保存并要求整个SafetyAlert值为0才允许“正常TC”候选，不只清这三位就忽略其它告警。PFAlert/PFStatus同理完整保留且非零均不能作为正常结束周期的证据。

## 0x2719适用界线

既有本机证据确认legacy FFA5接口、本机扩展DeviceType=0x2719，以及0051／0053／0054／0057／0071的现有帧和用途；标准TI器件身份为2610。不能把“同样echo＋checksum可通过”升级为0x2719的新0050／0056所有bit语义已确认。

候选显式要求 `compatibility_verified`，解析器绝不自动设置它。该门槛至少包括：相同本机／启动身份、既有extended2719身份、0050／0052／0056真实payload长度和回显、0056保留位与QEN/DSG/TC/FC的合理关联、Operation既有封印／自动FET／Gauging运行态一致。如果一次采样恰好TCA=0、TC=0，只能证明该次帧兼容，不能单凭零位确认TCA正常因果；自然发生的终止事件及独立Full证据仍需之后观察。

本规范未宣称原厂Android代码已使用0050／0056分类。已缓存 `oplus_bq27541.c/.h` 没有提供这两项分类的本机位语义证明；这里使用的是TI官方文档和明确的兼容性门槛。

## 什么时候才可以结束本轮、避免假超时

候选 `sm_tca_classify()` 只给出分类，**不设置控制位、不清latch、不授权再充**。承认 `NORMAL_TERMINATION` 并结束本轮timer，必须同时满足：

1. 新命令的本机兼容性已确认，所有MAC帧校验与该轮完整采集通过；新鲜时间、数据所有权及batch前后状态一致。
2. 当前没有任何已锁存的总线／寄存器／电气错误或已经成立的真正timeout。正常TC不允许“倒洗”旧fault；旧版本若只有无原因boolean latch，也不能擅自猜测它仅由TCA造成再清掉。
3. 整个SafetyAlert、SafetyStatus、PFAlert、PFStatus为0，OCA／OTA／TDA未置位；既有封印／自动FET／Gauging检查和温区／全局电芯／预算条件通过。
4. 前后BatteryStatus的TCA均为1，0056 TC=1；BatteryStatus.DSG和0056.DSG均为0，符合官方TCA的正常TC因果支路。TC／充电模式不一致按未知hold，不凭猜测当正常终止。
5. 还有独立终止证据：当前完整样本的MP2650 REG13真实Full，或此前完整的OEM软件Full证据，或已核对的0055.VCT。仅TC／FC／SOC100／电流0均不够。

若1–4满足但缺5，则输出 `TC_REQUEST_HOLD`：保持不充电，不能复位timer为“已完成周期”，更不能跨过TCA继续充电。此类hold时计时器本身应只累计实际充电段；没有实际充电却持续接线，不应该因为时间超过10小时制造新的“持续充电超时”。“暂停本轮累计”和“本轮已完成归零”是不同事件。

即使NORMAL_TERMINATION，之后仍保持正常Full的CHG停止，输入在真实预算内可用；TCA还在时不授权再充。TCA自然清除、再充电压连续样本与全部安全条件重新满足后，才允许未来新周期。旧fault／timeout始终保持其优先级。

## 未来单次只读确认所需最小原件

不需要扫NVM或读取整库。重连并获手机窗口后，可由**现有带MAC段锁的同一传输所有者**执行一个保存原包的batch；不要让用户态裸I2C选择器与充电／保护两个工作队列交叉。命令选择后读36字节的整个事务必须使用既有锁，不能只保证每个i2c_transfer各自串行。

- 前后各一次BatteryStatus0x0A；至少要求TCA/OCA/OTA/TDA/DSG/FC关键位稳定。
- 新字段0050 SafetyAlert、0056 GaugingStatus、0052 PFAlert，均36物理／4 payload／length8；为排除批次变化，0050／0056各在batch首尾留一份原包较有价值。
- 既有0051 SafetyStatus、0053 PFStatus、0054 OperationStatus（均4 payload／8），0057 ManufacturingStatus（2 payload／6）。DeviceType可复用同启动已验证身份，不能忽略身份或把2610冒作2719。
- 既有0071电芯、0x06温度、0x08整包、0x0C signed瞬时电流，及实际源许可／MP2650 REG13／驱动缓存的故障字段与年龄；可选0055 ChargingStatus（2 payload／6）用于VCT佐证。
- REG14由充电驱动单一所有者读取并缓存，观察工具复用该缓存及age，不再额外raw读取清除故障证据。

若任何length、echo、checksum、保留位、模式一致性或返回错误不符，保留原包与错误并结束这次确认；不要循环重试去“凑”预期、补写配置或解封。一次自然事件证据不足时仍保持hold，后续等真实普通充电事件补证据。
