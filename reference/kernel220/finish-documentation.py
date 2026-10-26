from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel220')
assert json.loads((here/'package-integration-validation.json').read_text())['canonical_r7_r2_recipes_and_deployment_locks_promoted']
health=json.loads((here/'final-health-validation.json').read_text());assert health['taint']==0
archive=json.loads((here/'final-evidence-validation.json').read_text());assert archive['archive_and_all_member_hashes_verified']
documents={
'linux-port/packages/libcamera/README.md':'''# libcamera 99990.7.2-r7：Realme X2 Pro补丁集

r7保留r6全部12个补丁、auto,virtual全部管线、11个子包及全部tuning/desktop输入，新增0013逐次刷新软件IPA的sensorInfo。2MP原先误用初始化时4MP行时长，1290行曝光报10117µs；现在报17057µs，与本模式计算值17057.85µs的整数微秒换算一致。[220记录](../../../reference/kernel220/README.md)、[源锁](source-lock.json)。

220使用完整对象缓存和官方abuild build/rootpkg/index阶段，保留原214树并在终态恢复2254个文件/链接。13个框架/配置包验签、34个ARM64 ELF、5IPA与新核心公钥以及Qt/Python入口通过。候选与已装系统共288帧元数据换算检查通过，包含独立IPA进程；默认GStreamer另六帧通过。219的像素算法验收保留，本轮没有改变像素处理或标定。

构建以LIBCAMERA_IPA_PRIVATE_KEY指定保留的外部私有输入，APK签名另用原项目受信任密钥；strip后重签IPA并保持核心/代理一致。私钥不得进入包或仓库。已保留输入，尚未证明二次构建逐字相同。

当前回退为实际原七个r6/config-r1包及220事务前world/repo/配置备份，原生七包降级模拟通过，未执行本轮完整回退往返。早期r5/r4快照分别保存。标准手动曝光API、真实CFA/几何/颜色/延迟标定、后置四摄、GPU ISP与完整rootfs继续开放。
''',
'linux-port/packages/samurai-camera-config/README.md':'''# Realme X2 Pro 相机配置包

当前samurai-camera-config与stack为0.1.0-r2，固定libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r7。配置payload与r1逐字相同：CPU ISP/system heap、两heap模块自动加载及权限，目录0755/文件0644。通用堆video/uaccess，FastRPC专用池root0600。

220统一升级七包，修复不同模式的曝光元数据换算；4MP分配修复和16MP实验开关保持。[220记录](../../../reference/kernel220/README.md)。完整16MP默认关闭。实验的IPA独立进程配置仅用于临时验证，没有改变产品YAML。

回退使用220保留的七个r6/r1包与本轮world/repo/配置；本轮降级只模拟通过。勿混用214早期r4删除/恢复步骤。本包不含内核、设备树或签名私钥。
''',
'linux-port/camera/libcamera/README.md':'''# IMX471与CPU ISP补丁

0007/0008/0009的IMX471 helper、1000nm属性与首帧LUT修复保留；219加入原生尺寸Quad CPU实验和dma_heap选择，220新增逐次刷新软件IPA的传感器模式信息。当前完整产品为r7/config-r2。[完整配方锁](../../packages/libcamera/source-lock.json)。

本目录[source-lock](source-lock.json)明确保留213三补丁源码快照的历史范围，并链接当前部署。220修复2MP曝光元数据误用4MP行时长，288帧及独立IPA进程传递检查通过；未改变像素处理算法。[220证据](../../../reference/kernel220/README.md)。

219真实4MP/实验16MP RAW及CPU RGB、暗场噪声和图案对照仍是像素路径证据；完整模式内部TPG为普通Bayer周期，不能证明真实Quad颜色。手动曝光API、标准CFA/几何、真实曝光延迟/颜色/方向/标定、后置四摄和GPU路径仍开放。
''',
}
for name,text in documents.items():(repo/name).write_text(text)
path=repo/'linux-port/camera/README.md';text=path.read_text().replace('用户态为完整libcamera99990.7.2-r6/config0.1.0-r1','用户态现为完整libcamera99990.7.2-r7/config0.1.0-r2')
if '\n220进一步修复模式切换' in text:text=text.split('\n220进一步修复模式切换',1)[0]
text+='\n220进一步修复模式切换后的曝光元数据：软件IPA现在在每次配置时获取当前时序。2MP/4MP/实验16MP及独立IPA进程共288帧换算误差均小于1µs整数化范围；实际曝光延迟与光度标定仍未验收。产品配置payload不变。[220记录](../../reference/kernel220/README.md)。\n';path.write_text(text)
readme=(here/'README.md').read_text().replace('完整r7/r2构建进行中，保留全部原管线与子包。','完整r7/r2已构建并部署，保留全部原管线与子包。')
readme=readme.replace('手机包尚未替换。','首次打包还因旧子包目录残留失败；移开候选pkg目录、复用完成的44目标构建重新封装，未重编译或丢弃原目录。[打包失败记录](initial-packaging-failure-validation.json)。')
if '\n## 部署与回归' in readme:readme=readme.split('\n## 部署与回归',1)[0]
readme+='''
## 部署与回归

13包签名与34个ARM64 ELF核对通过，5IPA与r7核心内嵌公钥匹配，原Qt/Python/GStreamer等完整功能保持。[产物](forward-package-artifact-validation.json)、[运行与IPA验签](host-runtime-qa-validation.json)。原214完整目录2254个文件/链接已恢复，候选完整源/对象保留，原密钥复用，没有生成或上传私钥。

候选线程模式的2MP/4MP/实验16MP各36帧、强制独立IPA进程的2MP/4MP各36帧通过；独立进程由临时ipa.force_isolation配置启用，并实际观察到隔离日志。没有去掉或破坏签名来触发隔离。[独立进程2MP](exposure-metadata-candidate-isolated-1920x1088-validation.json)、[独立进程4MP](exposure-metadata-candidate-isolated-2296x1728-validation.json)。

七组件统一升级为r7/config-r2，944包中的937无关记录保持，49条payload核对通过，原七个r6/r1包及world/repo/配置保留，原生降级模拟通过，未执行本轮完整降级往返。[原生事务](r7-package-install-validation.json)。仅重载WirePlumber，桌面/PipeWire身份保持。

默认系统库下2MP/4MP/实验16MP各36帧通过，新修复共验证288帧。所有样本与本模式行时长计算的差小于1µs，是整数微秒量化范围，不是实际曝光精度/延迟标定。三模式的阵列时序/PLL和内核模块没有更改。

| 2MP最后一帧 | 元数据 | 当前模式计算值 |
| --- | ---: | ---: |
| r6，1290行 | 10117µs | 17057.85µs |
| 已装r7，1290行 | 17057µs | 17057.85µs |

[已装2MP](exposure-metadata-system-r7-1920x1088-validation.json)、[4MP](exposure-metadata-system-r7-2296x1728-validation.json)、[实验16MP](exposure-metadata-system-r7-4608x3456-validation.json)。所有试验只读帧元数据和数值控制，没有映射/保存图像；媒体图/格式/控制均恢复。

默认GStreamer另取六帧通过。[标准API](standard-gstreamer-validation.json)。首次包装器因继承探针路径的匹配字符串被误改，在取流前退出；已校验并复用同一探针后修正路径，保留[前置失败](gst-preflight-failure-validation.json)。

[最终健康](final-health-validation.json)：三DSP running，前摄/CCI/CAMSS休眠、两前摄电源零用户/关闭、时钟/本域票释放，参数N/图案0，GNSS空闲、BT关闭无连接，taint与五类fault0，NV/非相机程序保持。[146成员私人归档](final-evidence-validation.json)逐一哈希核对，指纹/场景/坐标不公开。

配方与部署锁已整合，[整合收据](package-integration-validation.json)。尚未验收标准手动曝光API、真实曝光延迟、CFA/几何/颜色/正常光照画质、后置四摄与GPU ISP。GNSS真实fix、蜂窝真实业务及其余[全硬件目标](../../linux-port/docs/HARDWARE-STATUS.md)继续active。
'''
(here/'README.md').write_text(readme)
status=repo/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段220。保持boot219/e49模块，用户态已升完整r7/config-r2，修复2MP曝光元数据误用4MP行时长；288帧和独立IPA进程传递通过，实际曝光/画质及后置四摄、GNSS等仍开放。全外设goal active。[220报告](../../reference/kernel220/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
lines=text.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | boot219/e49与完整r7/r2部署；219真实4MP/实验16MP RAW及CPU RGB、暗场/图案与时序修复保持，system heap解决4MP四缓冲失败。220逐配置刷新IPA模式信息，288帧曝光元数据换算及独立代理通过；2MP的1290行由错误10117µs修为17057µs，符合当前时序的17057.85µs整数化。13包/34ELF/5IPA/Qt/Python核验及默认GStreamer六帧通过，937无关包保持，供电时钟释放、taint/fault0 | 手动曝光API、实际曝光/延迟/光度标定、标准CFA/几何、颜色/方向/GUI及RGB实时性能未验。16MP实验默认关，内部TPG为普通Bayer，不能验收真实Quad颜色。后置四路、GPU ISP退出告警、未知PLDO输入、冷启/长稳、逐字重复构建与完整kernel/rootfs整合仍开放 |'
status.write_text('\n'.join(lines)+'\n')
next_text='''# Realme X2 Pro 当前检查点

2026-10-16，220：保持boot219/e49模块，完整libcamera r7/config-r2已部署；修复2MP曝光元数据错用4MP行时长，288帧及独立IPA进程通过，GStreamer六帧通过。全外设goal active。[220记录](reference/kernel220/README.md)、[219像素验收](reference/kernel219/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 运输reference/kernel220/host.py；新邻居/原严格公钥认证，当前guard /var/lib/samurai/k220-baseline/boot-id-private.txt。与219-runtime同一启动；218及219-baseline/before-reboot属于旧启动，不能授权新切换。220所有试验终态，参数N/WirePlumber恢复；无重启/刷写。219切换marker closed，220包事务verified。BT只扫描、不新增振动。
- boot219 156f0370…/DTB a214fd6b…，前摄200/400/748.8MHz；Image183 bfa72dd9…/logdump183 e73754c7…保持，persist/NV保持。当前IMX471 e49dab26…，CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…/BT185等保持，772ko/786文件。TFTP207/MCFG、MM191/GNSS/SSC、Wi-Fi指纹见219，均无本轮改动。
- 前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP。默认1928×1088和2304×1728；完整4608×3456需模块及用户态两个实验开关，当前默认关。错误COMPOSE已删除，真实CROP/FOV/CFA语义仍开放。
- libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r7，config/stack0.1.0-r2，944包/937无关记录保持，49条payload核对。mode cpu/dma_heap system，配置payload与r1相同；通用堆root/video0660、DSP池root0600。WP为手动进程；重载仅停WP并现取argv/env/UID10000，桌面/PipeWire身份保持。
- 219已证明4MP/实验16MP真实RAW与CPU RGB各六帧，暗RAW噪声约0.47/0.60、变化35%/51%，全有效像素DMA同步、无图片保存。r5第三个4MP RGB缓冲分配失败，r6起同尺寸四缓冲system heap通过。完整TPG仍普通Bayer周期，只验传输/非黑输出，不代表Quad真实颜色；暗RGB近黑不能单独判bug。
- 驱动时序已修：旧行长实读5120，三模式阵列速率387200000/326400000/578133333，不改PLL；各120帧RAW速率约57.82018/30.00030/60.03122/30.01381，与控件吻合，不证明CPU RGB30fps。
- 220发现软件IPA init缓存4MP行时长，2MP1290行元数据报10117µs，应约17057.85µs。新增0013每次configure传当前sensorInfo，已装r7报17057µs；候选3模式+独立IPA2模式+已装3模式共288帧，换算差均<1µs整数化，未宣称物理曝光精度/延迟。标准API仍只证明Contrast/Gamma，手动曝光未接入。
- 13包/34 ARM64 ELF/5IPA公钥、Qt/Python及默认GStreamer六帧通过；cam三模式各36帧，隔离代理另2×36。隔离只用临时配置，产品YAML保持；本轮不改像素算法，算法证据见219。
- 最终健康k220-final-health：相机/CCI/CAMSS suspended，两前摄电源disabled/用户0、MCLK/本域票释放、图案0、参数N；三DSP running、GPS0/Signalsfalse/rate30、BT关无连接、watch空闲、chrony Normal、taint/五fault0，NV/非相机程序保持。

## 源码、产物与回退依据

- kernel /home/cy122/pmos-samurai-kernel136/kernel的canonical仍216源cc756279…/对象1388a070…/旧DTB22c1…，原25 tracked/11 untracked保持；不能把旧DTB当当前部署树刷写。实际219源私人timing-source/imx471.c 61931497…，模块e49dab26…/DTB a214fd6b…；四补丁链已独立重放相同源码/板级树。
- 时序模块回退：设备k219-timing-baseline/imx471-original.ko d82c941d…及k219-timing-driver-test-r2/before-tree；更早216在k219-baseline。先现取身份/确认空闲，正常解绑/卸载/恢复/depmod/加载/策略恢复，不强卸。boot回退私人211/boot-partition-k211-sensor-domain.img c3bf043f…，与模块回退分别核对。
- SDK /home/cy122/x2pro-linux/libcamera214-root。220复用原完整对象缓存，44目标编译+官方abuild rootpkg/index；原214目录2254文件/链接已恢复在/work/libcamera，无待恢复快照。候选完整源/对象保留/work/libcamera220-built，配方/work/libcamera220与/work/samurai-camera-config220；13包在/packages220、/packages-config220和私人kernel220/camera-forward-repo，QA前缀libcamera220-qa-prefix/chroot/candidate220。
- 220两次构建/打包失败及GStreamer前置失败均保留并恢复；全部任务已终态，勿重放。详情见220记录。
- canonical配方/配置/源码锁/部署锁为r7/r2，0013补丁d6aa409f…，原12补丁/tuning/YAML保留。原IPA214与APK203私钥复用，未生成/上传。尚未证明二次构建逐字相同；canonical内核及完整rootfs整合继续。
- 当前事务k220-r7-package-transaction verified，原944包DB/world/repo/config已保存。实际r6/r1回退七包在设备k219-r6-package-candidates/forward及私人219/camera-forward-repo，签名/当前旧payload核对与安装后七包降级模拟通过，未执行完整回退往返。更早r5/r4分别保留，不混用。
- 220原生私人归档146成员逐一核对，219另512成员保持；不公开指纹/密钥/场景/坐标。USB严格新邻居/原密钥/64KiB有效，截断根因仍未修。当前capsule私人kernel220/current-work-private.json，完整旧交接保存在archive/NEXT-SESSION-through219-2026-10-16.md。

## 续作与已知风险

用户关灯、室内窗边；无闪光灯/外部光源。前摄手动曝光API、实际曝光/延迟、真实CFA/几何/颜色/方向/标定/GUI与RGB性能继续；后置GW1/3M5/IMX319/人像四路未接入，未知PLDO输入不猜。211 GPU ISP CMA/黑帧/IOMMU unmap349 WARN/taint512开放，CPU通过不替代GPU，149 CCU修复保持。

GNSS真实fix/正CNR未解决，无无遮挡户外/Android基线；209小UTC误差未改善约6秒报告，208 ADC不证明RF正常。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207 MCFG173文件/8807671B RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp仍0B；真实SIM/数据/通话/SMS/UIM开放，通话发信需用户明确目标。

BT phase5、传感器FastRPC reclaim/SSR与首次启动失败、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护闭环、指纹/NFC及旧rootfs132软件整合按[硬件清单](linux-port/docs/HARDWARE-STATUS.md)推进。不要因相机局部修复完成/暂停全外设goal。
'''
assert len(next_text.encode())<=6500,len(next_text.encode());(repo/'NEXT-SESSION.md').write_text(next_text)
r=dict(stage=220,exposure_metadata_cached_mode_defect_fixed_and_deployed=True,framework='99990.7.2-r7',config='0.1.0-r2',
 new_corrected_metadata_samples=288,isolated_ipa_serialisation_verified=True,quantisation_difference_below_microseconds=1,
 full_original_feature_set_and_13_packages_verified=True,original214_files_links_restored=2254,
 no_kernel_boot_or_pixel_algorithm_change=True,private_native_archive_members=146,
 manual_api_physical_calibration_other_cameras_and_full_peripheral_goal_still_open=True)
(here/'final-validation.json').write_text(json.dumps(r,indent=2)+'\n')
state=json.loads((private/'current-work-private.json').read_text());state.update(state='r7/r2 deployment,288 metadata samples,GStreamer and146-member private archive verified; source locks updated; mirror pending',
 active_build_session=None,active_validation_session=None,active_archive_session=None,transition_pending=False,
 phone_still='boot219 e49 module plus full r7/config-r2; full mode N',
 next='Finish source checks and stable public mirror compare; then continue original full peripheral goal, including manual control API/geometry/rear cameras and GNSS/radio/power open items')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(r))
