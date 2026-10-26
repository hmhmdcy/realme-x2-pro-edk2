from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段196' in old.decode()
s='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段197，完整外设goal active。修复CAMSS拒绝Qualcomm D-PHY clock lane7，IMX471普通驱动及实体media链路已建立；取帧仍在CSID reset超时，无实体帧。193 WARN/taint512保留。见[边界](WORKING-BOUNDARIES.md)，用户暂无耳机。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 部署 | kernel183/logdump183、boot/DTB172、modules132覆盖hci_uart185/fastrpc189；Mesa149/UCM173、MM191 |
| 相机197 | lane7校验修复/29项实际C回归通过，候选W=1零诊断。23个实体含IMX471→CSIPHY2→CSID0→VFE0RDI0；三次物理取帧均CSID reset超时，无帧 |
| 对照 | 原CAMSS与新候选各一次内部TPG均VFE reset超时；126历史3帧成功不能代表当前boot。活动TITAN/IFE0 on、CSID600MHz/Y；core AHB80MHz enable/prepare4但hw N，原因未定 |
| 最新21014.32秒 | 同189第二boot；taint512/WARN1来自193，BT重组1来自189；Oops/GPU/SLPI fatal0。ADSP/SLPI/modem running，MM PowerState3/GPS0，SensorProxy三个Has true |
| 恢复 | 四轮前摄及两TPG无新增所列故障；临时资源撤销，原CAMSS e9b73f4c…恢复、时钟引用与196基线一致。三脚/七Q LDO采样恢复，P0/Q1、VIO1.8V关/用户0、S8C1.352V/用户3 |

依据：[197报告](reference/kernel197/README.md)、[原生](reference/kernel197/front-native-validation.json)、[健康](reference/kernel197/native-health-validation.json)。[196逐字快照](archive/NEXT-SESSION-through196-2026-10-15.md)保留旧源码/回退/比较仓库索引，相对链接按根目录解释。

## 源码、产物与回退依据

- WSL源/home/cy122/pmos-samurai-kernel136/kernel；197仅新改CAMSS解析及超时诊断，原源保持。21个tracked改动、6个相机新文件及5个既有备份未暂存。补丁反向apply/checkpatch通过。[源码收据](reference/kernel197/source-final-validation.json)
- CAMSS源cc212a4c…、CSID诊断源691de929…；最终候选6f746445…、仅lane修复候选7f56e2e1…；原安装e9b73f4c…已恢复，持久模块未替换。组合VB2 common/memops/v4l2/dma-sg目标解决单模块modpost缺导出，最终W=1零诊断。
- IMX471源110977b8…/模块c49dca63…，CCI库f9c9272a…；OF供电VIF→VANA→VDIG，反序关、ACPI bulk保留。196普通probe/ID0471及一次PM通过；197同驱动三次绑定，未获得帧。
- overlay源c67b480e…/模块92d9176e…、DTBO b240769b…复用196；helper固件文件名仍samurai/k196-front.dtbo，已撤销。MFD195 d1ff82c0…、VIO9e83668e…、CCI193 d3b4610d…；现场引用56/201/240/251与临时VIO301均核后撤销，下一次重读。
- MFD195冷迁移/warm及失败复位37场景保持；四路PLDO父输入仍未知，候选schema四项缺失。P先占8时Q安全拒绝；失败复位边界见196。OEM1.05/1.10V编程1.056/1.104V；退出恢复关闭输出原VSET1200/1800mV。
- Image183 bfa72dd9…、DTB22c1f2ad…、config55f1f0a3…保持，符号16793行/模块顺序770恢复。FastRPC源41c8db5c…/模块88553112…、hci_uart f6c5ed35…，189原件回退。未刷写/重启，NV/校准备份保持。
- GPIO12/15/29实际CTL地址0x0390c000/0x0390f000/0x0351d000，初值1/0/1。193 helper读0x0310f000 west不能证明GPIO15 north恢复；196/197按真实资源核对。所有写仍通过普通框架，本轮诊断MMIO只读。
- MM固定7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a，运行b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc，源949132f3…。190能力/191 LOC修复保持，XTRA50406字节注入成功0→168h；Predicted仅模拟。正式MM入APK待办，更新会覆盖。197只签名离线新增v4l-utils及libs1.32.0-r1，未升级旧包/MM。
- MM190 fbc40848…回退手机k191-mm-deploy/ModemManager.original及主机kernel191/ModemManager.before191，发行版4d5a8258…在190。INFO/激活恢复、DMS只开一次保持online。SSC1902…、184 libssc/每boot一次门控、A.11 samurai-a11-r187/00121原件保留，不盲目stop/start。
- 手机boot身份k189r2-reboot-runtime/boot-id-private.txt，197另存基线；host197沿196→190私人Wi-Fi端点、原HostKeyAlias/公钥。USB190双向IPv6未恢复；一次gadget重绑无正向证据、Windows网卡复位拒绝访问。新boot重读身份/端点。
- 197私人归档e5bde026…/183逐成员验证，含四轮会话/两TPG/健康/模块/工具；196 c7c98afc…/160、195 10c5f4aa…/37在快照。私人日志保留E:\\edk2-samurai-out\\kernel197；没有RAW帧。首次目录名错误发生在overlay加载前，空目录保留。

