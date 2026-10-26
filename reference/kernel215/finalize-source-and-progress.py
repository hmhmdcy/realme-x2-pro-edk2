from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel215');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source=json.loads((here/'test-pattern-source-validation.json').read_text());build=json.loads((here/'imx471-module-build-validation.json').read_text())
assert json.loads((here/'final-evidence-validation.json').read_text())['archive_and_all_member_hashes_verified']
old=json.loads((private.parent/'kernel210/source-before/source-file-hashes-private.json').read_text());intentional=json.loads((here.parent/'kernel211/source-final-validation.json').read_text())['three_intentional_source_changes'];intentional['drivers/media/i2c/imx471.c']=source['source_after_sha256']
assert all(sha(kernel/name)==intentional.get(name,digest) for name,digest in old.items())
before=json.loads((private.parent/'kernel211/source-before/hashes-private.json').read_text())
assert all(sha(kernel/name)==before[name] for name in ['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'])
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
for p in here.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
lock=dict(stage=215,upstream_repository=source['related_primary_repository'],upstream_repository_commit=source['related_primary_commit'],upstream_patch_commit=source['upstream_patch_commit'],patch_sha256=sha(repo/'linux-port/camera/kernel/0001-imx471-test-pattern-width.patch'),source_before_sha256=source['source_before_sha256'],source_after_sha256=source['source_after_sha256'],module_sha256=build['module_sha256'],module_bytes=build['module_bytes'],vermagic=build['vermagic'],scope='IMX471 test pattern register width only; gain limit unchanged800',own_factory_low_byte_address='0x0601',own_factory_low_byte_value=1,runtime_evidence='../../../reference/kernel215/test-pattern-acceptance-validation.json',old_module_sha256='a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a',old_module_backed_up_privately=True)
(repo/'linux-port/camera/kernel/source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
path=repo/'linux-port/camera/deployment-lock.json';deployment=json.loads(path.read_text());deployment.update(stage=215,camera_framework_deployment_stage=214,kernel_changed=True,kernel_image_changed=False,sensor_kernel_module_sha256=build['module_sha256'],sensor_kernel_module_deployment_stage=215,sensor_kernel_patch_source_lock='kernel/source-lock.json',runtime_evidence='../../reference/kernel215/default-clients-validation.json',sensor_test_pattern_evidence='../../reference/kernel215/test-pattern-acceptance-validation.json');path.write_text(json.dumps(deployment,indent=2)+'\n')
report=dict(stage=215,only_test_pattern_width_added_to_saved_kernel_changes=True,other_saved_kernel_sources_preserved=True,config_symbols_order_image_and_board_preserved=True,kernel_diff_check_passed=True,no_kernel_source_staged=True,canonical_upstream_patch_and_source_lock_recorded=True,reference_python_syntax_passed=True,only_one_sensor_module_installed=True,other_771_modules_preserved=True,no_flash_or_reboot=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(here/'README.md').write_text('''# 215：IMX471 内部测试图寄存器位宽修复并实测

本轮从214的r5完整相机栈继续，修复传感器内部测试图控制读回成功、实际仍输出现场画面的缺陷。只将IMX471_REG_TEST_PATTERN的CCI_REG8(0x0600)改为CCI_REG16(0x0600)，增益上限、模式表、供电/时钟/GPIO和相机软件包均保持。[源差异](test-pattern-source-validation.json)、[canonical补丁](../../linux-port/camera/kernel/0001-imx471-test-pattern-width.patch)。完整画质/16MP、后置四摄及全部外设目标仍开放。

相关原始来源是同款IMX471在ThinkPad X1 Carbon Gen14上的[作者报告](https://cschalle.github.io/mipi-fixes-x1-aura/)和[补丁仓库](https://github.com/cschalle/mipi-fixes-x1-aura/tree/533d995b7acbd6965e5b0b85c97f8bafab9fed4e)。本轮固定仓库提交533d995b，宽度补丁原提交e8c7bce0；8位写入把模式写到高字节，16位写入才能正确更新低字节。自己的原厂sunny_imx471 BIN也记录固色模式向0601写1，与该修复相符。报告中的笔记本镜头校正、色彩标定和增益修改不在本轮套用范围；不能把它们视为本机标定。

新鲜核对仍为214同一启动、内核Image183/boot211、r5数据库原样、相机休眠、taint0，原a28dd67a模块已备份。[基线](baseline-validation.json)。W=1编译无警告，所有导入符号匹配原16798符号表，vermagic不变，新模块25448B、SHA256为6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c；Image/DTB/板级源码/CCI和构建元数据保持。[构建](imx471-module-build-validation.json)、[最终源码核对](source-final-validation.json)。

首次停止空闲WirePlumber后没有用户态camera FD，但modprobe -r仍提示模块在使用，退出前没有替换驱动文件，WirePlumber已恢复，桌面/PipeWire身份和内核健康保持。复查refcnt3、holders空、原模块/绑定原样，把初次marker的泛用failed-restored更正为failed-no-driver-change，原失败保留。[首次尝试](module-reload-validation.json)、[引用检查](reload-ref-validation.json)。

第二次先正常解绑7-0010，释放绑定持有的引用，再卸载旧模块、替换唯一的imx471.ko、depmod并加载新模块，静态绑定成功。只此1个ko变化，771个其它模块保持；WirePlumber恢复，PipeWire/桌面身份不变，未使用强制卸载、未刷机或重启，taint/五fault0。[更新](module-reload-r2-validation.json)。

实际测试使用UID10000、系统r5库和默认CPU配置，没有候选loader/IPA覆盖；RAW读取有DMA READ START/END并排除每行填充。内部彩条模式2的6帧RAW每像素仅0/1023两级，均值819.249、标准差408.562，空间分布非均匀且后5帧逐像素相同；RGB从首帧起非黑。整个测试保留物理传感器CSI输入，未用CSID替代，也未把控制缓存读回当硬件证据。[RAW](system-sensor-raw-validation.json)、[RGB](system-sensor-rgb-validation.json)、[验收](test-pattern-acceptance-validation.json)。

关闭内部图案后，6帧RAW均值63.9824～64.016、标准差0.4405～0.4735，相邻帧32.9%～34.6%像素变化，恢复到真实暗场。所有图案、sensor控制及media graph已恢复，相机设备休眠，未使用闪光灯或外部光源；RGB暗场全零仍不能单独判bug。[图案关闭后的RAW](system-dark-raw-validation.json)。

热更新后默认cam和GStreamer标准API各完成6帧物理前摄取流，无报错、超时、内核fault；普通用户客户端仍使用默认系统路径，未保存场景图。[客户端](default-clients-validation.json)。最终3DSP running、相机休眠/VDIG和VANA释放、MCLK及自身MMCX票0、图案关闭，taint/五fault0，NV与非相机程序保持；GPS0/Signalsfalse/rate30、蓝牙关闭无连接。[健康](final-health-validation.json)。99成员私人原生归档和全部成员核对通过，包括原模块及原元数据，未公开私钥和场景。[归档](final-evidence-validation.json)。

本轮相机包仍为99990.7.2-r5，完整944包数据库不变。模块回退依据为手机k215-baseline/imx471-original.ko、k215-driver-test-r2/before-tree及私人归档，SHA256 a28dd67a…；当前r2 transition-state为verified，初次为failed-no-driver-change。需要回退时先重新核对当前启动和空闲状态，停止相机策略进程，正常解绑后卸载，恢复旧ko、depmod/加载/绑定并重启策略进程；不得重放本轮提交marker。boot211/Image183没有变化，模块回退与214的r5/r4软件包回退分别处理。

下一步核查增益上限/曝光与控制延迟、RAW10白平衡统计位深是否仍有缺陷，先用可控输入证明本机影响；笔记本镜头shading参数不可直接移植。完整16MP和后置四路、GPU ISP、GNSS真实fix/正CNR、蜂窝真实业务、BT phase5、传感器FastRPC/SSR、充电/PM及完整rootfs继续按[全硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)推进。
''')
path=repo/'NEXT-SESSION.md';text=path.read_text();(repo/'archive/NEXT-SESSION-through214-2026-10-16.md').write_text(text)
old=text.split('\n\n')[1];text=text.replace(old,'2026-10-16，阶段215：IMX471内部测试图位宽修复已部署，6帧RAW/RGB图案和关闭后暗场变化通过；默认cam/GStreamer各6帧保持。关灯、同一启动、未刷机/重启。完整外设goal active。[215报告](reference/kernel215/README.md)、[214相机包](reference/kernel214/README.md)、[边界](WORKING-BOUNDARIES.md)。',1)
text=text.replace('当前运输reference/kernel214/host.py，guard为/var/lib/samurai/k214-baseline/boot-id-private.txt','当前运输reference/kernel215/host.py，guard为/var/lib/samurai/k215-baseline/boot-id-private.txt')
text=text.replace('214安装/策略重载marker均verified，旧211/212切换已闭环，不重放。','215驱动r2 marker verified，首次卸载在使用失败且确认无驱动变化，marker已更正failed-no-driver-change；旧动作不重放。')
text=text.replace('IMX471 a28dd67a…','IMX471当前6b2bb0b4…（旧a28dd67a…）')
text=text.replace('214无kernel变更，211三个文件及其余33份保存改动保持','215只在211基础上改IMX471测试图寄存器8→16位，其余保存源码保持')
text=text.replace('[源码核对](reference/kernel214/source-final-validation.json)','[源码核对](reference/kernel215/source-final-validation.json)')
text=text.replace('214原生归档167成员已核对。','214原生归档167成员、215原模块/元数据等99成员已核对。')
text=text.replace('传感器TPG的CCI_REG8(0600)与原厂0601疑点未修，数字正对照用已确认有效的CSID源并恢复原link/控制。','215已将0600改CCI_REG16，与原厂0601低字节记录及同款传感器补丁一致；内部图案6帧RAW仅0/1023两级，RGB首帧非黑，关闭后恢复暗噪声。可用sensor或已确认的CSID作正对照，均须恢复控制/link。')
text=text.replace('先修TPG/控制延迟、tuning/曝光/方向及完整16MP','下一步核查增益上限/曝光、控制延迟、RAW10白平衡统计位深及tuning/方向和完整16MP')
text=text.replace('- 私人213归档','- sensor模块回退为k215-baseline/imx471-original.ko及r2/before-tree（旧a28dd67a…），已导出；正常解绑传感器才能释放引用再卸载，不强卸。当前源码8b0bf567…、module6b2bb0b4…，boot211/Image183保持。\n- 私人213归档')
path.write_text(text);assert path.stat().st_size<=6500
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();text=text.replace('最后核对2026-10-16，阶段214。','最后核对2026-10-16，阶段215。').replace('完整相机r5已部署，默认cam/GStreamer各6帧及暗场RAW/数字白首帧对照通过','完整相机r5已部署；215修复sensor内部测试图位宽，6帧RAW/RGB及关闭后暗噪声通过，默认cam/GStreamer各6帧保持').replace('[214报告](../../reference/kernel214/README.md)','[215报告](../../reference/kernel215/README.md)')
text=text.replace('前摄仅1928×1088模式，TPG位宽、延迟/方向/tuning','215 sensor内部TPG位宽已修，RAW/RGB/关闭后暗场及默认客户端通过；前摄仍仅1928×1088模式，增益/曝光、RAW10白平衡位深、延迟/方向/tuning')
path.write_text(text)
path=repo/'DOCS-INDEX.md';text=path.read_text().replace('[214完整包部署与默认客户端](reference/kernel214/README.md)','[215传感器图案位宽](reference/kernel215/README.md)、[214完整包部署与默认客户端](reference/kernel214/README.md)');path.write_text(text)
plan=dict(stage=215,previous_goal_turn='progress:214 full camera r5 package deployment and default client acceptance',state='IMX471 TPG width8-to16 fixed from pinned primary patch and own factory0601;module6b2bb0b4 installed after normal unbind,onlyoneko changed,771others preserved;6raw/rgb pattern and6dark frames,defaultcam/gst6each passed,taint/fault0;nativearchive99verified;no reboot/flash. Fullgoalactive.',device_guard='/var/lib/samurai/k215-baseline/boot-id-private.txt',device_transport='reference/kernel215/host.py',next='Finish docs mirror; continue sensor gain/exposure/control delay and RAW10 AWB bit-depth evidence. Same-sensor primaryrepo cschalle/mipi-fixes-x1-aura pinned533d995b has gain and AWB leads, but laptop calibration cannot be applied to handset. Keep full16MP/rear4/GPUISP/GNSS/cellular/BT/sensor/power/rootfs scope.215r2markerverified;firstattempt failed-no-driver-change;neverblindlyrerun transitions.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report));print('NEXT-SESSION bytes='+str((repo/'NEXT-SESSION.md').stat().st_size))
