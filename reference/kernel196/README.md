# 阶段196：普通IMX471实体probe、OF媒体端点与运行时供电

普通`imx471`驱动已在真机CCI1 master1的7位地址0x10成功绑定，其实际probe通过寄存器0x0016的0x0471身份校验；随后一轮运行时供电开关通过。这里已超出模块ABI加载和独立ID诊断，但**尚未取得实体图像**。本轮只给已有CAMSS节点建立了真实端点，尚未重新建立CAMSS的异步notifier/media链路或启动sensor模式表/数据流。

## 最终改动

OF路径按本机原厂已验证的VIF→VANA→VDIG顺序分别启用电源，每步至少等待1ms；避免bulk接口允许的异步执行顺序。电源/时钟失败时撤销已启用资源，正常下电按反向关电。ACPI保持原bulk行为，模式、曝光及增益表不变，标准V4L2时钟接口保持。[驱动补丁](imx471-of-ordered-power.patch)

实际供电/上电/下电函数15个ASan/UBSan场景通过，覆盖每路enable失败、时钟失败、pinctrl失败、sleep失败时主错误保持与ACPI路径。用一个允许的bulk调度顺序执行旧函数会触发电源先后约束断言，原失败日志保留。没有声称这些测试覆盖所有V4L2绑定或物理regulator失效。[主机测试](imx471-power-host-validation.json)

[开发overlay](front-probe-overlay.dtso)使用真实VIO phandle、Q的LDO2/LDO5、S8C输入、TLMM12复位/29选择/15 MCLK2、CCI1 master1、DPHY2及CAMSS端点。Q PM8008按195普通MFD探测；没有补假PLDO输入。外部引用由同boot的新读取值编译，本地引用带fixups，不依赖当前树缺失的全局symbols。[overlay构建](overlay-build-validation.json)

[资源模块](samurai-front-overlay.c)通过标准OF overlay API应用/撤销资源，sensor操作由普通IMX471驱动执行；没有保持外部CCI PM引用来包住sensor probe。195 VIO引用模块与193 CCI启用模块只承担已验证的开发资源接入。最终overlay模块92d9176e…，其诊断时钟查询只get/put，不启用时钟或设率。

## 四次未绑定与媒体图原因

最初的probe-only overlay只有sensor本地endpoint，没有remote-endpoint。`imx471_check_hwcfg()`使用`fwnode_graph_get_endpoint_by_id(..., flags=0)`；当前`drivers/base/property.c`实现会跳过没有可用远端的endpoint。得到NULL后，`v4l2_fwnode_endpoint_alloc_parse()`按`drivers/media/v4l2-core/v4l2-fwnode.c`约定返回EPROBE_DEFER(-517)。因此schema中的本地节点合法，不等于这个驱动能在孤立端点上probe。

| 尝试 | 结果与证据 |
| --- | --- |
| first | 模块加载0，设备未绑定；资源和电源采样恢复 |
| r2 | 等待12秒并保存deferred原因：hwcfg -517；sensor未上电 |
| r3 | 设备/OF节点/provider三路时钟查询未报错，仍hwcfg -517；尚未据此证明所有clock对象内容 |
| r4 | 暂改OF必需时钟接口仍为相同失败；此试验已撤回，源/模块保留私人目录 |
| r5 | 加入真实CAMSS port2双向端点后，原V4L2时钟路径的普通驱动绑定并接受实体ID；观察脚本因I2C adapter未公开runtime_status而停止，撤销通过 |
| r6 | 将该adapter状态记为not-exposed，保留sensor和controller检查；普通probe及一轮供电开关完成，撤销通过 |

正确修复是补齐真实媒体连接。没有加入虚构远端、重复sensor power-domain或固定假时钟来绕过图检查。r4时钟源码/模块不是最终候选，最终IMX471仍使用标准V4L2 helper。[六轮原生收据](front-native-validation.json)

## 实体probe与运行时供电范围

最终IMX471源110977b8…、模块c49dca63…。正常probe先取得真实电源/时钟、释放reset，然后通过驱动的chip-ID判断，才可能成功注册并绑定。对象由devm_kzalloc新建，其identified初始为false；本次没有独立I2C总线读跟踪，因此身份依据是已核对实际代码的正常probe成功，不声称另有独立trace。

