"""Record verified temporary IPA2 work without changing the formal deployment."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
h=json.loads((HERE/'current-state-validation.json').read_text());r=json.loads((HERE/'runtime-r2-validation.json').read_text());hw=json.loads((HERE/'hardware-r2-validation.json').read_text())
assert h['passed'] and r['passed'] and hw['passed'] and h['m2m']['completed']==239
s=json.loads((HERE/'source-state.json').read_text());s.update(post_fix_hardware_pending=False,post_fix_main_12_all_observations_committed=True,native_isolated_ipa_verified=True,native_in_process_ipa_verified=False,automatic_ipe_numeric_generation=False,numerical_tmc_history_integrated=False,phone_accessed=True,installed=False,all_transactions_terminal=True,last_device_evidence_stage=421)
save(HERE/'source-state.json',s)
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text());assert d['latest_work_stage']==420
 d.update(stage=421,in_progress_stage=421,latest_work_stage=421,current_device_revalidated_stage=421,ipe_latest_hardware_stage=421,icp_latest_device_experiment_stage=421,
  in_progress_installed=False,latest_stage_device_mutated=True,latest_stage_phone_accessed=True,
  in_progress_installed_scope='421 temporary matching IPA2/library/proxy tested then exited;production419 pair and installed420 r31/r26 files/notes/config unchanged.No kernel reload.',
  kernel_source_scope='421 kernel unchanged419;userspace owned same-SOF statistics history and aggregate result receipt;fix stats publication before synchronous IPA reentry and stop epoch guard.Candidate not installed.',
  ipe_frame_observation_history_hardware_verified=True,ipe_frame_observation_history_evidence=prefix+'kernel421/hardware-r2-validation.json',
  ipe_frame_observation_history_installed=False,ipe_numeric_tmc_ltm_history_integrated=False,ipe_candidate_private_ipa_version=2,
  ipe_statistics_publication_reentry_candidate_fixed=True,ipe_statistics_publication_reentry_fix_installed=False,
  ipe_media_request_iq_ipa_parameter_generation_integrated=False,
  ipe_latest_stage_actual_frames=146,ipe_latest_stage_RT_frames=146,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=24,
  ipe_latest_stage_frames_scope='421 added146direct=81r1candidate+41r2candidate+24formal-front rechecks;RAW-only6pairs noIPE.R1main10/12paired revealed reentry;fixr2main12/12.Isolatedr2 29images:28metadata matches,1real missingstats;one superseded receipt.No automatic IPE IQ.',
  ipe_current_cumulative_counters={k:h['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']},
  ipe_current_counter_epoch='420 production419 module epoch unchanged:239direct=420original93+421new146,starts/stops17.',
  ipe_current_failed_counter_scope='Current239all successful,no kernel failure/cancel;421r1 premature stats fallback andr2 genuine missingstats separately recorded,not image failures.',
  current_health_scope='421-r2 formal420 unchanged r31/r26/419pair;239direct,resources released,17clocks0/9railsdisabled/allPMsuspended,services13618/13621.Historical417 WARN taint512.',
  icp_next_step='421 real owned statistics/exposure/gain and final aggregate observation receipts are verified in matching IPA2 candidate;connect factory407..416 numerical TMC/LTM state and required LA/mask/scalars/inverseGamma with actual input-domain proof.Bind numerical state base revision for overlap/failures;missing stats need explicit reuse/bypass,no fabricated same-SOF inputs.Avoid double IFE/IPE CC/Gamma.421 not packaged;formal420 r31/r26 remains.Full363 scope remains.')
 for k,n in [('in_progress_evidence','README.md'),('current_camera_evidence','README.md'),('current_readonly_device_evidence','current-state-validation.json'),('device_closeout_evidence','current-state-validation.json')]:d[k]=prefix+'kernel421/'+n
 if rel.endswith('deployment-lock.json'):d.update(final_health_evidence=prefix+'kernel421/current-state-validation.json',system_services=dict(stage=421,services=h['services'],evidence=prefix+'kernel421/current-state-validation.json',current_boot_revalidated=True))
 save(p,d)
text='''# 当前检查点：421（真实观测/最终回执及统计发布重入修复）

读WORKING-BOUNDARIES.md、reference/kernel421/README.md。完整多摄/ISP目标active；用户已开灯。420归档archive/NEXT-SESSION-through420-2026-10-21.md。不要重跑已完成事务/算法矩阵。

## 421候选（未永久安装）

候选/mnt/samurai-full282/libcamera421-frame-history/src/libcamera-v0.7.2，基于已部署420r31。4文件0042补丁零fuzz复现。新增IPE观测拥有1024BHIST副本、同SOF曝光ns/物理增益、原始行/码/source、IFErevision、可用lux/exposureIndex和Gamma override标记。统计DMA可复用，不持旧buffer指针。Statistics携token/摘要到pipeline，最终tryComplete在图像/RAW配对后反馈success；RAW-only不提交，缺统计不造token。最大64pending，epoch/token单调，晚到旧成功superseded不回退，stop清pending。

**这是观测历史，不是TMC/LTM数学状态；自动IPE非零参数仍旁路。** 不能把Gamma override标记当传递域证明，不能把单曝光观测造为HDR双槽或DRC/darkGain/raw124/140。数学候选还要绑定计算所依赖的history版本/重叠请求/失败依赖，不能直接宣称成功commit数学已完成。

私有IPA接口2（YAML/内核UAPI未改），库/IPA/生成proxy配套构建/签名通过。最新r3 librarySHA9fb54db05e713f165dd00a203fa3c0e509f0a56ab1f3d7986a80afb60ae16597；IPAced9de9043e095314a7e3662f5bf56e26e6f88e356bbd6f3ce9312d67528e9f2，proxy15ec5035df641782ec189d088d36768525896e868a21ea39020f5f2f89bd4973。不要只换单个新IPA2组件。22history+12实际aggregate+11实际stats/queue函数ASanUBSan共45项，native实测默认/强制隔离；**原生in-process IPA未测**。

## 重入问题及实机

r1 worker12693/root /var/lib/samurai/k421-history-r1：四摄48+dual6+isolated27=81IPE，RAW-only六对不启IPE且6观测全discard；正式前摄再12。主摄12图像仅10观测配对/commit，13prepare/3abort。SOF1/2明明有观测却fallback：statsProcessed先erasepending，调用queueIspUpdate→同步prepareParameters，等待期间递归处理相机事件，histogram尚未发布，completeMissing错误判缺。旧函数模型重现counterexample。

修复先发布/认领统计再同步IPA调参；返回后检查running/epoch；queueIspUpdate也防停流后使用已释放paramsbuffer。r2 worker13575/root ...k421-history-r2只复测受影响主摄/隔离路径，不重跑其它物理摄/RAW：主摄12/12观测配对及commit、无metadata fallback；隔离29图像/29观测，28有配对回执（27commit/1晚到旧sof superseded），1未认领观测abort。应用28份有统计曝光/增益与同SOF记录匹配；**应用SOF7确实没有BHIST，metadata恢复且无token/回执，不计为匹配**。正式前摄再12。

r2首次离线checker错误假设每图像都有BHIST，KeyError7保留hardware-r2-first-check-validation；修checker明确计无统计并核对无commit，未修改原worker或为修报告重拍。r1/r2 worker/client/collector全终态、rawpayload/日志保留。源准备几次文本空白断言失败均仅主机；r2第一次launch缺staging-r2报告在发命令前退出，补保存报告后才launch。不能重启旧事务。

## 正式设备保持420

已装五libcamera运行包99990.7.2-r31+config/stack0.1.0-r26；419生产core/adapter。421仅临时库/IPA/proxy环境，未改正式文件/个体配置/加载notes、未卸模块/刷写/重启。当前239direct=原420的93+421新146（81+41候选及24正式），failed/cancel/firsterror0、starts/stops17。PW13618/WP13621 uid10000各一，owner_refs53桌面CAMSS句柄。ICP/CAMSS双CCI suspended，17clk0/9railsdisabled-users0，CPU/IRQ/PM/map/import释放，新fault/dump0。历史417WARN taint512保留；guard394=/var/lib/samurai/k394-recovered/boot-id-private.txt保持。

维护内核source354 branch samurai-ipe-error-buffer419 commit07d2ca735f88649587c0e89802febff6dbf2b443干净。core419848B SHA63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632，adapter132400B SHA46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、DT389/CAMSS389/logdump365/SGownerFW未动。**e27吞ACK测试核心不能当生产**。保护394重启/ramoops和3952us脉冲/readback/双freshACK后退役修复；419原worker混时钟false与严格有序verifier成功分开保留，不重复注入。

## 接续主线

直接在421真实观测/回执位置接407..416原厂数值及本路径所需LA/mask/weights/scalars/inverseGamma，确认IFE/IPE域，防重复已有CC/Gamma。区分缺统计的明确沿用/旁路与“有统计却被重入提前完成”；后者候选已修，正式r31尚未收录。匹配IPA2库/模块/proxy后续统一集成，当前421未打包。不把全部观测/模型通过当完整画质或数学状态已完成。

全scope reference/kernel363/REMAINING-CAMERA-SCOPE.md：GW1主/IMX319广角/S5K3M5长焦/IMX471前基础取流；第五2MP身份/mux未完（vendor OV02A1B不足证明，PHY2/MCLK2/reset12/GPIO29共享前摄不能猜OV02A10）；多模式/帧长/防频闪、连续AF/光学/几何/同步、implicitfences/SSC/旋转未全复验。SoC/板级/主线/驱动/用户空间分层。

原厂数学416及420归档：IPE input SP340非SP240，2760调校管理器非版本，cache149a8.version1才设request1否则初始0/ptr3024；HDR88/92槽1/0 time/sensitivity比，control2零。154TMC两架构一致仅合成统计。darkY不clipanchor1/nohistBYTE1/平滑左值已更新/firstgain>=1024不夹unity；raw124/140未解，90次计算非帧，历史atten前ADRC后待数学commit。406显式IP位勿回退HAL DC/quarter gate；405unknownDMA整parcel+images保引用。

每次WSL源码/build/ext4访问先root storage284.mounted_build挂原32GiB，不重建格式化。root PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原厂系数/ELF/图像/完整日志私存/mnt/e/edk2-samurai-out/kernel421及前序；公共只作者代码/脱敏报告，本地scoped mirror提交护无关index、不push/PR。保护NV/OTP/备份/密钥/电池温控；未知事务先查；按改动测试，不默认全量扫描/重复下载。
'''
assert len(text.encode())<=6500,len(text.encode())
archive=ROOT/'archive/NEXT-SESSION-through420-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从421继续完整多摄/ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/421README。421私有IPA2候选拥有真实同SOF BHIST/曝光/增益/IFE版本，最终图像+RAW后回执；45模型通过，四摄/RAW/隔离实测。仅观测history，非TMC数学状态/非自动非零IQ。r1主10/12观测暴露erasepending→同步IPA→hist发布前重入缺陷，候选改先发布认领、加停流epoch保护；r2主12/12，隔离29图像28有统计元数据匹配/1真实缺统计无commit；1旧成功superseded，不能倒退历史。checkerKeyError7已保留并仅修分析不重拍。两事务终态，正式420的r31/r26及419模块未改、当前239direct failed/cancel0，资源回收/PW13618/WP13621，历史taint512/guard394。421未打包，不混IPA1/2。接原厂407..416数值所需LA/mask/scalars/inverseGamma和域证明，数学history须绑定base版本并处理重叠失败；防重复IFE CC/Gamma。勿重跑旧事务/大矩阵，363第五摄/模式/AF/光学/同步scope保持；WSL先storage284挂原ext4，原厂私存，本地提交不push。\n')
note='421当前：IPA2候选真实同SOF观测/最终回执通过，修复同步IPA期间过早判统计缺失，主摄修复后12/12观测配对；真实缺统计及乱序提交分开处理。候选未安装，正式420 r31/r26及419驱动保持，当前239direct错误/取消0。自动非零IPE数值及完整校准继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel421/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel421/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel421/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('420当前：');p.write_text(note+'[421证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[420 正式逐帧IQ通道与93作业验证](reference/kernel420/README.md)','[421 真实观测与统计发布重入修复](reference/kernel421/README.md)'))
print(json.dumps(dict(stage=421,next_bytes=len(text.encode()),full_goal_active=True,passed=True)))
