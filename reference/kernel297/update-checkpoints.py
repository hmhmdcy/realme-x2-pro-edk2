"""Promote only the tested k297 deployment and preserve its acceptance limits."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text())
health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json');source=load(HERE/'source-validation.json');sof=load(HERE/'sof-association-validation.json')
assert health['kernel_build']==297 and health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert sof['shared_sof_contract_passed'] and sof['all_five_observable_roi_transitions_exact'] and sof['statistics_starvation_sequence_gap']==7
assert load(HERE/'stats-r2-capture-validation.json')['passed'] and not load(HERE/'stats-capture-validation.json')['passed']
assert load(HERE/'four-camera-regression-validation.json')['passed'] and load(HERE/'four-camera-regression-validation.json')['frames']==232
assert load(HERE/'stats-pixel-validation.json')['all_phase_color_contracts_passed'] and load(HERE/'optical-statistics-validation.json')['all_packets_valid']
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')==source['commit'] and not git('status','--porcelain')
archive='archive/camera-before297-2026-10-19';assert load(ROOT/archive/'manifest.json')['prior_documented_stage']==296
def advance_existing_references(d):
 for key,value in d.items():
  if isinstance(value,str) and '/reference/kernel296/' in value:
   name=value.rsplit('/',1)[-1]
   if (HERE/name).is_file():d[key]=value.replace('/reference/kernel296/','/reference/kernel297/')
 return d
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=advance_existing_references(load(p))
d.update(stage=297,maintained_branch=source['branch'],maintained_commit=source['commit'],actual_kernel_image_stage=297,actual_kernel_release=package['release'],module_count=778,
 deployed_camera_modules=health['modules'],previous_lock_archive='../../../'+archive+'/linux-port/camera/kernel/source-lock.json',
 source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],source_worktree_is_undeployed_candidate=False,
 bhist_steady_roi_evidence='../../../reference/kernel297/sof-association-validation.json',shared_sof_frame_association_verified_in_tested_scope=True,
 statistics_starvation_sequence_gaps_verified=True,full_statistics_sof_acceptance_passed=False,first_statistics_packet_invalid=False,statistics_ready_for_automatic_exposure=False)
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=advance_existing_references(load(p))
d.update(stage=297,current_boot_guard_stage=297,kernel_image_stage=297,kernel_release=package['release'],kernel_modules=health['modules'],
 kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],candidate_kernel_source_commit=source['commit'],candidate_kernel_source_branch=source['branch'],
 image_sha256=package['image_sha256'],logdump_sha256=package['logdump_sha256'],kernel_config_sha256=build['artifacts']['.config']['sha256'],
 guard_path='/var/lib/samurai/k297-work/boot-id-private.txt',previous_lock_archive='../../'+archive+'/linux-port/camera/deployment-lock.json',
 current_boot_actual_capture_validation_pending=False,current_boot_optical_scene_retest_pending=False,candidate_kernel_deployed=True,
 ssc_boot_start_failed=False,sensor_startup_fresh_boot_passed=True,sensor_startup_fresh_boot_validation_pending=False,desktop_temporary_nodeps_restore=False,
 automatic_rotation_currently_available=True,whole_system_healthy=False,checked_runtime_healthy=True,
 spectra_hardware_image_processing_supported_scope='Experimental physical CSI FULL NV12/WB/BHIST with shared SOF identity tested on tele and independent metadata restart/starvation; apps remain RAW plus CPU ISP; BLC/IPA/full IQ and broader SOF cases incomplete',
 standard_bhist_evidence='../../reference/kernel297/sof-association-validation.json',standard_bhist_full_acceptance_passed=False,
 standard_bhist_startup_acceptance_passed=True,first_statistics_packet_invalid=False,statistics_ready_for_automatic_exposure=False,
 shared_sof_frame_association_evidence='../../reference/kernel297/sof-association-validation.json',statistics_starvation_sequence_gaps_verified=True,
 previous296_778_modules_preserved=True,
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel297 AF search not retested; Continuous and distance calibration incomplete')
procs={r['comm']:r for r in health['processes']}
d['system_services'].update(stage=297,new_processes=[dict(name=r['comm'],pid=r['pid'],start_ticks=r['start_ticks']) for r in health['processes'] if r['comm'] in ['pipewire','wireplumber']],
 phoc_pid=procs['phoc']['pid'],phosh_pid=procs['phosh']['pid'],current_manifest='/var/lib/samurai/k297-services-verified-private.json',ssc_running=True,temporary_nodeps_desktop_start=False,physical_rotation_retest_pending=True)
p.write_text(json.dumps(d,indent=2)+'\n')
text=f'''# Realme X2 Pro 当前检查点

2026-10-19：[297共享SOF与断粮恢复](reference/kernel297/README.md)、[296统计SRAM初始化](reference/kernel296/README.md)。多摄／骁龙ISP目标继续推进；BLC／偏色、硬件pipeline／IPA和完整画质未完成。

## 当前部署与启动身份

现机 **#297**、`{package['release']}`，samurai-sof297／{source['commit']}。完整Image和独立778模块已部署读回，加载build-id匹配。boot276、DTB、原厂固件、961包／50相机载荷保持，libcamera r24／config-r19、PW／SPA／Gst1.6.9-r3保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA {package['image_sha256']}；logdump {package['logdump_sha256']}；boot {package['firmware_boot_preserved_sha256']}；DTB {package['dtb_sha256']}。

当前运输reference/kernel297/host.py与 `/var/lib/samurai/k297-work/boot-id-private.txt`，严格原SSH密钥、新端点；旧296 guard不用于当前启动。按entity发现，本次main6-0010／lens6-0072、tele8-002d、wide7-0010、front9-0010。Phoc3673／Phosh3899／PW5303／WP5316，start_ticks见[最终检查](reference/kernel297/final-health-validation.json)。

## 已验证与当前缺陷

- **PIX图像／统计改用共享CAMIF SOF标签**，不再分别按完成次数编号。两个驱动文件40增／18删；缺标签ERROR，参数报告下一SOF序号，无DT／固件／UAPI／产品包修改。实际旧函数负对照失败，新函数ASan／UBSan、相邻SOF先于DONE、缺标签、断粮、回绕及1000轮重排队通过。
- 长焦R2：126图像／111有效统计／128标准SOF，全部找到SOF，110组共同帧号配对；停统计改4×2 ROI再晚启，首包SOF19／人口2，旧计数18。耗尽三个统计buffer后图像继续，恢复序号保留7帧间隔。五次ROI变化首包与参数10／28／37／46／55一致。[关联与范围](reference/kernel297/sof-association-validation.json)
- WB11阶段颜色最大误差<1.235，10非法包拒绝、8参数完成，六次可观察颜色变化与参数帧号一致。未以最近完成时间配对，统计／图像完成相差可达−32100至102微秒。
- 首轮探针1图像／1统计后因空事件队列ENOENT处理不足退出，失败保留；实际图与资源已回收、fault0。独立R2修探针，无再次刷写。早期默认服务未就绪快照保留，后来默认成功，未重试SSC或nodeps。[过程](reference/kernel297/preparation-notes.json)
- 广角实景18图像／18有效统计，人口499392；曝光500→3000→500，Y75.6113→95.6392→75.6110，hist均值73.0162→120.0075→73.0164。已实际查看私人预览，结构可辨仍暗绿，BLC／AWB／IQ未校准。两成功探针合计144图像／129统计，不含R1失败。四摄RAW＋CPU ISP18段232帧，主摄SIGINT28后重开12通过。
- 多次未观测SOF合并、严重IRQ延迟、其它模式／长稳、多参数／Request API与硬件IPA未验收；广角没有独立订阅本轮SOF事件。ready_for_automatic_exposure=false，完整统计与画质仍未验收。
- 最终camera／lens／CCI／CAMSS suspended，九rails与共享IO关闭、MCLK／CCI clocks0，fault0／taint0／pstore空，无CCI错误。SSC／桌面／SensorProxy默认成功，Wi-Fi／HCI和modem／adsp／slpi正常。checked_runtime_healthy=true限定所列检查；旧SSC EPERM根因、GPU默认故障、旧modem watchdog及整机长稳未结案，whole_system_healthy=false。物理旋转／本启动AF未重测。

## 源码回退与下一步

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel` 干净samurai-sof297／{source['commit']}，本轮1本地提交未推送、未证明上游接受。完整构建138.08秒，五阶段诊断0，40CAMSS组件Werror、778模块及3嵌入BT模块一致。config SHA {build['artifacts']['.config']['sha256']}；input-initramfs297／modules297，输出/mnt/samurai-full282/build，先用284/storage.py核backing并挂载。296六产物保存在私人kernel297/completed-boot296。

固定四份Titan17x BLS12来源并交叉生成头：0x6b0配置、0x6b4／0x6b8阈值、lens enable bit11、14位offset、17位scale寄存器／Q11小数；[来源与数值](reference/kernel297/blc-protocol-validation.json)。尚未实现BLS或完成本机黑电平标定，不把其它手机参数或单场景截距当校准。下一步对应位深／模式的BLC与偏色验证，再接libcamera硬件pipeline／IPA；主／前摄硬件路径、AF Continuous／距离映射、Shine OV02A1B、GUI录像与长稳继续开放。

项目仍7.3rc6派生，54本地提交／177改动文件，libcamera配方28补丁含发行版既有、PipeWire6项目补丁，三个ignore_unused仍在；跨新内核／完整rootfs／上游接受未证明，不能承诺更新零或最小补丁。[更新审计](reference/kernel297/layering-validation.json)

稳定回退仍#290 logdump SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及原778模块；296／295／294／293／292／288等独立树、k132776及248整机备份保留，未回退往返。本轮一次启动切换，仅刷logdump；构建与所有采集已终态，勿盲目重放。私人目录E:/edk2-samurai-out/kernel297；像素、参考载荷、校准与密钥不公开。[边界](WORKING-BOUNDARIES.md)
'''
assert len(text.encode())<=6500
(ROOT/'NEXT-SESSION.md').write_text(text)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[296统计SRAM/首包修复](reference/kernel296/README.md)';assert needle in s
s=s.replace(needle,'[297共享SOF与断粮恢复](reference/kernel297/README.md)、'+needle);assert len(s.encode())<=10000;p.write_text(s)
banner='297（2026-10-19）：现机#297／778模块，图像／统计共享CAMIF SOF，126图像／111统计／128事件通过，110组配对、断粮恢复保留7帧间隔；5次ROI／6次WB生效帧对应。广角18／18有效，四摄18段232帧通过。固定BLS12协议资料，BLC／偏色／硬件pipeline／IPA仍待完成。'
for name,link in [('linux-port/camera/README.md','../../reference/kernel297/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel297/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel297/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel297/README.md')]:
 p=ROOT/name;p.write_text(banner+f'[297证据]({link})。以下旧阶段按历史阅读。\n\n'+p.read_text())
p=ROOT/'sessions/297-shared-sof-statistics-frame-identity.md';assert not p.exists();p.write_text('# 297：共享SOF帧号与统计断粮恢复\n\n'+banner+'\n\n[来源、实际结果、范围与部署](../reference/kernel297/README.md)。R1事件探针失败保留，R2独立工具修复后通过；未将局部帧关联扩大成完整IPA／画质验收。\n')
files={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [ROOT/'NEXT-SESSION.md',ROOT/'DOCS-INDEX.md',ROOT/'linux-port/camera/deployment-lock.json',ROOT/'linux-port/camera/kernel/source-lock.json']}
(HERE/'checkpoint-validation.json').write_text(json.dumps(dict(stage=297,current_kernel_build=297,source=source['commit'],shared_sof_in_tested_scope_passed=True,full_statistics_sof_and_pipeline_acceptance_passed=False,whole_system_healthy=False,goal_incomplete=True,files=files),indent=2)+'\n')
print(json.dumps(dict(stage=297,next_bytes=len(text.encode()),index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,goal_incomplete=True),indent=2))
