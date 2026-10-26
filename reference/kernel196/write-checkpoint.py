from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel196';old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段195' in old.decode()
s='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段196，完整外设goal active。普通IMX471驱动已在CCI1 master1/0x10通过实体ID0x0471并绑定，一轮运行时供电开关完成；尚未实体出图。孤立endpoint导致hwcfg -517，补真实CAMSS端点后解决，时钟接口试验已撤回。193时钟WARN/taint512保留；规则见[边界](WORKING-BOUNDARIES.md)，用户暂无耳机。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 部署 | kernel183/logdump183、boot/DTB172、modules132覆盖hci_uart185/fastrpc189；Mesa149/UCM173、MM191 |
| 相机196 | OF按VIF→VANA→VDIG，真实三电源/引脚/CCI/DPHY2-CAMSS端点；r5/r6普通probe绑定，r6短PM通过。非ABI-only或独立ID helper；尚未CAMSS取帧 |
| 最新19039.04秒 | 同189第二boot；taint512/WARN1来自193r2，BT重组1来自189；Oops/GPU/SLPI fatal0。ADSP/SLPI/modem running，MM191/PowerState3/GPS0，SensorProxy三个Has true |
| 196撤销 | 六轮无新增所列故障，所有临时模块/节点/适配器移除。三脚输入低/实际CTL恢复，七Q LDO采样恢复、P0/Q1，VIO1.8V关闭/用户0，S8C1.352V/用户3 |
| GPS/传感器 | 191完整XTRA注入0→168小时，300秒303NMEA及online后90秒仍无fix/CNR；189三轮45.2—45.3秒PM success3/fail0、7266 callbacks err0，桌面Claim通过 |

依据：[196报告](reference/kernel196/README.md)、[六轮原生](reference/kernel196/front-native-validation.json)、[健康](reference/kernel196/native-health-validation.json)。[195逐字快照](archive/NEXT-SESSION-through195-2026-10-15.md)保留旧源/回退/比较仓库索引，相对链接按根目录解释。

## 源码、产物与回退依据

- WSL源/home/cy122/pmos-samurai-kernel136/kernel，原14源保持；19个tracked改动、Sony绑定及5个OF开发C新文件均未暂存。196完整开发代码checkpatch/反向apply通过，绑定沿194。[当前源/补丁](reference/kernel196/source-final-validation.json)
- IMX471源110977b8…/模块c49dca63…，CCI库f9c9272a…；OF顺序enable/反向disable、ACPI bulk保留，15实际C函数场景ASan/UBSan通过。required-clock试验源f0956d6b…/模块4eeac6fb…没有解决孤立endpoint，已撤回，最终仍标准V4L2 clock helper。
- 资源overlay源c67b480e…/模块92d9176e…，最终DTBO b240769b…；MFD195源057ccd62…/模块d1ff82c0…，VIO helper9e83668e…、CCI193 helperd3b4610d…复用。均树内Kbuild/符号与ABI核对，最终W=1无诊断；仅私人临时加载，安装模块未改。
- 195 MFD冷迁移与warm真机probe、失败复位回退37场景保持。196 VIO phandle301由现场资源建立后撤销，非硬编码启动值；overlay本地fixups/外部新取引用，不依赖__symbols__。PLDO四路输入仍未知，实际PMIC候选schema四项缺失，不能称完整上游板级DT。
- Image183 bfa72dd9…、canonical DTB22c1f2ad…、config55f1f0a3…保持，Module.symvers16793行/modules.order770恢复。运行FastRPC源41c8db5c…/模块88553112…，hci_uart f6c5ed35…；189原件回退，不强卸载活跃模块。
- 193独立helper只读0x0310f000位于west，不匹配当前DT GPIO15 north，旧CTL比较不能证明MCLK脚恢复。196实际资源地址：12=0x0390c000、15=0x0390f000、29=0x0351d000，原CTL1/0/1六轮恢复；没有直接MMIO写。后续用实际资源核对，不沿用旧比较结论。
- MM固定7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a，190能力+191 LOC顺序/引用/分片/回退修复；257场景/4原版失败/3破坏变体通过。运行b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc，源949132f3…。XTRA原生成功，Predicted仅模拟；APK DB未改，正式入包待办，APK更新会覆盖。DMS只开启一次，保持online不重复reset。
- MM190 fbc40848…回退在手机k191-mm-deploy/ModemManager.original/主机kernel191/ModemManager.before191，发行版4d5a8258…在190；INFO/激活恢复。SSC固定1902…文件服务、184 libssc/每boot一次门控，A.11 /lib/firmware/qcom/sm8150/realme/samurai-a11-r187及原00121保留。共享池−22未解，不盲目stop/start。
- 当前boot手机k189r2-reboot-runtime/boot-id-private.txt，196基线另存；host196沿190私人Wi-Fi端点、原HostKeyAlias/公钥。USB190双向IPv6未恢复，gadget一次重绑无正向证据、Windows网卡复位拒绝访问；下一boot重新读身份/端点。
- 196归档c7c98afc…/160、195 10c5f4aa…/37、194 0afa8fa2…/42均逐成员验证。更早证据/回退见快照；BDS164/固件172/FdtBlob129、183/181及NV/校准备份保持。196未刷写/重启。

