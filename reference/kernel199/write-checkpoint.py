from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段198' in old.decode()
s='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段199，完整外设goal active。CAMSS已集成运行时MMCX请求，保持原频率表、无需独立性能helper，两轮IMX471实体1928×1088 RAW10共6帧及两轮暂停/再恢复通过。静态DT/模块成对启动部署待做。193 taint512保留；199热overlay更改既有属性产生两条OF内存警告。见[边界](WORKING-BOUNDARIES.md)。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 仍部署 | kernel183/logdump183、boot/DTB172、modules132覆盖hci_uart185/fastrpc189；CAMSS安装仍旧e9b73f4c…，Mesa149/UCM173、MM191 |
| 新CAMSS199 | 候选82cbc052…保持频率表；自身第四域mmcx runtime384→0，两轮共6帧、pattern0、RAW变化/序号/时间戳及>99.9% DMA覆盖通过，无400MHz上限/独立helper |
| 活动/暂停 | 两活动快照自身genpd:3 active384、VFE847MHz/CSID600MHz/Y；两轮idle自身suspended0；移除后聚合64。之前独立消费者原安装CAMSS TPG3帧通过，聚合64→384→64 |
| 最新23456.64秒 | 同189第二boot；taint512，WARNING总3=193内核WARN1+199 OF属性警告2；Oops/GPU/SLPI fatal0，旧BT重组1。ADSP/SLPI/modem running，MM PowerState3/GPS0，SensorProxy三个Has true |
| 恢复 | 原模块/三域属性/22实体空sensor图恢复，临时资源撤销。三脚/七Q LDO采样/P0Q1恢复，VIO1.8V关/用户0、S8C1.352V/用户3。相机闲置高频最后约847/600MHz，引用归零 |

依据：[199报告](reference/kernel199/README.md)、[原生](reference/kernel199/front-native-validation.json)、[健康](reference/kernel199/native-health-validation.json)。[198逐字快照](archive/NEXT-SESSION-through198-2026-10-15.md)保留旧源码/回退/参考仓库索引，相对链接按根解释。

## 源码、产物与回退依据

- WSL源/home/cy122/pmos-samurai-kernel136/kernel；25 tracked改动/11 untracked（6相机源+5旧备份）未暂存。原14其它源及sensor/MFD/OF helpers保持。新增CPAS/core/DTS/binding三补丁系列各checkpatch/反向apply通过。[收据](reference/kernel199/source-final-validation.json)
- CPAS源3ee20b59…、core53d8a710…、模块82cbc052…；r2格式修正后二进制与实测相同。17实际C场景ASan/UBSan及缺请求变体拒绝，W=1零诊断，频率表保持。
- CPAS自己的mmcx/device-link在runtime恢复前请求384、暂停撤销；失败暂停保留请求/时钟并恢复ICC。活动按最高950MHz需求，未细分模式。原厂VDD_HIGH=TURBO，SM8150_MMCX=9。
- 静态DT在主机kernel199/sm8150-samurai-mmcx-static-private.dtb，2e2f8e64…/108410字节；canonical22c1…仅改CAMSS两域属性，908节点其余属性/phandle相同。未打包/启动/刷写。源DTS/binding也4域，节点schema及3负例通过，不称全板验证。
- 新驱动需要四域DT，安装仍旧e9b73f4c…。Image183 bfa72dd9…/DTB22c1f2ad…/config55f1f0a3…保持，符号16793行/顺序770恢复。未刷写/重启，NV/校准备份保持。
- IMX471源110977b8…/模块c49dca63…、CCI库f9c9272a…；OF VIF→VANA→VDIG/反序关，ACPI bulk保留。OF overlay源c67b480e…/模块92d9176e…，固定FW文件名samurai/k196-front.dtbo；199四域开发DTBO6a77ec47…已撤销，196无MMCX属性更新DTBO b240769b…保留。
- MFD/VIO/CCI helper及回退详见198快照，195冷迁移/warm及复位37场景保持。PLDO四路输入未知/schema4项缺失，P占8时Q拒绝。OEM1.05/1.10V编程1.056/1.104V；退出恢复关闭输出VSET1200/1800mV。
- GPIO12/15/29实际CTL0x0390c000/0x0390f000/0x0351d000，初值1/0/1；193 west0x0310f000不能证明GPIO15 north恢复，196–199按实际资源核对。新现场phandles56/201/240/251、RPMH124/索引9、临时VIO301核后撤销，下一次重读。
- FastRPC源41c8db5c…/模块88553112…、hci_uart f6c5ed35…及189回退保持。MM运行b350c55b…，固定源7f0bf17…/949132f3…；XTRA50406字节0→168h，Predicted仅模拟。MM正式入APK待做，更新会覆盖；197仅新增视频工具包。
- MM/SSC回退见198快照，INFO/DMS online、184门控/A.11固件/00121保持，不盲目stop/start。用户暂无耳机。
- 当前boot身份k189r2-reboot-runtime/boot-id-private.txt，199另存；host199沿198→190私人Wi-Fi端点、原HostKeyAlias/公钥。USB190双向IPv6未恢复；新boot重读身份/端点。
- 199私人89原生文件逐成员核验，含两张实体RAW；图像/统计/相关哈希只私人保存E:\\edk2-samurai-out\\kernel199。198 87文件及197/196更早归档见快照。

