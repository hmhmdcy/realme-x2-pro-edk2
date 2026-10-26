"""Record target policy/cache progress without claiming Android runtime observation."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
report=json.loads((HERE/'runtime-validation.json').read_text());assert report['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.update(tmc11_target_dependency_version_policy_verified=True,tmc_adrc_metadata_cache_copy_verified=True,
    tmc_ltm_version_selection_gate_verified=True,tmc_metadata_previous_input112_label_corrected=True,
    tmc_ipe_request_version_global_table_owner_verified=False,tmc_runtime_metadata_actually_observed=False,
    tmc_runtime_version_selection_verified=False,tmc11_verified=False,tmc_trigger_and_mix_policy_verified=False,
    full_ltm_numeric_math_complete=False,phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    p=ROOT/rel;d=json.loads(p.read_text());assert d['latest_work_stage']==414 and d['current_device_revalidated_stage']==406
    for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=415
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
        kernel_source_scope='406 clean explicit-IP kernel unchanged.415 offline target TMC11 dependency/version policy,IPE ADRC cache wire transport,LTM version gate.No device/default integration.',
        in_progress_installed_scope='415 offline only;last406 restored formal395/393 four cameras48;no new phone workers/frames/module changes.',
        ipe_ltm_tmc_target_dependency_version_policy_verified=True,
        ipe_ltm_tmc_adrc_metadata_cache_copy_verified=True,ipe_ltm_tmc_ltm_version_gate_verified=True,
        ipe_ltm_tmc_runtime_policy_evidence=prefix+'kernel415/runtime-validation.json',
        ipe_ltm_tmc11_scope='414 three-layer interpolation and136dynamic numeric chains retained.415 target policy733+7invalid/consumer1152+3/metadata63+1,hostASanUBSan/ARM bytes44400/18480/271360 equal.Module enable raw->version;locks after cache;force equal triggers retains histogram.Property missing clears only enable/unknown version keeps knees.Exact wire transport not hardware validation.IPE node149a8 cache corrected from earlier ISPInput112 label.Request version global table owner and actual Android value unverified.',
        ipe_ltm_tmc_version_mix_policy_verified=False,ipe_ltm_tmc11_verified=False,
        ipe_ltm_adrc_numeric_math_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
        ipe_ltm_curve_product_integrated=False,ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
        ipe_latest_stage_frames_scope='415 offline only;last406 device evidence not counted again.',
        current_health_scope='Last physical check406-r2 restored formal395/393 four cameras48/resources released.407-415 no device access.',
        icp_next_step='Trace request version global table owner/init at2cfa70..2cfaa0 and complete producer-property-consumer dataflow/freshness;full SWTMC11 Execute/continuous states with existing storage.Then HDR88/92,408raw124/140/requestcommit,remaining IQ/domain/stats,nonzero hardware/continuous/recovery/media request-libcamera;full363 scope remains.')
    p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through414-2026-10-21.md';assert not archive.exists()
archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：415（TMC状态/版本门槛/ADRC缓存通过；实机仍406）

先读WORKING-BOUNDARIES.md和reference/kernel415/README.md。完整多摄/骁龙ISP目标active。414归档archive/NEXT-SESSION-through414-2026-10-21.md。用户开灯出门，样本按实际照明/曝光解释。

## 415新增与下一步

kernel415/libipa/tmc_runtime验证本机TMC11依赖/版本、IPE metadata缓存及LTM选择门槛。733valid+7invalid policy、1152+3consumer、63+1metadata，两架构hostASanUBSan/ARM SDKQEMU各44400/18480/271360B零差；target169658policy指令无provider、metadata+consumer18117指令仅51memcpy。已有ADRC存储前提，不测分配/完整Execute；根选择复用412，数值复用414/413未重复全量。

policy入口383728到383cdc(将计算)或38565c(退出)：只有缓存空/UID变才刷新root/enable，区别新版含enable/dynamicmask比较。只有moduleEnable==1才算，raw值直接写请求3016版号；六触发floatabs→double<1e-9。触发变更新全部缓存/有新hist才换指针；相等仅force==1重算不换hist。禁用时发布已有ADRC指针到请求3024，module104指针清零但ADRC旧对象不清；AWB/AE bytes98/99同时==1在缓存/版本更新后抑制计算。

纠正早期ISPInput112标签：2d0050/54构造14938，2d0150/58存node+14938到SP408；2dffe4..2e01f8写其112，即真正node+149a8的4236B ADRC缓存，版本+4。v0膝点拷32B留union尾8，v1拷40，未知版保留旧膝点但公共区照拷；属性缺失只清enable。公共wire接口保持此语义，不是硬件验证器，接入必须查来源/新鲜度/版本/请求归属。

LTM360088选择gate：root10存在且enable1/use_ltm1/请求version0→363988自身10分支，已验证至363994 flag；否则读上游指针并copy ltmEnable，未额外globalenable/version gate。未执行自身10分配/完整计算。注意请求version来源还未闭合：2cfa70..2cfaa0全局基址60e3d8+索引*8+189f28取64bit→写请求3016，owner/init/实际值未明；别拿新版IPENode从m_adrcInfo.version赋值当本机证据。下步优先找该表写入/初始化、producer→属性→consumer完整流、旧缓存处理；可完整SWTMC11 Execute/连续状态。此前无挂起进程。

HDR88/92身份、408raw124/140/state随请求commit，再LA/mask/weights/scalars、352inverseGamma、IFE/IPE输入域/统计粗级、非零全调校实像素/连续参数/恢复/标准media request-libcamera继续。实际Android运行版/fullLTMnumeric/product/default仍false。reference/kernel363/REMAINING-CAMERA-SCOPE.md完整范围保持：第五2MP/OV02A1B身份mux勿猜OV02A10、多模式/帧长/防频闪、连续AF/光学、几何/多摄同步，implicitfences/SSC/旋转未全复验。

## 414/413/412/411保留

414三层前缀383cdc..384048：搜索4ac150/4ac498/4ac908、回调4ab450均原指令仅memset。root136B/DRC24/HDR40/AEC192=trigger16+region176；root ctrl68/72、core120/128；module64root/72DRC/80gain/84lux/88及92HDR，X23=SP64。HDR0读88/1读92/2实际触发零并选第三区间，88/92身份未证勿套新版第三HDR浮点输入。

2846valid(2524factory+322多层合成)+15invalid两架构514980B0差，2847529target指令；68根全ctrl[0,0]且DRC/HDR各1段，forcedgain/HDR1/2/多层只夹具；关闭根不启，qtechGW1未绑定非第五相机。动态68根各2=136/51gap，portable tree实际输出→gen/sample/ADRC/sourcepacker/nativeLUT：全生成1127712B等，131LUT67072B等/5subunity拒绝。分进程合成stats非runtime，math provider hostlibm，最终原HALpacker未跑。

413actual gen384048..38565c：198区去重31组156+12invalid两架构1393056B等，154finite/2nonfinite拒绝；142LUT72704B等/12subunity拒绝。module76dark/96hist/104ADRC/112Gamma257，X24=module112。defaultGamma38396c..383a28从0/FF写同编译表末1023，controlledGamma非运行使用证据；logweights/db39c、Gamma/d5fe8私存。darkY=anchor2/ratio不clipanchor1，generation-r1 26项251B已修；model-r1 X23错/r2漏X24失败保留。nohist是BYTE1=01010101非float1，区别zero hist；hist4轮原地平滑右后左且左已更新，coeff b按/h再/h。

412 68根198区XML等，4物理14普通上下文28查询与GetModule相符，全model2/order5；Bezier未验。主/广两版on、前两版off、长焦10off/11on不能推实际运行版。412/411数值与源版本差异详各README，既有测试复用。

## 底层与设备

维护内核406 samurai-ipe-full-pass-ip406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；407-415仅用户空间数值，SoC/板级DT/主线/传感器/DMA/请求/default不改，phone/新worker/新帧0。原厂源码/系数/表/ASM/XML/产物/日志图像密钥私存/mnt/e/edk2-samurai-out/kernel415及前序，公共mirror仅本地提交不push/PR，保护无关index。

408Face首指针124float，BPS10003或raw140==1跳state，勿猜HDR/flash；signal>0切换重置90次计算非帧，previous+(current-previous)*.05独立float；strength→smoothing→保存proposed历史→atten→quant，ADRC后，history勿存atten后，仍需requestcommit。409 scale3/curve4顺序平滑更新左值；407signed delta<0或>=32768置bit11，漏大正delta698B已修。

406 stripe416=explicitIP→reg5c60bit10，勿恢复原HAL DC&&IP&&quarter>=72×54 gate到当前单fullframeAPI；IP&&mask324step/6halo/crop±2else328/4，outputcrop保持。正确private406/core-intree-r1.ko415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4，test-intree旧405。406R2 fixed52=44LTM+8Gamma 640/650×480 NV12/21，mask移位修，LA灰块非彩色全图常量，LTM+linearGamma最大差1；两轮200仅transport。20269/20313及21352/21413/clients终态。恢复正式395/393/CAMSS389，r30/r25四摄48/error-cancel-extra0，资源释放/双CCI等休眠/17clks0/9railsdisabled-users0/taint0，PW21581/WP21584 uid10000单例/owner_refs53桌面句柄。407-415未访问不作新健康声明。

host406→…394同boot394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt；保护394丢ACK重启/206061Bramoops和395reset2us/readback/双IPE freshACK后退役修复。未知事务先查；Image363/DT389/logdump365/SGownerFW不改。405typed2800锁内copy/check后MAP，IQ8944/pre32/post96/type1-opcode1-reg5c08/13LUT2736，未知DMA整parcel保留。source/build先root storage284 mounted_build()挂原32GiB ext4勿格式化；rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/个体备份/密钥/电池温控。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从415继续完整多摄/骁龙ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/reference/kernel415/README。TMC11 policy733+7/metadata63+1/LTMgate1152+3两架构44400/271360/18480B0差；仅已有ADRC分配。UID-only刷新、raw enable→3016version、force相等不换hist、双锁在缓存/版本更新后抑calc；禁用仍发布旧ADRC3024。metadata真正node149a8，早期ISPInput112标签错误已纠正，v0拷32/v1拷40膝点，未知保留旧膝点，缺失只清enable，wire层不是硬件验证器。LTM own10条件rootenable1/useLtm1/version0，否则copyupstreamLtm，无globalenablegate。下一步查2cfa70..2cfaa0请求版本全局表60e3d8+index*8+189f28的owner/init/实际值，不能据新版m_adrcInfo.version推本机；producer→property→consumer新鲜度及完整SWTMC11 Execute/连续状态。414三层及136动态chain/131LUT、413生成保留；随后HDR88/92/408raw124/140/requestcommit/其余IQ域统计/非零硬件连续恢复/libcamera及363全scope。内核406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；416explicitIP勿恢复DCquarter，395reset修复保持。407-415 phone0,last406正式395/393四摄48 guard394。已开灯。先storage284挂原ext4；原厂私存，公共仅本地提交不push/PR。\n')
note='415当前：本机TMC11状态/版本策略、IPE元数据缓存拷贝和LTM选择门槛已逐字节核对；请求版本全局表来源/完整调校/实机接入继续，最后实机仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel415/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel415/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel415/README.md')]:
    p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('414当前：')
    p.write_text(note+'[415证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[414 TMC11三层插值与动态链](reference/kernel414/README.md)','[415 TMC状态与版本门槛](reference/kernel415/README.md)'))
print(json.dumps(dict(stage=415,next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,last_device_stage=406,full_goal_active=True)))