## 续作与已知风险

1. 优先重新建立CAMSS notifier/media链路并实体取帧。当前普通sensor probe与一次短PM通过，1928×1088 RAW10/4lane/200MHz；未执行mode/stream寄存器。孤立endpoint会被fwnode API跳过，需真实双向远端。CCI runtime suspended时同窗TITAN on、MCLK enable1/Y/19.2MHz；不据CCI状态单独推断域关闭，也未加sensor重复PD。
2. Hotdog只读参考/home/cy122/x2pro-linux/hotdog-ref195固定47087509c4289c2580c54f5433e55366b2e00445，其1748方形/525.2625MHz及CAMNOC补丁私人保存，和本机126已通过TPG/DMA先比较。PM8009/BOB/gate/CCI1 master0/弹出机构不照搬。
3. PLDO物理父网络、P/Q整机冷启动、其它镜头/完整模式/用户态待验。若P先占用8，Q安全拒绝并保持复位；迁移出错请求自身复位，GPIO调用失败只记错不保证物理恢复。OEM1.05/1.10V实际1.056/1.104V已核。本轮退出恢复的是关闭输出时原VSET1200/1800mV，不是工作电压。
4. GNSS仍无有效fix/CNR、16条SV事件无列表；RF/接收条件/平台未分。继续GNSS-only GeoClue/辅助自动加载及本机RF/时钟核对，正常授权不伪造位置。两UIM no-atr/Slot absent-active、MM sim-missing/bearer0不证明物理插卡状态，注册/数据/通话/SMS仍待验。
5. BT phase5/3.2Mbps/chunk13/partial0/firstff重组1区别185旧phase2 NUL，只扫描。FastRPC普通信号/freezer、共享池−22/SSR，传感器运动/方向/亮暗/精度/冷启/长稳开放。Wi-Fi189第二轮35秒未关联，第三轮PM后才恢复，不能称自行恢复；USB独立链路待解。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(s.encode())<=6500,len(s.encode());archive=root/'archive/NEXT-SESSION-through195-2026-10-15.md';assert not archive.exists();archive.write_bytes(old);(root/'NEXT-SESSION.md').write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段196。普通IMX471通过实体ID0x0471并绑定，一轮运行时供电开关通过；尚未实体出图。真实CAMSS端点修复hwcfg -517，时钟试验已撤回；193 west GPIO15辅助比较已纠正为本轮实际north资源核对。19039.04秒同189 boot/taint512，六轮无新增所列故障，临时资源已撤销。GNSS/蜂窝/BT等完整goal active。[196报告](../../reference/kernel196/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 196普通IMX471在CCI1 master1实体ID0x0471通过/绑定，一轮短PM三电源开关通过，同窗TITAN on/MCLK1/Y；实际三脚CTL/七Q LDO采样恢复。195 MFD地址迁移/失败回退保持 | 尚未实体出图；CAMSS notifier/media链路及模式/取帧、四路PLDO输入/双PMIC整机冷启动、其它镜头/用户态待验。一次短PM不代表长稳，193时钟WARN/taint512及旧west寄存器辅助比较错误保留 |'
p.write_text('\n'.join(lines)+'\n');print(json.dumps(dict(stage=196,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(s.encode()))))
