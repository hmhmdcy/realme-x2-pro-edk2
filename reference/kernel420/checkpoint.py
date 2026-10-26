"""Record the installed production channel and the unchanged full scope."""
from pathlib import Path
import copy,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
h=json.loads((HERE/'current-state-validation.json').read_text());a=json.loads((HERE/'package-artifact-validation.json').read_text());r=json.loads((HERE/'install-validation.json').read_text())
assert h['passed'] and r['passed'] and r['driver_pair_installed'] and h['m2m']['completed']==93
for package in ['libcamera','samurai-camera-config']:
 recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';d=json.loads(p.read_text())
 d.update(candidate_only=False,installed=True,native_install_validation='reference/kernel420/install-validation.json',actual_current_payload_validation='reference/kernel420/current-state-validation.json',candidate_package_validation='reference/kernel420/package-artifact-validation.json',matched_ipe_core_stage=419,matched_ipe_adapter_stage=419,combined_candidate_hardware_verified=True,ipe_media_request_included=True,automatic_ipa_iq_generation=False)
 save(p,d);dest=ROOT/'linux-port/packages'/package
 for file in recipe.iterdir():
  if file.is_file():shutil.copyfile(file,dest/file.name)
kernel=json.loads((ROOT/'linux-port/camera/kernel/source-lock.json').read_text());mods=copy.deepcopy(kernel['deployed_camera_modules'])
for name,sha,size in [('qcom_camss_icp_a5_core','63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632',419848),('camss_icp_a5_m2m','46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f',132400)]:
 mods[name].update(sha256=sha,bytes=size,loaded=True,loaded_note_matches_disk=True,targeted_validation_stage=420,source_stage=419,parameters={})
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text());assert d['latest_work_stage']==419
 d.update(stage=420,in_progress_stage=420,latest_work_stage=420,in_progress_installed=True,current_device_revalidated_stage=420,
  icp_latest_device_experiment_stage=420,ipe_latest_hardware_stage=420,latest_stage_device_mutated=True,latest_stage_phone_accessed=True,
  framework_version='99990.7.2-r31',configuration_version='0.1.0-r26',candidate_framework_version='99990.7.2-r31',candidate_configuration_version='0.1.0-r26',
  current_icp_core_deployment_stage=420,current_icp_adapter_deployment_stage=420,current_icp_core_source_stage=419,current_icp_adapter_source_stage=419,
  ipe_libcamera_candidate_permanently_installed=True,ipe_userspace_deployment_stage=420,current_camera_userspace_stage=420,
  installed_ipa_source='/mnt/samurai-full282/libcamera420-request-r31/src/libcamera-v0.7.2',installed_ipa_source_stage=420,ipa_numerical_contract_reused_from_stage=362,
  in_progress_installed_scope='Production419 core+adapter and signed r31/r26 userspace installed420;Image363/DT389/CAMSS389/FW/private tuning unchanged.No test modules.',
  kernel_source_scope='419 driver source unchanged clean;420 packages and durably installs tested request/control channel and safe error-buffer dequeue fix.No SoC/board/sensor/IPA algorithm changes.',
  ipe_cc_encoder_candidate_installed=True,a5_icp_candidate_source_installed=True,
  ipe_media_request_iq_libcamera_integrated=True,ipe_media_request_iq_ipa_parameter_generation_integrated=False,
  ipe_cc_per_frame_runtime_api_scope='420 installed r31/production419:standard Media Request typed6008 control,OUTPUT request/CAPTURE ordinary.All four cameras log requests=1.Automatic IQ payload remains bypass.',
  ipe_media_request_iq_libcamera_scope='420 signed r31 and419 production pair installed;81 camera IPE frames plus12 ordinary PipeWire=93success,zero failures/cancellations.Nonzero diagnostics and forced ACK recovery evidence reused418/419;automatic IPA generation pending.',
  ipe_ltm_runtime_submission_scope='Typed LTM submission channel is installed420;nonzero tests validated418/419.Pipeline automatic parameters still bypass;default advanced IQ off.',
  ipe_cc_colour_conversion_pair_enabled_scope='Encoder and channel installed420;advanced automatic RGB/IPE IQ still off pending actual input-domain proof.IFE already processes CC/Gamma.',
  ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,ipe_ltm_curve_product_integrated=False,
  ipe_latest_stage_actual_frames=93,ipe_latest_stage_RT_frames=93,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
  ipe_latest_stage_frames_scope='420 installed production epoch93=4cameras48+dual6+isolated27+ordinary PipeWire12;RAW-only6pairs noIPE.Nonzero diagnostic and fault tests reused418/419,not repeated.',
  ipe_current_cumulative_counters={k:h['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']},
  ipe_current_counter_epoch='420 production419 module reload:93jobs93direct,starts/stops7;48fourcamera+6dual+27isolated+12PipeWire.',
  ipe_current_failed_counter_scope='Current production420 lifetime93complete,failed/cancel0.Historical419 expected fault epochs and raw worker clock-classification false remain separate.',
  current_health_scope='420 installed r31/r26 and419 pair:93direct,resources released,17clocks0/9railsdisabled/allPMsuspended,services11073/11076.Historical417 WARN taint512 retained.',
  device_current_taint=512,device_force_restart_currently_needed=False,
  icp_next_step='Connect actual IPA prepare/result,statistics/exposure/gain and factory407..416 math to installed typed channel.History commit only after final image processed(success);discard failures.Request completion alone not success.Avoid double IFE/IPE CC/Gamma.Full363 scope remains;do not rerun passed matrices or419 fault just for report cleanup.')
 for key,name in [('current_camera_evidence','README.md'),('in_progress_evidence','README.md'),('device_closeout_evidence','current-state-validation.json'),('current_readonly_device_evidence','current-state-validation.json'),('installed_userspace_current_versions_evidence','install-validation.json'),('installed_userspace_evidence','install-validation.json'),('ipe_libcamera_pipeline_evidence','hardware-validation.json'),('ipe_media_request_iq_libcamera_evidence','hardware-validation.json')]:d[key]=prefix+'kernel420/'+name
 if rel.endswith('deployment-lock.json'):
  d.update(built_packages=a['packages'],installed_camera_packages=r['packages'],kernel_modules=copy.deepcopy(mods),final_health_evidence=prefix+'kernel420/current-state-validation.json',system_services=dict(stage=420,services=h['services'],evidence=prefix+'kernel420/current-state-validation.json',current_boot_revalidated=True))
 else:d['deployed_camera_modules']=copy.deepcopy(mods)
 save(p,d)
