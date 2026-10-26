from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel217');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source=json.loads((here/'factory-mode-candidate-source-validation.json').read_text());build=json.loads((here/'factory-mode-candidate-build-validation.json').read_text())
assert json.loads((here/'candidate-style-validation.json').read_text())['checkpatch_passed']
assert json.loads((here/'final-evidence-validation.json').read_text())['archive_and_all_member_hashes_verified']
assert sha(private/'candidate-source/imx471.c')==source['source_sha256'] and sha(private/'candidate-source/sm8150-samurai.dts')==source['board_sha256']
assert sha(private/'candidate-build-r3/imx471-factory-modes.ko')==build['module_sha256'] and sha(private/'candidate-build-r3/factory-modes.dtb')==build['dtb_sha256']
old=json.loads((private.parent/'kernel210/source-before/source-file-hashes-private.json').read_text());intentional=json.loads((here.parent/'kernel211/source-final-validation.json').read_text())['three_intentional_source_changes'];intentional['drivers/media/i2c/imx471.c']='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
assert all(sha(kernel/name)==intentional.get(name,digest) for name,digest in old.items())
before=json.loads((private.parent/'kernel211/source-before/hashes-private.json').read_text());assert all(sha(kernel/name)==before[name] for name in ['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'])
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
for path in here.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
report=dict(stage=217,canonical_kernel216_sources_and_saved_changes_preserved=True,config_symbols_order_image_and_canonical_dtb_preserved=True,candidate_driver_source_and_artifact_hashes_match=True,candidate_only_not_installed=True,kernel_diff_check_passed=True,no_kernel_source_staged=True,reference_python_syntax_passed=True,host_original_sensor_and_cci_build_artifacts_restored=True,no_device_install_flash_or_reboot=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(here/'README.md').write_text('''# 217：原厂三模式验证、完整分辨率候选与时序差异

本轮为完整16MP适配解码了本机原厂IMX471模式，并构建可审查的驱动/DTB候选。**手机仍运行216模块1388a070…，候选未安装、未刷写/重启；16MP取流和完整图像处理尚未验收。** 全外设目标继续开放。

原厂BIN的Parameter Parser1.3.2符号表有一个ResolutionInformation和3个256字节ResolutionData记录。保留原厂BIN不变，仅在私人分析副本中投影原128字节传感器上下文和resolutionInfo引用，并在分析专用XSD移除BIN中不存在的两个尾部字段。厂商工具最终导出真实3模式XML，独立有界解码器逐项核对所有标量、流尺寸和174条8位寄存器写入；尺寸/裁剪、RAW10/4lane、FLL/LLP均与寄存器一致。[核对](factory-mode-crosscheck-validation.json)、[独立解码器](decode-and-crosscheck-modes.py)。未解码个人EEPROM/NV或公开原厂XML/私有库。

| 模式 | 原厂帧率字段 | LLP/FLL | 输出时钟字段 | 后处理 |
| --- | --- | --- | --- | --- |
| 4608×3456 | 30.01 | 5120/3762 | 599040000 | SWRemosaic |
| 2304×1728 | 30 | 2560/4250 | 320000000 | 2×2 binning |
| 2304×1728 | 60.02 | 2560/2124 | 320000000 | 2×2 binning |

三模式均使用本机19.2MHz外部时钟，模拟窗口0..4655/0..3495；完整输出数字裁剪偏移24/20，binning模式12/10。30/60两组固定寄存器只在FLL与曝光的4个字节不同，可通过相应VBLANK/曝光控件覆盖；这仍需实机验证，不把元数据帧率当实测帧率。OP PLL、4lane/RAW10与输出时钟元数据相互对应：binning候选link400MHz、完整候选748.8MHz。

16MP模式明确需要软件重马赛克。已有发行版quad-Bayer补丁只为IMX371配置2×2 cell collapse，主要用于GPU路径并产生半宽半高输出；不能将其直接用于IMX471并声称获得完整16MP。后续需按模式识别CFA、保持完整原生采样尺寸、实现正确CPU重马赛克，并处理RAW/输出缓冲区预算及COMPOSE几何。完整RGB、方向/颜色/画质、控制延迟和实际灵敏度仍未验收。

候选保留1928×1088旧寄存器表，添加2304×1728和4608×3456原厂表、按固件声明过滤频率、模式切换时更新link/pixel/VBLANK控件，并增加数字COMPOSE/BOUNDS信息。完整未处理RAW还要求unprocessed_fullres显式模块参数；默认不开放，避免当前普通Bayer路径将其作为成片使用。候选DTB只扩充该sensor endpoint的link-frequencies为200/400/748.8MHz；它尚未打入boot.img。[候选补丁](imx471-factory-modes-candidate.patch)、[源记录](factory-mode-candidate-source-validation.json)。

最终候选模块bc4649fb9dbfd42b5b69c4585cf6c62ca9ac8706348b43b1aa0155d85f96ee75、29688B，vermagic保持183；候选DTB a214fd6b2ccb93e5bbb5adc774e7c510398541e8fab286832682cc6bbd76ca42，相比已部署211 DTB仅上述频率属性不同。W=1无诊断、全部导入符号可用，checkpatch0错误/0警告。构建后宿主216源码、sensor/CCI对象及模块、配置/符号/order、Image和旧canonical DTB全部恢复。[构建](factory-mode-candidate-build-validation.json)、[风格](candidate-style-validation.json)、[最终源码](source-final-validation.json)。编译通过不证明物理模式、实际带宽或RGB处理正确。

当前旧预览另做12帧及120帧有限RAW时间戳观察，5次流中采样均为pixel_rate160000000、LLP2328/FLL1308、exposure1270/gain0。控件计算52.5447fps，缓冲区时间戳中位间隔约17.296ms、约57.8168fps，序号连续。cam源码确认其输出来自FrameMetadata时间戳；这个差异保留为待查，尚未区分传感器PLL、输出/阵列时钟定义、IRQ及取流行为，未据此盲改PLL或声称时序标定完成。全部控件恢复、场景未保存、相机休眠、taint/五fault0。[12帧](current-raw-timing-validation.json)、[120帧及活跃控件](active-raw-timing-validation.json)。

保留的失败：第一次厂商工具返回0却无XML；第二次只有传感器上下文XML，因误把重复引用当内联结构而没有模式，均未当成功。第三次错误的minOccurs断言提前终止；按XSD重复引用修正为144字节上下文投影后，第四次才导出3模式。独立解码最初猜错remosaic枚举值，改为按XSD枚举表解释。候选首次仅编sensor导致MODPOST缺CCI符号，恢复后加入CCI目标；风格检查的两个空格缩进及说明换行问题修复，再编译最终候选。所有失败日志和旧候选仍私下保留，手机未受这些离线失败影响。

最终手机仍为216原模块、r5/944包及49条相机payload保持；3DSP running，sensor/CAMSS/CCI休眠、前摄电源/时钟票释放，图案关闭、taint/五fault0，NV与非相机程序核对保持。GPS0/Signalsfalse/rate30、蓝牙关闭无连接。[健康](final-health-validation.json)。22成员私人原生归档全部核对，含原216模块备份和时序采样；未保存场景图或公开私钥。[归档](final-evidence-validation.json)。

续作先完成按模式的完整分辨率重马赛克、COMPOSE到有效物理区域的映射和输入/输出DMABUF预算，再进行隔离候选的物理RAW、已知非黑输入、实际帧率/曝光及默认客户端验证，之后才整合部署。不能把4MP折半/放大结果当16MP，也不能把当前候选DTB当已部署镜像。后置四路、GPU ISP、GNSS真实fix、蜂窝业务、BT phase5、传感器FastRPC/SSR、充电/PM及radio/Mesa/完整rootfs保持[完整目标](../../linux-port/docs/HARDWARE-STATUS.md)。
''')
path=repo/'NEXT-SESSION.md';old_text=path.read_text();archive=repo/'archive/NEXT-SESSION-through216-2026-10-16.md';assert not archive.exists();archive.write_text(old_text)
path.write_text('''# Realme X2 Pro 当前检查点

2026-10-16，阶段217：独立核对原厂3模式/174寄存器，驱动与DTB候选已构建，尚未安装。手机保持216增益/215图案修复与214完整r5栈；关灯、同一启动、未刷机/重启。全外设goal active。[217报告](reference/kernel217/README.md)、[216部署](reference/kernel216/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 运输reference/kernel217/host.py，guard /var/lib/samurai/k217-baseline/boot-id-private.txt。当前最终3DSP running，相机休眠/电源时钟释放，taint/五fault0；GPS0/Signalsfalse/rate30、BT关闭无连接。216驱动r2 marker verified，217没有安装或切换。所有旧marker不重放。
- boot211 c3bf043f…/DTB6f9f5b0f…，Image183 bfa72dd9…/logdump183 e73754c7…保持。IMX471当前1388a070…、CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…/BT185保持，772ko/786文件。TFTP207 b3bb82b9…/wifi854c9a8c…/MCFG helperd4c62be6…/MM191/helper421/init54/SSC9a1保持。
- 前摄静态CCI1 master1/0x10、MCLK2 19.2MHz、4lane/当前声明200MHz、CSIPHY2、独立TITAN_TOP域保持。PM8008源码&i2c4为0x890000/运行i2c-1，不混淆总线号。当前仅1928×1088。
- libcamera/IPA/tools及gstreamer/v4l2为99990.7.2-r5，config/stack0.1.0-r0，共944包；49条payload核对保持。13包构建/签名和5IPA内嵌公钥验证通过；尚未验逐字重复构建。CPU配置由包接管，目录0755/文件0644；通用堆root/video0660，FastRPC专用池root0600。策略进程/桌面运行保持。
- 213首帧LUT修复已随214部署，数字白RAW1023/RGB首帧起254。215内部TPG8→16位修复通过RAW两级图案/RGB及关闭后暗噪声；216按原厂将增益800补至960，0/800/960/0噪声约0.47/0.95/2.35/0.44，非实际灵敏度标定。默认cam/GStreamer各6帧通过；配置前cam仅列Contrast/Gamma，标准手动控制API仍未验收。

## 源码、产物与回退依据

- kernel /home/cy122/pmos-samurai-kernel136/kernel。当前IMX471源码cc756279…；211三文件及其它保存改动、25 tracked/11 untracked保持。217临时构建后原源码/对象/模块、配置fbde3690…、16798符号/order772、Image183和旧canonical DTB22c1…均恢复。旧canonical不能当当前部署树刷写。[源码核对](reference/kernel217/source-final-validation.json)。
- 私人kernel217/candidate-source为未应用候选，candidate-build-r3的module bc4649fb…/DTB a214fd6b…已构建；候选DTB只增sensor的400/748.8MHz频率，未打入boot.img。频率依固件过滤，完整RAW还需unprocessed_fullres参数；当前DTS只有200MHz，参数本身不足以开放新模式。W=1/符号/风格通过不等于实机或RGB验收。
- 当前模块回退为k216-baseline/imx471-original.ko及k216-driver-test-r2/before-tree，215旧6b2bb0b4…已导出。先核对当前启动与空闲，再停策略进程/正常解绑以释放引用、卸载/还原/depmod/加载/绑定/恢复；不强卸。boot回退仍私人210/boot-partition-k210-front.img 89242ade…，与模块回退分别核对。
- 相机配方linux-port/packages/libcamera及samurai-camera-config，部署锁仍对应216已装模块/r5；217只在reference保存候选。r5/r4回退快照和步骤见214报告：删stack移4包、装3个r4、恢复原3配置/world及策略进程，不能混留r5数据库。私钥只在私人构建目录。
- 私人归档213/214/215/216/217分别227/167/99/86/22成员核对通过。217原厂BIN/XML和旧失败也留在私人输出，不公开。USB邻居恢复/64KiB传输有效，但213截断/超时根因未修。

## 续作与已知风险

用户关灯、室内窗边；保持无闪光灯/外部光源。RAW必须DMA READ START/END、去行填充，用分布/噪声/帧间变化区分暗场与全零；RGB黑位校正后全零不能直接判bug。传感器图案和CSID正对照都须恢复控制/link，场景不公开。

217原厂模式：4608×3456@字段30.01，LLP5120/FLL3762、输出时钟599.04M、4lane、SWRemosaic；2304×1728@30/60.02，LLP2560/FLL4250或2124、输出320M、2×2bin。全部19.2MHz，模式寄存器/流尺寸已双解码核对；30/60固定表仅FLL/曝光不同。后续先做完整尺寸CPU重马赛克、模式CFA/数字COMPOSE映射与DMABUF预算，再隔离测完整RAW/非黑输入、时序曝光和默认客户端，之后整合部署。现有IMX371 quad补丁折半且CPU受限，不能用折半/放大当16MP。

217旧模式120帧buffer时间戳约57.8168fps，5次流中仍pixel_rate160M、LLP2328/FLL1308（控件算52.5447fps）；差异未归因，不盲改PLL。控制延迟/曝光/API、方向/tuning/画质仍开放。AWB先核真实输入格式：packed10P已取8位，勿盲套unpacked缩放补丁；不复制笔记本镜头标定。

后置6400万主摄/1300万长焦/800万超广角/200万人像四路仍未接入；未知PLDO输入不能猜。211相机GPU ISP有CMA不足/黑帧/IOMMU unmap349 WARN/taint512，CPU通过不能替代GPU验收，149已修CCU故障结论保留。

GNSS真实fix/正CNR未解决，无无遮挡户外或Android基线；209较小UTC误差未改善约6秒报告，208 ADC变化不证明RF正常，勿重做同一UTC实验。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207原厂MCFG173文件8,807,671B自动RAM复制/mdtime可读，PDC1平台/25软件活动无pending、mcfg.tmp仍0B；真实SIM/数据/通话/SMS/UIM未验。BT phase5、传感器FastRPC/SSR与SSC首次失败、Wi-Fi/USB PM、音频长稳/耳机（用户暂无）、充电保护闭环、指纹/NFC及完整rootfs继续按[全硬件清单](linux-port/docs/HARDWARE-STATUS.md)推进。
''');assert path.stat().st_size<=6500
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text().replace('最后核对2026-10-16，阶段216。','最后核对2026-10-16，阶段217。').replace('完整相机r5和215测试图修复保持；216按原厂补齐前摄模拟增益960/名义16倍，RAW响应与回低增益、默认客户端通过，未作光照灵敏度标定','手机保持216已部署相机栈；217双解码核对原厂3模式/174寄存器并构建未安装候选，4608×3456需软件重马赛克，未宣称16MP成片支持').replace('[216报告](../../reference/kernel216/README.md)','[217报告](../../reference/kernel217/README.md)')
text=text.replace('前摄仍仅1928×1088，实际灵敏度/曝光、标准手动控制API、AWB输入格式/延迟/方向/tuning','前摄实机仍仅1928×1088；217原厂16MP/4MP候选已构建但未安装，完整尺寸重马赛克/缓冲区/COMPOSE/时序待验；实际灵敏度/曝光、标准手动API、AWB输入格式/延迟/方向/tuning')
path.write_text(text)
path=repo/'DOCS-INDEX.md';text=path.read_text().replace('[216原厂增益范围](reference/kernel216/README.md)','[217原厂模式与未部署候选](reference/kernel217/README.md)、[216原厂增益范围](reference/kernel216/README.md)');path.write_text(text)
plan=dict(stage=217,previous_goal_turn='progress:216 own factory gain range deployed and RAW response accepted',state='217 verified own3mode/174register decode vs independent vendorXML, built unapplied candidate modulebc4649fb anddtba214fd6b undercandidate-build-r3;allhostproduction216sources/artifacts restored;no deviceinstall/reboot/flash. Current216module1388a070/r5 package944 intact;3DSP running,PMreleased,taint/fault0;22nativearchive membersverified. Globalgoalactive.',device_guard='/var/lib/samurai/k217-baseline/boot-id-private.txt',device_transport='reference/kernel217/host.py',next='Finish docs mirror. Continue mode-aware fullnative16MP CPU quad remosaic preserving per-pixel CFA samples; do not useIMX371 collapse/upsampling as16MP. Geometry needs COMPOSE-to-native mapping and RAW/CPU output DMABUF budget. Then isolated raw16MP+nonblack pattern/FPS/exposure/defaultclients withcandidate DTB frequency support andexplicit unprocessedopt-in; onlyintegrateafterappropriateacceptance. Currentcandidate notinstalled, fullRGB unfinished, moduleunderplain216running.120rawtimestampcontrols gap52.54vs57.82fpsunresolved;no PLLguess. Preserve fullrear4/GNSS/cellular/BT/sensors/power/rootfs scope.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report));print('NEXT-SESSION bytes='+str((repo/'NEXT-SESSION.md').stat().st_size))
