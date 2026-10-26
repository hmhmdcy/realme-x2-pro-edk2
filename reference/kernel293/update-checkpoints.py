"""Reconcile current source, real deployment, passed camera tests and failed SSC startup."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text())
health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json');source=load(HERE/'source-validation.json')
assert health['kernel_build']==293 and health['camera_tests_and_resource_health_passed'] and not health['whole_system_healthy']
assert load(HERE/'wb-params-pixel-validation.json')['all_phase_color_contracts_passed'] and load(HERE/'frame-association-validation.json')['exact_frame_association_proven']
regression=load(HERE/'four-camera-regression-validation.json');assert regression['passed'] and regression['frames']==232
assert load(HERE/'optical-pixel-validation.json')['exposure_response_and_return_passed'] and load(HERE/'optical-review.json')['recognizable_scene_edges_and_structures']
TREE='/home/cy122/x2pro-linux/camera279-isp-kernel'
git=lambda *a:subprocess.check_output(['git','-C',TREE,*a],text=True).strip()
assert git('rev-parse','HEAD')==source['commit'] and not git('status','--porcelain')
(HERE/'combined-params-from290.patch').write_bytes(subprocess.check_output(['git','-C',TREE,'diff','15c8639d8badf5d4146bfd1b2c2fcb2460a137e5..HEAD','--','drivers/media/platform/qcom/camss']))
archive='archive/camera-before292-2026-10-19'
assert (ROOT/archive/'manifest.json').is_file()
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=load(p)
d.update(stage=293,maintained_branch=source['branch'],maintained_commit=source['commit'],actual_kernel_image_stage=293,actual_kernel_release=package['release'],module_count=778,
 deployed_camera_modules=health['modules'],current_boot_evidence='../../../reference/kernel293/postboot-identity-validation.json',full_kernel_candidate_evidence='../../../reference/kernel293/boot-candidate-build-validation.json',
 previous_lock_archive='../../../'+archive+'/linux-port/camera/kernel/source-lock.json',source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],source_worktree_is_undeployed_candidate=False,
 candidate_source_evidence='../../../reference/kernel293/source-validation.json',final_health_evidence='../../../reference/kernel293/final-health-validation.json',standard_wb_params_evidence='../../../reference/kernel293/wb-params-pixel-validation.json',
 standard_wb_frame_association_evidence='../../../reference/kernel293/frame-association-validation.json',ssc_default_start_failed=True,hardware_isp_pipeline_and_statistics_still_incomplete=True)
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=load(p)
d.update(stage=293,current_boot_guard_stage=293,kernel_image_stage=293,kernel_release=package['release'],kernel_modules=health['modules'],kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],
 candidate_kernel_source_commit=source['commit'],candidate_kernel_source_branch=source['branch'],image_sha256=package['image_sha256'],logdump_sha256=package['logdump_sha256'],kernel_config_sha256=build['artifacts']['.config']['sha256'],
 guard_path='/var/lib/samurai/k293-work/boot-id-private.txt',current_camera_evidence='../../reference/kernel293/README.md',final_health_evidence='../../reference/kernel293/final-health-validation.json',
 previous_lock_archive='../../'+archive+'/linux-port/camera/deployment-lock.json',candidate_kernel_receipt='../../reference/kernel293/boot-candidate-build-validation.json',planned_boot_transition_evidence='../../reference/kernel293/postboot-identity-validation.json',
 current_stack_four_camera_regression='../../reference/kernel293/four-camera-regression-validation.json',current_boot_actual_capture_validation_pending=False,current_boot_optical_scene_retest_pending=False,
 candidate_kernel_deployed=True,ssc_boot_start_failed=True,sensor_startup_fresh_boot_passed=False,sensor_startup_fresh_boot_validation_pending=False,desktop_temporary_nodeps_restore=True,
 automatic_rotation_currently_available=False,whole_system_healthy=False,ssc_failure_evidence='../../reference/kernel293/ssc-failure-validation.json',desktop_recovery_evidence='../../reference/kernel293/desktop-restore-validation.json',
 spectra_hardware_image_processing_supported=True,spectra_hardware_image_processing_supported_scope='Experimental physical CSI FULL NV12 and WB gains; product apps remain RAW plus CPU ISP; stats/BLC/IPA/full IQ incomplete',
 standard_wb_parameters_verified=True,standard_wb_parameters_evidence='../../reference/kernel293/wb-params-pixel-validation.json',standard_wb_frame_association_evidence='../../reference/kernel293/frame-association-validation.json',
 physical_scene_exposure_response_evidence='../../reference/kernel293/optical-pixel-validation.json',physical_scene_recognizable_but_full_iq_unverified=True,hardware_isp_user_space_params_stats_pipeline_ipa_still_incomplete=True,
 previous290_778_modules_preserved=True,previous292_778_modules_preserved=True,unbooted292_r1_778_modules_preserved=True,layering_and_upgrade_evidence='../../reference/kernel293/layering-validation.json',
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel293 AF search not retested; Continuous and distance calibration incomplete')
sv=d['system_services'];sv.update(stage=293,new_processes=[dict(name=r['comm'],pid=r['pid'],start_ticks=r['start_ticks']) for r in health['processes'] if r['comm'] in ['pipewire','wireplumber']],
 phoc_pid=5644,phosh_pid=5714,current_manifest='/var/lib/samurai/k293-services-verified-private.json',ssc_running=False,temporary_nodeps_desktop_start=True,physical_rotation_retest_pending=True)
p.write_text(json.dumps(d,indent=2)+'\n')
next_text=f'''# Realme X2 Pro 当前检查点

2026-10-19：[293标准WB参数/FULL修复及实景](reference/kernel293/README.md)、[292真实失败](reference/kernel292/README.md)。多摄及骁龙ISP目标active，统计/BLC/IPA、产品硬件pipeline和完整画质未完成。

## 当前部署与启动身份

现机 **#293**、`{package['release']}`，samurai-params293／{source['commit']}；完整Image和独立778模块已部署读回。boot276、DT、961包、libcamera r24/config-r19、PW/SPA/Gst1.6.9-r3及50相机载荷保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA {package['image_sha256']}；logdump {package['logdump_sha256']}；boot {package['firmware_boot_preserved_sha256']}；DTB {package['dtb_sha256']}。

运输用reference/kernel293/host.py、严格原SSH密钥、新端点及 `/var/lib/samurai/k293-work/boot-id-private.txt`。旧292/290guard不再用于当前操作。按实体/driver发现：本轮main8-0010/lens8-0072、tele6-002d、wide9-0010、front7-0010。Phoc5644/Phosh5714/PW7087/WP7089，start_ticks见[最终状态](reference/kernel293/final-health-validation.json)和手机k293-services-verified-private.json。

## 已验证与当前缺陷

- 292新增实际输出pad门控、VFE175零DMA参数节点及metadata link validator，但FULL原num_outputs==1校验遗漏，WB两次及实景均在QBUF EINVAL、0帧。媒体图/供电恢复，无新增fault；失败收据保留。293通用SoC修复允许可选零DMA参数输出，保留格式/client/plane/地址检查；旧实现负对照失败、新实际函数ASan/UBSan通过。
- #293长焦真实CSI→CSID175→VFE175 FULL：标准META_OUTPUT QCIP，10类非法包拒绝，7次参数完成，81帧九阶段。R/B/G四分之一、DISABLE、bypass更新、ENABLE、停参数流和重开默认值均与独立RAW色块参考匹配，最大通道误差<1.235；QBUF后改用户buffer不影响内核快照。[像素](reference/kernel293/wb-params-pixel-validation.json)
- 五次可观察变化首帧10/19/28/37/55与PARAM_DQ sequence精确相同；仅单参数更新/S5K3M5图案/320×240，不等同request API或完整pipeline。[帧对应](reference/kernel293/frame-association-validation.json)
- 用户已确认后摄无遮挡；本轮广角无图案实景18帧Y均值74.230→89.303→74.230，私人预览有可辨识边缘/结构，仍偏暗偏绿，BLC/AWB/画质未校准。四摄18段232帧含SIGINT28/重开12通过，普通cam仍RAW＋CPU ISP。[实景](reference/kernel293/optical-pixel-validation.json)、[回归](reference/kernel293/four-camera-regression-validation.json)
- **本次SSC默认启动失败**：FastRPC attach EPERM/exit4、SLPI offline，SensorProxy/自动旋转不可用。已一次临时nodeps恢复桌面，永久依赖配置不变，未盲目重试SLPI；旧273同现象根因未明。[故障](reference/kernel293/ssc-failure-validation.json)、[恢复](reference/kernel293/desktop-restore-validation.json)
- 最终778模块/50载荷/961包核对，sensor/lens/CCI/CAMSS suspended，九rails/共享IO关闭，MCLK/CCI clocks0，fault0/taint0/pstore空；modem/adsp、Wi-Fi/HCI正常。此项不覆盖SSC失败，也不代表GPU默认故障/旧modem watchdog或整机长稳已结案。

## 源码回退与下一步

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel` 干净samurai-params293／1aa1955077c977b611c722eca0bc467c3bf052ed，父86c7b9d及290/288分支保留，四个新本地提交未推送/未证明上游接受。完整构建152.74秒/五阶段诊断0，39CAMSS组件Werror；配套778模块、3个嵌入BT模块一致。

输出/mnt/samurai-full282/build；先用284/storage.py核backing并挂载。config SHA {build['artifacts']['.config']['sha256']}，input-initramfs293/modules293。完整292 R2六产物已保存在私人kernel293/completed-boot292-r2；292 R1从未启动且778模块另存。所有本轮构建/切换/采集已终态，勿盲目重放。

下一步SSC attach根因、统计/BLC、libcamera硬件pipeline/IPA；补主/前摄硬件路径、模组校准、AF加速/Continuous/距离映射、Shine OV02A1B、GUI录像及长稳。278单次AF证据不晋升为#293重测。原厂接线归DT、协议归公共驱动、调校归IPA/模组数据，不硬编码单场景黑电平。

主线基础仍7.3rc6；当前树相对base有48本地提交/175改动文件，libcamera配方28补丁（含发行版既有补丁）、PW另6项目补丁，三项ignore_unused仍在。存在底层收敛，**尚不能承诺主线内核及关键包更新零/最小补丁**；需上游接受、跨版本及完整rootfs/冷启/PM验收。[分层审计](reference/kernel293/layering-validation.json)

即时稳定回退首选#290 logdump，SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及原778模块；292/288各778、k132776、183镜像和整机248备份保留，未做回退往返。私人资料E:/edk2-samurai-out/kernel292和kernel293，不公开像素/校准/密钥。[操作边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)
'''
assert len(next_text.encode())<=6500,len(next_text.encode())
(ROOT/'NEXT-SESSION.md').write_text(next_text)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();s=s.replace('[291两sensor硬件FULL/RAW色彩对照](reference/kernel291/README.md)、[290完整部署](reference/kernel290/README.md)','[293标准WB参数/实景及SSC失败](reference/kernel293/README.md)、[292部署后FULL回归](reference/kernel292/README.md)、[291实体色彩](reference/kernel291/README.md)');assert len(s.encode())<=10000;p.write_text(s)
banner='293（2026-10-19）：实际#293/778模块，标准WB参数81帧/10非法包/7完成/九阶段色彩及五次帧号对照通过；广角实景18帧可辨结构，四摄RAW＋CPU ISP 18段232帧通过。SSC默认FastRPC attach EPERM/exit4、SLPI offline，已一次临时nodeps恢复桌面，自动旋转不可用；统计/BLC/IPA及完整画质未完成。'
for name,link in [('linux-port/camera/README.md','../../reference/kernel293/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel293/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel293/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel293/README.md')]:
 p=ROOT/name;p.write_text(banner+f'[293当前证据]({link})。以下旧阶段按历史阅读。\n\n'+p.read_text())
session=ROOT/'sessions/293-vfe175-standard-white-balance-and-full-regression.md';assert not session.exists();session.write_text('# 293：VFE175标准白平衡参数及FULL回归修复\n\n'+banner+'\n\n[完整来源、提交、实际结果与限制](../reference/kernel293/README.md)。前置292真实失败、两版镜像及模块保留；现机boot276、DT和用户态包保持。目标active，未标记完成。\n')
manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [ROOT/'NEXT-SESSION.md',ROOT/'DOCS-INDEX.md',ROOT/'linux-port/camera/deployment-lock.json',ROOT/'linux-port/camera/kernel/source-lock.json']}
(HERE/'checkpoint-validation.json').write_text(json.dumps(dict(stage=293,current_kernel_build=293,source=source['commit'],camera_tests_passed=True,whole_system_healthy=False,ssc_failure_preserved=True,goal_active=True,files=manifest),indent=2)+'\n')
print(json.dumps(dict(stage=293,next_bytes=len(next_text.encode()),index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,current_kernel=293,goal='active',ssc_failed=True),indent=2))
