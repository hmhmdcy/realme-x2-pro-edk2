"""Publish the verified release state without reducing the remaining goal."""
from pathlib import Path
import copy,hashlib,importlib.util,json,shutil
import storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];storage.mount.mounted_build()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
h=json.loads((HERE/'current-state-validation.json').read_text());a=json.loads((HERE/'package-artifact-validation.json').read_text());r=json.loads((HERE/'install-r3-validation.json').read_text());pre=json.loads((HERE/'hardware-validation.json').read_text())
assert h['passed'] and h['installed'] and r['passed'] and r['terminal'] and not r['worker_live'] and not r['client_live'] and h['m2m']['completed']==56
assert pre['passed'] and pre['automatic_delivered_images']==406 and pre['successful_automatic_math_commits']==386
for package in ['libcamera','samurai-camera-config']:
 recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';d=json.loads(p.read_text())
 d.update(candidate_only=False,installed=True,native_install_validation='reference/kernel440/install-r3-validation.json',actual_current_payload_validation='reference/kernel440/current-state-validation.json',candidate_package_validation='reference/kernel440/package-artifact-validation.json',matched_camss_driver_stage=434,matched_ipe_core_stage=434,matched_ipe_adapter_stage=434,combined_candidate_hardware_verified=True,automatic_ipa_iq_generation=True,private_ipa_version=5,private_default_profiles_updated=True,public_generic_configuration_data_unchanged=True,original_factory_data_private_overrides=True,raw_only_pd10_requirement_fixed=True)
 save(p,d)
 label='libcamera r32' if package=='libcamera' else 'config／stack r27'
 text=f'''# {label}：四摄原厂自动调校发布

已正式安装五个 libcamera 运行包99990.7.2-r32及config／stack0.1.0-r27，匹配434生产CAMSS／ICP core／m2m。包含0042—0050真实PD10、GTM实际版本、成功数学历史与前摄IPE CCM，再以0051修复RAW-only没有IPE消费者时错误强制PD10的问题。既有子包和其它IPA保留。

四摄原生／隔离整合实拍406帧通过。默认四摄GStreamer、RAW／双流、主摄与前摄自动链路及普通用户PipeWire通过；最终部署与适用范围见[440记录]({{link}})。原厂表仅在本机私有配置；公共通用YAML内容不变，配置包精确固定r32依赖。完整画质、更多尺寸／视频／HDR和多摄校准继续。

构建输入和实际安装证据见[源锁](source-lock.json)。早期逐帧通道发布记录见[420历史]({{history}})，不代表当前仍使用旧版旁路调校。
'''
 (recipe/'README.md').write_text(text.format(link='../../../../reference/kernel440/README.md',history='../../../kernel420/README.md'))
 dest=ROOT/'linux-port/packages'/package
 for file in recipe.iterdir():
  if file.is_file():shutil.copyfile(file,dest/file.name)
 (dest/'README.md').write_text(text.format(link='../../../reference/kernel440/README.md',history='../../../reference/kernel420/README.md'))
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 d.update(stage=440,in_progress_stage=440,latest_work_stage=440,in_progress_installed=True,current_device_revalidated_stage=440,current_camera_userspace_stage=440,current_camera_configuration_stage=440,
  framework_version='99990.7.2-r32',configuration_version='0.1.0-r27',candidate_framework_version='99990.7.2-r32',candidate_configuration_version='0.1.0-r27',
  current_icp_pair_deployment_stage=440,current_icp_core_deployment_stage=440,current_icp_adapter_deployment_stage=440,current_icp_core_source_stage=434,current_icp_adapter_source_stage=434,
  current_camss_deployment_stage=440,current_camss_source_stage=434,ipe_userspace_deployment_stage=440,installed_ipa_source='/mnt/samurai-full282/libcamera440-release-r32/src/libcamera-v0.7.2',installed_ipa_source_stage=440,
  ipe_libcamera_candidate_permanently_installed=True,ipe_automatic_dual_pass_candidate_installed=True,ife_gtm_candidate_installed=True,ipe_frame_observation_history_installed=True,ipe_statistics_publication_reentry_fix_installed=True,ipe_numeric_tmc_ltm_history_installed=True,ipe_ltm_pd10_coarse_io_candidate_installed=True,
  ipe_media_request_iq_libcamera_integrated=True,ipe_media_request_iq_ipa_parameter_generation_integrated=True,ipe_ltm_runtime_submission_enabled=True,ipe_ltm_product_default_enabled=True,ipe_ltm_curve_product_integrated=True,ipe_cc_colour_conversion_pair_enabled=True,
  ipe_full_factory_tone_pipeline_complete=False,ipe_main_image_quality_accepted=False,ipe_front_absolute_quality_accepted=False,
  ipe_main_image_quality_issues=['absolute colour/flat-field/sharpness/noise not accepted','other processed dimensions, full modes/video/HDR branches pending'],
  last_live_hardware_evidence_stage=440,last_successful_scene_stage=440,last_successful_automatic_ipe_scene_stage=440,maintained_userspace_ipa_candidate_stage=440,maintained_userspace_ipa_candidate_build=2,maintained_userspace_ipa_candidate_source='/mnt/samurai-full282/libcamera440-release-r32/src/libcamera-v0.7.2',
  latest439_all_four_camera_cohort_retest_pending=False,latest440_four_camera_native_isolated_images=406,latest440_successful_math_commits=386,latest440_bootstrap_images=20,latest440_raw_only_images=90,latest440_dual_images=6,
  latest440_default_path_ipe_images_across_r2_r3=162,latest440_default_main_auto_images=52,latest440_default_front_auto_images=44,latest440_current_module_epoch_ipe_completed=56,
  ipe_current_cumulative_counters={k:h['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']},ipe_current_counter_epoch='440 durable installation r3:44 front automatic+12 ordinary-user PipeWire=56. Seven completed default-path cases reused from identical r2 payload; historical counters not added.',
  ipe_current_failed_counter_scope='Current installed434 module epoch56direct,failed/cancelled0. Installation r1/r2 verifier count errors triggered complete offline rollback; immutable reports retained. One r1 stop-aborted image did not commit IPA history.',
  ipe_auto_tone_scope='440 installed r32/IPA5/434 modules and private stock profiles:GW1 4608x3456,IMX319 1632x1224,S5K3M5 2104x1560,IMX471 2304x1728 sensor modes; processed640x480 real-PD10 dual-pass,single exposure.406 native/isolated images386math+20bootstrap. Other dimensions/full variants/absolute quality pending.',
  ipe_gtm_applied_version_history_scope='440 four-camera cohort uses actual GTM cookie/generation and WB context frozen to observed SOF,real PD10 and final successful IPE math history. Rear both banks;front stock GTM disabled/bank0. Default main52 andfront44 independently audited.',
  ife_gtm_hardware_scope='434 fixed-exposure IFE proof retained;440 production IPA binds actual GTM versions to same-SOF FULL/PD10 and successful TMC/LTM history,all four native and isolated.Current module installed.',
  ipe_ltm_dc_consumption_scope='430 fixed-input deterministic real/black/white/repeat PD10 causal LTM proof retained;434 RT2 kind0 bank0 clear/write coarse then full consume;440 same-SOF production IPA automatic dual-pass verified.No bytewise DC SRAM table export claim.',
  ipe_ltm_product_default_scope='Enabled by four installed private factory profiles for documented modes;public generic APK profiles unchanged. Rear IFE CCM;front nonidentity IPE CCM;stock per-camera TMC/GTM switches preserved.',
  ipe_cc_colour_conversion_pair_enabled_scope='Proven CST/CV YUV-RGB bridge used for LTM input domain;rear colour matrix stays in IFE;front stock CC13 runs in IPE.Module flags5rear/7front,not duplicate rear colour/gamma processing.',
  ipe_cc_per_frame_runtime_api_scope='Installed440 standard Media Request typed6008 IPE packet generated by production IPA from real same-frame statistics and effective GTM/WB version;only successful images commit history.RAW-only no IPE/no math.',
  in_progress_installed_scope='440 r32/r27,three434 production modules,four private factory profiles installed;default paths and56-current-epoch jobs pass.Image363/DT389/sensors/firmware unchanged;no reboot acceptance this phase.',
  kernel_source_scope='Kernel source354 clean434 HEAD9bc07e63 unchanged;440 installs matching3 modules andpackages.Fix0051 only generic processed-consumer PD10 policy,no SoC/board/sensor changes.',
  current_device_health='440 installed r32/r27/434 modules;current56direct,failed/cancel0,newfault0,taint0,PM suspended,CPU/IRQ/maps/import/DMA released;PipeWire/WirePlumber restored singleton.',
  current_device_loaded_module_state='Three production434 modules loaded and disk hashes/build-id notes match;no test parameters.',current_device_last_successfully_restored_experiment='440 installationr3 succeeded;priorr1/r2 full APK/module/profile rollback passed.',
  current_health_scope='440 current-state-validation:installed hashes+loaded notes+private profiles+default paths+56direct+services+PM+DMA ownership verified.No cold reboot or absolute image-quality acceptance.',device_current_taint=0,device_force_restart_currently_needed=False,current_device_recovery_required=False,
  icp_next_step='Extend real-PD10 automatic dual-pass beyond640x480 using original striping/grid/mode data,then remaining video/HDR/manual/v2/optics/fifth2MP/multicam scope.Preserve nativeRAW and correct IFE/IPE domains.No repeated passed matrices or unsafe429diagnostic.')
 links={'current_camera_evidence':'README.md','in_progress_evidence':'README.md','device_closeout_evidence':'current-state-validation.json','current_readonly_device_evidence':'current-state-validation.json','final_health_evidence':'current-state-validation.json','installed_userspace_current_versions_evidence':'install-r3-validation.json','installed_userspace_evidence':'install-r3-validation.json','ipe_libcamera_pipeline_evidence':'hardware-validation.json','ipe_media_request_iq_libcamera_evidence':'hardware-validation.json','ipe_auto_tone_latest_evidence':'README.md','ipe_auto_tone_evidence':'README.md','ipe_auto_dual_pass_evidence':'hardware-validation.json','ipe_gtm_auto_history_evidence':'hardware-validation.json','maintained_userspace_ipa_candidate_evidence':'build-validation.json'}
 for key,name in links.items():d[key]=prefix+'kernel440/'+name
 if rel.endswith('deployment-lock.json'):
  mods=copy.deepcopy(d['kernel_modules']);mods.update(h['modules']);d.update(built_packages=a['packages'],installed_camera_packages=r['packages'],kernel_modules=mods,system_services=dict(stage=440,services=h['services'],evidence=prefix+'kernel440/current-state-validation.json',current_boot_revalidated=True))
 else:
  mods=copy.deepcopy(d['deployed_camera_modules']);mods.update(h['modules']);d['deployed_camera_modules']=mods
 save(p,d)
