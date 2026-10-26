from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel193';old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段192' in old.decode()
readme='''# 阶段193：前摄IMX471实体识别与CCI/MCLK电源域验证

**本机前摄通过CCI1 master1，在7位地址0x10、寄存器0x0016实际读到0x0471，确认IMX471。** 这次是实体传感器应答；阶段192只解码原厂候选BIN。尚未配置传感器输出、启动MIPI或取得图像，完整摄像头适配仍未完成。

## 真机路径

当前DTB的CCI1原先disabled。临时模块仅对`/soc@0/cci@ac4b000/status`建立可撤销changeset，使用已有`i2c-qcom-cci`驱动，实际注册master0/1为i2c-6/7；[changeset接口文档](https://docs.kernel.org/devicetree/changesets.html)。CCI单独启用没有新增所列故障。[CCI源码](samurai-cci-bringup.c)、[实机](cci-native-validation.json)

前摄执行已与原厂工具交叉核对的供电流程：TLMM29选择、TLMM12复位、PM8150L L1 VIO 1.8V、PM8008 Q的L5 VANA 2.8V、L2 VDIG 1.056V、MCLK2 19.2MHz、释放复位后读取ID。1.056V复现原厂1.05V请求向8mV网格取整的编程值，并非另行提高输出；[192电压依据](../kernel192/pmic-voltage-contract-validation.json)。L5/L2均读取到VREG_READY，随后一次两消息CCI事务返回正确ID。[完整原生结果](front-native-validation.json)

PMIC P@0x08/09、两根PMIC复位线、SID/全局使能及MAX98937没有改动。Q@0x04/05在测试时被临时I2C客户端保留，只有L5/L2 VSET和enable被写入；结束后七个LDO的本次全部采样值，包括VSET/enable/status，与测试前一致。没有单独复位共享QUP总线，也没有编程sensor模式或曝光寄存器。

临时资源使用正常regulator/GPIO/clk/pinctrl API。S8C保持1.352V、最终用户数3，没有改变其电压；另一颗名为ldo1的0.752V电源保持用户数1。VIO结束后用户数0、state disabled；此前state unknown，因此不能说VIO状态字符串逐字未变。GPIO12/15/29恢复输入、物理低；MCLK引脚GPIO15_CTL前后整值一致。只读映射此一个TLMM寄存器用于取得原配置及比较，所有引脚写入经过pinctrl/GPIO接口。

当前VIO节点没有phandle，且两个PMIC都存在名为ldo1的regulator。诊断使用临时名称查找后先校验1.8V，取得0.752V对象会在上电前退出；这是本机受限诊断方法，正式设备树必须建立明确供电引用，不能照搬名称查找。[诊断源码](samurai-front-identify.c)

## 两个失败与电源域修正

| 尝试 | 真实结果 | 退出后的状态 |
| --- | --- | --- |
| first | pin级pinctrl getter返回-ENOTSUPP(-524)；Qualcomm驱动仅实现group配置，ready0/ID0 | 未进入传感器上电，PMIC采样与GPIO恢复 |
| r2 | 改为group状态后两电源ready，但MCLK2报stuck off，返回-EBUSY(-16) | 电源/GPIO/PMIC恢复；新增一次WARN，内核taint变512 |
| r3 | 保持CCI父设备运行时PM引用后，result0、ID0x0471、ready2、restore0 | 采样/GPIO恢复，新增故障0；已有taint512保留 |

r2的实际调用栈在`clk_branch_toggle`，源于独立诊断消费者启动MCLK时TITAN_TOP_GDSC已关闭。r3在所有时钟读取/设频/启用之前`pm_runtime_resume_and_get(cci_parent)`，关钟并恢复原频率后再`pm_runtime_put_sync`。依赖已有CCI的标准genpd管理，不直接操作GDSC寄存器；接口语义见[内核运行时PM文档](https://docs.kernel.org/power/runtime_pm.html)。修复的是这个独立诊断流程；还不能据此断言已有正式IMX471 I2C驱动存在同样的缺陷。正式设备层次和PM关系仍需原生验证。

没有抹去r2告警、清taint或通过重启把它改成无故障结果。r3没有新增告警，结束仍为taint512。三个版本源/模块、原始日志和前后快照全部保留在私人归档中。

## 构建与检查范围

新增两个默认禁用的开发模块及Kconfig/Makefile入口。[完整补丁](samurai-camera-bringup.patch)、[最终源核对](source-final-validation.json) CCI模块SHA d3b4610d…；最终前摄模块c9856835…，源47ec57a2…。通过树内Kbuild正常生成模块元数据，没有手写intree标记、强制加载或掩盖taint。两个目标W=1告警0，vermagic及所有导入符号匹配当前kernel183。[CCI构建](cci-helper-build-validation.json)、[前摄构建](front-helper-build-validation.json)

原14个改动源码、Image/DTB保持；`.config`恢复原字节SHA55f1f0a3…，完整Module.symvers16793行/modules.order770恢复。首次构建自动添加“新选项未启用”注释，被不变检查检出并恢复；后续临时预置新选项n，退出后仍恢复原文件。前摄第一次编译的camcc头文件名称错误在加载前修正。完整组合补丁checkpatch无error/warning/check。

实际CCI init/exit函数在主机16个场景覆盖既有设备、属性/通知失败、回退和引用平衡。实际电源/下电及PM引用函数在49个场景覆盖每一步失败、错误/部分ID读取和7种撤销错误，ASan/UBSan通过；模型要求MCLK启用时电源域活跃。资源查找和pinmux创建没有被这49个测试全部仿真，三个原生尝试提供该部分证据。[CCI测试](cci-helper-host-validation.json)、[电源测试](front-sequence-host-validation.json)

## 最终状态与续作

前摄诊断模块、CCI changeset模块及原先未加载的i2c-qcom-cci均已正常卸载；CCI1恢复disabled、两个临时适配器和PMIC客户端移除。没有刷写分区或重启，也没有把诊断模块安装成启动项。[最终健康](native-health-validation.json)

11872.27秒仍为189第二个boot；MM191/PowerState3、GPS关闭、三个DSP running、SensorProxy加速度/亮度/接近均true。全boot保留warning1（本次r2时钟）和BT重组1；Oops/GPU fault/SLPI fatal均0。不能再用旧taint0收据描述当前启动。

下一步把已确认的前摄接入正式IMX471驱动：OF匹配、VIO/VANA/VDIG和选择GPIO、正确的PM父设备关系、CCI/DPHY2/CAMSS端点及真实取帧。主线现有驱动仅ACPI/vana，尚未修改或部署。Q的L5在本次条件下可达ready，仍不等于已确定四组PLDO的物理父供电，或冷启动地址/复位已通过。其余相机、GNSS有效fix、蜂窝业务和BT后段故障保持完整目标范围。

手机67份证据归档及每成员哈希通过：[归档收据](evidence-export-validation.json)。原始日志、身份与寄存器快照只保存在私人目录。完整goal active。
'''
next_text='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段193，完整外设goal active。前摄实体IMX471已通过CCI读到0x0471；真实图像仍未取得。r2独立诊断因MCLK电源域关闭产生一次WARN，当前taint512；r3持有CCI父设备PM引用后读取成功且无新增故障。诊断资源已撤销。规则见[边界](WORKING-BOUNDARIES.md)，用户暂无耳机。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 组合 | kernel183/logdump183、boot/DTB172；modules132覆盖hci_uart185/fastrpc189，Mesa149/UCM173 |
| 相机193 | CCI1临时注册两master；GPIO29/12、VIO1.8V、Q L5=2.8/L2=1.056V、19.2MHz，两个VREG_READY后真实ID0x0471；PMIC采样/GPIO恢复，正式驱动与MIPI未接入 |
| 最新11872.27秒 | 同189第二新boot，taint512/WARN1来自r2时钟；三个DSP running、MM191/PowerState3/GPS0、SensorProxy三个Has true。全boot BT重组1，Oops/GPU/SLPI fatal0 |
| GPS191 | 50406字节50片标准MM注入约0.801秒，49片完成先于ACK；有效期0→168小时，XTRA/3服务器。300秒303条NMEA仍无fix/CNR，电源online后另90秒仍无fix |
| 189传感器PM | 45.2784/45.2053/45.2838秒，success3/fail0/RTC3、7266 callbacks err0；醒后四CLI及Wayland UID10000 Claim/Release通过 |

