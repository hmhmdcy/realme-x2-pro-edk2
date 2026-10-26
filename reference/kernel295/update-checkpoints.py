"""Record actual k295 and preserve failed zero-count/startup-statistics evidence."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text())
health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json');source=load(HERE/'source-validation.json')
stats=load(HERE/'statistics-pixel-validation.json');scene=load(HERE/'optical-statistics-validation.json');regression=load(HERE/'four-camera-regression-validation.json');layer=load(HERE/'layering-validation.json')
assert health['kernel_build']==295 and health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert stats['steady_roi_contracts_passed'] and not stats['passed'] and not stats['startup_statistics_valid']
assert scene['stable_exposure_response_and_return_passed'] and not scene['all_packets_valid']
assert regression['passed'] and regression['frames']==237 and load(HERE/'stats-pixel-validation.json')['all_phase_color_contracts_passed']
assert load(HERE/'frame-association-validation.json')['exact_frame_association_proven']
assert load(HERE/'optical-pixel-validation.json')['exposure_response_and_return_passed'] and load(HERE/'optical-review.json')['recognizable_scene_edges_and_structures']
TREE='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',TREE,*a],text=True).strip()
assert git('rev-parse','HEAD')==source['commit'] and not git('status','--porcelain')
archive='archive/camera-before294-2026-10-19';assert (ROOT/archive/'manifest.json').is_file()
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=load(p)
d.update(stage=295,maintained_branch=source['branch'],maintained_commit=source['commit'],actual_kernel_image_stage=295,actual_kernel_release=package['release'],module_count=778,
 deployed_camera_modules=health['modules'],current_boot_evidence='../../../reference/kernel295/postboot-identity-validation.json',full_kernel_candidate_evidence='../../../reference/kernel295/boot-candidate-build-validation.json',
 previous_lock_archive='../../../'+archive+'/linux-port/camera/kernel/source-lock.json',source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],source_worktree_is_undeployed_candidate=False,
 candidate_source_evidence='../../../reference/kernel295/source-validation.json',final_health_evidence='../../../reference/kernel295/final-health-validation.json',standard_wb_params_evidence='../../../reference/kernel295/stats-pixel-validation.json',
 standard_wb_frame_association_evidence='../../../reference/kernel295/frame-association-validation.json',ssc_default_start_failed=False,hardware_isp_pipeline_and_statistics_still_incomplete=True,
 bhist_steady_roi_evidence='../../../reference/kernel295/statistics-pixel-validation.json',first_statistics_packet_invalid=True,statistics_ready_for_automatic_exposure=False)
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=load(p)
d.update(stage=295,current_boot_guard_stage=295,kernel_image_stage=295,kernel_release=package['release'],kernel_modules=health['modules'],kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],
 candidate_kernel_source_commit=source['commit'],candidate_kernel_source_branch=source['branch'],image_sha256=package['image_sha256'],logdump_sha256=package['logdump_sha256'],kernel_config_sha256=build['artifacts']['.config']['sha256'],
 guard_path='/var/lib/samurai/k295-work/boot-id-private.txt',current_camera_evidence='../../reference/kernel295/README.md',final_health_evidence='../../reference/kernel295/final-health-validation.json',
 previous_lock_archive='../../'+archive+'/linux-port/camera/deployment-lock.json',candidate_kernel_receipt='../../reference/kernel295/boot-candidate-build-validation.json',planned_boot_transition_evidence='../../reference/kernel295/postboot-identity-validation.json',
 current_stack_four_camera_regression='../../reference/kernel295/four-camera-regression-validation.json',current_boot_actual_capture_validation_pending=False,current_boot_optical_scene_retest_pending=False,
 candidate_kernel_deployed=True,ssc_boot_start_failed=False,sensor_startup_fresh_boot_passed=True,sensor_startup_fresh_boot_validation_pending=False,desktop_temporary_nodeps_restore=False,
 automatic_rotation_currently_available=True,whole_system_healthy=False,checked_runtime_healthy=True,
 previous_ssc_failure_evidence='../../reference/kernel293/ssc-failure-validation.json',ssc_failure_evidence=None,desktop_recovery_evidence=None,
 spectra_hardware_image_processing_supported=True,spectra_hardware_image_processing_supported_scope='Experimental physical CSI FULL NV12, WB and steady BHIST; invalid first stats packet; product apps remain RAW plus CPU ISP; BLC/IPA/full IQ incomplete',
 standard_wb_parameters_verified=True,standard_wb_parameters_evidence='../../reference/kernel295/stats-pixel-validation.json',standard_wb_frame_association_evidence='../../reference/kernel295/frame-association-validation.json',
 physical_scene_exposure_response_evidence='../../reference/kernel295/optical-pixel-validation.json',physical_scene_recognizable_but_full_iq_unverified=True,current_stack_visual_scene_review_pending=False,
 hardware_isp_user_space_params_stats_pipeline_ipa_still_incomplete=True,hardware_isp_statistics_and_ipa_incomplete=True,
 standard_bhist_steady_frames_verified=True,standard_bhist_evidence='../../reference/kernel295/statistics-pixel-validation.json',standard_bhist_full_acceptance_passed=False,
 first_statistics_packet_invalid=True,statistics_ready_for_automatic_exposure=False,physical_scene_bhist_evidence='../../reference/kernel295/optical-statistics-validation.json',
 previous290_778_modules_preserved=True,previous292_778_modules_preserved=True,previous293_778_modules_preserved=True,previous294_778_modules_preserved=True,unbooted292_r1_778_modules_preserved=True,
 layering_and_upgrade_evidence='../../reference/kernel295/layering-validation.json',
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel295 AF search not retested; Continuous and distance calibration incomplete')
sv=d['system_services'];processes={r['comm']:r for r in health['processes']}
sv.update(stage=295,new_processes=[dict(name=r['comm'],pid=r['pid'],start_ticks=r['start_ticks']) for r in health['processes'] if r['comm'] in ['pipewire','wireplumber']],
 phoc_pid=processes['phoc']['pid'],phosh_pid=processes['phosh']['pid'],current_manifest='/var/lib/samurai/k295-services-verified-private.json',ssc_running=True,temporary_nodeps_desktop_start=False,physical_rotation_retest_pending=True)
p.write_text(json.dumps(d,indent=2)+'\n')
text=f'''# Realme X2 Pro 当前检查点

2026-10-19：[295有效BHIST与首包缺陷](reference/kernel295/README.md)、[294零计数失败与metadata修复](reference/kernel294/README.md)。多摄/骁龙ISP目标active，统计首包、BLC/IPA、产品硬件pipeline和完整画质未完成。

## 当前部署与启动身份

现机 **#295**、`{package['release']}`；samurai-stats295／{source['commit']}。完整Image及独立778模块已部署读回；boot276、DTB、原厂固件、961包和50相机载荷保持，libcamera r24/config-r19、PW/SPA/Gst1.6.9-r3保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA {package['image_sha256']}；logdump {package['logdump_sha256']}；boot {package['firmware_boot_preserved_sha256']}；DTB {package['dtb_sha256']}。

运输reference/kernel295/host.py、原SSH严格密钥、新端点及 `/var/lib/samurai/k295-work/boot-id-private.txt`。旧294/293 guard不再用于当前启动；按driver/entity发现设备。本次main6-0010/lens6-0072、tele8-002d、wide7-0010、front9-0010。Phoc4052/Phosh4312/PW5724/WP5736，start_ticks见[最终状态](reference/kernel295/final-health-validation.json)。

## 已验证与当前缺陷

- 294通用metadata DMA启停、注册错误回收、图像重启保留统计buffer、部分输出启动失败回收；实际旧函数负对照失败，修复后ASan/UBSan及30处注册故障注入通过。295将误认的RS bit5更正为BHIST bit4，独立端口枚举/原厂HAL指令证明并保留错误解释。修复在SoC/公共驱动，无新增板级DT/固件/产品包改动。
- #295长焦99图像/90统计包，稳定ROI全幅820560/半幅410280/最小2精确匹配；统计独立启停、图像重启后三buffer均出现。标准接口，无用户空间MMIO写入。WB11阶段颜色误差<1.235，10非法包、7完成，五次颜色变化首帧与参数序号一致；不等于Request API或统计SOF严格对应。
- **统计首包不合格**：长焦启动17567538901、图像重开1160356（期望820560）；广角首包17552007722（期望499392），却返回正常flag；之后稳定帧正确。当前统计验收passed=false、ready_for_automatic_exposure=false。[统计缺陷](reference/kernel295/statistics-pixel-validation.json)
- 用户已确认后摄无遮挡；广角18图像/18统计，曝光500→3000→500时Y74.8023→92.1108→74.8024，稳定hist均值bin71.4364→110.6519→71.4400，人口499392；预览能辨结构仍暗绿，BLC/AWB/IQ未校准。[实景统计](reference/kernel295/optical-statistics-validation.json)
- 原产品RAW＋CPU ISP四摄18段237帧通过，主摄SIGINT33/重开12。当前SSC/桌面/SensorProxy默认成功，未nodeps/重试；294同样成功，但293 EPERM/exit4偶发根因未关闭。物理旋转及本启动AF未重测。
- 778模块/50载荷/961包核对，camera/lens/CCI/CAMSS suspended，九rails/共享IO关闭，MCLK/CCI clocks0，fault0/taint0/pstore空；Wi-Fi/HCI和modem/adsp/slpi正常。checked_runtime_healthy=true仅覆盖所列检查，whole_system_healthy=false，GPU默认故障/旧modem watchdog和整机长稳未结案。

## 源码回退与下一步

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel` 干净samurai-stats295／d249946aefa1a01d99fd5484825a4458423b7348；293/294父分支保留，4个新增本地提交未推送、未证明上游接受。完整295构建148.55秒/五阶段诊断0、40CAMSS组件Werror、778模块及3嵌入BT模块一致。输出/mnt/samurai-full282/build，先用284/storage.py核backing并挂载；config SHA {build['artifacts']['.config']['sha256']}，input-initramfs295/modules295。294 R2六产物已保存在私人kernel295/completed-boot294-r2。

先修统计RAM初始化/首份有效数据时机及错误标记，再做统计SOF关联、BLC、libcamera硬件pipeline/IPA。继续主/前摄硬件路径、模组校准、AF Continuous/距离映射、Shine OV02A1B、GUI录像及长稳。原厂DT提接线、内核/HAL提协议，画质须匹配模组与本机校准；不套其它手机调校或单场景黑电平。

主线基础仍7.3rc6，当前52本地提交/177改动文件；libcamera配方28补丁（含发行版既有）、PW另6项目补丁，三个ignore_unused仍在。已有底层收敛，**尚不能承诺主线内核/关键包更新零或最小补丁**；仍缺上游接受、跨版本与完整rootfs/冷启/PM验收。[分层审计](reference/kernel295/layering-validation.json)

稳定回退首选#290 logdump SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及原778模块；294/293/292/288各778、k132776、未启动292R1独立778及整机248备份保留。未做回退往返。本轮两次切换及所有构建/采集已终态，勿盲目重放。私人目录E:/edk2-samurai-out/kernel294、kernel295，像素/原厂载荷/校准/密钥不公开。[操作边界](WORKING-BOUNDARIES.md)
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();old='[293标准WB参数/实景及SSC失败](reference/kernel293/README.md)、[292部署后FULL回归](reference/kernel292/README.md)';assert old in s
s=s.replace(old,'[295有效统计与首包缺陷](reference/kernel295/README.md)、[294零计数及metadata修复](reference/kernel294/README.md)、[293WB/实景](reference/kernel293/README.md)');assert len(s.encode())<=10000;p.write_text(s)
banner='295（2026-10-19）：现机#295/778模块，BHIST稳定帧全/半/最小ROI通过，广角实景统计随曝光变化；启动/图像重开首个统计包仍异常，统计完整验收未通过，暂不交AE/IPA。WB99帧、四摄RAW＋CPU ISP18段237帧通过；当前SSC/桌面默认成功，293偶发失败根因未关闭，BLC/IPA/完整画质未完成。'
for name,link in [('linux-port/camera/README.md','../../reference/kernel295/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel295/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel295/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel295/README.md')]:
 p=ROOT/name;p.write_text(banner+f'[295当前证据]({link})。以下旧阶段按历史阅读。\n\n'+p.read_text())
p=ROOT/'sessions/295-vfe175-bhist-counts-and-startup-validity.md';assert not p.exists();p.write_text('# 295：VFE175有效BHIST计数与首包有效性缺陷\n\n'+banner+'\n\n[完整来源、范围和当前部署](../reference/kernel295/README.md)。统计稳定响应通过并保留首包反例；目标active，未标记完成。\n')
manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [ROOT/'NEXT-SESSION.md',ROOT/'DOCS-INDEX.md',ROOT/'linux-port/camera/deployment-lock.json',ROOT/'linux-port/camera/kernel/source-lock.json']}
(HERE/'checkpoint-validation.json').write_text(json.dumps(dict(stage=295,current_kernel_build=295,source=source['commit'],camera_transport_and_resource_tests_passed=True,steady_statistics_passed=True,full_statistics_acceptance_passed=False,whole_system_healthy=False,goal_active=True,files=manifest),indent=2)+'\n')
print(json.dumps(dict(stage=295,next_bytes=len(text.encode()),index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,goal='active',first_statistics_packet_invalid=True),indent=2))
