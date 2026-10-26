from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel194';old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段193' in old.decode()
text='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段194，完整外设goal active。PM8008 Q复位地址8→运行地址4已由普通MFD驱动在真机验证，已分配地址probe也通过。IMX471 OF/三路电源/pinctrl候选已构建并加载验证ABI，尚未实体probe或取帧。193实际前摄ID0x0471保持；其r2时钟WARN/taint512未清除。规则见[边界](WORKING-BOUNDARIES.md)，用户暂无耳机。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 部署 | kernel183/logdump183、boot/DTB172、modules132覆盖hci_uart185/fastrpc189；Mesa149/UCM173、MM191 |
| 相机194 | Q GPIO4复位后8/9、SID2；新MFD自身设置SID1迁移4/5并绑定/注册七LDO；warm直接probe。前中后全部采样一致，临时节点/模块撤销，P0/Q1恢复 |
| 最新15014.14秒 | 同189第二boot，taint512/WARN1来自193r2；ADSP/SLPI/modem running，MM191/PowerState3/GPS0，SensorProxy三个Has true；BT重组1，Oops/GPU/SLPI fatal0 |
| GPS191 | 标准MM 50406字节50片XTRA注入，49片完成先到，固件有效期0→168小时；UTC成功。300秒303NMEA仍无fix/CNR，online后另90秒仍无fix |
| 传感器189 | 三轮45.2—45.3秒PM，success3/fail0/RTC3，7266 callbacks err0；四CLI及Wayland UID10000 Claim/Release通过 |

依据：[194报告](reference/kernel194/README.md)、[MFD原生](reference/kernel194/pmic-native-validation.json)、[最终健康](reference/kernel194/native-health-validation.json)、[193实体ID](reference/kernel193/README.md)。[193逐字快照](archive/NEXT-SESSION-through193-2026-10-15.md)保留旧源、失败及回退索引，相对链接按根目录解释。

## 源码、产物与回退依据

- WSL源/home/cy122/pmos-samurai-kernel136/kernel。原14源保持；当前19个tracked改动，新增Sony绑定与3个OF开发C文件，均未暂存。194开发代码/两绑定分开checkpatch通过，完整集合有3项“绑定应分开”提示。[最终源/补丁](reference/kernel194/source-final-validation.json)
- IMX471源30e94aa1…、模块62e5f050…/CCI库f9c9272a…；MFD源0101c9b5…/模块9382ba34…；fixture e5b9405e…。均树内Kbuild/ABI/导入符号通过，非强制加载。7+35实际C函数场景ASan/UBSan通过；目标W=1无告警，全树另5条既有告警。模块仅私人临时加载，安装目录未改。
- [前摄候选DT](reference/kernel194/sm8150-samurai-camera-warm.dts)引用真实三路电源/选择GPIO/CCI1 master1/DPHY2；Q有reset/initial-address，P暂用GPIO1 hog保持复位。独立DTB d79dd115…未部署；Sony严格schema通过，PMIC仍缺四路PLDO输入报4项required，未伪造接线。不是上游完整板级DT。
- Image183 bfa72dd9…、canonical DTB 22c1f2ad…、config 55f1f0a3…保持；Module.symvers16793行/modules.order770恢复。193独立前摄PM引用修复/失败保留。运行FastRPC源41c8db5c…/模块88553112…，hci_uart f6c5ed35…；原件回退在189，不强卸载活跃模块。
- MM固定7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a，190能力发现+191 LOC异步/引用/分片/回退修复；257场景/4原版失败/3破坏变体通过。原生XTRA通过，Predicted成功仅模拟。运行b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc，源949132f3…，MM native190源已更新191；签名SDK复用，APK DB未改，正式入包待办，APK更新会覆盖。
- MM190回退fbc40848…在手机k191-mm-deploy/ModemManager.original/主机kernel191/ModemManager.before191，发行版4d5a8258…在190。INFO/激活已恢复。DMS只开启过一次，保持online，不重复reset。
- SSC固定1902…文件服务、184独立libssc、每boot一次门控；303来源/24固件只复制私人RAM。A.11路径/lib/firmware/qcom/sm8150/realme/samurai-a11-r187，原00121保留。共享池−22未解决，不盲目stop/start。
- 当前boot手机k189r2-reboot-runtime/boot-id-private.txt，194基线另存；host194沿用190私人Wi-Fi端点、原HostKeyAlias/公钥。USB190双向IPv6未恢复，一次gadget重绑无正向证据、Windows网卡复位拒绝访问；下一boot重新读身份/端点。
- 194归档0afa8fa2…/42、193 936fe956…/67、192 322bfbce…/23均逐成员验证；191主843c4d47…/42及radio b6628078…/23保留。BDS164/固件172/FdtBlob129、183/181及NV/校准备份保持。