archive=ROOT/'archive/NEXT-SESSION-through439-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text='''# 当前检查点：440（四摄原厂自动调校 r32 已正式安装）

完整多摄／骁龙ISP目标active。读WORKING-BOUNDARIES和reference/kernel440/README。手机正式版本已由420 r31/r26与419模块切换至libcamera五包99990.7.2-r32、config/stack0.1.0-r27、434匹配三模块和四份私有原厂配置。Image363/DT389/sensor/FW未变；本轮未重启验收。

## 当前源码与载荷

源码/mnt/samurai-full282/libcamera440-release-r32/src/libcamera-v0.7.2，保留439副本。420基线叠0042—0051十补丁零fuzz/offset，48个受影响文件相同。13子包构建，7运行包签名与6IPA签名通过，其它5IPA与r31相同。实际剥离包内ARM64合约通过。核心SHA0884c73489815132b5f180c303ab5ed2edc4c52f0f7b191365054aa855849a48，IPA8703093d5882488e7a0125002a71e5a23f5382594b0a5b4ae30f9ed0d63ec796，协议5。0051只修RAW-only错误强制PD10：requiresPd10=processedEnabled&&sensorConfiguration.pd10，保留内部统计，不伪造IPE历史。

内核source354/samurai-vfe175-gtm-reopen434，HEAD9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3干净。正式三模块CAMSS3edb28d1/core d391fa24/m2m e6828a0c，loaded notes匹配disk，无test参数。原厂私有profile来源主437、广角/长焦438、前439；公共YAML不变、原件不入APK。前摄保持IFE CCM/TMC10/11/GTM关闭、IPE CCM13/LTM/Gamma开启，未知1928裁剪不套2304模式。

