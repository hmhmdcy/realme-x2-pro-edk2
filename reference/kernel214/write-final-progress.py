from pathlib import Path
import ast,json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214')
for name,field in [('source-final-validation.json','seven_package_native_install_and_default_clients_verified'),('final-evidence-validation.json','archive_and_all_member_hashes_verified'),('final-health-validation.json','camera_packages_upgraded_and_native_transaction_verified')]:assert json.loads((here/name).read_text())[field]
(here/'README.md').write_text('''# 214：完整相机包已部署，默认客户端通过

本轮把213的隔离修复整合进完整libcamera软件包，已在同一启动升级并验收普通用户默认取流，没有刷机或重启。范围是前摄1928×1088 RAW10/CPU ISP、首帧修复和软件包集成；完整16MP、图像质量、后置四摄、GPU ISP及其它外设仍未完成。

USB重新发现邻居后恢复同一scoped端点，用原密钥确认同一启动。213原归档按64KiB续传，全部227成员核对通过；此前截断/超时保留，不声称根因或大传输稳定性已修。[连接](fresh-endpoint-probe-validation.json)、[回收](previous-evidence-recovery-validation.json)。214新鲜基线确认原r4三包/数据库/配置保持，保存48份文件记录，三个DSP running、相机休眠、taint/五fault0。[基线](baseline-validation.json)。

独立宿主Alpine/aarch64构建root使用QEMU10.2.1、ARM GCC15.2.0和4个编译任务。完整r5配方保留原auto/virtual、全部子包、六个补丁及tuning/desktop输入，加入IMX471 helper、1µm属性和CPU首帧LUT三补丁。0010仅增加可选外部IPA密钥构建项，默认空值保留上游行为；strip后用同一保留密钥重签IPA，APK沿用203项目密钥。[配方与源锁](../../linux-port/packages/libcamera/README.md)、[构建](full-libcamera-build-validation.json)、[特性](full-feature-configuration-validation.json)。

11个相机子包及2个设备配置/栈包全部构建，13包按手机现有信任验签；34个ELF均aarch64、5个IPA及签名齐全，无私钥/运行脚本/文件归属冲突。宿主ARM模拟下cam/lc-compliance/qcam帮助、Python导入和全部5个IPA对编译核心内嵌公钥验签通过；没有把这些检查当作手机画质验收。[产物](forward-package-artifact-validation.json)、[运行检查](host-runtime-qa-validation.json)。保留源码、工具和私有签名输入，但未重复构建验证二进制逐字一致。

回退依据来自实际安装r4的备份文件和包数据库：3个快照包保留原内容、模式、软链接和依赖，使用现有受信任项目密钥签名，明确不冒称原发行版签名。缓存r4原包签名无法用保留信任验证，故未采用。用手机实际940包记录在宿主完成真实升级/回退，49条前向记录及44条原包记录核对通过，937个无关包记录不变，配置和world恢复。[回退输入](rollback-snapshot-inputs-validation.json)、[快照包](rollback-snapshot-package-validation.json)、[完整演练](package-roundtrip-validation.json)。

完整候选实机先通过暗场RAW、CSID数字白RAW与RGB，再通过手机原生安装预演。随后一次记录状态的APK事务升级libcamera/IPA/tools三包至99990.7.2-r5，新增gstreamer/v4l2/config/stack四包，当前944包；49条安装文件记录核对通过，原3份配置被包管理接管。相机栈固定版本，本地索引也已验签。仅重启原本空闲且加载旧库的WirePlumber，PipeWire和桌面进程身份保持，新进程加载r5库且没有旧删除映射。[候选](full-candidate-staging-validation.json)、[预检](native-install-preflight-validation.json)、[安装](package-install-validation.json)、[用户策略进程](wireplumber-reload-validation.json)。

安装后的UID10000使用系统默认库与CPU配置，没有loader/IPA候选路径覆盖。6帧物理暗场RAW均值63.9844～63.9881、标准差0.4411～0.4423，相邻帧33.03%～33.14%像素变化，非全零或冻结；读前后DMA同步并排除行填充。暗场RGB首帧14～15，黑位校正后其余5帧为0，这本身不判bug。CSID全1已知输入的6帧RAW每像素1023，6帧RGB从首帧起每字节254，未丢弃首帧。[暗场RAW](system-dark-raw-validation.json)、[暗场RGB](system-dark-rgb-validation.json)、[白RAW](system-white-raw-validation.json)、[白RGB](system-white-rgb-validation.json)。传感器内部TPG仍未作为有效正对照。

默认cam和安装的GStreamer插件通过标准API各取6帧，无报错、超时或新增内核fault。手机未装gst-inspect/gst-launch工具，首次检查因此停止；随后编译有限无窗口appsink客户端验证插件，不新增工具包。未用未同步的GStreamer缓存像素作画质证据，也未保存/展示房间场景。[客户端](default-clients-validation.json)。

最终sensor/CAMSS/CCI suspended，前摄两电源disabled/users0、MCLK与自身MMCX票释放、图案关闭；3DSP running、taint/五fault0，NV及非相机程序核对保持。GPS0/Signalsfalse/rate30、UTC第8次准备成功、chrony Normal，蓝牙关闭无连接。[最终健康](final-health-validation.json)、[源码](source-final-validation.json)。本轮私人原生归档167成员与完整归档均核对通过，不含私钥和场景图。[归档](final-evidence-validation.json)。

保留的失败：首次构建校验和顺序错误、第二次缺libyuv运行库均在输入/配置阶段终止并已修；配置包索引最初因宿主缺项目公钥失败，加入现有公钥后验签通过。宿主首次回退索引命令误用了mkndx不支持的--compat，改为deflate压缩；候选首次预检误按完整版本匹配SONAME，实际0.7软链接正确，已在采集前修正并保留原记录。以上失败不改写成通过。[校验顺序](checksum-order-repair-validation.json)、[libyuv](libyuv-dependency-repair-validation.json)、[配置构建](config-package-build-validation.json)。

回退须先重新核对当前启动、安装状态及相机/音频空闲，使用/var/lib/samurai/k214-package-candidates/rollback的3个签名r4快照。先删除samurai-camera-stack（本机原生模拟只会移除4个新增包），再通过仅含rollback/packages.adb的临时repositories文件明确安装三个=99990.7.2-r4；随后从k214-baseline/files恢复原3份配置和world，核对原库记录、移除本轮60-samurai-camera.list并重载WirePlumber。不能只还原库而留下r5包记录，不能忽略配置包删除时也会删其文件；快照重签后的APK数据库不声称与原数据库逐字一致。实际回退未发送。[当前回退检查](installed-rollback-readiness-validation.json)。

续作：IMX471内部TPG的0600/0601位宽、延迟/曝光/tuning/方向、完整16MP和应用画质；后置四路逐路供电/时钟/CCI接入；GPU ISP另修CMA/全黑/IOMMU释放。GNSS真实fix/正CNR、蜂窝真实业务、BT phase5、传感器FastRPC/SSR、Wi-Fi/USB PM、充电闭环、其它硬件及radio/Mesa/完整rootfs均保持开放。[全硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
''')
(repo/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-16，阶段214：完整相机r5包已部署，默认UID10000的cam/GStreamer各6帧通过，暗场RAW及数字白首帧对照通过；同一启动、未刷机/重启。完整外设goal active。[214报告](reference/kernel214/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输reference/kernel214/host.py，guard为/var/lib/samurai/k214-baseline/boot-id-private.txt。最终3DSP running，相机休眠/供电时钟释放、taint/五fault0；GPS0/Signalsfalse/rate30、BT关闭无连接。214安装/策略重载marker均verified，旧211/212切换已闭环，不重放。
- boot211 c3bf043f…/DTB6f9f5b0f…，Image183 bfa72dd9…/logdump183 e73754c7…保持。IMX471 a28dd67a…、CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…/BT185保持，模块树772ko/786文件。TFTP207 b3bb82b9…/wifi854c9a8c…/MCFG helperd4c62be6…/MM191/helper421/init54/SSC9a1保持。
- 前摄静态CCI1 master1/0x10、MCLK2 19.2MHz、4lane/200MHz、CSIPHY2；独立TITAN_TOP域、裁剪和PM修复保持。PM8008源码&i2c4为0x890000、运行i2c-1，不能混淆总线编号。
- libcamera/IPA/tools为99990.7.2-r5，另装gstreamer/v4l2同r5及samurai-camera-config/stack0.1.0-r0，共944包；937个无关包记录保持，49条payload核对通过。完整auto/virtual与11子包都已构建，未把213三pipeline候选当完整包。5IPA内嵌公钥签名、全部13包签名/架构通过；未验证逐字重复构建。
- CPU配置已由配置包接管，/etc/libcamera目录0755/文件0644；两个heap模块自动加载，通用堆root/video0660+uaccess，FastRPC专用池root0600拒绝。WirePlumber已优雅重载新库，PipeWire/桌面身份保持。
- 安装后暗场RAW六帧均值63.9844～63.9881、标准差0.4411～0.4423，相邻帧33.03%～33.14%变化；DMA同步、排除填充。数字白RAW六帧每像素1023，RGB从首帧起每字节254；真实暗场RGB黑位校正后可全0，不直接判bug。默认cam/GStreamer接口各6帧无错误；手机无gst CLI工具，使用有限标准API客户端。

## 源码、产物与回退依据

- kernel为/home/cy122/pmos-samurai-kernel136/kernel；214无kernel变更，211三个文件及其余33份保存改动保持，25 tracked/11 untracked未暂存。配置fbde3690…、16798符号/order772、Image183及旧canonical DTB22c1…保持，旧canonical不能刷作当前树。[源码核对](reference/kernel214/source-final-validation.json)。
- 完整配方linux-port/packages/libcamera，配置配方相邻samurai-camera-config；linux-port/camera/deployment-lock.json记录13产物，三补丁canonical在camera/libcamera。外部IPA保留私钥和203 APK签名输入只在私人构建目录；源码/包不含私钥。新rootfs尚未生成，kernel/radio/Mesa整合债仍开放。
- 私人kernel214/camera-forward-repo保留完整13包，camera-selected-repo为实机7包；rollback-snapshot-apks的3个r4包来自实际已安装备份并由现有项目密钥签名，非原发行版签名。宿主实际940记录升级/回退通过，当前手机仅模拟回退，没有真实回退。手机原48记录在k214-baseline，事务备份在k214-package-transaction。[回退说明](reference/kernel214/README.md)。
- 回退需新鲜核对空闲状态：删stack移除4新包，用仅指向rollback/packages.adb的临时repo明确安装3个r4，再恢复原3配置/world、移除本轮repo并重载WP；不能混留r5数据库。boot回退仍私人210/boot-partition-k210-front.img，89242ade…，与相机包回退分开核验。
- 私人213归档227成员已补全；214原生归档167成员已核对。USB邻居重新发现恢复同地址连接、64KiB传输成功仅为恢复手段，213截断/超时根因未证明。历史失败保持，不重放旧动作。

## 续作与已知风险

用户关灯、室内窗边；保持无闪光灯/外部光源。RAW用DMA READ START/END、去stride填充、分通道直方图/方差/帧间变化判断；不能仅凭RGB全0判bug。传感器TPG的CCI_REG8(0600)与原厂0601疑点未修，数字正对照用已确认有效的CSID源并恢复原link/控制。

前摄当前仅1928×1088模式；先修TPG/控制延迟、tuning/曝光/方向及完整16MP，后置6400万主摄/1300万长焦/800万超广角/200万人像四路逐个接入。未知PLDO输入不能猜。GPU ISP仍有CMA不足/黑帧/IOMMU unmap349 WARN/taint512的211证据；CPU通过不能替它验收，也不影响149已修CCU故障结论。

GNSS真实fix/正CNR未解决，无无遮挡户外或Android基线。209较小UTC误差未改善约6秒报告，候选未部署；208 ADC变化不能证明RF正常，勿重复同一UTC实验。[相关realme/OPPO/一加机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。UTC第8次准备成功和chrony Normal不等于定位成功。

207原厂MCFG173文件8,807,671B自动RAM复制/mdtime可读，PDC1平台/25软件活动无pending，mcfg.tmp仍0B；真实SIM注册/数据/通话/SMS/UIM未验。完整目标还包括BT phase5、传感器FastRPC共享池/SSR和SSC首次204退出、Wi-Fi第2轮PM35秒未关联/USB稳定性、音频长稳和耳机（用户暂无）、充电控制保护闭环、指纹/NFC真实读卡等。[完整清单](linux-port/docs/HARDWARE-STATUS.md)。
''')
assert (repo/'NEXT-SESSION.md').stat().st_size<=6500
path=repo/'linux-port/packages/libcamera/README.md';text=path.read_text();start=text.index('214正在');text=text[:start]+'''214已在独立宿主QEMU模拟ARM/Alpine环境构建全部11个子包，另有2个配置/栈包；13包验签和架构/文件清单通过，5个IPA与核心内嵌公钥验签通过。手机已升级core/IPA/tools三包并新增gstreamer/v4l2/config/stack，默认UID10000的cam/GStreamer接口各取6帧通过；首帧数字白正对照及暗场RAW变化通过。[214验收](../../../reference/kernel214/README.md)、[部署锁](../../camera/deployment-lock.json)。

保留源输入与签名密钥支持后续构建，尚未重复构建证明二进制逐字一致。完整分辨率、图像质量、后置四摄和GPU ISP故障仍开放。设备默认CPU配置及heap权限由相邻samurai-camera-config包管理；r4回退快照来自实际已安装文件并明确重签，详见214报告。
''';path.write_text(text)
(repo/'linux-port/packages/samurai-camera-config/README.md').write_text('''# Realme X2 Pro 相机配置包

samurai-camera-config0.1.0-r0管理默认CPU ISP配置、两个通用heap模块自动加载和权限规则，文件与linux-port/camera中的canonical输入相同，目录0755/文件0644。通用堆给予video/uaccess，FastRPC专用池保持root0600。

samurai-camera-stack固定libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r5，并依赖配置包。214已用手机原生APK事务安装，默认用户客户端验收通过。[完整记录](../../../reference/kernel214/README.md)。本包不包含kernel驱动、设备树或签名私钥。

回退时删除配置包也会删除它接管的原文件，须按214备份恢复原3份配置和world并核对模式，不能仅降级libcamera。[回退检查](../../../reference/kernel214/installed-rollback-readiness-validation.json)。
''')
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();first=text.split('\n\n')[1];text=text.replace(first,'用途：当前硬件验收清单。最后核对2026-10-16，阶段214。完整相机r5已部署，默认cam/GStreamer各6帧及暗场RAW/数字白首帧对照通过；前摄画质/完整16MP、后置四摄和完整外设goal仍开放。[214报告](../../reference/kernel214/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。',1)
rows=text.splitlines()
for n,row in enumerate(rows):
    if row.startswith('| 摄像头 |'):rows[n]='| 摄像头 | 210静态前摄RAW10、211 CROP/独立供电及212默认CPU跨启动保持；214完整r5包已部署，默认UID10000 cam/GStreamer接口各6帧，暗场RAW噪声/帧间变化与数字白首帧对照通过，控制链路恢复、供电时钟释放、taint/fault0；11相机子包及2配置包构建/签名/架构通过 | 前摄仅1928×1088模式，TPG位宽、延迟/方向/tuning、完整16MP/画质及GUI应用未验。后置四路未接入；GPU ISP的CMA不足/黑帧/IOMMU unmap、未知PLDO输入/冷启/长稳开放；未验证重复构建逐字一致，kernel及完整rootfs尚未整合 |'
    if row.startswith('| 普通USB与OTG |'):rows[n]=row.replace('大传输/当前连通性仍未解决；','214重新发现同地址USB邻居后严格密钥连回同启动，64KiB完成213全部227成员和214全部167成员归档核对，当前连接恢复；根因和大传输稳定性仍未证明修复；')
path.write_text('\n'.join(rows)+'\n')
path=repo/'DOCS-INDEX.md';text=path.read_text().replace('[213暗场与首帧修复候选](reference/kernel213/README.md)','[214完整包部署与默认客户端](reference/kernel214/README.md)、[213暗场与首帧对照](reference/kernel213/README.md)');path.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='Stage214 complete progress: original213 archive227 recovered; full13 camera packages built/verified,7 installed native/r5,default cam andGst API6frames each and RAWdark/digitalwhite firstframe passed. Native214 archive167 members verified. Sameboot, noflash/reboot,3DSP running,PMrailsreleased,taint/fault0. Globalgoalactive.',next='Continue IMX471 sensorTPG0600/0601 width, verified control delays/tuning/full16MP and rear4;GPUISP separate CMA/IOMMU issue. Preserve all GNSS/cellular/BT/sensors/power/rootfs gaps. Do not rerun one-shot prior scripts/installation markers. Finish source docs mirror audit.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
for path in here.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
print('214 deployment evidence and remaining global scope recorded; NEXT-SESSION bytes='+str((repo/'NEXT-SESSION.md').stat().st_size))