## 续作与已知风险

1. 优先解CAMSS复位/时钟/PM。197 r3/r4/r5物理链路及sensor/CSID pattern0已证，1928×1088 RAW10 stride2416/2628608字节，仅请求未取帧；CSID version/IRQ/mask/strobe全0，IRQ不增。r5三个活动快照IFE0/TITAN on、IFE847MHz/Y、CSID600MHz/Y、CPHY400MHz/Y但core AHB80MHz count4/hwN。两TPG均VFE reset失败。不能只凭CCI runtime suspended推断域关闭，也不能据此直接改线序/频率/加重复sensor PD。
2. 197所有临时节点、FW、CCI适配器与模块已撤销，原CAMSS仍有22实体空sensor图。要重建notifier需普通CAMSS重新probe；退出先释放CAMSS notifier再删overlay，然后恢复原模块。原196 overlay复用固件文件名k196；197模块/准备目录及取帧脚本参考README，失败前先读真实状态。
3. Hotdog只读参考/home/cy122/x2pro-linux/hotdog-ref195固定47087509c4289c2580c54f5433e55366b2e00445，其1748方形/525.2625MHz/CAMNOC补丁只作比较。PM8009/BOB/gate/CCI1 master0/弹出机构不照搬。PLDO物理网络、P/Q整机冷启动、其它镜头、完整模式/用户态仍待验。
4. GNSS191 300秒303NMEA、online后90秒仍无fix/CNR，16SV事件无列表；RF/接收条件/平台未分，继续GeoClue/辅助自动加载及本机RF/时钟核对。两UIM no-atr/absent-active、MM sim-missing/bearer0不证明物理插卡状态；注册/数据/通话/SMS待验。
5. BT phase5/3.2Mbps/chunk13/partial0/firstff重组1区别185 phase2 NUL，只扫描。FastRPC普通信号/freezer、共享池−22/SSR和传感器运动/亮暗/方向/精度/冷启/长稳开放；189三PM45.2–45.3秒success3/fail0、7266 callbacks err0/桌面Claim是已证范围。Wi-Fi第二PM35秒未关联、第三PM后恢复，不称自行恢复。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(s.encode())<=6500,len(s.encode());archive=root/'archive/NEXT-SESSION-through196-2026-10-15.md';assert not archive.exists();archive.write_bytes(old);(root/'NEXT-SESSION.md').write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段197。CAMSS clock lane7校验修复，IMX471实体media链路建立；三次物理采集CSID reset超时，无实体帧。原/候选无sensor TPG均VFE reset失败，活动core AHB引用与硬件状态不一致待查。21014.32秒同189 boot/taint512，无新增所列故障，临时资源撤销/原CAMSS恢复。GNSS/蜂窝/BT等完整goal active。[197报告](../../reference/kernel197/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,l in enumerate(lines):
 if l.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 197修复clock lane7校验并通过29实际C场景，23实体含普通IMX471→CSIPHY2→CSID0→VFE；原驱动/拓扑/供电/三脚/时钟引用恢复，196 ID与短PM证据保持 | 实体取帧3次CSID reset超时/0帧；原及候选TPG均VFE reset失败，活动core AHB count4/hwN待查。当前boot未通过TPG。PLDO父网络、双PMIC冷启、其它镜头/模式/用户态待验；193 WARN/taint512保留 |'
p.write_text('\n'.join(lines)+'\n');print(json.dumps(dict(stage=197,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(s.encode()))))


