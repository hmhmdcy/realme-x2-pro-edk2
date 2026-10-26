from pathlib import Path
import hashlib,importlib.util,json,subprocess
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel233')
health=json.loads((R/'final-health-validation.json').read_text());evidence=json.loads((R/'evidence-validation.json').read_text())
assert health['taint']==0 and not any(health['fault_counts'].values()) and evidence['all_members_verified']
archive=ROOT/'archive/NEXT-SESSION-through232-2026-10-16.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
else:assert archive.read_bytes()==(ROOT/'NEXT-SESSION.md').read_bytes()
text='''# Realme X2 Pro 当前检查点

2026-10-16，233：232 PM8008候选已实际部署，新boot身份/P身份、Q暖/provider冷managed解绑及前摄RAW/RGB回归通过，taint/fault0。后摄仍未出图；完整goal active。[233](reference/kernel233/README.md)、[上一交接](archive/NEXT-SESSION-through232-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输reference/kernel233/host.py，严格原公钥/USB新邻居；guard /var/lib/samurai/k233-runtime/boot-id-private.txt。所有此前guard包括230-runtime均失效。私人233/current-work-private.json为操作指针。当前无活动切换/构建/捕获，跟踪实例已删除、WP/桌面恢复。
- boot232实际45f398f2…/100663296B，DTB7e8345ae…；Image183 bfa72dd9…、logdump183 e73754c7…保持。本轮一次Linux→bootloader、fresh fastboot核身份/几何后仅刷boot一次、reboot一次。NCM初次尚未Up，实际出现后刷新邻居连回，未重复切换。
- 新MFD f633467f…/20520B、reset provider2223f337…/9744B，实际加载note与默认一致/intreeY。加载前options experimental_p_address_only=1与softdep provider顺序经kmod query验证。P/Q/provider均绑定，P身份0x0100匹配；P无secondary dummy/MFD/regulator子设备，未知VIN未填写。Q七路关闭/用户0。
- Q逐设备暖unbind先拆P、provider保持；Q重绑后P自动再探测，七路Q状态/电压保持、无冷迁址。provider逐设备冷unbind拆P/Q，软件GPIO trace为P0/P0/Q0，重绑P0/Q0/Q1/P0/P1，完成一次8→4后才释放P。不能称管脚电压物理读回。无恢复性补绑，前摄sensor/WP恢复、桌面/PipeWire身份保持。
- 前摄e49dab26…/29536B、CAMSS fae1ed40…/777360B，libcamera99990.7.2-r13/config0.1.0-r8保持；CCI1/master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2。冷循环后RAW/RGB各6帧有效非全零，RAW均值117.739–120.819、RGB26.6843–70.8944，图/格式/控制/PM恢复。仅RAM统计、不存照片、不加照明；纯色参照按用户延期，不再追问，不称颜色准确/AE收敛。设备/CCI/CAMSS suspended、双轨关/users0、图案0/fullres=N。
- 773ko/787相关文件及944包核对；FastRPC运行/默认2abde0ea…/50192B/intreeY、ref1。taint0/全部模块taint空，WARN/Oops/GPU/DSP fatal/BT重组0。三DSP running、SensorProxy三Has真；新boot自动真实加速度69/光线10条readiness。230五流/保活/活动Wayland Claim是前一boot证据，不冒作本次全矩阵。
- Wi-Fi connected、chrony Normal；GPS0/Signalsfalse/rate30，watch空闲/UTC自动准备/data worker0，无新搜星/注入。226四轮零CNR/168h XTRA是旧启动证据。MM191 b350c55b…保持，State−1/原因2/Power1，用户无SIM；BT关/无连接，phase5未修。

## 源码、产物与回退依据

- 接受的实验组件完整源/补丁/两板源/接入片段及source-lock在linux-port/camera/pmic。MFD源bd6c578e…、provider b0e46fad…。真实树内W=1零诊断/匹配ABI；97例实际函数ASan/UBSan、三个删除防护负对照通过，现已补原生Q暖/provider冷循环。编译用CONFIG_RESET_REALME_RMX1931_PM8008=m覆盖；canonical仍after228，未声称完整新内核/rootfs重建或供电schema通过。
- canonical /home/cy122/pmos-samurai-kernel136/kernel：FastRPC f378afed…已在228整合，16798符号/772全局顺序、配置/Image/DTB保持。相机canonical仍旧216 IMX/旧CAMSS，不刷整体输出。当前相机源锁及r13/r8见camera/kernel、225；完整FastRPC在ssc/kernel。SSR/DMA排空、reclaim−22、新模块PM/精度开放。
- 232候选boot45f3在私人232/boot-partition-k232-pmic-identity.img，完整解包证明仅内嵌DTB改变、固件代码/头/ramdisk/兼容DTB/尾保持；219回退156f0370…/96MiB在私人219/boot-partition-k219-front-modes.img。旧MFD d1ff82c0…/14336B在设备k233-baseline及k233-module-stage，14元数据备份于k233-baseline/module-metadata-before；原配置新增项此前不存在。回退须新身份，原子恢复文件/配置/元数据后正常重启，不能热卸有children模块。
- 暂存三I/O异常验证通过。实际暂存仅改变MFD+新增provider及depmod/一份配置，旧195保留到重启。清理四前摄端点，保留旧Q/regulator，不复用230历史断言；restart页长4096未改。前/后分区与模块清单分开核对。
- 其它回退见232归档。私人233原生158成员逐项核对，含暂存/清理/新启动/循环/前摄/最终健康和232加载审计；无场景像素，归档指纹不公开。最后完整镜像232为8486文件/HEAD5c80582，233镜像以私人233最终收据为准。

## 续作与已知风险

下一步进入真实后摄驱动/供电：IMX319的L1P1.104V/L4P2.8V和原厂序列已知，先严格限制只注册这两路（0x09），不把七路统一相机化：OEM L7P为指纹3.3V。当前P无VIN；OEM源另有P@9 NLDO→S8C声明，必须与当前Q→S8C区分，PLDO父网仍未知，不编造。真实父供电可能被core按dropout投票，须核最终固定约束。dummy不证明物理VIN。两家IMX319 BIN共136 init及前五模式一致，1632×1224为171条WRITE8/RAW10/四lane；需XML独立交叉核对及实际OF/runtime实现，226/227只有设计。详见233/RESEARCH-FOLLOWUP。

BT优先补phase5有界诊断的had_skb/type/expect/padding/RX序号并关联GENI；partial0不是已证帧边界、firstff不是错误offset，不补04/吞FF。205 RTS模型编译失败，没有16例通过；先修模型/实际函数负对照，再审set_termios/RFR同步。不要用未复现或已有DMA补丁称修复。

GNSS仍无正CNR/TRACK/fix，室内窗边/无无遮挡户外或同机Android基线。231 shared是persist独立命名空间、原厂mdtime也缺，当前RRQ拒绝统一error1（源码推导无抓包），未部署伪别名/规则。R RF线缆GPIO26/SMEM136未证GNSS依赖；82已纠正所谓stock回滚boot是第三方，226基础DTB来源未知，不拿来跨版本推断。继续RF/OEM真实差异，不重做已过online/精度/辅助矩阵。

后摄四路、前摄真实CFA/白平衡/几何/光学延迟/GUI/性能、GPU ISP211黑帧/unmap349 WARN、传感器运动精度/PM/SSR、Wi-Fi/USB PM与大块截断、音频/耳机缺失、充电保护、指纹/NFC实卡、rootfs132可复现整合等见[完整清单](linux-port/docs/HARDWARE-STATUS.md)。三路只读研究授权保持，手机串行；不能把局部通过当全goal完成。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
status=ROOT/'linux-port/docs/HARDWARE-STATUS.md';s=status.read_text();start=s.index('用途：');end=s.index('\n\n',start)
s=s[:start]+'用途：当前硬件验收清单。最后核对2026-10-16，233。后摄PM8008依赖已受控部署，新boot/P身份、Q暖/provider冷循环及前摄RAW/RGB回归通过，taint/fault0；后摄尚未出图。当前boot232/两个PMIC新模块，Image183/r13-r8保持。用户延期前摄纯色校验，完整goal active。[233](../../reference/kernel233/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[end:]
s=s.replace('boot219/e49/fae1保持','boot232/e49/fae1保持')
s=s.replace('232后摄复位/地址/身份候选仅离线通过、待部署','233后摄复位/地址依赖已部署，P身份及Q暖/provider冷managed解绑通过、无P供电子设备，前摄RAW/RGB各6帧回归通过；真实后摄供电/驱动待做')
status.write_text(s)
for stage in [230,231,232,233]:
 dest=P.parent/('kernel'+str(stage))/'current-work-private.json'
 data=json.loads(dest.read_text());data.update(next='Continue from private233/current-work-private.json and root checkpoint; 233 hardware PMIC deployment/native cycles/front regression passed. Guard233-runtime; all earlier guards stale.',full_peripheral_goal_active=True,front_known_colour_test_deferred_by_user=True)
 if stage==233:
  data.update(state='233 native deployment, Q warm/provider cold cycles, front RAW/RGB and final health passed; full goal active',guard='/var/lib/samurai/k233-runtime/boot-id-private.txt',active_native_context=None,active_native_session=None,active_build_session=None,active_evidence_session=None,transition_pending=False,native_members=158,previous_goal_turn_classification='progress',next='Advance strict L1P/L4P partial regulator/IMX319 OF-runtime/native table candidate, or bounded BT phase5/RTS model; see233 RESEARCH-FOLLOWUP. Do not repeat passed PMIC/camera matrices. Runtime233 guard. Canonical after228 preserved; experimental source profile published.')
 dest.write_text(json.dumps(data,indent=2)+'\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
for file in R.glob('*.py'):compile(file.read_text(encoding='utf-8-sig'),str(file),'exec')
for file in R.glob('*.sh'):subprocess.run(['sh','-n',str(file)],check=True)
report=dict(stage=233,python_compile=len(list(R.glob('*.py'))),shell_syntax=len(list(R.glob('*.sh'))),checkpoint_bytes=len((ROOT/'NEXT-SESSION.md').read_bytes()),private_native_members=158,hardware_pmic_and_front_regression_verified=True,full_peripheral_goal_active=True)
(R/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
