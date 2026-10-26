"""Record two measured hardware-ISP sensor profiles without product promotion."""
from pathlib import Path
import hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
health=json.loads((HERE/'final-health-validation.json').read_text())
joint=json.loads((HERE/'joint-physical-validation.json').read_text())
ae=json.loads((HERE/'ae-r1-association-validation.json').read_text())
assert health['checked_camera_runtime_healthy'] and joint['passed'] and ae['passed']
assert not ae['all_epochs_reached_target']
archive=ROOT/'archive/camera-before306-2026-10-19';assert not archive.exists();archive.mkdir()
names=['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','linux-port/camera/README.md',
 'linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']
rows=[]
for name in names:
 p=ROOT/name;target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 rows.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(archive/'manifest.json').write_text(json.dumps(dict(stage=306,files=rows),indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-19：[306长焦原厂BLS／硬件AE](reference/kernel306/README.md)、[305几何／产品回归](reference/kernel305/README.md)、[303广角硬件AE](reference/kernel303/README.md)。目标active、未完成。两种当前sensor模式已接实验硬件IPA；完整多摄／ISP校准、RGB统计／AWB仍待完成。

## 当前部署与启动身份

USB NCM和原严格密钥SSH可用，306核同一305启动guard，#298／7.3.0-rc6-rmx1931-samurai-k298+、taint0。guard：/var/lib/samurai/k305-geometry-r2/boot-id-private.txt；306/host.py继承305。303/304旧guard拒绝当前启动，勿覆盖历史guard或重放旧切换。

仍为298 Image加305长焦单模块，s5k3m5.ko SHA d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9。778模块、961包、50相机载荷全量核验沿用305；306核10关键模块及加载note一致，APK数据库／world与桌面／PW／WP身份不变。libcamera r24／config-r19和PW／SPA／Gst1.6.9-r3仍RAW＋CPU ISP；候选未安装，无本阶段刷写／重启。

Image SHA eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d，boot276与固件保持。内核树/home/cy122/x2pro-linux/camera305-sensor-kernel，samurai-geometry305／18b0a5a753e9363594f682049bf131169488c644，干净；原298树保留。未来完整构建含305修复。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

## 最新证据与边界

- 原厂qtech_s5k3m5sx调校只读提取、哈希与卸载验证。19个IFE根152区域均960 U14，经类型表和原厂解析器一致；BPS另有990，未用于IFE。仅显式实验参考，不是本机个体标定。[306](reference/kernel306/README.md)
- 长焦2104×1560／481930000pixelrate／9648line／min1663frame：240帧9次单控，7次有足够信噪比，均写入SOF＋2；两次较小变化不用于延迟证明。独立profile限定该模式，通用303后端不改。
- 联合恒EV20ms×8↔10ms×16，480帧、18次双控36写入，90个BHIST／Y分区域无混合EV瞬态。隔离AE再480帧，3生效revision／6写入、15可辨响应域与元数据同帧；写入＋2，提议＋5（含IPC排队）。[联合](reference/kernel306/joint-physical-validation.json)、[AE](reference/kernel306/ae-r1-association-validation.json)
- **长焦目标收敛false**：当前低照度稳定在接近模式／策略曝光上限（量化允许差2行）和16倍增益，低于0.16目标。passed只表示目标或受限边界检查。WB unity固定，不声称AWB、变光、双向收敛或完整IQ。
- 三次新实验合计1200硬件帧，图／格式／裁剪／控制／video与PM恢复，worker退出。五sensor／lens、两CCI、CAMSS休眠，9供电用户0、MCLK／CCI0，fault／taint／pstore／CCI错误0。[收尾](reference/kernel306/final-health-validation.json)
- 305长焦活动阵列4208×3120几何已修，产品四摄348帧回归保留。303广角在上一启动另有联合480帧、AE960帧，同样只验证低照度上限；候选通用库与本次复用字节相同，IMX319／S5K3M5数据不混用。
- 304 EEPROM双读4420通道值独立解码一致，但完整schema／checksum／绑定／LSC几何／尺度／golden合成未确认，不应用个体值。旧GPU／modem／SSC问题仍开放，whole_system_healthy=false。

## 源码回退与下一步

SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline仍303源码，使用303/build-candidate.py；306只构建独立应用并复用固定300／303候选库，不重放旧安装器。306 delay-r1、joint-r1、ae-r1均终态，不重放。下一实验使用新run，先核实际状态。

继续RGB统计／AWB：已固定8份原厂主来源在E:/edk2-samurai-out/kernel306/awb-primary，主源收据见306。AWB BG DMA client15、BHIST16，常规区域24字节含R/B/Gr/Gb求和计数；位域、阈值、区域限制和多统计DMA生命周期还待核，不把源码阅读当实机支持。优先公共SoC参数／统计层与同SOF配对，再接用户空间算法。

继续AE明亮／变光与错误恢复、主前摄／其它模式、正式暗场／颜色／阴影调校。用户延期纯色／遮光保持。构建卷按284/storage.py核backing；稳定#290及独立模块、k132776／248备份保留。[操作边界](WORKING-BOUNDARIES.md)、[维护收据](reference/maintenance-2026-10-19/README.md)。上游接受／零补丁升级未证明。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('''继续多摄／骁龙ISP校准目标（active、未完成）。读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel306/README.md。

当前原密钥USB，同一305 guard，仍#298 Image加305长焦模块；内核树camera305-sensor-kernel，samurai-geometry305／18b0a5a753e9363594f682049bf131169488c644。产品RAW＋CPU ISP、候选未安装。306只新增应用／profile，SDK仍303源码。

长焦OEM IFE BLS19根152区域960 U14，原厂解析器与独立解码一致；BPS含990未混用。240帧单控中7有效阶跃写入SOF＋2；联合480帧36写入90域通过；隔离AE480帧3revision／6写入15域对齐。目标0.16仍未达到，仅接近上限；不是变光／双向收敛或正式校准。三实验终态、资源恢复、taint/fault0，勿重放。

下一步公共SoC RGB统计／AWB与同SOF配对。8份原厂源已固定于私人kernel306/awb-primary，AWB BG client15、BHIST16、常规区域24字节；位域／阈值／范围／DMA生命周期仍需核。继续主前摄／其它模式与AE错误恢复、正式IQ；304 EEPROM校验／绑定／几何未完成，不应用个体值。保持分层，不将模组调校塞入DT。旧GPU／modem／SSC问题仍开放。
''')
banner='306（2026-10-19）：同一305 guard／#298，长焦原厂IFE BLS与两帧控制延迟已核，新增1200硬件帧含联合控制与隔离AE；当前低照度只证明上限边界，目标收敛false。产品RAW＋CPU ISP不变，RGB统计／AWB与完整校准待完成，目标active。'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/name;p.write_text(banner+'[306事实与范围]('+prefix+'reference/kernel306/README.md)。以下按历史阅读。\n\n'+p.read_text())
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=json.loads(p.read_text())
 d.pop('candidate_hardware_ae_current_mode_frames',None)
 d.update(stage=306,previous_lock_archive=prefix+'archive/camera-before306-2026-10-19/'+name,
  current_camera_evidence=prefix+'reference/kernel306/README.md',
  final_health_evidence=prefix+'reference/kernel306/final-health-validation.json',
  current_boot_evidence=prefix+'reference/kernel306/preflight-validation.json',
  current_boot_tele_hardware_frames=1200,current_boot_tele_ae_frames=480,
  current_boot_tele_ae_effective_revisions=3,current_boot_tele_ae_control_writes=6,
  candidate_hardware_ae_real_frames_total=1440,
  candidate_ae_target_convergence_verified=False,
  experimental_hardware_ae_verified_frames_by_sensor={'imx319_prior_boot':960,'s5k3m5_current_boot':480},
  experimental_hardware_ae_scope='Opt-in IMX319 and S5K3M5 current modes only; fixed frame duration; low-light exposure/gain limits; target convergence unverified',
  experimental_sensor_profiles={
   'imx319':{'profile':prefix+'reference/kernel303/imx319-ae.yaml','timing':prefix+'reference/kernel302/runtime-association-validation.json','boot_scope':'prior303'},
   's5k3m5':{'profile':prefix+'reference/kernel306/s5k3m5-ae.yaml','timing':prefix+'reference/kernel306/delay-analysis-r1-validation.json','joint':prefix+'reference/kernel306/joint-physical-validation.json','ae':prefix+'reference/kernel306/ae-r1-association-validation.json','boot_scope':'same305'}},
  s5k3m5_factory_bls_evidence=prefix+'reference/kernel306/tele-bls-export-validation.json',
  rgb_statistics_source_evidence=prefix+'reference/kernel306/awb-primary-source-validation.json',
  rgb_statistics_hardware_implemented=False,hardware_awb_implemented=False,
  candidate_pipeline_generic_source_unchanged=True,inline_userspace_candidate_installed=False,
  current_adaptation_goal_status='active',goal_complete=False,whole_system_healthy=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'DOCS-INDEX.md';s=p.read_text();anchor='[305长焦几何与四摄回归](reference/kernel305/README.md)';assert s.count(anchor)==1
p.write_text(s.replace(anchor,'[306长焦原厂BLS／硬件AE](reference/kernel306/README.md)、'+anchor))
(ROOT/'sessions/306-s5k3m5-factory-bls-timing-and-hardware-ae.md').write_text('# 306：长焦原厂BLS、时序与硬件AE\n\n'+banner+'\n\n[来源、独立核验、实验与未完成范围](../reference/kernel306/README.md)。当前内核、产品包和303候选源码保持；增加独立模组profile，使用既有公共后端。实验passed不等同目标收敛或正式校准。\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
report=dict(stage=306,actual_kernel_image_stage=298,actual_sensor_module_stage=305,
 hardware_frames_this_stage=1200,telephoto_delay_useful_steps=7,telephoto_joint_changes=18,
 telephoto_joint_real_writes=36,telephoto_ae_revisions=3,telephoto_ae_real_writes=6,
 candidate_source_unchanged=True,product_packages_unchanged=True,target_convergence_verified=False,
 full_calibration_complete=False,goal_status='active')
(HERE/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