## 续作与已知风险

1. 成对准备静态四域DT2e2f8e64…/CAMSS82cbc052…启动包和回退，fresh核设备后部署，验证冷启/实体采集/暂停。当前仍旧boot/模块。保留Image/已验字段，两个属性变化及源DTS已核；schema全源码候选1f980473…不是已验boot产物。
2. 199热overlay更新既有power-domains/names触发OF内存保留警告2条，已撤销属性但警告/少量保留内存不假装消失。当前同boot WARNING总3，只有193旧clk_branch_toggle是真内核WARN；未新增内核WARN/其它所列故障。新baseline同boot应据实区分，不能套旧warning1。后续静态DT避免该属性替换路径并实机核对，不抑制告警。
3. 实体会话k199-front-capture-r1；helper75007bf6…仅独立TPG原型，集成采集未加载。新DT启动后使用不再更新MMCX属性的sensor overlay；FW仍固定k196-front.dtbo。退出先释放CAMSS notifier，再删overlay/恢复原模块。
4. core AHB hw0亦见于成功帧，不当单独根因；193 CTL辅助错误已纠正，198限频已撤回。曝光/色彩/方向/光学/其它模式/持续帧率、其它镜头/用户态、PLDO网络/双PMIC冷启/长稳待验。
5. GNSS191 300秒303NMEA、online后90秒仍无fix/CNR，16SV无列表；继续GeoClue/辅助自动加载与RF/时钟核对。两UIM no-atr/absent-active、sim-missing/bearer0不证明物理插卡状态；注册/数据/通话/SMS待验。
6. BT phase5/3.2Mbps/chunk13/partial0/firstff重组1区别185旧NUL，只扫描。FastRPC普通信号/freezer、共享池−22/SSR及传感器运动/亮暗/方向/精度/冷启/长稳开放；189三PM success3/fail0、7266 callbacks err0/桌面Claim仅已证范围。Wi-Fi第二PM35秒未关联、第三PM后恢复，不称自行恢复。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(s.encode())<=6500,len(s.encode());p=root/'archive/NEXT-SESSION-through198-2026-10-15.md';assert not p.exists();p.write_bytes(old);(root/'NEXT-SESSION.md').write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段199。CAMSS集成MMCX运行时请求，保持原频率表/无独立性能helper，两轮IMX4711928×1088 RAW10共6帧和384→0暂停/恢复通过。静态DT2e2f8e64…与模块82cbc052…待成对启动部署。热overlay替换既有属性产生OF内存警告2条；23456.64秒同189 boot/taint512，WARNING总3含旧内核WARN1，无新增内核WARN/Oops/GPU/SLPI fatal。完整goal active。[199报告](../../reference/kernel199/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,l in enumerate(lines):
 if l.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 199 CAMSS自身MMCX runtime请求384→0，保持原频率表、无外部性能helper，两轮IMX471 RAW10共6帧和暂停/再恢复通过，活动VFE847/CSID600MHz。17实际C场景/W=1/schema及三补丁检查通过 | 静态四域DT/配套模块尚未部署启动，旧安装已恢复；热overlay更新既有属性引入两条OF内存警告，需静态启动复核。曝光/色彩/其它模式/镜头/用户态/冷启长稳、PLDO网络待验。core AHB hw0非单独根因 |'
p.write_text('\n'.join(lines)+'\n');print(json.dumps(dict(stage=199,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(s.encode()))))