依据：[193实体前摄](reference/kernel193/README.md)、[原生三轮](reference/kernel193/front-native-validation.json)、[最终健康](reference/kernel193/native-health-validation.json)、[191 GPS](reference/kernel191/README.md)。[192逐字快照](archive/NEXT-SESSION-through192-2026-10-15.md)保存上一完整检查点与旧源/回退索引，相对链接按根目录解释。

## 源码、产物与回退依据

- 193只新增开发helper：drivers/of/Kconfig/Makefile和samurai-cci-bringup.c、samurai-front-identify.c，默认禁用。[完整补丁](reference/kernel193/samurai-camera-bringup.patch)；前摄源47ec57a2…/模块c9856835…，CCI模块d3b4610d…。树内Kbuild、W=1告警0/符号匹配；16/49实际C函数场景与ASan/UBSan通过。不是正式IMX471驱动修复或实体出图。
- 当前临时模块全部卸载，CCI1恢复disabled，i2c-6/7与Q PMIC临时客户端移除。S8C保持1.352V/用户3，另ldo1a0.752V/用户1；相机VIO1.8V/用户0现明确disabled（此前unknown）。GPIO12/15/29恢复输入低，MCLK pin_CTL整值恢复。r2 WARN/taint512未清除；原始失败均保留。
- WSL内核/home/cy122/pmos-samurai-kernel136/kernel，193前14源保持：183的12源+hci_qca185+fastrpc189。新增2个tracked构建文件/2个新C；Image/DTB/config保持，config SHA55f1f0a3…，Module.symvers16793行/modules.order770恢复。FastRPC源41c8db5c…/模块88553112…，hci_uart f6c5ed35…；原件回退在189，不强卸载运行模块。
- MM固定提交7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a；190能力发现+191四条LOC异步顺序/独立引用/提前完成/分片关联/回退清理补丁。257场景/4原版失败/3破坏变体通过；原生XTRA回退成功，Predicted成功仅模拟。当前程序b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc，源949132f3…。
- MM native190源已更新191，隔离签名SDK复用；190程序fbc40848…在k191-mm-deploy/ModemManager.original及主机kernel191/ModemManager.before191；发行版4d5a8258…在190。激活/INFO已恢复，APK DB未改；正式入包仍待办，APK更新会覆盖。
- SSC固定1902…文件服务、184独立libssc、每boot一次门控；303来源/24固件只复制私人RAM。A.11路径/lib/firmware/qcom/sm8150/realme/samurai-a11-r187，原00121保留。共享池−22未解决，持续服务不盲目stop/start。
- 当前启动身份手机k189r2-reboot-runtime/boot-id-private.txt，193基线另保存；host193沿用190私人Wi-Fi端点和原HostKeyAlias/公钥。USB190双向IPv6未恢复，一次gadget重绑无正向证据，Windows网卡复位拒绝访问。下一boot先读新身份/端点，不沿用旧PID或启动标识。
- 193私人归档936fe956…/67文件、192归档322bfbce…/23文件均逐成员验证；191主843c4d47…/42与radio b6628078…/23保留。BDS164/固件172/FdtBlob129及183/181回退和NV/校准备份保持。