text='''# 当前检查点：420（逐帧IQ生产通道已正式安装）

读WORKING-BOUNDARIES.md、reference/kernel420/README.md。完整多摄/骁龙ISP目标active；已开灯。419全文归档archive/NEXT-SESSION-through419-2026-10-21.md；不再反复扩大已通过算法矩阵。

## 正式设备

已安装五个libcamera运行包99990.7.2-r31与config/stack0.1.0-r26、419生产core+adapter。13包构建/签名核对，6IPA签名匹配包内核心，6IPA二进制与r30相同；原40补丁/全功能子包/IPA接口保留，新增0041请求补丁。公共配置payload不变，精确依赖pin更新；/etc四份个体配置未变，原厂表不进公共包。

候选源码/mnt/samurai-full282/libcamera420-request-r31/src/libcamera-v0.7.2复制418已验证源，四文件hash相同，复用418零fuzz及37模型/16非零实像素证据。包内strip核心SHAd8c841d28f65bd1746e240beea71af33b83087f511e6359ba75099ea09c0b05b，不混418未strip实验库55721…。linux-port/packages两配方与源锁已更新。

420一次事务root /var/lib/samurai/k420-install-r1，worker10893/client/collector终态且passed。停止消费者→owner/DMA释放→原子替换2模块/depmod/重载→七包精确离线升级→测试→重启原用户服务。正式磁盘文件与loaded notes一致，测试参数无。旧r30/r25七包/签名索引/world/repo/395核心393适配器备份保留，本轮没有执行回退。勿重启已完成事务或重新stage旧root。准备阶段两次只读查询错误已修，无状态切换。

生产93jobs=93done/direct，failed/cancel/firsterror0，starts/stops7：四摄各12=48；主RAW+NV12六（原IFE SOF匹配）；RAW-only六对无IPE；独立进程IPA27/五control阶段/GammaACK1；普通用户PipeWire四节点/广角12。四摄/dual/isolated日志均requests=1；WirePlumber实际映射系统库。GammaACK为IFE，**自动IPE参数仍全零旁路**，不称自动原厂画质。

最终PW11073/WP11076 uid10000单例，owner_refs53为桌面CAMSS句柄。ICP/CAMSS双CCI suspended、17clk0/9railsdisabled-users0，CPU/IRQ/PM/backing/map/import释放；新fault/dump0、watchdog/protocol0。guard394=/var/lib/samurai/k394-recovered/boot-id-private.txt不变，本轮无重启。taint512源417-r2已修WARN，保留不清标记，不声称taint0。

## 内核和恢复依据

source354 branch samurai-ipe-error-buffer419 commit07d2ca735f88649587c0e89802febff6dbf2b443干净，420未改代码。生产core419848B SHA63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632；adapter132400B SHA46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f。**e27ad524…吞ACK临时核心绝不能当生产**。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、DT389/CAMSS389/logdump365/SGownerFW保持。SoC/板级/主线/UAPI/驱动/用户空间分层描述。

419 ERROR缓冲修复：七项逐帧所有权均释放才不queue_error，便于DQBUFFER返回已知ERROR；未知DMA继续poison及保引用，全局fatal不删。24实际worker/vb2模型、W1/Werror构建、真实typed LTM+Gamma成功ACK被吞一次/变体通过。约5.1秒reset，IQ8944B/parcel548864B保留到双freshACK3,3后退役；恢复460800字节等406参考。blocked失败回调6.7ms。物理停机失败仅模型覆盖，本轮未重复故障注入。

419原始r2 worker报告state.passed=false必须保留：混printk/uptime误把4条预期错误归unexpected。严格fault-validation按唯一drop→reset→retirement→下一SYS_INIT边界，恰一核心-110与适配器[-110,-5,-5]，无其它fault；client通过/正式恢复。原报告不改，不为修报告重做实验。保护394丢ACK重启/ramoops及395两微秒复位/readback/freshACK后释放修复。

## 下一步（主线工作）

接IPA prepare/result、407..416原厂数学与真实曝光/增益/统计/输入域，生成非零LTM/LCE；history只最终图像processed(success)提交，失败discard。Media Request完成不等于图像成功。IFE已有CC/Gamma，未经域证明不再次叠原厂RGB曲线。补实际缺的LA/mask/weights/scalars/inverseGamma，优先主摄再复用四摄；基础AE/AWB/IFE调校已存在。当前通道已部署，不再把打包或失ACK验证当未完成主线。

完整scope读reference/kernel363/REMAINING-CAMERA-SCOPE.md：四摄GW1主/IMX319广角/S5K3M5长焦/IMX471前基础可用不等于原厂画质；第五2MP身份未定，vendor OV02A1B不足以证明，PHY2/MCLK2/reset12/GPIO29与前共享需正确mux，不能猜OV02A10。多模式/帧长/防频闪、连续AF/光学/几何/多摄同步、implicitfences/SSC/旋转未全复验。

原厂数学细节416及419归档：IPE input SP340非SP240；2760调校管理器非版本；cache149a8.version1才设request1，否则初始0/ptr3024。HDR88/92槽1/0 time/sensitivity比，control2零。154TMC两架构一致仅合成统计。darkY不clipanchor1/nohistBYTE1/原地左值已更新/firstgain>=1024不夹unity；raw124/140身份未解、90次计算非帧、历史atten前ADRC后待commit。406显式IP位勿回退HAL DC/quarter gate，maskhalo/crop保留；405unknownDMA整parcel+images保引用。

## 环境

每次WSL访问source/build/ext4先root storage284.mounted_build挂原32GiB，勿重建/格式化；source354/build在/mnt/samurai-full282。root PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原厂系数/夹具/ELF/图像/完整日志仅/mnt/e/edk2-samurai-out/kernel420及前序。公共仅作者代码/脱敏报告，mirror本地scoped commit护无关index，不push/PR。保护NV/OTP/个体备份/密钥/电池温控；未知事务先查。按改动验证、复用未变结果，不默认全量扫描/固定次数/重复下载。
'''
assert len(text.encode())<=6500,len(text.encode())
archive=ROOT/'archive/NEXT-SESSION-through419-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从420继续完整多摄/ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/420README。已正式安装419生产core63131+adapter46f9和签名r31/r26用户空间，四摄48+dual6+isolated27+普通PipeWire12=93direct，failed/cancel0。各摄requests=1，自动IPE参数仍旁路。6IPA同r30，旧配置/数据保持。worker10893/client/collector终态，PW11073/WP11076，资源回收，新fault0，历史taint512/guard394保持，无重启。旧包/模块离线回退已存但本轮未执行。勿再把419故障或420打包当未完成；直接推进IPA prepare/result与真实统计/曝光/输入域和407..416数学，最终图像成功commit失败discard，防重复IFE已有CC/Gamma。419原worker混时钟false保留，严格fault-verifier passed，不重复注入。维护源419commit07d2ca7干净，Image/DT/CAMSS/FW未变。363全部第五摄/AF/光学/模式/同步scope仍有效。WSL先storage284挂原ext4；原厂私存、本地scoped提交不push。\n')
note='420当前：419生产驱动与签名libcamera r31/config-stack r26已正式安装；四摄/RAW双流/隔离IPA/普通用户PipeWire共93direct完成，错误与取消0，各摄日志requests=1。资源回收、新fault0，历史taint512保留。自动IPE画质参数仍旁路，完整校准继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel420/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel420/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel420/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('419当前：');p.write_text(note+'[420证据]('+link+')。以下为历史。\n\n'+rest)
for package in ['libcamera','samurai-camera-config']:
 for base,prefix in [(HERE/'recipes','../../../../reference/'),(ROOT/'linux-port/packages','../../../reference/')]:
  p=base/package/'README.md';first,rest=p.read_text().split('\n\n',1);p.write_text(note+'[420证据]('+prefix+'kernel420/README.md)。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[419 逐帧IQ失ACK恢复与ERROR出队](reference/kernel419/README.md)','[420 正式逐帧IQ通道与93作业验证](reference/kernel420/README.md)'))
save(HERE/'source-state.json',dict(stage=420,kernel_source_commit=h['driver_source_commit'],kernel_source_unchanged_from419=True,userspace_source='/mnt/samurai-full282/libcamera420-request-r31/src/libcamera-v0.7.2',numerical_ipa_unchanged=True,driver_pair_installed=True,userspace_installed=True,automatic_ipa_iq_generation=False,full_goal_active=True))
print(json.dumps(dict(stage=420,next_bytes=len(text.encode()),formal_recipes_updated=True,passed=True)))