r6在probe前CCI controller已suspended，使用正常I2C设备层次。普通probe后sensor自动suspended，三路用户0且disabled。将sensor `power/control`临时设on后，三路均enabled/用户1，VDIG=1.056V、VANA=2.8V、VIF=1.8V；保持超过CCI自动休眠窗口再观察，sensor仍active。

同窗CCI controller显示suspended，但共享`titan_top_gdsc`为on，MCLK2 prepare/enable计数1、报告19.2MHz、hardware enabled Y，consumer为7-0010。不能单凭CCI的runtime_status推断TITAN已关闭。恢复原auto后，sensor suspended，三路disabled/用户0。这只是一轮短时PM检查，不是整机休眠、跨boot或长期恢复验收。

## 引脚资源地址纠正与完整撤销

核对当前DT的四个TLMM reg-names及SM8150 group映射时发现，193独立helper给GPIO15使用的只读地址0x0310f000位于west，而GPIO15 group属于north；旧记录中的该整值比较不能作为north GPIO15恢复证据。193经标准pinctrl/GPIO/CCI路径取得实体ID的结果仍保留，但不再沿用那条辅助校验结论。

本轮按实际DT资源计算并只读采样：GPIO12 0x0390c000、GPIO15 0x0390f000、GPIO29 0x0351d000。原值分别1/0/1，三脚均输入、物理低。所有寄存器写入由正常pinctrl/GPIO接口执行，没有直接写TLMM寄存器。

overlay的sleep状态匹配这次原值；撤销时资源模块先通过标准pinctrl选择恢复状态，移除OF资源后用户态再经GPIO v2恢复输入方向。六轮的三处实际CTL和电平全部恢复。Q节点的电压约束会在regulator注册时改VSET，退出后恢复已捕获的LDO2原1200mV、LDO5原1800mV编程值，七LDO本轮完整采样与最初相同；全部输出均关，P0/Q1保持。恢复的是测试前关闭输出的配置，不代表传感器工作时使用这两个原始值。

## 构建与最终状态

IMX471和CCI库作为两个模块目标一起经树内Kbuild生成，W=1诊断0，vermagic与所有导入符号匹配kernel183。CCI库仍f9c9272a…。[模块构建](imx471-module-build-validation.json)。前两次单模块modpost无法解析CCI导出：预置完整Module.symvers和KBUILD_EXTRA_SYMBOLS没有解决树内单目标的输入方式；组合两个目标后解决，没有伪造导出或强制加载。资源模块新增Kconfig help首次完整检查不足四行，已补充说明后通过。

原14个改动源、MFD195、VIO和CCI helper保持；当前19个tracked改动及6个相机新文件。完整开发代码checkpatch通过（仅忽略新文件MAINTAINERS通用提示），反向apply检查通过；Image183、canonical DTB172、config原字节、完整Module.symvers16793行/modules.order770保持。[最终源码](source-final-validation.json)

19039.04秒仍为189第二个boot：既有taint512、WARN1来自193时钟试验，BT重组1来自189；六轮新WARN/Oops/GPU fault/SLPI fatal/BT重组均0。ADSP/SLPI/modem running，MM191/PowerState3/GPS关闭，SensorProxy三个Has true。所有临时模块、PMIC/sensor/恢复节点、CCI临时适配器、VIO phandle及本轮firmware overlay文件已移除；CAMSS port2也已撤销。没有替换安装模块、刷写或重启。[最终健康](native-health-validation.json)

160份手机证据归档c7c98afc…下载并逐成员验证；保留六轮失败与成功、两版sensor模块和资源模块版本，原始身份/日志/寄存器快照只在私人目录。[归档收据](evidence-export-validation.json)

下一步重新建立CAMSS notifier/media链路，验证真实sensor数据到CSIPHY2/CSID/VFE并取得独立帧；当前驱动模式为1928×1088 RAW10/200MHz。195固定的Hotdog模式可作后续比较，但本机板级资源保持独立。四路PLDO输入、双PMIC整机冷启动、其它镜头、完整相机用户态、GNSS有效fix、蜂窝业务、BT后段重组与传感器完整验收仍属active goal。
