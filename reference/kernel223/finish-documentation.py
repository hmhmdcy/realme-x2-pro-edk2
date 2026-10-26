from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel223')
assert json.loads((here/'package-integration-validation.json').read_text())['canonical_r8_r3_recipes_promoted']
readme='''# 223：捕获帧与控制快照配对已部署

2026-10-16，当前为boot219/Image183/IMX471 e49、CAMSS fae1、完整libcamera99990.7.2-r8/config0.1.0-r3。本轮没有重启或刷写。[安装](coherent-install-validation.json)、[最终健康](final-health-validation.json)、[部署锁](../../linux-port/camera/deployment-lock.json)。全外设goal继续active。

原驱动RAW请求间隔500ms时，缓冲号仍连续0–15；原r7 RGB请求4对应buffer33，却用请求索引读取曝光历史。新CAMSS用真实SOF标记每个缓冲，重新排队清有效位，缺标记交付buffer error，仅SM8150/VFE170订阅FRAME_SYNC。完成时间戳仍为EOF；IRQ掩码、时钟和电源策略保持。[补丁](camss-sm8150-paired-sof-candidate.patch)、[原RAW基线](baseline-raw-gap-validation.json)。

新libcamera在捕获回调按采集号读取DelayedControls并保留独立快照，统计处理使用此副本；IPA上下文仍用请求号，无frameStart平台保留原路径。[用户态补丁](libcamera-capture-control-snapshot.patch)。这次配套部署解决已复现的采集帧/曝光历史关联错误，尚未加入标准手动曝光API。

临时内核试验2MP/4MP RAW/RGB共64帧，配套r8另做96帧，均能在独立事件流找到每个缓冲的SOF，没有缺标记。r8的64帧RGB在普通/隔离IPA均验证采集号与控制索引一致，曝光换算误差小于1µs。临时试验均先恢复82c，之后才配套安装fae1/r8。[内核试验](paired-sof-native-validation.json)、[配套试验](control-snapshot-native-validation.json)。这些证据不代替光学曝光延迟标定。

安装后普通/隔离IPA另64帧间断请求通过；实验16MP另36帧元数据换算通过，已恢复实验参数N及WP。默认cam/GStreamer各6帧通过。原771个其他模块文件、944包中的937个无关记录、49相机payload/权限复核通过；world仅更新stack版本。[安装后控制](installed-control-validation.json)、[16MP](exposure-metadata-system-r8-4608x3456-validation.json)、[GStreamer](standard-gstreamer-validation.json)。

关灯条件下真实4MP RAW、RGB各6帧只在内存统计：RAW值62–133、标准差2.656–2.666，相邻帧约56.2%像素变化，RAW/RGB全零帧均为0。这批样本包含暗光信号及噪声，未复现固定全零输出；不据此验收颜色、曝光质量或所有镜头。[暗帧分类](dark-frame-classification-validation.json)。没有保存场景图像、闪光或外部照明。

完整13包保留全部原13补丁、全部子包/管线/tuning，签名、34个ARM64 ELF、5IPA匹配核心公钥及Qt/Python入口通过。原214构建树2254个文件/链接/权限及内核180份源/对象/模式恢复，原r7对象缓存保留。私钥仍为原214/203外部输入，未进入包或仓库。[完整产物](forward-package-artifact-validation.json)、[运行入口](host-runtime-qa-validation.json)。二次逐字重建未验证。

原82c模块在设备k223-r8-paired-deployment及本轮私人证据中；实际七个r7/r2回退包仍在k220-r7-package-candidates，降级模拟通过，未执行完整回退往返。首个安装后验证器误把/run测试可执行文件当成候选库，16帧本身成功；已保留失败记录，改为仅检查库映射并用新目录完成回归。[验证器修正](installed-validator-correction.json)。

标准手动曝光/增益/独立Auto/Manual尚未加入；RAW-only仍绕过SWISP配置和统计，不能只验RGB就宣称完整API。真实CFA/几何/颜色/物理延迟、后置四摄和GPU ISP故障仍开放。GNSS仍无真实fix/正CNR；蜂窝业务、蓝牙phase5、传感器SSR等按[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)继续。两槽状态引用221历史记录，不是本轮重新查询。
'''
(here/'README.md').write_text(readme)