## 实拍与正式路径

同一最终包及三模块/四配置，四摄native+isolated8路交付406图=386math+20bootstrap，每路8连续AWBlocked，实际GTM/WB版本、同SOF PD10与成功历史逐帧对应。后摄两GTM bank，前摄GTM关闭/bank0。RAW-only主72+其它各6=90图无IPE；主双流6，同SOF配对。临时cohort共412IPE完成，非当前安装计数。

正式默认路径r2/r3：四摄GST各12共48、主双流6、主自动52(49math+3bootstrap)、前自动44(42+2)、普通用户PW12，共162IPE；另RAW-only6无IPE。r3比较完全相同载荷，复用7个已通过案例，仅新跑front44+PW12。当前驱动epoch56jobs=completed=direct，failed/cancel/firsterror0，owner_refs57为桌面句柄；ICP/CAMSS/双CCI suspended，CPU/IRQ/PM/map/import/DMA释放，PW788/WP794各1 uid10000，新fault0/taint0。

安装r1/r2原报告false保留，均已实际完整离线回滚包/三模块/四配置和服务：r1把6交付等同6物理完成，另1已入队帧停机abort未commit；r2把PD10/观察数等同图像数，主52图外3观察正常discard。新审计逐SOF/token核对queue/receipt/GTM来源/成功lux/math/stop/pending，旧实拍缓存审计也通过；无运行库改动。成功root /var/lib/samurai/k440-install-r3，worker659/client终态。不要重新启动旧事务。当前仓库入口为该root签名forward，旧r31/r26七包/索引/world/repo/三模块/四配置备份齐全。

