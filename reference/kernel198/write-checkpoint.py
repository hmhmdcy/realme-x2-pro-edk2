from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段197' in old.decode()
s='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段198，完整外设goal active。IMX471普通驱动/真实CAMSS链路在临时400MHz配置首次连续3帧1928×1088 RAW10，pattern均0，RAW结构/像素变化已核；尚未完整相机。193 WARN/taint512保留。见[边界](WORKING-BOUNDARIES.md)，用户暂无耳机。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 部署 | kernel183/logdump183、boot/DTB172、modules132覆盖hci_uart185/fastrpc189；Mesa149/UCM173、MM191 |
| 相机198 | 临时VFE/CSID上限400MHz：内部TPG320×240/3帧及实体IMX4711928×1088/3帧通过。实体SRGGB10P stride2416/2628608字节，序号0/1/2、时间戳增、活动区>99.9%覆盖、sensor/CSID pattern0 |
| 高频未解 | 原/只读诊断950MHz TPG仍VFE reset超时。core AHB刚enable即hw0，但400MHz成功时同样hw0，不能单独当根因。MMCX低档与高频、PLL/配置尚需分离 |
| 最新22018.82秒 | 同189第二boot；taint512/WARN1来自193，BT重组1来自189；Oops/GPU/SLPI fatal0。ADSP/SLPI/modem running，MM PowerState3/GPS0，SensorProxy三个Has true |
| 恢复 | 原CAMSS e9b73f4c…及22实体空sensor图恢复，临时资源撤销。三脚/七Q LDO采样恢复，P0/Q1、VIO1.8V关/用户0、S8C1.352V/用户3。8时钟引用恢复；VFE/CSID最后400/400MHz，不声称速率全还原 |

依据：[198报告](reference/kernel198/README.md)、[实体帧](reference/kernel198/front-native-validation.json)、[健康](reference/kernel198/native-health-validation.json)。[197逐字快照](archive/NEXT-SESSION-through197-2026-10-15.md)保留旧源码/回退/参考仓库索引，相对链接按根解释。

## 源码、产物与回退依据

- WSL源/home/cy122/pmos-samurai-kernel136/kernel；198临时诊断/400MHz编译后还原camss.c/vfe.c/h，当前源码保持197。21 tracked改动、6个相机新文件及5个旧备份未暂存。临时补丁apply/checkpatch通过。[收据](reference/kernel198/source-final-validation.json)
- 198诊断模块cc3ebabf…、400MHz模块9c637d05…，W=1零诊断；仅加载实验，原安装e9b73f4c…已恢复。400MHz为开发对照，不将限频替代正式频率/性能等级管理。197 CAMSS源cc212a4c…/CSID诊断691de929…、候选6f746445…仍保留。
- IMX471源110977b8…/模块c49dca63…、CCI库f9c9272a…；OF供电VIF→VANA→VDIG/反序关，ACPI bulk保留。196实体ID0471/短PM、197 lane7校验29项通过，198同sensor驱动真正出帧。
- overlay源c67b480e…/模块92d9176e…、DTBO b240769b…复用196；固件文件名仍samurai/k196-front.dtbo，已撤销。MFD195 d1ff82c0…、VIO9e83668e…、CCI193 d3b4610d…；现场引用56/201/240/251与临时VIO301核后撤销，下一次重读。
- MFD195冷迁移/warm与失败复位37场景保持；四路PLDO父输入未知，候选schema四项缺失。P先占8时Q拒绝，失败复位边界见196。OEM1.05/1.10V编程1.056/1.104V；退出恢复关闭输出VSET1200/1800mV。
- Image183 bfa72dd9…、DTB22c1f2ad…、config55f1f0a3…保持，符号16793行/模块顺序770恢复。FastRPC源41c8db5c…/模块88553112…、hci_uart f6c5ed35…，189原件回退。未刷写/重启，NV/校准备份保持。
- GPIO12/15/29实际CTL地址0x0390c000/0x0390f000/0x0351d000，初值1/0/1。193 helper读west0x0310f000不能证明GPIO15 north恢复；196–198按真实资源核对。198新追踪为独立instance，原root状态保持、instance已删，无直接门控MMIO写。
- MM固定7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a，运行b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc，源949132f3…。190能力/191 LOC修复保持，XTRA50406字节0→168h；Predicted仅模拟。正式MM入APK待办，更新会覆盖。197只签名离线新增v4l-utils/libs1.32.0-r1。
- MM/SSC回退详见197快照，INFO/激活及DMS online保持。SSC1902…/184 libssc/每boot一次门控/A.11固件及00121保留，不盲目stop/start。
- 手机boot身份k189r2-reboot-runtime/boot-id-private.txt，198另存；host198沿197→190私人Wi-Fi端点、原HostKeyAlias/公钥。USB190双向IPv6未恢复；一次gadget重绑无正向证据、Windows网卡复位拒绝访问。新boot重读身份/端点。
- 198私人原生87文件逐成员验证，含首张实体RAW；图像/统计/相关哈希仅私人保存。E:\\edk2-samurai-out\\kernel198。197归档e5bde026…/183、196 c7c98afc…/160等见快照。

