from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel222')
health=json.loads((here/'final-health-validation.json').read_text());assert health['original_camss_file_and_loaded_note_verified'] and health['taint']==0
assert json.loads((here/'final-evidence-validation.json').read_text())['verified_members']==71
next_text='''# Realme X2 Pro 当前检查点

2026-10-16，222：复现请求间断后曝光历史仍按请求号读取；SM8150标准SOF候选临时实测105连续事件，已恢复原CAMSS82c，手动曝光尚未接入。仍boot219/Image183/e49/完整r7-r2，全外设goal active。[222记录](reference/kernel222/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 运输reference/kernel222/host.py，新USB邻居/原严格公钥；guard /var/lib/samurai/k222-baseline/boot-id-private.txt，与219-runtime/220/221-baseline同boot。218及219-baseline/before-reboot旧身份不可授权新切换。无活任务/未决切换；219marker closed、220包事务verified。BT只扫描、不新增振动。
- boot219 156f0370…/DTB a214fd6b…，前摄200/400/748.8MHz；Image183 bfa72dd9…/logdump183 e73754c7…、NV保持。IMX471 e49dab26…、CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…；772ko/786文件。TFTP207/MCFG、MM191/GNSS/SSC、Wi-Fi与BT185指纹见219，未改变。
- 前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP；默认1928×1088/2304×1728，4608×3456需模块+用户态两个实验开关，当前N。COMPOSE已删，真实CROP/FOV/CFA开放。
- libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r7，config/stack0.1.0-r2；944包/937无关记录保持，49payload本轮复核。CPU/system heap，YAML与r1逐字相同；通用堆root/video0660+uaccess、DSP池root0600。WP为手动进程，操作需现取argv/env/UID10000，保留桌面/PipeWire身份；本轮已两次恢复。
- 219真实4MP/实验16MP RAW与CPU RGB各六帧，暗RAW噪声约0.47/0.60、变化35%/51%；DMA同步、不存图。r6起system heap解决4MP四缓冲分配；完整TPG仍普通Bayer，不能证明Quad真实颜色。暗RGB近黑不能单判bug。
- 三模式时序/PLL和RAW帧率证据见219；2MP约57.82fps，未验CPU RGB30fps。
- 220修复IPA缓存旧时序，2MP1290行由10117µs改17057µs（计算17057.85µs）；0013逐configure传sensorInfo，288帧差<1µs整数化，未验物理曝光/延迟。完整包/IPA/标准API验收见220。
- 222标准元数据探针四请求一组、间隔500ms、共16请求；原r7请求4对应buffer33，8对应66，12对应99，但DelayedControls读取索引2/6/10。连续220样本0–35恰好无间断，不足以发现此问题。三轮共48个RGB请求，不映射客户端像素、不存图，均恢复控制/格式/媒体图。
- 当前原CAMSS没有frameStart源。候选仅SM8150开放FRAME_SYNC、用现有RDI SOF IRQ独立计数，源三文件/补丁见222；模块9c3b9db6…/776664B，intree/W1/符号/vermagic/checkpatch通过。两次临时加载后恢复82c文件/loaded-note、图/格式/WP。第二轮105事件0–104连续，中位17.296ms，libcamera识别frameStart，16请求完成；这不证明buffer号与SOF完全配对。未进入产品部署锁。
- 222最终k222-final-health：同boot/e49/49payload/原82c保持；相机/CCI/CAMSS休眠、两前摄电源关闭/用户0、参数N/图案0；GPS0/Signalsfalse/rate30、watch空闲无新增worker、chrony Normal；三DSP running、BT关无连接，taint/五fault0，NV源核对。无本轮刷写/重启/GNSS引擎启动。

## 源码、产物与回退依据

- kernel /home/cy122/pmos-samurai-kernel136/kernel canonical仍216源cc756279…/对象1388a070…/旧DTB22c1…；原25 tracked/11 untracked，不能当当前部署树。219实际imx471.c61931497…/e49模块/a214DTB，四补丁链已独立重放核对。
- IMX模块回退设备k219-timing-baseline/imx471-original.ko d82c941d…及k219-timing-driver-test-r2/before-tree；更早216在k219-baseline。现取身份/空闲，正常解绑/卸载/恢复/depmod/加载/策略恢复，不强卸。boot回退私人211/boot-partition-k211-sensor-domain.img c3bf043f…，分别核对。
- 222候选私人kernel222/sof-candidate-source与qcom-camss-sof222.ko，补丁reference/kernel222/camss-sm8150-sof-candidate.patch。缺vb2构建失败与ENOENT观测失败保留，180份源/对象/元数据及两次驱动/WP切换已恢复，所有任务终态。手机原82c备份k222-sof-trial及trial-r2，当前仍加载原82c。
- SDK /home/cy122/x2pro-linux/libcamera214-root；原/work/libcamera2254文件/链接恢复，r7源/对象/work/libcamera220-built。13包、配方、QA前缀与签名输入路径见220，无活构建或待恢复快照。
- canonical配方/配置/源码锁/部署锁r7/r2；0013 d6aa409f…与前12补丁/tuning/YAML保留；原IPA214与APK203私钥复用，不生成/上传，未证明二次构建逐字相同。实际r6/r1回退七包在设备k219-r6-package-candidates/forward及私人219/camera-forward-repo，验签/payload/降级模拟通过，未完整回退往返；更早r5/r4分开。
- 222原生71成员私人归档逐一核对；221另37、220另146、219另512保持。健康记录错沿221“未拍摄”标记已更正并保留原报告；UIM槽状态明确来自221。USB严格邻居/原密钥/64KiB是绕过，截断根因未修。capsule私人kernel222/current-work-private.json；旧完整交接archive/NEXT-SESSION-through221-2026-10-16.md。

## 续作与已知风险

先将捕获缓冲与真实SOF配对（当前buffer.sequence按BUF_DONE计数），在捕获回调保存相应DelayedControls快照以免历史环回。再接标准曝光/增益、独立Auto/Manual、AeEnable优先级、Auto期间忽略手动值、模式冻结和Camera::start控制；按实际生效模式返回元数据，不能只回显请求或仅改get(frame)索引。详见222记录及私人capsule设计笔记。

用户关灯、室内窗边；不闪光/外部照明、不存场景。实际曝光/延迟、真实CFA/几何/颜色/方向/标定/GUI/RGB性能、后置GW1/3M5/IMX319/人像继续；未知PLDO输入不猜。GPU ISP211 CMA/黑帧/unmap349 WARN/taint512开放，149 CCU修复保持。

GNSS无真实fix/正CNR、无遮挡户外/Android基线，星座启用不证明RF；209小UTC误差未改善约6秒报告，勿重复。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207 MCFG173文件/8807671B RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp0B；真实SIM/注册/数据/通话/SMS/UIM开放，外发需明确目标。BT phase5、传感器FastRPC/SSR/首启失败、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护、指纹/NFC及rootfs132整合按[硬件清单](linux-port/docs/HARDWARE-STATUS.md)继续；全goal保持active。
'''
assert len(next_text.encode())<=6500,len(next_text.encode())
old=(repo/'NEXT-SESSION.md').read_text();archive=repo/'archive/NEXT-SESSION-through221-2026-10-16.md';assert not archive.exists();archive.write_text(old);(repo/'NEXT-SESSION.md').write_text(next_text)
status=repo/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段222。复现请求间断后采集号/请求号分离；临时SOF候选取得105连续事件并恢复原驱动，手动曝光未完成。当前仍boot219/e49/CAMSS82c/r7-r2，全外设goal active。[222报告](../../reference/kernel222/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
lines=text.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | boot219/e49、CAMSS82c与完整r7/r2保持；219真实4MP/实验16MP RAW和CPU RGB、时序及system heap修复、220逐配置曝光换算288帧证据保留。222请求间断复现req4/buf33等错配；仅SM8150的SOF候选临时实测105连续事件、16请求，已恢复原模块/图/格式/WP，taint/fault0，49payload保持 | 先完成SOF与捕获缓冲配对及控制快照，再接标准手动曝光/增益和真实生效模式元数据；候选未部署。物理曝光/延迟/颜色/几何/CFA/方向/GUI/实时性能、后置四路、GPU ISP告警、未知PLDO输入、冷启/长稳及完整kernel/rootfs整合开放；完整16MP实验关、TPG普通Bayer不验真实Quad颜色 |'
status.write_text('\n'.join(lines)+'\n')
path=repo/'linux-port/camera/README.md';text=path.read_text();text+='\n222复现请求间断导致请求号与真实采集号分离；新增SM8150标准SOF候选，临时取得105连续事件并恢复原CAMSS。标准手动曝光仍需捕获帧/控制快照配对，候选未进入部署锁。[222证据](../../reference/kernel222/README.md)。\n';path.write_text(text)
state=json.loads((private/'current-work-private.json').read_text());state.update(state='222 request-gap defect reproduced; SM8150 SOF candidate verified with105 consecutive events; original82c/e49/r7-r2 restored;71 native archive members verified',transition_pending=False,active_session=None,active_kernel_build_session=None,next='Complete SOF-to-buffer association and capture-time delayed-control snapshots before exposing standard manual exposure/gain. Keep all original peripheral goals active; candidate SOF module is NOT deployed.',candidate_module=str(private/'qcom-camss-sof222.ko'),candidate_module_sha256='9c3b9db6b2933ebf5f1c01deea9fca7bb823fb2a745cd7f3a1d88e3ccc54e83e',guard='/var/lib/samurai/k222-baseline/boot-id-private.txt')
state['manual_control_design_notes']='First retain a real SOF tag per queued CAMSS buffer, clearing its validity when requeued; at SOF tag oldest active buffer not already started, account for SOF and previous DONE coalescing. Keep EOF timestamps unless timestamp-source semantics are explicitly changed. Missing SOF tags must not be silently reported as accurate. Current candidate changes only events/counter, not buffer.sequence. Then snapshot DelayedControls at captured-buffer callback by actual SOF sequence (not Request::sequence), store in SimpleFrameInfo until stats; avoid16-entry ring eviction. Opaque delayed-control cookie can associate applied ExposureTimeMode/AnalogueGainMode/AeState with the actual sensor command slot; preserve it on auto-queued no-ops. Standard manual modes independent, AeEnable lower precedence, ignore and do not retain manual values while corresponding mode Auto, freeze last computed target on Auto-to-Manual without explicit value, retain manual values only in Manual, seed Auto from last manual output. Camera::start controls must be honoured before stream-on. Publish mode-specific exposure/gain ranges after configure through coherent IPA/core/proxy ABI; retain r7 mode-info fix. Validate controls applied through DelayedControls/physical registers and metadata, not merely names or echoing requests. Preserve full13 feature packages, matching retained IPA key, all tuning/configuration, original2142254-file tree and actualr7 rollback before any product upgrade. Actual exposure delay/photometric calibration remains separate.'
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=222,next_session_bytes=len(next_text.encode()),full_goal_active=True,current_deployment_restored=True)))
