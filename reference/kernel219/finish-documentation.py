from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel219')
health=json.loads((here/'final-health-validation.json').read_text());assert health['taint']==0
archive=json.loads((here/'final-evidence-validation.json').read_text());assert archive['archive_and_all_member_hashes_verified']
assert json.loads((here/'package-integration-validation.json').read_text())['canonical_full_feature_r6_and_config_r1_recipes_promoted']
documents={
'linux-port/camera/README.md':'''# Realme X2 Pro 相机接入

219已部署boot219、IMX471原厂4MP/实验16MP模式及像素阵列时序修复，用户态为完整libcamera99990.7.2-r6/config0.1.0-r1。真实4MP RAW、2296×1728 RGB，以及实验4608×3456 RAW/RGB均取流通过。默认系统库和配置下，普通UID10000的cam/GStreamer显式请求4MP，各取得六帧。[219记录](../../reference/kernel219/README.md)、[部署锁](deployment-lock.json)。

配置包管理CPU ISP、system heap选择、heap模块自动加载和权限。原r5在4MP第三个RGB缓冲分配失败，r6保持相同尺寸与四缓冲后通过。通用堆video/0660与活动会话权限保持，FastRPC专用池root/0600。目录0755/文件0644；不能靠放宽DSP池权限解决相机分配。

默认传感器开放1928×1088和2304×1728。完整16MP须显式启用模块实验参数及用户态Quad配置，当前两者默认关闭；其真实颜色、标准CFA/几何、标定及RGB实时性能仍未验收。内部TPG在完整模式仍按普通Bayer周期生成，只作传输正对照。[相位检查](../../reference/kernel219/test-pattern-layout-notes.md)。

房间关灯的RAW用DMA同步后的有效像素噪声与帧间变化判定；处理后近黑RGB配合真实RAW与图案对照解释，不据它单独判故障。没有保存或展示房间图片，没有闪光灯或外部照明。

[内核补丁链](kernel/source-lock.json)及[完整软件包配方](../packages/libcamera/README.md)已保存；宿主canonical内核仍216源码，旧canonical DTB不能刷成当前树。GPU ISP退出告警、后置主摄/长焦/超广角/人像四路、GUI日用、冷启/长稳与完整rootfs继续开放。213首帧LUT、215测试图案位宽和216增益修复保持，不能用单路前摄证明全部镜头可用。
''',
'linux-port/packages/libcamera/README.md':'''# libcamera 99990.7.2-r6：Realme X2 Pro补丁集

保留原auto,virtual管线、全部11子包、原10补丁及全部tuning/desktop输入，新增0011原生尺寸Quad CPU实验实现与0012软件ISP分配堆选项。产品配置选择CPU/system heap，Quad实验默认关闭。[源清单](source-lock.json)、[完整验收](../../../reference/kernel219/README.md)。

219完整构建另配两个配置/栈包，共13包；现有受信任签名验证、34个ELF的ARM64核对及5个IPA与新核心内嵌公钥验签均通过。Qt/Python入口、手机50组真实CPU类合成输入及实际4MP/实验16MP取流通过。七个组件已统一升级，944包中的937个无关记录保持；默认系统库与配置下的cam/GStreamer各六帧通过。

构建使用LIBCAMERA_IPA_PRIVATE_KEY指定保留的外部私有输入，APK签名另用原项目受信任密钥；不得重新生成后混用，也不得把私钥打进包或源码。strip后重签IPA，核心公钥、IPA与代理须一致。已保留构建输入，但尚未重复构建证明二进制逐字一致。

r6回退依据为实际原七个r5/config-r0包、当前事务前world/repo/配置备份及原生七包降级模拟；没有执行本轮完整降级再升级。214较早的三个r4快照属于另一次历史事务，不能混用。正常光照颜色/标定、标准CFA/几何、RGB实时吞吐、后置四摄和GPU ISP仍未验收；完整rootfs整合继续开放。
''',
'linux-port/packages/samurai-camera-config/README.md':'''# Realme X2 Pro 相机配置包

samurai-camera-config0.1.0-r1管理CPU ISP、dma_heap: system、两个通用heap模块自动加载和权限规则；与linux-port/camera的输入逐字一致，目录0755/文件0644。通用堆video/uaccess、FastRPC专用池root0600保持。

samurai-camera-stack固定libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r6，配置包与栈包为r1。219已原生统一升级七包并验证默认用户cam/GStreamer的4MP取流。system heap解决原r5第三个4MP RGB缓冲分配失败，保持原尺寸与四缓冲数量。[219记录](../../../reference/kernel219/README.md)。

完整16MP仍需两个明确实验开关，默认关闭。回退用原七个r5/r0包及本轮保存的world/repo/配置；本轮原生降级仅模拟通过。勿套用214早期删除配置包、恢复三个r4包的历史步骤。本包不包含内核、设备树或签名私钥。
''',
'linux-port/camera/libcamera/README.md':'''# IMX471与CPU ISP补丁

基于libcamera0.7.2与原发行版六补丁，0007回移IMX471增益/黑位helper，0008加入静态属性和1000nm像元尺寸，0009强制首帧生成CPU查找表。这些修复于214完整r5部署，219的完整r6继续保留。[历史因果对照](../../../reference/kernel213/README.md)。

当前完整配方还含外部IPA签名输入支持、原生尺寸Quad CPU实验及dma_heap选择；全部源输入以[产品配方锁](../../packages/libcamera/source-lock.json)为准。本目录[source-lock](source-lock.json)保留213三补丁源码快照，已明确标注历史范围并链接当前r6部署依据。

219已构建13包、统一升级七组件，验证5个IPA与核心公钥、Qt/Python入口、50组合成Quad输入及实机4MP/实验16MP取流。完整模式的内部TPG不是Quad物理滤色阵列的模拟；真实颜色与标准CFA/几何、控制API/延迟、曝光/方向/标定、后置四摄和GPU路径仍开放。[当前记录](../../../reference/kernel219/README.md)。
''',
'linux-port/camera/isp/experimental/README.md':'''# IMX471原生尺寸Quad Bayer实验补丁

0001-libcamera-imx471-native-quad-cpu.patch已作为0011加入完整r6配方，两份补丁逐字一致。原始算法与400组独立参考检查见[218记录](../../../../reference/kernel218/README.md)，完整包实机验证见[219记录](../../../../reference/kernel219/README.md)。

实现保留原生4608×3456尺寸，明确实验配置才开启，默认关闭。219完整r6库重新通过50组/780,337,408像素的CPU类合成测试，真实传感器完整RAW及CPU RGB也各取得六帧，包含暗场与图案正对照。

内部TPG在完整模式按普通Bayer周期生成，因此RGB图案仅证明尺寸/传输/分配与非黑输出。真实场景标准CFA/几何、颜色/标定和日用画质仍未验；RAW传感器约30fps不代表CPU RGB可实时30fps。完整模式模块参数与用户态实验选项均默认关闭。[图案边界](../../../../reference/kernel219/test-pattern-layout-notes.md)。
''',
'linux-port/camera/kernel/README.md':'''# IMX471内核补丁链

依次保留215的测试图案16位写与216的模拟增益上限修复，219新增原厂4MP/实验16MP模式、固件链路频率过滤及像素阵列时序修复。新增两补丁在保存的216源/板级树上独立重放，结果与实际部署源码逐字一致。[锁](source-lock.json)、[重放收据](../../../reference/kernel219/kernel-patch-integration-validation.json)。

旧模式实际行长5120；三模式阵列速率387.2/326.4/约578.133MHz经活动寄存器和各120帧时间戳核对。保持PLL表，显式写旧模式行长，修正PIXEL_RATE元数据。16MP仍须模块实验参数，默认关闭，真实颜色/标准CFA/几何未验收。

本目录保存补丁与指纹，不代表宿主canonical源/DTB已更新；其仍为216源和旧canonical板级树。部署boot219及模块e49与旧输出分别核对，禁止把旧canonical DTB当当前部署树刷写。Image183保持，后置四摄/未知供电父网与完整rootfs整合继续开放。
''',
}
for name,text in documents.items():(repo/name).write_text(text)
readme=(here/'README.md').read_text()
old='完整r6配方保留原11子包、全部管线及5个IPA，增加可配置`software_isp.dma_heap`，产品配置选择system；原生Quad选项仍默认关闭。构建继续使用原签名输入，不生成新密钥。[源码准备](r6-package-source-validation.json)。本检查点的完整构建仍在进行，手机仍为r5/config-r0；不能把隔离候选通过写成产品包已修复。'
new='完整r6配方保留原11子包、全部管线及5个IPA，增加可配置`software_isp.dma_heap`，产品配置选择system；原生Quad选项仍默认关闭。原签名输入继续使用。[13包验签/架构](forward-package-artifact-validation.json)、[5个IPA与核心公钥](host-runtime-qa-validation.json)、[完整r6 CPU类50组测试](r6-cpu-isp-tests-validation.json)通过。七组件已原生统一升级为r6/config-r1，944包中的937无关记录保持，49条payload核对通过，[七包r5降级模拟](r6-package-install-validation.json)通过。'
assert readme.count(old)==1;readme=readme.replace(old,new)
readme+='''
## 完整包实机回归与当前状态

隔离r6与已安装r6各完成八组取流，每组六帧：4MP真实暗场RAW/RAW图案、2296×1728 RGB图案/暗场及实验完整16MP的对应四组。[安装后4MP RGB](installed-r6-2296x1728-rgb-pattern2-default-validation.json)、[完整16MP RGB](installed-r6-4608x3456-rgb-pattern2-full-validation.json)。r5原第三缓冲失败保留，r6同尺寸/四缓冲使用system heap通过。

普通用户使用默认系统库及CPU配置、显式请求4MP，[cam](standard-cam-validation.json)与[标准GStreamer API](standard-gstreamer-validation.json)各六帧通过，全部格式/图/控制恢复。GStreamer只核对流元数据，不宣称未同步的像素统计；其短FD采样窗没有观察到导出器，system分配依据为独立同步取流收据。

[最终健康](final-health-validation.json)：相机休眠、前摄两电源零用户/关闭、MCLK与本域票释放，实验参数N、两个测试图案关闭；三个DSP运行、GNSS空闲、BT关闭无连接、taint/五类fault0，NV与非相机程序保持。初次最终检查把合法升级的配置与旧212指纹比较而失败，已按签名包归属核对新配置并保留[原失败](final-health-initial-failure-validation.json)，没有重放安装或硬件操作。

产品配方、配置与部署锁已整合，[内核四补丁链](kernel-patch-integration-validation.json)重放一致。完整r6构建后abuild按常规清理了src/pkg目录；配方、13个签名包和独立解包QA前缀保留。IPA验证使用保留的上游验证程序，已核对其实际加载新r6核心/基础库，从新核心获取公钥。尚未证明二次构建逐字一致。

私人原生归档逐成员核对通过，[归档收据](final-evidence-validation.json)不公开归档指纹、密钥、场景或坐标。全外设goal继续active。
'''
readme=readme.replace('产品相机配方仍r5，尚未完成219源码与完整包整合。','产品相机配方现为完整r6/config-r1；内核补丁链已保存，宿主canonical内核及完整rootfs整合仍待完成。')
(here/'README.md').write_text(readme)
status=repo/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段219。boot219/时序修复模块与完整r6/config-r1已部署；默认系统库下4MP RGB分配问题修复，cam/GStreamer各六帧通过，实验16MP RAW/RGB取流通过。真实颜色/几何及后置四摄、GNSS等仍开放，全外设goal active。[219报告](../../reference/kernel219/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
lines=text.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 219原厂4MP/实验16MP真实RAW及完整CPU RGB取流通过；完整r6/config-r1七组件已统一部署，13包签名/34个ARM64 ELF/5IPA核心公钥、50组合成测试通过。system heap解决原第三个4MP RGB缓冲失败，同尺寸四缓冲及默认系统库cam/GStreamer各六帧通过。四模式120帧时序与控件吻合，格式/图/控制恢复，供电时钟释放、taint/fault0 | 16MP实验开关默认关闭，内部TPG是普通Bayer周期，不能验收真实Quad颜色。标准CFA/几何、正常光照画质/标定/方向/曝光/API/GUI与RGB实时性能未验。后置四路、GPU ISP的CMA/黑帧/IOMMU退出告警、未知PLDO输入、冷启/长稳仍开放；内核canonical源、逐字重复构建与完整rootfs整合待完成 |'
status.write_text('\n'.join(lines)+'\n')
next_text='''# Realme X2 Pro 当前检查点

2026-10-16，阶段219：boot219/时序模块与完整r6/config-r1已部署；真实4MP/实验16MP RAW及CPU RGB、默认系统库cam/GStreamer的4MP取流通过。全外设goal active。[219报告](reference/kernel219/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 运输reference/kernel219/host.py，新启动guard /var/lib/samurai/k219-runtime/boot-id-private.txt。218及219-baseline/before-reboot属于旧启动，不可授权新切换。219刷写/重启marker closed，时序模块verified；所有完整模式试验已finish，当前N/WirePlumber恢复。BT只扫描，不新增振动。
- boot219 156f0370…/DTB a214fd6b…，仅前摄endpoint增加400/748.8MHz、200保留；Image183 bfa72dd9…/logdump183 e73754c7…保持，persist/NV不变。当前IMX471 e49dab26…；CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…/BT185保持。772ko/786文件，其余771ko不变。
- TFTP207 b3bb82b9…/wifi854c9a8c…/MCFG helperd4c62be6…/MM191 b350c55b…/GNSS42168f33…/init54b81745…/SSC9a1fd03f…保持。新boot早期就绪延迟后原服务自动启动，未手动restart，不称SSC修复。
- 前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP；默认1928×1088与2304×1728，4608×3456需模块参数及用户态实验配置，当前均默认关闭。删除错误COMPOSE，CROP/FOV/标准CFA语义仍开放。
- libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r6，config/stack0.1.0-r1，944包、937无关记录保持、49条payload核对通过。mode cpu/dma_heap system；通用堆root/video0660，DSP池root0600。WP为手动进程，正常重载仅停WP并现取argv/env/UID10000，桌面/PipeWire身份保持。
- r5的2296×1728 RGB第三缓冲分配失败保留；r6相同尺寸/四缓冲通过。13包签名/34个ARM64 ELF、5IPA与r6核心公钥、Qt/Python入口通过。完整r6库手机50组/780337408像素合成测试通过；隔离与安装r6各八组实机取流、每组六帧通过。默认系统库cam/GStreamer显式4MP各六帧通过，后者只验元数据、不宣称CPU像素同步统计。
- 真实4MP暗RAW噪声约0.47/变化35%，16MP约0.60/变化51%，各六帧有效像素DMA同步统计，无图片保存。处理后暗RGB近黑不单独判bug。完整模式TPG实测仍是普通2×2 Bayer周期，只证明完整传输/分配/非黑输出，不能验收真实Quad颜色；真实滤色阵列/画质仍开放。
- 时序旧行长实读5120、原报2328，三模式阵列速率修为387200000/326400000/578133333，不改PLL。四组120帧约57.82018/30.00030/60.03122/30.01381fps与控件吻合；只读帧元数据，无像素访问。早期错误DMA方法标签已更正，私人原始输出保留。这是RAW速率，不证明CPU RGB实时30fps。
- 最终健康在k219-final-health-r2：三相机设备suspended，两前摄电源disabled/用户0、MCLK/本域票释放、图案0、参数N；三DSP running、GPS0/Signalsfalse/rate30、BT关闭无连接、watch空闲、chrony Normal、taint/五fault0。首轮检查因新r1配置与旧212指纹不同退出，已按签名包归属修正核验，原失败保留，无安装/硬件重放。

## 源码、产物与回退依据

- kernel /home/cy122/pmos-samurai-kernel136/kernel的canonical仍216源cc756279…/对象1388a070…、旧canonical DTB22c1…；原25 tracked/11 untracked保持，不能把旧DTB当当前部署树刷写。实际219源私人timing-source/imx471.c 61931497…、timing-build模块e49dab26…/DTB a214fd6b…；W=1/增量checkpatch0。linux-port/camera/kernel四补丁链已独立重放为相同源码/板级树。
- 当前时序回退设备k219-timing-baseline/imx471-original.ko d82c941d…与k219-timing-driver-test-r2/before-tree；更早216在k219-baseline。先现取启动身份/确认空闲，正常解绑/卸载/恢复/depmod/加载/策略恢复，不强卸。boot回退私人211/boot-partition-k211-sensor-domain.img c3bf043f…，与模块回退分开核对。
- 完整r6构建session40635已完成，不能重启同一abuild all。chroot /home/cy122/x2pro-linux/libcamera214-root，配方/work/libcamera219与/work/samurai-camera-config219；输出/packages219、/packages-config219及私人kernel219/camera-forward-repo共13包。abuild常规清理r6 src/pkg，旧214/218源码与原产物仍保留；libcamera219-qa-prefix及chroot/candidate219解包前缀保留。
- IPA验证复用保留的上游ipa_verify，已核对它实际加载新r6核心/base并取其公钥。原IPA214和APK203私钥复用，未生成/上传新私钥。canonical配方、配置、源码锁与部署锁现为r6/r1；尚未重复构建证明逐字相同，完整kernel/rootfs整合仍待完成。
- r6事务k219-r6-package-transaction状态verified；旧944包DB/world/repo/config已保存。实际r5回退七包在设备k214-package-candidates/forward，host私人214/camera-forward-repo；七包签名/当前旧payload已验，安装后原生七包降级模拟通过，未执行本轮完整回退往返。勿混用214更早的三个r4快照。
- 本轮私人原生归档成员逐一核对通过，见219归档收据；源脚本/原失败与本轮新健康均保留。USB严格新邻居/原密钥/64KiB分块有效，原大传输截断根因仍未修。当前capsule私人kernel219/current-work-private.json；所有过渡marker终态后再执行新切换。

## 续作与已知风险

用户关灯、室内窗边，无闪光灯/外部光源，场景/坐标不公开。前摄标准CFA/几何、真实颜色/曝光/API/延迟/方向/标定/GUI与实际RGB性能继续；后置GW1/3M5/IMX319/人像四路未接入，未知PLDO输入不得猜。211 GPU ISP CMA不足/黑帧/IOMMU unmap349 WARN/taint512仍开放，CPU通过不代替GPU，149 CCU修复结论保持。

GNSS真实fix/正CNR未解决，无无遮挡户外或Android基线；209小UTC误差未改善约6秒报告，208 ADC不证明RF正常。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207 MCFG173文件/8807671B自动RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp仍0B；真实SIM注册/数据/通话/SMS/UIM开放，通话发信需用户明确目标。

BT phase5、传感器FastRPC reclaim/SSR与首次启动失败、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护闭环、指纹/NFC与旧rootfs132软件整合按[硬件清单](linux-port/docs/HARDWARE-STATUS.md)推进。不要因相机局部进展完成/暂停全外设goal。
'''
assert len(next_text.encode())<=6500,len(next_text.encode());(repo/'NEXT-SESSION.md').write_text(next_text)
r=dict(stage=219,boot219_timing_and_full_r6_stack_deployed=True,four_mp_rgb_allocation_failure_fixed=True,
 raw_timing_metadata_matches_hardware=True,full_native_raw_and_rgb_experiment_passed=True,
 generated_full_sensor_pattern_is_ordinary_bayer=True,real_scene_cfa_geometry_colour_quality_and_rgb_throughput_open=True,
 canonical_package_recipes_and_kernel_patch_chain_locked=True,host_kernel_canonical_source_still216=True,
 original_failures_preserved=True,private_native_archive_members_verified=archive['verified_members'],
 full_peripheral_goal_active=True,no_flash_or_external_illumination=True,no_scene_images_saved=True)
(here/'final-validation.json').write_text(json.dumps(r,indent=2)+'\n')
state=json.loads((private/'current-work-private.json').read_text());state.update(state='boot219 e49 module and full r6/r1 stack verified; archive complete; canonical recipes and patch chains integrated',
 active_build_session=None,active_verification_session=None,scoped_full_mode_may_be_active_until_verification_finally=False,experimental_fullres_current='N',
 final_health_directory='/var/lib/samurai/k219-final-health-r2',transition_pending=False,
 next='Complete stable documentation mirror compare; then continue full peripheral goal: real CFA/geometry/quality or rear camera topology, GNSS real reception, radio and power integration debt')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(r))
