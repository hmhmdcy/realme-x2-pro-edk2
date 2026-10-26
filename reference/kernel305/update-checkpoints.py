"""Publish the verified new-boot sensor deployment while preserving prior facts."""
from pathlib import Path
import hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
health=json.loads((HERE/'final-health-validation.json').read_text())
commit=json.loads((HERE/'kernel-commit-validation.json').read_text())
assert health['checked_camera_runtime_healthy'] and commit['source_clean']
names=['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','linux-port/camera/README.md',
 'linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',
 'sessions/303-hardware-ae-candidate-and-joint-latch-preparation.md']
archive=ROOT/'archive/camera-before305-2026-10-19';assert not archive.exists();archive.mkdir()
records=[]
for name in names:
 p=ROOT/name;target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 records.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(archive/'manifest.json').write_text(json.dumps(dict(stage=305,files=records),indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-19：[305长焦几何／四摄回归](reference/kernel305/README.md)、[303硬件AE](reference/kernel303/README.md)、[304EEPROM](reference/kernel304/README.md)。目标active、未完成。长焦活动阵列已在sensor驱动修正并部署，完整多摄／ISP校准仍开放。

## 当前部署与启动身份

USB NCM和原严格密钥SSH已恢复。重连后启动ID变化，当前仍#298／7.3.0-rc6-rmx1931-samurai-k298+、taint0。新guard：/var/lib/samurai/k305-geometry-r2/boot-id-private.txt。305/host.py使用USB；303/304旧guard会拒绝当前启动，后续继承305入口并核当前状态，不覆盖历史guard。

当前298 Image加305单模块：778模块中仅s5k3m5.ko更新，SHA d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9，intree=Y、加载note匹配。其余777模块／961包／50相机载荷及APK数据库／world保持。libcamera r24／config-r19及PW／SPA／Gst1.6.9-r3仍RAW＋CPU ISP，303候选未安装。本阶段未刷写或重启。

Image SHA eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d，boot276和固件保持。

最新内核树/home/cy122/x2pro-linux/camera305-sensor-kernel，samurai-geometry305／18b0a5a753e9363594f682049bf131169488c644，干净。原camera279-isp-kernel、samurai-blc298／c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117保持；未来完整构建应包含305修复。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

## 最新证据与边界

- 305先查Hotdog同sensor方案，核本机三份寄存器表，只改s5k3m5.c几何；SoC、板级DT、寄存器表不变。ACTIVE／TRY八查询及libcamera属性通过：阵列4208×3120，19.2MHz输出2104×1560，全阵列裁剪。24MHz仅核表；方向、静态属性和延迟未猜测。
- 产品四摄18段272帧，另补长焦中断64帧／重开12帧，共348帧，不能算硬件IPA校准。图、格式／裁剪／控制／video恢复，桌面PID保留、PW／WP重启。五sensor／lens、两CCI和CAMSS休眠，9供电用户0、MCLK／CCI0，fault／taint／pstore／CCI错误0，worker退出。[最终核对](reference/kernel305/final-health-validation.json)
- 303在上一启动完成IMX319联合恒EV480帧／36写入SOF＋2；硬件AE隔离／线程共960帧，17生效revision／34写入，81可辨响应域与元数据同帧。低照度最终3331行×16仍低于0.16目标；严格0.01误差检查false，只证明正确到上限，未证明目标收敛。[实机边界](reference/kernel303/README.md)
- AE仅双Auto或双Manual启动，混合／运行中切换拒绝；WB固定，RGB AWB、动态帧长、防频闪及完整IQ未做。主机DSO／线程1440合成帧另列，真机隔离已通过。
- 304纠正旧EEPROM XML后半错位，WB Q=1、LSC221点，双读4420通道值独立C/Python一致。完整schema、校验／有效标志、模组绑定、LSC几何／尺度和golden合成未确认，未应用个体值。[304](reference/kernel304/README.md)
- 原厂IMX319 BLS960 U14仅OEM参考，临时WB不是正式校准。旧GPU／modem／SSC问题未关闭，whole_system_healthy=false。

## 源码回退与下一步

SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline为303源码，使用303/build-candidate.py；302源码／最终包保全，不重放旧安装器。305 R2因列表断言误判完整回退，R3修后成功；外部M=模块缺intree从未加载。安装／回归均终态，勿重放。

继续原厂S5K3M5模式调校、长焦独立硬件profile与控制延迟实测；补明亮场景AE正反向收敛、错误恢复、RGB统计／AWB、主前摄／其它模式与正式IQ。保持SoC／板级／sensor／IPA／模组数据分层。用户延期纯色／遮光保持。

构建卷按284/storage.py核backing，保留Rust环境；305树内同时构建CCI和sensor后恢复原输出。稳定#290及独立778模块、k132776／248备份保留。[操作边界](WORKING-BOUNDARIES.md)、[维护收据](reference/maintenance-2026-10-19/README.md)。上游接受与零补丁升级尚未证明。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('''继续多摄／骁龙ISP校准目标（active、未完成）。读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel305/README.md。

USB NCM／原密钥SSH恢复，但启动ID变化；仍#298、taint0。用305/host.py和新guard k305-geometry-r2，不沿用303/304旧guard。当前298 Image加305长焦单模块，SHA d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9；其余777模块／961包／50相机载荷保持。最新树camera305-sensor-kernel，samurai-geometry305／18b0a5a753e9363594f682049bf131169488c644，原298树保持。

长焦标准几何与libcamera属性通过。产品四摄18段272帧，再补中断／重开76帧，图和资源恢复，taint/fault0。仍RAW＋CPU ISP，303候选未安装。305 R2回退、R3安装／采集均终态，勿重放。

SDK work/libcamera299-inline仍303源码；上一启动硬件AE只验证低照度上限，目标亮度收敛待验。304 EEPROM解码不是完整校验，未应用个体值。继续原厂长焦调校、独立硬件profile和延迟实测，补RGB统计／AWB、多摄／模式、正式IQ，保持分层。旧GPU、modem、SSC问题仍开放。
''')
banner='305（2026-10-19）：USB恢复，启动ID变化后重新建立#298基线。仅长焦模块更新，标准几何及产品四摄348帧回归通过，taint/fault0；产品仍RAW＋CPU ISP，完整校准目标active、未完成。'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/name;p.write_text(banner+'[305当前事实]('+prefix+'reference/kernel305/README.md)。以下按历史阅读。\n\n'+p.read_text())
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=json.loads(p.read_text());d.update(stage=305,
  previous_lock_archive=prefix+'archive/camera-before305-2026-10-19/'+name,
  final_health_evidence=prefix+'reference/kernel305/final-health-validation.json',
  current_camera_evidence=prefix+'reference/kernel305/README.md',
  current_boot_evidence=prefix+'reference/kernel305/current-boot-preflight-validation.json',
  current_boot_guard_stage=305,current_boot_guard_path='/var/lib/samurai/k305-geometry-r2/boot-id-private.txt',
  current_boot_usb_original_key_verified=True,current_boot_changed_since_303=True,
  current_boot_optical_scene_retest_pending=True,
  actual_kernel_image_stage=298,actual_image_source_commit=commit['base_commit'],
  current_sensor_module_stage=305,sensor_module_geometry_only_update=True,
  current_sensor_module_sha256=commit['deployed_sensor_module_sha256'],
  current_sensor_source_sha256=commit['source_sha256'],current_sensor_source_commit=commit['commit'],
  current_sensor_source_tree=commit['tree'],maintained_branch=commit['branch'],maintained_commit=commit['commit'],
  source_worktree_branch=commit['branch'],source_worktree_commit=commit['commit'],
  source_worktree_is_undeployed_candidate=False,candidate_source_clean=True,
  kernel_source_commit=commit['commit'],kernel_source_branch=commit['branch'],
  candidate_kernel_source_commit=commit['commit'],candidate_kernel_source_branch=commit['branch'],
  source_and_deployment_split='298 complete Image; 305 sensor-only module; other777 unchanged',
  complete_kernel_image_and_modules_deployed=False,complete_new_kernel_image_and_modules_deployed=False,
  full_kernel_rebuild_with305_sensor_pending=True,only_s5k3m5_module_changed=True,other777_modules_preserved=True,
  current_product_four_camera_regression_frames=348,
  current_product_four_camera_regression_evidence=prefix+'reference/kernel305/four-camera-regression-validation.json',
  interrupt_restoration_evidence=prefix+'reference/kernel305/interrupt-restoration-validation.json',
  s5k3m5_geometry_evidence=prefix+'reference/kernel305/geometry-install-r3-validation.json',
  module_build_evidence=prefix+'reference/kernel305/kernel-build-validation.json',
  candidate_source_evidence=prefix+'reference/kernel305/kernel-commit-validation.json',
  candidate_runtime_restoration_evidence=prefix+'reference/kernel305/interrupt-restoration-validation.json',
  candidate_ae_evidence_from_prior_boot=True,phone_current_boot_not_reverified=False,goal_complete=False,
  current_adaptation_goal_status='active')
 if 's5k3m5_source_sha256' in d:d['s5k3m5_source_sha256']=commit['source_sha256']
 if 'deployed_camera_modules' in d:d['deployed_camera_modules']=health['modules']
 if 'maintenance_handoff' in d:d['maintenance_handoff']['historical_record_not_current_goal_status']=True
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'DOCS-INDEX.md';s=p.read_text();anchor='[304原厂EEPROM布局](reference/kernel304/README.md)';assert s.count(anchor)==1
p.write_text(s.replace(anchor,'[305长焦几何与四摄回归](reference/kernel305/README.md)、'+anchor))
(ROOT/'sessions/303-hardware-ae-candidate-and-joint-latch-preparation.md').write_text('''# 303：硬件AE与联合控制的实机验证

候选复用通用libipa AGC。上一#298启动实际完成联合恒EV480帧、硬件AE隔离／签名线程960帧，17生效revision、34写入和81可辨响应域同帧核对。低照度达到传感器上限，目标亮度收敛未验证；固定WB、其它模式及完整IQ待办。主机DSO／线程合成1440帧另列。

[来源、实机、保留失败和边界](../reference/kernel303/README.md)。305重连后启动ID已变，当前用305新guard；303候选未安装，产品RAW＋CPU ISP。[当前部署](../reference/kernel305/README.md)。
''')
(ROOT/'sessions/305-s5k3m5-selection-geometry-and-four-camera-regression.md').write_text('# 305：长焦标准几何与四摄回归\n\n'+banner+'\n\n[来源、sensor补丁、构建／安装、回退与边界](../reference/kernel305/README.md)。当前为298 Image加305单模块，本阶段无刷写或重启。18段272帧和独立中断恢复76帧分列，不冒充硬件IPA校准。\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
report=dict(stage=305,latest_sensor_source_commit=commit['commit'],actual_image_stage=298,
 usb_restored=True,new_boot_guard_recorded=True,source_deployment_split_recorded=True,
 historical303_session_corrected=True,goal_complete=False)
(HERE/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