## 续作与已知风险

1. 优先完成正常时钟/供电等级修复。950MHz无sensor TPG复位失败，400MHz TPG及实体各3帧通过；高频失败与MMCX/PLL/配置尚未区分。CAMCC DTS required-opps低SVS，OEM VFE400MHz为较低等级、950MHz为较高等级；用正常genpd/RPMH/OPP验证支持档位，查PLL/高频序列，不直接把400MHz上限当完整修复。
2. core AHB0xc1c8写1读0且未见软件写0，1762/1762事件完整；只读诊断证明复位前即hw0，成功出帧时仍hw0。不得继续把该读数直接当失败根因。临时诊断仅增加状态读取/打印，会改变时序；默认关闭，源码已还原，补丁在198。
3. 198实体会话k198-front-capture-r1，使用197静态front-capture工具、196硬编码FW文件名。普通CAMSS notifier重建/清理顺序见脚本，退出先释放notifier再删overlay，恢复原模块。当前节点/FW/CCI适配器/模块均撤销。RAW已解码非恒值，但曝光/色彩/方向/光学/其它模式/持续帧率及长稳未验。
4. PLDO物理网络、双PMIC整机冷启、其它镜头/用户态待验。Hotdog参考/home/cy122/x2pro-linux/hotdog-ref195固定47087509c4289c2580c54f5433e55366b2e00445，其525.2625MHz/1748方形/CAMNOC只比较；PM8009/BOB/gate/CCI1 master0/弹出机构不照搬。
5. GNSS191 300秒303NMEA及online后90秒无fix/CNR，16SV事件无列表；继续GeoClue/辅助自动加载与本机RF/时钟核对。两UIM no-atr/absent-active、sim-missing/bearer0不证明物理插卡状态；注册/数据/通话/SMS待验。
6. BT phase5/3.2Mbps/chunk13/partial0/firstff重组1区别185 phase2 NUL，只扫描。FastRPC普通信号/freezer、共享池−22/SSR、传感器运动/亮暗/方向/精度/冷启/长稳开放；189三PM45.2–45.3秒success3/fail0、7266 callbacks err0/桌面Claim仅已证范围。Wi-Fi第二PM35秒未关联、第三PM后恢复，不称自行恢复。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(s.encode())<=6500,len(s.encode());p=root/'archive/NEXT-SESSION-through197-2026-10-15.md';assert not p.exists();p.write_bytes(old);(root/'NEXT-SESSION.md').write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段198。临时VFE/CSID400MHz配置首次采到IMX471实体1928×1088 RAW10连续3帧、pattern0及RAW变化已核；TPG也3帧。950MHz复位失败尚需MMCX/PLL分离，core AHB hw0在成功时仍存在，不能单独当根因。22018.82秒同189 boot/taint512，无新增所列故障，原模块/临时资源恢复。完整goal active。[198报告](../../reference/kernel198/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,l in enumerate(lines):
 if l.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 198临时400MHz首次IMX471实体1928×1088 RAW10连续3帧，sensor/CSID pattern0、序号/时间戳与>99.9% DMA覆盖及RAW变化通过；同档TPG3帧。退出原模块/拓扑/三脚/Q LDO/引用恢复 | 正式动态频率/供电等级、950MHz复位/MMCX/PLL未解；core AHB hw0亦见于成功帧，不作为单独根因。限频补丁仅开发实验/源已还原，未部署最终相机。曝光/色彩/模式/其它镜头/用户态/冷启长稳与PLDO网络待验 |'
p.write_text('\n'.join(lines)+'\n');print(json.dumps(dict(stage=198,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(s.encode()))))