path=repo/'linux-port/packages/libcamera/README.md';s=path.read_text();s=s.replace('# libcamera 99990.7.2-r7：','# libcamera 99990.7.2-r8：')
s=s.replace('当前回退为实际原七个r6/config-r1包及220事务前world/repo/配置备份，原生七包降级模拟通过，未执行本轮完整回退往返。早期r5/r4快照分别保存。','当前回退为实际七个r7/config-r2包及223事务前world/repo/配置和原82c CAMSS，原生七包降级模拟通过，未执行完整回退往返。更早r6/r1及r5/r4分别保存。')
s+='\n223在保留原13补丁和完整功能的基础上新增0014捕获时控制快照，与CAMSS fae1配套部署。请求间断后按实际采集号选择历史，保持IPA请求索引；普通/隔离IPA候选与安装后共128帧关联检查，以及36帧实验16MP换算通过。手动API仍未加入。[223记录](../../../reference/kernel223/README.md)。\n';path.write_text(s)
path=repo/'linux-port/packages/samurai-camera-config/README.md';s=path.read_text().replace('0.1.0-r2','0.1.0-r3').replace('99990.7.2-r7','99990.7.2-r8')
s=s.replace('回退使用220保留的七个r6/r1包与本轮world/repo/配置；本轮降级只模拟通过。','回退使用220保留的七个r7/r2包与223的world/repo/配置及原82c模块；降级只模拟通过。')
s+='\n223配套安装捕获帧SOF驱动和r8控制快照；产品YAML保持相同。[223记录](../../../reference/kernel223/README.md)。\n';path.write_text(s)
path=repo/'linux-port/camera/libcamera/README.md';s=path.read_text().replace('当前完整产品为r7/config-r2','当前完整产品为r8/config-r3')
s+='\n223新增捕获时独立控制快照，与实际SOF编号配对的CAMSS一起部署；128帧普通/隔离IPA间断请求关联检查通过。标准手动API仍待实现。[223证据](../../../reference/kernel223/README.md)。\n';path.write_text(s)
path=repo/'linux-port/camera/kernel/README.md';s=path.read_text();s+='\n223新增独立的0005 CAMSS补丁：只在SM8150/VFE170发布标准FRAME_SYNC，给缓冲保存真实SOF号，缺标记返回错误。fae1模块与r8已配套部署，160帧临时试验逐帧对应独立事件流。完成时间戳保持EOF，未校准物理曝光延迟；canonical CAMSS仍原始源，完整内核/rootfs整合待办。[锁内camss条目](source-lock.json)、[223证据](../../../reference/kernel223/README.md)。\n';path.write_text(s)
path=repo/'linux-port/camera/README.md';s=path.read_text().replace('用户态现为完整libcamera99990.7.2-r7/config0.1.0-r2','用户态现为完整libcamera99990.7.2-r8/config0.1.0-r3，CAMSS为223配套fae1模块')
s+='\n223已完成并配套部署缓冲SOF配对和捕获控制快照，候选/安装后普通及隔离IPA共128帧关联检查通过。关灯后4MP RAW与RGB有数值波动，无全零帧；没有保存场景。原82c及实际r7/r2回退保留，标准手动曝光和其它镜头仍开放。[223记录](../../reference/kernel223/README.md)。\n';path.write_text(s)
path=repo/'linux-port/docs/HARDWARE-STATUS.md';s=path.read_text();a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段223。CAMSS fae1与r8/config-r3已配套部署；实际SOF缓冲号和捕获控制快照关联通过。boot219/e49保持，全外设goal active。[223报告](../../reference/kernel223/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[b:]
a=s.index('| 摄像头 |');b=s.index('\n',a)
s=s[:a]+'| 摄像头 | boot219/e49保持，223 CAMSS fae1与完整r8/r3配套安装。160帧临时缓冲/SOF配对、128帧普通/隔离IPA请求间断控制关联、36帧实验16MP换算及cam/GStreamer通过；暗4MP RAW/RGB各6帧非全零且变化，最终taint/fault0，49payload及其它771模块保持 | 标准手动曝光/增益/Auto-Manual与RAW-only控制链仍待实现；物理曝光/延迟/颜色/几何/CFA/方向/GUI/实时性能、后置四路、GPU ISP告警、未知PLDO输入、冷启/长稳及完整kernel/rootfs开放；16MP实验已关、TPG普通Bayer不验真实Quad颜色 |'+s[b:];path.write_text(s)
path=repo/'linux-port/camera/deployment-lock.json';d=json.loads(path.read_text());d.pop('kernel_or_boot_changed_in_stage223',None);d['kernel_image_or_boot_changed_in_stage223']=False;path.write_text(json.dumps(d,indent=2)+'\n')

handoff='''# Realme X2 Pro 当前检查点

2026-10-16，223：CAMSS fae1和libcamera r8/config-r3已配套部署，安装后回归及健康通过；全外设goal active。[223记录](reference/kernel223/README.md)、[边界](WORKING-BOUNDARIES.md)。旧完整交接[through222](archive/NEXT-SESSION-through222-2026-10-16.md)。

## 当前部署与已验证状态

- 运输reference/kernel223/host.py，当前USB邻居/原严格公钥；guard /var/lib/samurai/k223-baseline/boot-id-private.txt，与219-runtime/220/221/222-baseline同boot。218及219-baseline/before-reboot旧身份不可授权切换。223部署state verified，所有实机任务终态；BT只扫描、不新增振动。
- boot219 156f0370…/DTB a214fd6b…，Image183 bfa72dd9…/logdump183 e73754c7…；本轮未刷/重启。IMX471 e49dab26…/29536B，CAMSS fae1ed40…/777360B文件及loaded-note核对。772ko、其他771文件及权限保持；CCI f9c9272a…/PM8008 d1ff82c0…与其它外设指纹见219保持。
- 完整libcamera/IPA/tools/gstreamer/v4l2=99990.7.2-r8，config/stack=0.1.0-r3；944包/937无关记录保持、49payload核对。world仅stack版本更新，产品CPU/system heap YAML不变。通用堆root/video0660+uaccess，DSP池root0600。WP手动UID10000， reload须现取argv/env，桌面/PipeWire身份保持。
- 前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP；默认1928×1088/2304×1728。4608×3456须模块+用户态双实验开关，当前N。COMPOSE已删，真实CROP/FOV/CFA开放。
- 219三模式时序/真实4MP与实验16MP RAW/CPU RGB证据保持；2MP RAW约57.82fps，未验RGB30fps。TPG完整模式仍普通Bayer，不能验真实Quad颜色。220逐配置sensorInfo修复误用行时长，原288帧证据保留。
- 223修复BUF_DONE连续号遗漏丢帧，以及请求号误索引控制历史：CAMSS仅SM8150/VFE170发布FRAME_SYNC，缓冲保存SOF号；重排清标签，缺标签buffer error，完成时间戳仍EOF。libcamera在捕获回调按采集号快照DelayedControls，统计只用该副本；IPA仍请求号，无frameStart保留旧路径。
- 临时原r7+新驱动64帧、新驱动+r8 96帧，160缓冲均对应独立SOF事件，无缺标签；r8普通/隔离IPA候选64+安装后64 RGB帧均核对历史索引/增益/曝光换算<1µs。实验16MP另36帧、默认cam/GStreamer各6帧通过，实验开关/WP已恢复。标准手动API未加入，光学延迟未校准。
- 关灯4MP RAW/RGB各6帧只在RAM统计：RAW62–133，std约2.66，相邻约56.2%像素变化；两者无全零帧。支持暗光噪声输出，不验颜色/曝光质量。没有存图、闪光或外部照明。首个安装后检查误判/run探针为候选库，16帧本身正常；原报告保留，改库映射过滤后新目录回归通过。
- k223-final-health：相机/CCI/CAMSS休眠，两前摄电源关闭/用户0，图案0/参数N；GPS0/Signalsfalse/rate30，watch空闲0workers，chrony Normal；三DSP running、BT关无连接、taint/五fault0、NV源保持。Modem State−1/原因2/Power1；UIM两槽no-atr/absent是221历史只读结果，不证明未插卡。

## 源码、产物与回退依据

- canonical kernel /home/cy122/pmos-samurai-kernel136/kernel仍216 IMX源cc756279…/对象1388a070…/旧DTB22c1…，CAMSS仍原82c对应源；25 tracked/11 untracked保持。当前219实际IMX源61931497…/e49/a214与223 CAMSS候选源另存，不能刷旧canonical输出。
- 223源码/模块私人kernel223/sof-candidate-source、qcom-camss-sof223.ko，公共linux-port/camera/kernel/0005-camss-sm8150-paired-sof.patch及source-lock.camss锁基线/四文件/模块。W1/checkpatch0、符号/vermagic/intree通过；构建前显式JSON模式清单核对180原源/对象/模式已恢复，不用NTFS仿真权限。
- r8官方abuild完整13包/34ARM64 ELF/5IPA匹配核心公钥、Qt/Python入口通过；原13补丁/tuning/全子包保持，新0014捕获快照。SDK /home/cy122/x2pro-linux/libcamera214-root原/work/libcamera2254文件/链接/权限已恢复，无待恢复快照；候选/work/libcamera223-built，r7缓存220-built保留。原IPA214/APK203私钥外置复用，不生成/上传；二次逐字重建未验。
- 产品配方/配置/源码锁/部署锁已更新r8/r3+fae1。设备原82c回退/世界/仓库/配置在k223-r8-paired-deployment，实际七个r7/r2包在k220-r7-package-candidates/forward及私人220/camera-forward-repo，签名/payload/降级模拟通过，未完整回退往返。更早r6/r1在219，分开保留。
- 同boot现取身份/空闲后，停止WP、正常解绑/卸载CAMSS、APK七包降级（恢复原world/repo）、恢复82c/depmod/加载、恢复图/格式、按现取上下文重启WP；不要只回退其中一边。IMX回退设备k219-timing-baseline/imx471-original.ko d82c941d…；boot回退私人211/boot-partition-k211-sensor-domain.img c3bf043f…，各自核对。
- 私人capsule kernel223/current-work-private.json。222私人71、22137、220146、219512成员归档保持；223本轮归档另见final-evidence-validation.json。USB严格邻居/原密钥/64KiB仅绕过截断，根因未修。

## 续作与已知风险

下一步标准曝光/增益独立Auto/Manual、AeEnable优先级、Auto期间忽略手动值、切换冻结、Camera::start控制及真实生效模式元数据；不要只回显请求。RAW-only目前绕过SWISP配置/统计，须实现真实控制/元数据链，不能仅验RGB。控制物理2/1帧延迟尚未校准。

真实CFA/几何/颜色/方向/曝光/标定/GUI/性能、后置GW1/3M5/IMX319/人像及未知PLDO输入继续；不猜供电。GPU ISP211 CMA/黑帧/unmap349 WARN/taint512开放，149 CCU修复保持。

GNSS仍无fix/正CNR，手机室内窗边；221GPS强制/GLO-BDS-QZSS-GAL启用与四黑名单0不证明RF，多频GET error57不证明无L5。209小UTC误差未改善约6秒报告，勿重复。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207MCFG173文件/8807671B RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp仍0B；实际SIM/注册/数据/通话/SMS开放，外发需明确目标。

BT phase5、传感器FastRPC/SSR/首启失败、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护、指纹/NFC实卡和rootfs132整合按[清单](linux-port/docs/HARDWARE-STATUS.md)继续；全goal保持active。
'''
planned=len(handoff.encode());assert planned<=6500,planned
(repo/'NEXT-SESSION.md').write_text(handoff)
d=json.loads((private/'current-work-private.json').read_text());d.update(state='223 coherent deployment and installed regressions/health passed; source locks promoted; native archive and final source/mirror checks finishing',transition_pending=False,active_build_session=None,active_native_session=None,
 next='Implement standard manual exposure/gain modes and truthful RAW-only control/metadata; continue GNSS/cellular/rear cameras/other peripherals',
 current_deployment=dict(boot_stage=219,image_stage=183,imx471='e49dab26',camss='fae1ed40',framework='99990.7.2-r8',configuration='0.1.0-r3'),
 next_session_bytes=planned)
(private/'current-work-private.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(stage=223,documentation_updated=True,next_session_bytes=planned,full_goal_active=True)))