## 后续完整目标

下一步扩展真实PD10自动双遍至其它预览/录像输出尺寸，先复用原厂striping、DC网格和模式绑定，在底层处理尺寸/遍次同步；当前处理640x480，RAW原生尺寸。随后完整legacy/manual/v2/HDR、正常光学色准/平场/噪声/清晰度、连续AF/距离、第五2MP与多摄几何/同步等363完整scope继续。AWB锁定不是绝对画质验收。429越界诊断绝不恢复；DC bank/clear/消费证据沿用430/434，没有新增逐字节SRAM表导出。

每次WSL源/build/ext4先root284/storage.mounted_build挂原E盘32GiB，不格式化；SDK bind串行。20261022两轮清理保留当前源码/构建/回滚/原厂资料。USB SSH与429guard正常，密钥/原件/系数/像素/完整日志仅E:/edk2-samurai-out/kernel440及手机。镜像public导出/scoped本地commit保留无关index/worktree/untracked，不push；最新commit以git及private local-mirror-validation为准。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/ISP目标active，读NEXT-SESSION/WORKING-BOUNDARIES/reference/kernel440/README。440已正式安装r32/r27、三434模块、四原厂私有配置；source440、IPA5、0051修RAW-only错误强制PD10。四摄native/isolated406图386math+20bootstrap、90RAW-only无IPE、6dual通过。默认路径GST48/dual6/mainauto52/frontauto44/PW12跨r2/r3共162成功；r3复用相同载荷7案例，当前epoch56direct失败取消0，服务/PM/DMA释放，taint0无fault。r1/r2验收计数错误均已完整回滚，原报告false保留；按SOF/token/最终成功history审计，主额外3观察正常discard。成功事务k440-install-r3终态不可重启，离线旧r31/r26/三模块/四配置备份齐全，无重启。下一步扩真实PD10双遍至其它预览录像尺寸，原厂striping/DC网格/模式绑定底层收敛；640x480当前限制、完整模式/video/HDR/光学/连续AF/第五2MP/多摄几何同步继续。前摄原IPE CCM与TMC/GTM关闭域保持。原32GiB盘284挂载、SDKbind串行、429guard，原件私存，scoped本地提交不push。\n')
note='440当前：r32/r27、434三生产模块和四私有原厂配置已正式安装；四摄同一包原生/隔离406图386math，默认四摄预览/RAW/自动调校/PipeWire通过。当前56direct、新fault0/taint0，资源与服务正常；更多尺寸/视频/HDR及完整光学和多摄校准继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel440/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel440/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel440/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('439当前：');p.write_text(note+'[440证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';text=p.read_text();old='[439 前摄原厂IPE CCM与自动PD10实拍](reference/kernel439/README.md)';assert old in text;p.write_text(text.replace(old,'[440 四摄原厂自动调校r32正式安装](reference/kernel440/README.md)'))
p=HERE/'IN-PROGRESS.json';d=json.loads(p.read_text());d.update(phase='durable-release-installed-and-verified',formal_installed=True,formal_versions={'libcamera':'99990.7.2-r32','config':'0.1.0-r27'},last_terminal_worker='phone k440-install-r3 worker659/client terminal,passed;56 current IPE,taint0/no newfault',next=['Export reviewed current440 documents/recipes/evidence to mirror, preserve unrelated changes and make scoped local commit without push','Extend real-PD10 automatic dual-pass to additional dimensions, original striping/DC grid and mode data first','Full video/HDR/optical/fifth2MP/individual/multicamera scope remains active']);save(p,d)
spec=importlib.util.spec_from_file_location('index',ROOT/'linux-port/scripts/generate-session-index.py');index=importlib.util.module_from_spec(spec);spec.loader.exec_module(index);(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
print(json.dumps(dict(stage=440,canonical_recipes_updated=True,deployment_locks_updated=True,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,installed=True,full_goal_complete=False,passed=True)))
