"""Reconcile the actual SRAM initialization fix and its limited acceptance scope."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];load=lambda p:json.loads(p.read_text())
health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json');source=load(HERE/'source-validation.json');fix=load(HERE/'startup-fix-validation.json')
assert health['kernel_build']==296 and health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert fix['all_seven_startup_or_late_packets_valid'] and fix['hardware_image_frames']==216 and fix['hardware_statistics_packets']==198
assert load(HERE/'statistics-pixel-validation.json')['passed'] and load(HERE/'statistics-r2-pixel-validation.json')['passed']
assert load(HERE/'optical-statistics-validation.json')['all_packets_valid']
assert load(HERE/'four-camera-regression-validation.json')['passed'] and load(HERE/'four-camera-regression-validation.json')['frames']==244
assert load(HERE/'stats-pixel-validation.json')['all_phase_color_contracts_passed'] and load(HERE/'frame-association-validation.json')['exact_frame_association_proven']
TREE='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',TREE,*a],text=True).strip()
assert git('rev-parse','HEAD')==source['commit'] and not git('status','--porcelain')
(HERE/'combined-stats-from293.patch').write_bytes(subprocess.check_output(['git','-C',TREE,'diff','1aa1955077c977b611c722eca0bc467c3bf052ed..HEAD','--','drivers/media/platform/qcom/camss']))
archive='archive/camera-before296-2026-10-19';assert load(ROOT/archive/'manifest.json')['prior_documented_stage']==295
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=load(p)
d.update(stage=296,maintained_branch=source['branch'],maintained_commit=source['commit'],actual_kernel_image_stage=296,actual_kernel_release=package['release'],module_count=778,
 deployed_camera_modules=health['modules'],current_boot_evidence='../../../reference/kernel296/postboot-identity-validation.json',full_kernel_candidate_evidence='../../../reference/kernel296/boot-candidate-build-validation.json',
 previous_lock_archive='../../../'+archive+'/linux-port/camera/kernel/source-lock.json',source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],source_worktree_is_undeployed_candidate=False,
 candidate_source_evidence='../../../reference/kernel296/source-validation.json',final_health_evidence='../../../reference/kernel296/final-health-validation.json',standard_wb_params_evidence='../../../reference/kernel296/stats-pixel-validation.json',
 standard_wb_frame_association_evidence='../../../reference/kernel296/frame-association-validation.json',ssc_default_start_failed=False,hardware_isp_pipeline_and_statistics_still_incomplete=True,
 bhist_steady_roi_evidence='../../../reference/kernel296/statistics-pixel-validation.json',first_statistics_packet_invalid=False,statistics_ready_for_automatic_exposure=False,
 bhist_sram_initialization_evidence='../../../reference/kernel296/startup-fix-validation.json')
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=load(p)
d.update(stage=296,current_boot_guard_stage=296,kernel_image_stage=296,kernel_release=package['release'],kernel_modules=health['modules'],kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],
 candidate_kernel_source_commit=source['commit'],candidate_kernel_source_branch=source['branch'],image_sha256=package['image_sha256'],logdump_sha256=package['logdump_sha256'],kernel_config_sha256=build['artifacts']['.config']['sha256'],
 guard_path='/var/lib/samurai/k296-work/boot-id-private.txt',current_camera_evidence='../../reference/kernel296/README.md',final_health_evidence='../../reference/kernel296/final-health-validation.json',
 previous_lock_archive='../../'+archive+'/linux-port/camera/deployment-lock.json',candidate_kernel_receipt='../../reference/kernel296/boot-candidate-build-validation.json',planned_boot_transition_evidence='../../reference/kernel296/postboot-identity-validation.json',
 current_stack_four_camera_regression='../../reference/kernel296/four-camera-regression-validation.json',current_boot_actual_capture_validation_pending=False,current_boot_optical_scene_retest_pending=False,
 candidate_kernel_deployed=True,ssc_boot_start_failed=False,sensor_startup_fresh_boot_passed=True,sensor_startup_fresh_boot_validation_pending=False,desktop_temporary_nodeps_restore=False,
 automatic_rotation_currently_available=True,whole_system_healthy=False,checked_runtime_healthy=True,
 spectra_hardware_image_processing_supported_scope='Experimental physical CSI FULL NV12, WB and initialized BHIST including startup; apps remain RAW plus CPU ISP; strict SOF, BLC/IPA/full IQ incomplete',
 standard_wb_parameters_verified=True,standard_wb_parameters_evidence='../../reference/kernel296/stats-pixel-validation.json',standard_wb_frame_association_evidence='../../reference/kernel296/frame-association-validation.json',
 physical_scene_exposure_response_evidence='../../reference/kernel296/optical-pixel-validation.json',physical_scene_recognizable_but_full_iq_unverified=True,current_stack_visual_scene_review_pending=False,
 hardware_isp_user_space_params_stats_pipeline_ipa_still_incomplete=True,hardware_isp_statistics_and_ipa_incomplete=True,
 standard_bhist_steady_frames_verified=True,standard_bhist_evidence='../../reference/kernel296/statistics-pixel-validation.json',standard_bhist_full_acceptance_passed=False,
 first_statistics_packet_invalid=False,standard_bhist_startup_acceptance_passed=True,statistics_ready_for_automatic_exposure=False,
 bhist_sram_initialization_evidence='../../reference/kernel296/startup-fix-validation.json',physical_scene_bhist_evidence='../../reference/kernel296/optical-statistics-validation.json',
 previous295_778_modules_preserved=True,layering_and_upgrade_evidence='../../reference/kernel296/layering-validation.json',
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel296 AF search not retested; Continuous and distance calibration incomplete')
procs={r['comm']:r for r in health['processes']};sv=d['system_services']
sv.update(stage=296,new_processes=[dict(name=r['comm'],pid=r['pid'],start_ticks=r['start_ticks']) for r in health['processes'] if r['comm'] in ['pipewire','wireplumber']],
 phoc_pid=procs['phoc']['pid'],phosh_pid=procs['phosh']['pid'],current_manifest='/var/lib/samurai/k296-services-verified-private.json',ssc_running=True,temporary_nodeps_desktop_start=False,physical_rotation_retest_pending=True)
p.write_text(json.dumps(d,indent=2)+'\n')
text=f'''# Realme X2 Pro 当前检查点

2026-10-19：[296统计SRAM/首包修复](reference/kernel296/README.md)、[295首包真实缺陷](reference/kernel295/README.md)、[294零计数失败](reference/kernel294/README.md)。多摄/骁龙ISP目标active；统计SOF关联、BLC/IPA、产品硬件pipeline和完整画质未完成。

## 当前部署与启动身份

现机 **#296**、`{package['release']}`，samurai-stats296／{source['commit']}。完整Image及独立778模块已部署读回，加载build-id匹配；boot276、DTB、原厂固件、961包/50相机载荷保持，libcamera r24/config-r19、PW/SPA/Gst1.6.9-r3保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA {package['image_sha256']}；logdump {package['logdump_sha256']}；boot {package['firmware_boot_preserved_sha256']}；DTB {package['dtb_sha256']}。

运输reference/kernel296/host.py、原SSH严格密钥、新端点及 `/var/lib/samurai/k296-work/boot-id-private.txt`；旧295等guard不用于当前启动。按driver/entity发现，本次main8-0010/lens8-0072、tele6-002d、wide9-0010、front7-0010。Phoc3670/Phosh3891/PW5256/WP5270，start_ticks见[最终状态](reference/kernel296/final-health-validation.json)。

## 已验证与当前缺陷

- **295首包随机/残留计数已在所测场景修复**。两个仓库固定版本含同一生成寄存器头blob，确认BHIST RAM选择0x3a、CGC bit4、DMI0xc24/0xc28/0xc30。SoC驱动在像素到来前清零1024槽并恢复共享DMI/时钟状态，无板级DT/固件/UAPI/产品包改动。旧函数负对照失败，新实际函数ASan/UBSan、10万ROI及buffer生命周期测试通过。
- 本轮硬件216图像/198统计：长焦99/90→广角18/18→切回长焦99/90；7个初始/图像重开/统计晚启动首包全部精确。长焦全幅820560、半幅410280、最小ROI2；广角全部18包人口499392。第二轮停统计时重开参数改4×2，再晚启统计首包为新ROI的2，未出现旧全幅计数。[汇总与范围](reference/kernel296/startup-fix-validation.json)
- 无丢弃首包、无用户空间MMIO写入、无CPU伪造直方图。严格图像—统计SOF、队列饥饿/合并IRQ、多参数Request API、其它模式/长稳未验收，ready_for_automatic_exposure仍false。下一步统计帧关联、BLC、硬件pipeline/IPA。
- WB首轮11阶段颜色误差<1.235、10非法包、7完成，五次颜色变化首帧与参数序号一致；第二轮额外停统计时重开参数，共8完成，不等于Request API验收。[颜色](reference/kernel296/stats-pixel-validation.json)
- 广角实景曝光500→3000→500：Y75.0741→93.3138→75.0732，hist均值bin71.9740→113.7148→71.9721；已查看私人预览，结构可辨仍暗绿，BLC/AWB/IQ未校准。原产品RAW＋CPU ISP四摄18段244帧通过，主摄SIGINT40/重开12。
- 当前SSC/桌面/SensorProxy默认成功，未nodeps/重试；#293 EPERM偶发根因仍未关闭。物理旋转/本启动AF未重测。778模块/50载荷/961包核对，camera/lens/CCI/CAMSS suspended，九rails/共享IO关闭，MCLK/CCI clocks0，fault0/taint0/pstore空；Wi-Fi/HCI、modem/adsp/slpi正常。checked_runtime_healthy=true仅限所列检查；GPU默认故障、旧modem watchdog、整机长稳未结案，whole_system_healthy=false。

## 源码回退与下一步

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel` 干净samurai-stats296／f86906688666c0ebaabaeeec96c28d5741257f50；295及更早分支保留，本轮1个本地提交未推送、未证明上游接受。完整构建153.08秒、五阶段诊断0、40CAMSS组件Werror；778模块与3嵌入BT模块一致。输出/mnt/samurai-full282/build，先用284/storage.py核backing并挂载；config SHA {build['artifacts']['.config']['sha256']}，input-initramfs296/modules296。295六产物已保存私人kernel296/completed-boot295。

后续统计与图像SOF关联、BLC、libcamera硬件pipeline/IPA，继续主/前摄硬件路径、模组调校、AF Continuous/距离映射、Shine OV02A1B、GUI录像及长稳。原厂DT提接线、内核/HAL提协议，算法与模组数据放IPA；不套其它手机调校或单场景黑电平。

仍以7.3rc6为基础，53本地提交/177改动文件；libcamera配方28补丁（含发行版既有）、PW另6项目补丁，三个ignore_unused仍在。已有底层收敛，尚不能承诺主线内核/关键包更新零或最小补丁，缺上游接受、跨版本与完整rootfs/冷启/PM验收。[分层审计](reference/kernel296/layering-validation.json)

稳定回退首选#290 logdump SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及原778模块；295/294/293/292/288各778、k132776、未启动292R1独立778及整机248备份保留，未做回退往返。本轮一次切换和全部构建/采集已终态，勿盲目重放。私人目录E:/edk2-samurai-out/kernel296，像素/参考载荷/校准/密钥不公开。[操作边界](WORKING-BOUNDARIES.md)
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();old='[295有效统计与首包缺陷](reference/kernel295/README.md)';assert old in s
s=s.replace(old,'[296统计SRAM/首包修复](reference/kernel296/README.md)、[295首包缺陷](reference/kernel295/README.md)');assert len(s.encode())<=10000;p.write_text(s)
banner='296（2026-10-19）：现机#296/778模块，SoC驱动补BHIST SRAM初始化；216硬件图像/198统计、7个启动/重开/晚启动首包通过，含晚启前改最小ROI。无丢弃首包或用户空间MMIO写入；四摄RAW＋CPU ISP18段244帧通过。统计SOF关联、BLC/IPA、主/前摄硬件路径和完整画质仍未完成，目标active。'
for name,link in [('linux-port/camera/README.md','../../reference/kernel296/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel296/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel296/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel296/README.md')]:
 p=ROOT/name;p.write_text(banner+f'[296当前证据]({link})。以下旧阶段按历史阅读。\n\n'+p.read_text())
p=ROOT/'sessions/296-vfe175-bhist-sram-initialization.md';assert not p.exists();p.write_text('# 296：VFE175统计SRAM初始化与首包修复\n\n'+banner+'\n\n[来源、实际结果、范围与部署](../reference/kernel296/README.md)。295失败收据保留；所有首包检查直接验收，不丢弃或伪造。\n')
manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [ROOT/'NEXT-SESSION.md',ROOT/'DOCS-INDEX.md',ROOT/'linux-port/camera/deployment-lock.json',ROOT/'linux-port/camera/kernel/source-lock.json']}
(HERE/'checkpoint-validation.json').write_text(json.dumps(dict(stage=296,current_kernel_build=296,source=source['commit'],camera_transport_and_resource_tests_passed=True,bhist_initialization_passed=True,full_statistics_sof_and_pipeline_acceptance_passed=False,whole_system_healthy=False,goal_active=True,files=manifest),indent=2)+'\n')
print(json.dumps(dict(stage=296,next_bytes=len(text.encode()),index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,goal='active',first_statistics_initialization_verified=True),indent=2))