## 续作与已知风险

1. 优先正式接入前摄IMX471：OF/三路电源/选择GPIO/PM关系、CCI1 master1、DPHY2/CAMSS及取帧。当前VIO DT节点无phandle且ldo1重名，诊断名称查找校验1.8V只是临时方法，正式DT必须明确供电引用。主线驱动仅ACPI/vana，尚未修改。192原厂六BIN前缀已独立核对，只有前摄身份本轮实体确认；其它候选不能当实装。
2. P@0x08/09复位GPIO1原低，临时释放可识别后已恢复；Q@0x04/05、GPIO4保持，SID2/1、全局使能均1。OEM请求1.05/1.10V实际编程1.056/1.104V已核。Q L5当前可达ready不证明四组PLDO父供电网络；冷地址/复位、其它相机、完整模式/用户态及长稳仍开放。内部TPG三帧不是实体出图。
3. DMS已只开启一次，保持online/PowerState3，不重复重启。GPS辅助/UTC完整注入通过，仍无有效fix/CNR，16条SV事件无列表；接收条件与RF/平台原因未区分。继续GNSS-only GeoClue/自动辅助加载和本机RF/时钟核对，保留正常授权，不冒用Phosh或伪造坐标；168小时不证明跨基带重启保留。
4. 两UIM卡位no-atr-received/Slot absent-active，MM仍sim-missing/bearer0；不等于已确认物理插卡状态。卡槽、注册、数据、通话/SMS待验。BT phase5/3.2Mbps/chunk13/partial0/firstff重组1与185旧phase2前导00不同，继续只扫描。
5. FastRPC普通信号/freezer、共享池stop/start/reclaim−22/SSR及传感器运动/方向/亮暗/精度/冷启/长稳开放；失败SCM原型不当修复，不试遍未知owner。Wi-Fi189第二轮35秒未关联，第三轮PM后才恢复，不称自行恢复；USB独立链路问题仍待解。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(next_text.encode())<=6500,len(next_text.encode());archive=root/'archive/NEXT-SESSION-through192-2026-10-15.md';assert not archive.exists();archive.write_bytes(old)
(ref/'README.md').write_text(readme);(root/'NEXT-SESSION.md').write_text(next_text)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段193。前摄CCI实际读到IMX471 ID0x0471，尚未实体取帧；诊断MCLK电源域遗漏在r3修正，r2一次WARN使当前taint512，失败记录保留。11872.27秒同189 boot，三个DSP/MM191/PowerState3/SensorProxy保持；所有诊断模块已卸载。GPS191完整轨道注入通过但仍无fix，蜂窝业务/BT后段故障等仍开放，完整goal active。[193报告](../../reference/kernel193/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 193前摄经CCI1 master1实际读取0x0016→0x0471，GPIO/VIO/两PMIC电源ready/MCLK与撤销通过；另有内部TPG三帧及192六原厂BIN前缀独立核对 | 尚未实体出图；正式IMX471 OF/电源/选择GPIO/PM与DPHY/CAMSS端点、PLDO父供电/冷地址初始化、其它镜头/多模式/用户态待验；r2时钟WARN/taint512保留 |'
p.write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(stage=193,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(next_text.encode()))))
