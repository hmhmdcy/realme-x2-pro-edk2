from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel216');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((here/'gain-source-validation.json').read_text());build=json.loads((here/'imx471-module-build-validation.json').read_text())
assert json.loads((here/'final-evidence-validation.json').read_text())['archive_and_all_member_hashes_verified']
old=json.loads((private.parent/'kernel210/source-before/source-file-hashes-private.json').read_text());intentional=json.loads((here.parent/'kernel211/source-final-validation.json').read_text())['three_intentional_source_changes'];intentional['drivers/media/i2c/imx471.c']=source['source_after_sha256']
assert all(sha(kernel/name)==intentional.get(name,digest) for name,digest in old.items())
before=json.loads((private.parent/'kernel211/source-before/hashes-private.json').read_text());assert all(sha(kernel/name)==before[name] for name in ['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'])
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
for path in here.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
patches=repo/'linux-port/camera/kernel'
lock=dict(stage=216,upstream_repository='https://github.com/cschalle/mipi-fixes-x1-aura',upstream_repository_commit=source['upstream_repository_commit'],patches=[dict(file='0001-imx471-test-pattern-width.patch',commit='e8c7bce089b518b5d9076d585ebc469e9c390ff8',sha256=sha(patches/'0001-imx471-test-pattern-width.patch')),dict(file='0002-imx471-analogue-gain-limit.patch',commit=source['upstream_patch_commit'],sha256=sha(patches/'0002-imx471-analogue-gain-limit.patch'))],current_source_sha256=source['source_after_sha256'],current_module_sha256=build['module_sha256'],module_bytes=build['module_bytes'],vermagic=build['vermagic'],test_pattern_register_width=16,analogue_gain_code_max=960,own_factory_gain_max=16.0,previous215_module_sha256='6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c',kernel_image_and_boot_unchanged=True,runtime_evidence='../../../reference/kernel216/gain-acceptance-validation.json',actual_sensitivity_calibration_and_standard_manual_gain_api_not_accepted=True)
(patches/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
path=repo/'linux-port/camera/deployment-lock.json';deployment=json.loads(path.read_text());deployment.update(stage=216,sensor_kernel_module_sha256=build['module_sha256'],sensor_kernel_module_deployment_stage=216,runtime_evidence='../../reference/kernel216/default-clients-validation.json',gain_evidence='../../reference/kernel216/gain-acceptance-validation.json');path.write_text(json.dumps(deployment,indent=2)+'\n')
report=dict(stage=216,only_analogue_gain_limit_added_to215_kernel_source=True,other_saved_kernel_sources_preserved=True,config_symbols_order_image_and_board_preserved=True,kernel_diff_check_passed=True,no_kernel_source_staged=True,canonical_upstream_patch_and_source_lock_recorded=True,reference_python_syntax_passed=True,only_sensor_ko_changed_and_771_others_preserved=True,no_flash_or_reboot=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(here/'README.md').write_text('''# 216：补齐 IMX471 原厂模拟增益范围并验证 RAW 响应

本轮将前摄模拟增益寄存器上限从800改为960，名义范围从1～4.57倍扩展至1～16倍。只改这一个常量，215测试图位宽、模式/曝光、供电/时钟/GPIO和r5相机软件包保持。已部署并观察实际RAW噪声响应；未把它写成实际光照灵敏度标定、完整暗光画质或标准手动增益API验收。

本机原厂com.qti.sensor.imx471.so重新反汇编，指令102c加载16倍上限、1058加载960、1078比较960，与1024/(1024-code)换算一致；原库未修改，未读写校准或NV。该事实与同款传感器[上游作者的增益补丁](https://github.com/cschalle/mipi-fixes-x1-aura/blob/533d995b7acbd6965e5b0b85c97f8bafab9fed4e/kernel/patches/0003-media-i2c-imx471-Raise-the-analogue-gain-limit-to-th.patch)相符；固定仓库提交533d995b、补丁原提交5cf84f3e，不套用其笔记本镜头标定。[原厂依据](factory-gain-contract-validation.json)、[源变更](gain-source-validation.json)、[canonical补丁](../../linux-port/camera/kernel/0002-imx471-analogue-gain-limit.patch)。

新鲜基线确认同215启动、旧模块6b2bb0b4、原r5数据库和相机休眠、taint0，保存旧模块；实际V4L2控件上限仍800。[基线](baseline-validation.json)。W=1模块编译无诊断、导入符号和vermagic匹配，Image183/boot211及DTB/其它源码/构建元数据保持，新模块1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b、25448B。[构建](imx471-module-build-validation.json)、[源码核对](source-final-validation.json)。

按215验证的流程暂时停止空闲WirePlumber，正常解绑前摄释放引用，卸载/更换唯一imx471.ko、depmod/加载和静态绑定，再恢复策略进程。771个其它模块及PipeWire/桌面身份保持，未强卸、未刷机/重启，r2 transition-state为verified。[部署](module-reload-validation.json)。原215模块及全部原元数据已私下保留。

有限RAW测试先启动流，再用普通V4L2控件写0/800/960，写入及缓存读回成功后排队6帧；使用UID10000、系统r5库、DMA READ START/END并排除行填充，图案关闭，无外部光源。独立测试依次为0、800、960、0；稳定部分最后4帧的RAW标准差中位数分别0.47435、0.94529、2.34678、0.44158。噪声随增益上升，回到低增益后下降，表明960确实影响了传感器输出，不只是扩大控件元数据。[0-a](system-gain-raw-0-a-validation.json)、[800](system-gain-raw-800-a-validation.json)、[960](system-gain-raw-960-a-validation.json)、[0-b](system-gain-raw-0-b-validation.json)、[验收](gain-acceptance-validation.json)。

全部24帧与首帧保留。800/960的首帧标准差约0.48，随后约0.95/2.35，说明首帧可能保留切换前的响应；统计比较排除前两帧，但未把它推广成所有模式/曝光/增益的确定控制延迟。暗噪声不是受控光照响应，不能由这些数字宣称实测灵敏度恰为16倍或提高1.8档；均值仍约64符合暗场黑电平，RGB全零也不能单独判bug。

首次默认客户端预检中，我错误假设配置前cam --list-controls会列出AnalogueGain；它实际只列Contrast/Gamma，预检在采集前StopIteration退出，未改驱动状态。保留该记录，第二次仅核对实际内核上限960，并如实标注标准手动增益API未验收。随后默认cam和GStreamer各取6帧通过、无报错/超时/新增内核故障。[客户端](default-clients-validation.json)。仍需检查配置后的控制映射、IPA曝光/增益和用户态手动控制能力。

最终sensor/CAMSS/CCI suspended，VDIG/VANA disabled/users0、MCLK及自身MMCX票0、图案关闭；三个DSP running、taint/五fault0，NV与非相机程序核对保持，GPS0/Signalsfalse/rate30、蓝牙关闭无连接。[最终健康](final-health-validation.json)。原模块/元数据、首帧和初次预检失败等86成员私人归档完整核对通过；无私钥、无场景图。[归档](final-evidence-validation.json)。

回退为k216-baseline/imx471-original.ko及k216-driver-test-r2/before-tree，原215模块SHA256为6b2bb0b4…，已导出。必须重新核对当前启动和空闲状态，再停止策略进程、正常解绑/卸载、更换旧ko、depmod/加载/绑定和恢复策略；不能重放已完成marker。它保留215已验证的TPG修复。r5软件包未变化，与214的软件包回退分别处理。

下一步继续完整16MP模式、曝光/控制延迟和标准控制API，并逐路接入后置四摄。RAW10 AWB线索需要先核对实际输入格式：0.7.2的packed10P路径已经读8位值，同款补丁只给unpacked10/12的和做缩放，不能未经检查便称其修复本机白平衡。笔记本shading/色彩矩阵不套用。GNSS真实fix/正CNR、蜂窝真实业务、BT phase5、传感器FastRPC/SSR、GPU ISP、充电/PM及完整rootfs继续开放。[全硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
''')
path=repo/'NEXT-SESSION.md';text=path.read_text();(repo/'archive/NEXT-SESSION-through215-2026-10-16.md').write_text(text)
old=text.split('\n\n')[1];text=text.replace(old,'2026-10-16，阶段216：前摄模拟增益码上限按本机原厂从800补至960（名义16倍），RAW噪声响应/回低增益与默认客户端通过；215测试图修复保持。关灯、同一启动、未刷机/重启。完整外设goal active。[216报告](reference/kernel216/README.md)、[214相机包](reference/kernel214/README.md)、[边界](WORKING-BOUNDARIES.md)。',1)
text=text.replace('当前运输reference/kernel215/host.py，guard为/var/lib/samurai/k215-baseline/boot-id-private.txt','当前运输reference/kernel216/host.py，guard为/var/lib/samurai/k216-baseline/boot-id-private.txt')
text=text.replace('215驱动r2 marker verified，首次卸载在使用失败且确认无驱动变化，marker已更正failed-no-driver-change；旧动作不重放。','216驱动r2 marker verified；215首次卸载失败无驱动变化的记录保留，旧动作不重放。')
text=text.replace('IMX471当前6b2bb0b4…（旧a28dd67a…）','IMX471当前1388a070…（215旧6b2bb0b4…）')
text=text.replace('215只在211基础上改IMX471测试图寄存器8→16位','215/216只在211基础上修IMX471图案位宽并将增益上限800→960')
text=text.replace('[源码核对](reference/kernel215/source-final-validation.json)','[源码核对](reference/kernel216/source-final-validation.json)')
text=text.replace('- 安装后暗场RAW','- 214安装后暗场RAW')
text=text.replace('- sensor模块回退为k215-baseline/imx471-original.ko及r2/before-tree（旧a28dd67a…）','- sensor模块回退为k216-baseline/imx471-original.ko及r2/before-tree（215旧6b2bb0b4…）')
text=text.replace('当前源码8b0bf567…、module6b2bb0b4…','当前源码cc756279…、module1388a070…')
text=text.replace('215原模块/元数据等99成员已核对','215原模块/元数据99成员及216的86成员已核对')
text=text.replace('前摄当前仅1928×1088模式；下一步核查增益上限/曝光、控制延迟、RAW10白平衡统计位深及tuning/方向和完整16MP','216已核对原厂上限16倍/960；0/800/960/0的RAW噪声依次约0.47/0.95/2.35/0.44，非光照灵敏度标定，首帧延迟仍待定。配置前cam只列Contrast/Gamma，标准手动增益API未验收。前摄仍仅1928×1088，继续完整16MP、曝光/延迟/控制API及tuning/方向；AWB先核输入格式，packed10P已用8位，不能盲套unpacked补丁')
path.write_text(text);assert path.stat().st_size<=6500
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text().replace('最后核对2026-10-16，阶段215。','最后核对2026-10-16，阶段216。').replace('完整相机r5已部署；215修复sensor内部测试图位宽，6帧RAW/RGB及关闭后暗噪声通过，默认cam/GStreamer各6帧保持','完整相机r5和215测试图修复保持；216按原厂补齐前摄模拟增益960/名义16倍，RAW响应与回低增益、默认客户端通过，未作光照灵敏度标定').replace('[215报告](../../reference/kernel215/README.md)','[216报告](../../reference/kernel216/README.md)')
text=text.replace('前摄仍仅1928×1088模式，增益/曝光、RAW10白平衡位深、延迟/方向/tuning','216按原厂补齐模拟增益960/名义16倍、RAW响应通过；前摄仍仅1928×1088，实际灵敏度/曝光、标准手动控制API、AWB输入格式/延迟/方向/tuning')
path.write_text(text)
path=repo/'DOCS-INDEX.md';text=path.read_text().replace('[215传感器图案位宽](reference/kernel215/README.md)','[216原厂增益范围](reference/kernel216/README.md)、[215传感器图案位宽](reference/kernel215/README.md)');path.write_text(text)
plan=dict(stage=216,previous_goal_turn='progress:215 sensor test pattern width fix deployed and verified',state='Gain cap800->960 confirmed against own factorySO and pinned same-sensor patch;newmodule1388a070 hotreloaded normally,771others preserved;RAW0/800/960/0 noise response verified,defaultcam/Gst6each passed;86member archive verified,taint/fault0,no reboot/flash. Fullgoalactive.',device_guard='/var/lib/samurai/k216-baseline/boot-id-private.txt',device_transport='reference/kernel216/host.py',next='Finish docs mirror. Continue full16MP mode from own factoryBIN and exposure/delays/standardmanualcontrols,thenrear4. cam preconfigure list onlyContrast/Gamma;do notclaim standardmanualgain accepted. AWB packed10P already8bit;verify activeformat/controlledstats beforepatch. Keep full GNSS/cellular/BT/sensors/power/rootfs scope.216r2markerverified,do notrerun transitions.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report));print('NEXT-SESSION bytes='+str((repo/'NEXT-SESSION.md').stat().st_size))