## 续作与已知风险

1. 正式IMX471 probe、runtime PM、MIPI/CAMSS真实取帧仍待验。当前驱动只4lane/200MHz/1928×1088 RAW10；绑定允许硬件2/4lane，不代表驱动支持所有模式。前摄193实体ID已确认，其余192 BIN只是候选。VIO当前DT无phandle且ldo1重名，正式候选由编译建立引用，不照搬诊断名称查找。
2. 本次Q复位路径成功不等于整机断电/跨boot通过；若P先占用8，Q安全拒绝且自身保持复位，双PMIC顺序仍待设计。四路PLDO父网络未知，不因本次L5 ready补假BOB/VPH；OEM1.05/1.10V请求实际1.056/1.104V已核。其它镜头/完整模式/用户态待验；内部TPG三帧不是出图。
3. GNSS仍无有效fix/CNR，16条SV事件无列表；接收条件/RF/平台原因未区分。继续GNSS-only GeoClue/辅助自动加载及本机RF/时钟核对，正常授权、不伪造位置；168小时不证明跨基带重启保留。
4. 两UIM no-atr-received/Slot absent-active、MM sim-missing/bearer0不证明物理插卡状态。卡槽/注册/数据/通话/SMS待验。BT phase5/3.2Mbps/chunk13/partial0/firstff重组1区别185旧phase2前导00，只扫描。
5. FastRPC普通信号/freezer、共享池−22/SSR，传感器运动/方向/亮暗/精度/冷启/长稳仍开放，不把失败SCM原型当修复。Wi-Fi189第二轮35秒未关联，第三轮PM后才恢复，不称自行恢复；USB独立链路待解。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(text.encode())<=6500,len(text.encode());archive=root/'archive/NEXT-SESSION-through193-2026-10-15.md';assert not archive.exists();archive.write_bytes(old);(root/'NEXT-SESSION.md').write_text(text)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段194。PM8008 Q的复位地址8→4及warm普通MFD probe真机通过；IMX471 OF/三电源/pinctrl候选已构建及ABI加载，未实体probe或出图。193实体ID0x0471与r2一次WARN/taint512保持；15014.14秒同189 boot，三个DSP/MM191/PowerState3/SensorProxy保持，临时模块全部卸载。GNSS有效fix、蜂窝业务、BT后段重组等仍开放，完整goal active。[194报告](../../reference/kernel194/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 193真实CCI ID0x0471、供电/PM撤销通过；194普通MFD完成Q复位地址8→4和warm probe、七LDO注册/采样恢复；IMX471 OF/三电源/pinctrl模块ABI通过，独立DT候选已构建 | 尚未实体sensor probe/出图；runtime PM与MIPI/CAMSS实测、四路PLDO输入/双PMIC整机冷启动、其它镜头/模式/用户态待验；候选PMIC schema仍4项缺失，193时钟WARN/taint512保留 |'
p.write_text('\n'.join(lines)+'\n');print(json.dumps(dict(stage=194,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(text.encode()))))
