"""Record the actual first rear RAW, retained failures and current CAMSS."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel237')
health=json.loads((R/'final-health-validation.json').read_text());evidence=json.loads((R/'evidence-validation.json').read_text());build=json.loads((R/'camss-build-validation.json').read_text());probe=json.loads((R/'physical-probe-build-validation.json').read_text())
assert evidence['all_members_verified'] and health['taint']==0 and not any(health['fault_counts'].values())
for which,kind in [('rear','raw'),('front','raw'),('front','rgb')]:assert json.loads((R/f'{which}-{kind}-capture-r2-validation.json').read_text())['passed']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/'native-physical-probe.cpp')==probe['source_sha256']
assert all(sha(R/'camss-source'/n)==v for n,v in build['source_inputs'].items())
assert build['sha256']==health['default_and_loaded_modules']['qcom_camss']
spec=importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
assert helper.snapshot()==json.loads((P.parent/'kernel228/canonical-after-private.json').read_text())
text='''# Realme X2 Pro 当前检查点

2026-10-16，237：IMX319真实RAW六帧、前摄RAW/RGB各六帧回归通过，CAMSS回收已修；后摄近黑，曝光/光学/RGB/颜色待验。goal active。[237](reference/kernel237/README.md)、[236归档](archive/NEXT-SESSION-through236-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 仍236启动，guard /var/lib/samurai/k236-runtime/boot-id-private.txt，233及更早失效。运输reference/kernel237/host.py、私人237/current-work-private.json为操作指针。无活动手机worker/构建/切换，trace已删；未重启/刷分区。
- boot235 44c6a215…/100663296B、DTB469e1456…、Image183 bfa72dd9…、logdump183 e73754c7…保持。MFD6021a359…/22208B、lab5198e2bd…/17992B、provider2223f337…/9744B、imx319176f68d7…/36624B、前摄e49dab26…/29536B、FastRPC2abde0ea…/50192B、BT185 f6c5ed35…保持，默认/加载note匹配/intreeY。
- CAMSS已由fae1更新为ff9fdfa346249d836…/777680B。新鲜ref0/无相机客户端/五设备休眠后仅卸换CAMSS一次，两sensor及MFD/P/Q/provider保持。当前权威789文件清单为设备k237-camss-install/module-inventory-after-private.json，236清单中的旧CAMSS已过时；775ko/789文件中仅该ko摘要改变。
- 后摄imx319 7-0010现subdev14，前摄imx471 9-0010现subdev15，编号不固定。新probe同时核完整OF camera ID、Model、实体及sysfs对应关系，FrameSuccess、单预期stream/plane、序号/时间戳递增；旧219/233硬编码CCI1探针不可验后摄。
- 后摄1632x1224 RAW10六帧序号0..5、stride2048，每行2040有效字节+8padding，完成间隔32.621–33.445ms/窗口约30.15fps。样本62–78、均值64.2454–64.2656，帧间约32.36–32.59%值变化；不是全零，但接近黑电平64。完成时间不是SOF/曝光起点标定，未确认遮挡或其它原因，不称颜色/光学响应已可用。
- 前摄2304x1728 RAW、2296x1728 CPU RGB各6帧通过。三组均恢复整个媒体图、所有subdev格式、两sensor控制/翻转、sensor及CSID图案0，P/Q rails逐项保持；两sensor/CCI0/CCI1/CAMSS suspended、四相机rails OFF/users0、MCLK1/2关。实验unprocessed_fullres=N，用户延期的前摄纯色参照不再追问。只RAM统计，不存/显示场景/不闪光/不加照明。
- 首wrapper因错误参数名experimental_full_resolution在Popen之前失败，无帧；原源/失败/回收结果保留。r2首launcher又因复用xb日志路径在Popen之前退出，已核r2 context不存在/无worker，再改唯一日志名。实际r2三组各启动一次，无观察超时重放；finally逐步尽力恢复并累计错误，成功组restore_errors空。
- 最终775ko/789文件、944包/用户态/config/分区复核通过，三DSP running、SensorProxy三Has、Wi-Fi/chrony正常，taint及模块taint空、WARN/Oops/GPU/DSP fatal/BT重组0。BT开启/未发现/1连接仅观察，本轮未pair/connect/disconnect；GNSS0/Signalsfalse/rate30、watch空闲/timeprepared/dataworker0，无新搜星/注入或正CNR/fix。MM State−1/原因2/Power1，用户无SIM。

## 源码、产物与回退依据

- reference/kernel237/camss-source保存fae1四个SOF文件+video适配完整源。借鉴Hotdog47087509/0114：开流失败停此前成功下游、排除失败实体/保留原ret；正常stop个别错仍继续；VFE先摘指针/pending再只返ACTIVE且去重，active_num只在VFE170清，不写gen1 union。Linux7.3 prepare/unprepare及alloc_start、SOF/IRQ/clock/板级资源保持。375图启停+8192buffer实际函数ASan/UBSan与4负对照通过，非IRQ/并发或硬件故障注入。
- 树内W=1零诊断/183 ABI/符号/intree通过，canonical仍精确after228、16798符号/772顺序，Image/DTB保持；相机仍旧216/旧CAMSS，不刷旧输出。linux-port完整profile/kernel/rootfs仍开放，235/236冻结源保持。
- 237新探针native-physical-probe.cpp为29783f5b…，89112B二进制13b66342…，-Werror构建通过；显式pattern恢复/readback、stop/release检查、回调异常捕获。DMA_BUF start/end及有效RAW10像素统计保持。源码/产物/测试/原生收据见237，100原生成员已逐一私有校验，无像素或私有归档指纹公开。
- CAMSS旧fae1及元数据备份设备k237-camss-install/before，私人237证据归档含精确副本，新候选camss-build-r1；原fae1冻结源为私人223/kernel-before-paired-sof加sof-candidate-source四覆盖文件。回退需当前身份、停客户/ref0/PM和受控卸换，不直接重放本轮一次性脚本。235-stage/before仍有旧232 MFD+元数据/config，236-lab-fix/before有旧lab。当前lab有消费者，不能再用未绑定/ref0前提热换；不热卸有children的MFD。
- 235 boot私人235/boot-partition-k235-imx319-p-lab.img；232回退45f398f2…、219回退156f0370…继续保留。P仅mask9/L1P1.104V/L4P2.8V，无假VIN，其余五路不注册/写。PMIC父epoch故障、独立P复位隔离及I2C关闭+reset双失败的ref/WARN风险见236归档，隔离不等于寄存器恢复/物理电压实测。不触NV/校准/工厂备份。

## 续作与已知风险

下一步先补IMX319 libcamera helper：已查实际r13无helper/properties，gain code被直接当倍率，2.0只写code2约1x；真实2/4/8x为512/768/896。OEM3332行曝光被驱动默认1270行覆盖。再扩展exact探针验证显式曝光/增益及元数据、CPU RGB，不重放同样六帧。保持清理/前摄回归，无需纯色参照。222MHz link/209066666Hz VT仍推导，约30Hz完成不是时钟标定。

已授权只读代理：rear_camera_research审曝光链，peripheral_research审S5K3M5 19.2MHz，gnss_research离线审vendor GNSS ELF/rc/依赖。先读其结果，手机由主线程串行操作。

CSID need_vc_update使普通stop可能不写halt，但本轮单用户失败STREAMON和正常STREAMOFF均经unprepare→最后PM put→CSID IRQ/clock/poweroff，下次poweron重置。共享/持电重配语义仍开放，不宣称三hunk修好所有硬件故障。GNSS公开2024 SM8150/新SDK初始化不等于本机Android10版本，未找到可部署RF差异；不重复同CID/GSV/unlock/辅助矩阵，不盲分配MEMSHARE。[GNSS核对](reference/kernel237/GNSS-FOLLOWUP.md)、[近机型方案](reference/kernel236/RELATED-LINUX-SOLUTIONS.md)。其它后摄、传感器精度SSR、蜂窝业务、GPU ISP/PM/音频/充电/指纹/NFC/rootfs仍见[清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(text.encode())<=6500,len(text.encode())
(ROOT/'NEXT-SESSION.md').write_text(text)
status=ROOT/'linux-port/docs/HARDWARE-STATUS.md';s=status.read_text();a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'用途：当前硬件验收清单。最后核对2026-10-16，237。IMX319六帧1632×1224 RAW10成功、近黑光学响应待验；前摄RAW/CPU RGB各六帧回归通过，CAMSS失败回收已更新ff9。最终taint/fault0；BT开启1连接仅观察，GNSS无正CNR/fix。完整goal active。[237](../../reference/kernel237/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[b:]
lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):
  lines[i]='| 摄像头 | 当前boot235/236启动，前摄e49、CAMSSff9、完整libcamera r13/config r8。此前前摄RAW/CPU RGB、手动/自动控制、16MP实验与应用入口实测保持；237后摄IMX319六帧1632×1224 RAW10约30Hz完成、前摄4MP RAW/CPU RGB各六帧回归，三组图/格式/控制/P-Q rails/PM/MCLK恢复，taint/fault0 | 后摄数据近黑电平64，显式曝光/增益与光学响应、CPU RGB/颜色待验；其它三后摄/物理曝光与几何/CFA/方向/GUI/实时性能、GPU ISP、未知PLDO输入、冷启长稳及完整kernel/rootfs开放。前摄纯色参照按用户延期，16MP实验关，TPG普通Bayer不验真实Quad颜色 |'
status.write_text('\n'.join(lines)+'\n')
camera=ROOT/'linux-port/camera/README.md';camera.write_text(camera.read_text()+'\n237已部署CAMSS ff9失败回收修正，IMX319真实RAW六帧成功、前摄RAW/CPU RGB各六帧回归与全恢复通过；后摄近黑的曝光/光学响应及CPU RGB仍待验。[237证据](../../reference/kernel237/README.md)。\n')
(ROOT/'sessions/237-imx319-first-raw-and-camss-unwind.md').write_text('# 237 IMX319首批RAW与CAMSS失败回收\n\n2026-10-16。移植并部署CAMSS失败回收修正ff9，IMX319取得6帧1632×1224 RAW10；前摄RAW/CPU RGB各6帧回归，全图/控制/供电/PM恢复、taint/fault0。后摄接近黑电平，光学响应/曝光及RGB待验，未保存场景。两次Popen前的工具失败保留。\n\n[实现和原生证据](../reference/kernel237/README.md)、[检查点](../NEXT-SESSION.md)、[GNSS核对](../reference/kernel237/GNSS-FOLLOWUP.md)。\n')
p=P/'current-work-private.json';state=json.loads(p.read_text());state.update(state='237 CAMSSff9 loaded; six rear RAW and six each front RAW/RGB passed with full cleanup; rear nearblack optical/exposure response open',active_native_context=None,active_native_session=None,active_build_session=None,active_evidence_session=None,transition_pending=False,rear_raw_capture_verified=True,rear_optical_response_verified=False,current_camss=build['sha256'],current_module_manifest='/var/lib/samurai/k237-camss-install/module-inventory-after-private.json',native_members=evidence['native_members'],previous_goal_turn_classification='progress',full_peripheral_goal_active=True,next='Read 3 readonly agent results; extend exact-camera probe to explicit exposure/gain and capture metadata, verify IMX319 optical response then CPU RGB. Current236 guard. No same6frames replay.')
p.write_text(json.dumps(state,indent=2)+'\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
for p in R.glob('*.py'):ast.parse(p.read_text())
lock={str(p.relative_to(R)):sha(p) for p in R.rglob('*') if p.is_file() and p.suffix in ['.py','.cpp','.c','.h','.patch','.md']}
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
report=dict(stage=237,checkpoint_bytes=len(text.encode()),actual_rear_raw_six_frames=True,front_raw_rgb_regression=True,camss_unwind_deployed=True,nearblack_optical_response_still_open=True,canonical_after228_preserved=True,native_members=evidence['native_members'],python_syntax_files=len(list(R.glob('*.py'))),full_peripheral_goal_active=True)
(R/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
