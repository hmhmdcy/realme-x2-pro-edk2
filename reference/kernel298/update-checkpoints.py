"""Promote only the tested #298 deployment and retain calibration/IPA limits."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text())
health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json');source=load(HERE/'source-validation.json')
assert health['kernel_build']==298 and health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert load(HERE/'blc-pixel-validation.json')['all_phase_color_contracts_passed']
assert load(HERE/'blc-frame-association-validation.json')['exact_frame_association_proven']
assert load(HERE/'sof-association-validation.json')['shared_sof_contract_passed']
assert load(HERE/'scene-capture-validation.json')['passed'] and load(HERE/'raw-capture-validation.json')['passed']
regression=load(HERE/'four-camera-regression-validation.json');assert regression['passed'] and regression['frames']==233
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')==source['commit'] and not git('status','--porcelain')
archive='archive/camera-before298-2026-10-19';assert load(ROOT/archive/'manifest.json')['prior_documented_stage']==297
def advance(d):
 for key,value in d.items():
  if isinstance(value,str) and '/reference/kernel297/' in value:
   name=value.rsplit('/',1)[-1]
   name={'stats-pixel-validation.json':'blc-pixel-validation.json','frame-association-validation.json':'blc-frame-association-validation.json','optical-pixel-validation.json':'scene-analysis-validation.json'}.get(name,name)
   if (HERE/name).is_file():d[key]=value.rsplit('/reference/kernel297/',1)[0]+'/reference/kernel298/'+name
 return d
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=advance(load(p))
d.update(stage=298,maintained_branch=source['branch'],maintained_commit=source['commit'],actual_kernel_image_stage=298,actual_kernel_release=package['release'],module_count=778,
 deployed_camera_modules=health['modules'],previous_lock_archive='../../../'+archive+'/linux-port/camera/kernel/source-lock.json',
 source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],source_worktree_is_undeployed_candidate=False,
 standard_equal_channel_black_subtraction_implemented=True,standard_black_subtraction_evidence='../../../reference/kernel298/blc-pixel-validation.json',
 sensor_dark_calibration_pending=True,hardware_pipeline_ipa_integrated=False,scene_estimate_not_installed_as_tuning=True)
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=advance(load(p))
d.update(stage=298,current_boot_guard_stage=298,kernel_image_stage=298,kernel_release=package['release'],kernel_modules=health['modules'],
 kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],candidate_kernel_source_commit=source['commit'],candidate_kernel_source_branch=source['branch'],
 image_sha256=package['image_sha256'],logdump_sha256=package['logdump_sha256'],kernel_config_sha256=build['artifacts']['.config']['sha256'],
 guard_path='/var/lib/samurai/k298-work/boot-id-private.txt',previous_lock_archive='../../'+archive+'/linux-port/camera/deployment-lock.json',
 previous297_778_modules_preserved=True,checked_runtime_healthy=True,whole_system_healthy=False,
 spectra_hardware_image_processing_supported_scope='Experimental tele FULL NV12 BLS/WB/BHIST and shared-SOF lifecycle tested; wide RAW exposure reference and hardware BLS/WB/gain scene experiment improve darkness/green in one scene; apps remain RAW plus CPU ISP; covered-lens calibration, hardware pipeline/IPA, full IQ and broader SOF acceptance incomplete',
 standard_equal_channel_black_subtraction_implemented=True,standard_black_subtraction_evidence='../../reference/kernel298/blc-pixel-validation.json',
 sensor_dark_calibration_pending=True,covered_lens_dark_calibration_completed=False,scene_estimates_not_installed_as_tuning=True,
 provisional_scene_iq_evidence='../../reference/kernel298/scene-analysis-validation.json',raw_exposure_reference_evidence='../../reference/kernel298/raw-analysis-validation.json',
 hardware_pipeline_ipa_integrated=False,physical_hardware_isp_image_validation_pending_scope='Full sensors/modes/IQ; tested tele and wide experimental output has passed',
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel298 AF search not retested; Continuous and distance calibration incomplete')
procs={r['comm']:r for r in health['processes']}
d['system_services'].update(stage=298,new_processes=[dict(name=r['comm'],pid=r['pid'],start_ticks=r['start_ticks']) for r in health['processes'] if r['comm'] in ['pipewire','wireplumber']],
 phoc_pid=procs['phoc']['pid'],phosh_pid=procs['phosh']['pid'],current_manifest='/var/lib/samurai/k298-services-verified-private.json',ssc_running=True,temporary_nodeps_desktop_start=False)
p.write_text(json.dumps(d,indent=2)+'\n')
text=f'''# Realme X2 Pro 当前检查点

2026-10-19：[298黑电平映射与暗绿硬件对照](reference/kernel298/README.md)。BLS已实现／实机验证；遮光暗场标定、正式调校、libcamera硬件pipeline／IPA与完整IQ未完成。目标继续推进，应用仍RAW＋CPU ISP。

## 当前部署与启动身份

现机 **#298**、`{package['release']}`，干净samurai-blc298／{source['commit']}。完整Image和独立778模块已部署读回，加载build-id匹配。boot276、DTB、原厂固件、961包／50相机载荷保持，libcamera r24／config-r19、PW／SPA／Gst1.6.9-r3保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA {package['image_sha256']}；logdump {package['logdump_sha256']}；boot {package['firmware_boot_preserved_sha256']}；DTB {package['dtb_sha256']}。

当前运输reference/kernel298/host.py与 `/var/lib/samurai/k298-work/boot-id-private.txt`，严格原SSH密钥、新端点。按entity发现：main8-0010／lens8-0072、tele6-002d、wide9-0010、front7-0010。Phoc3789／Phosh4029／PW5436／WP5438，start_ticks见[最终检查](reference/kernel298/final-health-validation.json)。旧297 guard不用于本启动。

## 已验证与当前缺陷

- SoC两个文件55增／2删：复用公共WB相等减偏移U16→U14 BLS，Q11 scale保持unity；拒绝不等减偏移和非零加偏移，旁路缓存／恢复、停流、重开默认0。无新UAPI／DT／固件／产品包补丁。[协议](reference/kernel298/blc-protocol-validation.json)、[补丁](reference/kernel298/blc-candidate.patch)
- 长焦126图像／111统计／128SOF；11阶段减黑／WB对照独立RDI RAW最大通道误差<1.337，六次可观察图像变化与参数首个生效帧完全对应。110组共享SOF配对、5次ROI对应、断粮恢复保留7帧间隔，晚启首包SOF19／人口2。单参数／特定模式验证不等于完整IPA验收。
- 广角18帧RAW曝光500→3000→500／2×gain，六倍曝光场景拟合R／Gr／Gb／B截距中位数64 DN；不是遮光标定。临时灰世界R2.22／B1.90未安装为调校。另126硬件图像／111统计：只减黑Y98.199→65.927，联合WB后76.229，4×模拟增益后106.833；减黑后G相对R/B比1.493→1.019，4×时1.014。实际查看前后私人预览，暗绿改善但非色彩准确度证明。[实景](reference/kernel298/scene-analysis-validation.json)
- 两硬件探针合计252图像／222统计，独立RAW18帧；四摄产品回归18段233帧，含主摄SIGINT29后重开12。结束资源全部回收，fault0／taint0／pstore0，无CCI错误；SSC／桌面／SensorProxy默认成功，Wi-Fi／HCI与三个DSP正常。
- 用户选择正常场景、暂不遮光，不能把实景截距当暗场标定；没有安装临时场景系数。严重IRQ延迟／多丢失SOF／多参数、其它模式、主／前摄硬件路径和完整画质仍开放，statistics_ready_for_automatic_exposure=false。GPU默认故障、旧modem watchdog、SSC偶发EPERM根因与长稳未关闭，whole_system_healthy=false。GUI录像／物理旋转／本启动AF未重测。

## 源码回退与下一步

完整构建158.45秒，五阶段诊断0、40CAMSS组件Werror、778模块与3嵌入BT模块一致。config SHA {build['artifacts']['.config']['sha256']}；input-initramfs298／modules298，输出/mnt/samurai-full282/build，先用284/storage.py核backing并挂载，保持Rust工具环境。297六产物保存在私人kernel298/completed-boot297。

先补遮光暗场与曝光／增益／温度依赖，匹配模组后把参数放用户空间，再做中性色／多光源AWB与颜色校准。Sunny／Qtech保存XML已复查，但没有本轮可用黑电平标定字段，也不能凭sensor ID判断个体模组。然后按[硬件pipeline／IPA约定](reference/kernel298/HARDWARE-IPA.md)复用媒体图、V4L2元数据队列、sensor helper与DelayedControls。现有线性Y BHIST不是RGB AWB统计，当前硬件pipeline／IPA没有接入。

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel`：7.3rc6派生55本地提交／177改动文件；libcamera配方28补丁含发行版既有，PW6项目补丁，三个ignore_unused仍在。未推送或证明上游接受／跨新版本迁移；不能承诺零或最小升级补丁。[更新审计](reference/kernel298/layering-validation.json)

稳定回退仍#290 logdump SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及独立778模块。297／296／295等旧树、k132776和248备份保留。一次启动切换，仅刷logdump；首次尺寸预检拦下脚本数值替换错误，修正并重新核对后才写，未重复重启／刷写。[保留过程](reference/kernel298/preparation-notes.json)

所有构建和采集已终态，勿盲目重放。私人根E:/edk2-samurai-out/kernel298，像素／个体校准／密钥不公开。[边界](WORKING-BOUNDARIES.md)
'''
assert len(text.encode())<=6500; (ROOT/'NEXT-SESSION.md').write_text(text)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[297共享SOF与断粮恢复](reference/kernel297/README.md)';assert needle in s
s=s.replace(needle,'[298黑电平与暗绿对照](reference/kernel298/README.md)、'+needle);assert len(s.encode())<=10000;p.write_text(s)
banner='298（2026-10-19）：现机#298／778模块，公共WB减偏移映射BLS，长焦11阶段最大通道误差<1.337、六次图像生效帧对应。广角RAW场景估计64 DN及临时WB／gain改善暗绿；非遮光标定、未安装调校。两个硬件探针252图像／222统计，RAW18帧，四摄18段233帧通过。正式校准与硬件pipeline／IPA仍未完成。'
for name,link in [('linux-port/camera/README.md','../../reference/kernel298/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel298/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel298/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel298/README.md')]:
 p=ROOT/name;p.write_text(banner+f'[298证据]({link})。以下旧阶段按历史阅读。\n\n'+p.read_text())
p=ROOT/'sessions/298-black-level-mapping-and-hardware-scene.md';assert not p.exists();p.write_text('# 298：黑电平映射与暗绿硬件对照\n\n'+banner+'\n\n[源码、实测、原厂资料边界与部署](../reference/kernel298/README.md)。单场景灰世界与曝光截距没有升级为模组标定，正式调校与硬件IPA继续开放。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();needle='## 会话文件';assert needle in s;s=s.replace(needle,'[298黑电平与暗绿硬件对照](298-black-level-mapping-and-hardware-scene.md)：当前#298，遮光标定和硬件IPA未完成。\n\n'+needle,1);p.write_text(s)
names=[r['path'] for r in load(ROOT/archive/'manifest.json')['files']]
files={n:dict(bytes=(ROOT/n).stat().st_size,sha256=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()) for n in names}
(HERE/'checkpoint-validation.json').write_text(json.dumps(dict(stage=298,current_kernel_build=298,source=source['commit'],black_mapping_physical_contract_passed=True,covered_lens_calibration_pending=True,hardware_pipeline_ipa_complete=False,whole_system_healthy=False,goal_incomplete=True,files=files),indent=2)+'\n')
print(json.dumps(dict(stage=298,next_bytes=len(text.encode()),index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,goal_incomplete=True)))
