"""Record candidate LTM request ownership, keeping last device402 explicit."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];state=json.loads((HERE/'source-state.json').read_text());build=json.loads((HERE/'intree-build-validation.json').read_text())
for name in ['parcel','transfer','firmware-parcel','source-model','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert not build['diagnostics'] and state['clean'] and not state['installed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=405
 for key in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[key]=state['branch']
 for key in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[key]=state['commit']
 assert d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==402
 d.update(current_camera_evidence=prefix+'kernel405/README.md',latest_stage_device_mutated=False,latest_stage_phone_accessed=False,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,
 kernel_source_scope='405 typed LTM IQ/LUT, expanded pre/post layout and same-request ownership/internal synchronous API. Geometry404 retained. Built candidate,not installed; full numeric tuning and hardware LTM not verified.',
 in_progress_installed_scope='405 offline only,no phone access or frames. Last physical402-r2 formal395/393 restored,normal four cameras48 and resources released.',
 ipe_ltm_typed_iq_lut_interface_added=True,ipe_ltm_internal_submission_api_added=True,ipe_ltm_runtime_submission_implemented=True,ipe_ltm_runtime_submission_enabled=False,ipe_ltm_runtime_submission_scope='Implemented candidate internal run_ltm_status only; not installed or called by product adapter/libcamera. NULL falls back to existing Gamma/colour.',
 ipe_ltm_product_default_enabled=False,ipe_ltm_hardware_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
 ipe_ltm_combined_iq_bytes=8944,ipe_ltm_combined_iq_allocation_bytes=12288,ipe_ltm_cpu_copy_bytes=2800,ipe_ltm_pre_array_offset=32,ipe_ltm_post_array_offset=96,ipe_ltm_pre_max_programs=2,ipe_ltm_post_max_programs=3,ipe_ltm_same_request_lut_ownership=True,
 ipe_ltm_parcel_evidence=prefix+'kernel405/parcel-validation.json',ipe_ltm_ownership_evidence=prefix+'kernel405/transfer-validation.json',ipe_ltm_combined_firmware_evidence=prefix+'kernel405/firmware-parcel-validation.json',ipe_ltm_source_model_evidence=prefix+'kernel405/source-model-validation.json',
 ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,ipe_latest_stage_frames_scope='405 offline only,0frames;402-r2 Gamma20 plus normal48 are retained historical evidence.402-r1 failed pixels remain separate.',
 current_health_scope='405 candidate codec/request/build verified offline only. No new hardware health or LTM/optical/AF/SSC/rotation claim; last phone402.',
 icp_next_step='Complete original LTM numeric/interpolation and IFE/IPE input-domain policy; exercise405 typed request with fixed diagnostic adapter on hardware,validate pixels and recovery,restore formal camera path. Then standard media request/libcamera and original dynamic triggers,remaining363 full camera scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through404-2026-10-21.md';assert not archive.exists();old=(ROOT/'NEXT-SESSION.md').read_text();archive.write_text(old)
device=old[old.index('## 最后设备402'):].replace('（404无访问／帧／安装）','（405无访问／帧／安装）').replace('403／404只复用该历史证据','403／404／405只复用该历史证据').replace('host404→403→402','host405→404→403→402').replace('私存404与前序','私存405与前序')
mod=build['modules'][0]
text=f'''# 当前检查点：405（LTM类型化请求与所有权，最后实机402）

先读WORKING-BOUNDARIES.md、reference/kernel405/README.md。完整多摄／骁龙ISP目标active。用户已开灯出门，后续按实际照明判断。404交接归档archive/NEXT-SESSION-through404-2026-10-21.md。

## 候选实现与证据

branch {state['branch']}，HEAD {state['commit']}，父404 {state['parent']}。四文件colour.c/h、boot.c、ipe.h；干净未安装。新增camss_a5_ipe_run_ltm_status(a5,session,job,colour,gamma,ltm,result)，NULL LTM回原Gamma/colour。旧job/colour/Gamma布局和函数体未变，404几何未变。内部API已实现，不等于产品已调用或物理验证。

LTM CPU类型2800B：IQ22个有名u32（enable由显式请求固定1）；weights12xu16；LA2x64、curve64、mask64为u12base/s12delta，scale64/LCE2x16为s12base/s12delta；RGamma5x64为u14base/s14delta。拒绝越界/非0或1标志，不接任意CDM/寄存器/设备LUT地址。

组合IQ8944B/PAGE_ALIGN12288。arraybase2592、空common0、pre32(absolute2624,max2)、post96(2688,max3)；CST2784/56、CC2840/44、CV2884/40；GammaDMI2928/36、LUT2976/3072；LTMDMI6048/156、LUT6208/2736。pre CSTgeneric20+LTM11，post CC/CVgeneric20+Gamma12。旧Gamma路径6016/8192、pre32/post64仍保留，不能拿新post96用于旧API。

lock内先复制Gamma（可选）再LTM，校验副本后才coherent alloc/MAP；geometry DC/IP/mask从已检查ltm_copy读取。IQ/LUT与frame/stripe/scratch/BL在同一保留请求；临时CPU副本所有出口释放。未知MAP/frame/UNMAP或清理失败保留DMA backing，quiesce/reset前禁止释放。原有DMA/reset所有权未放宽。

parcel实际C hostASanUBSan/ARMQEMU各128cases1144832B零差，110invalid保持输出/tail；IQ92B对实际HAL3669e0..366b4c，DMI对实际WriteDMI/nested（type1 opcode1）。LUT packing在private编译403固定source四个packer，e2；仅量化打包，不是full numeric HWSetting/ADRC。夹具修正见405README，HAL未改。

firmware59cases：实际C页+404实际Cgeometry，完整HALstriping与FW CONFIG_IO/frameprepare止enqueue前，整512KiB CDM/32B job零差；全部colour/Gamma组合、NV12/21、128/326/650/1920/4608/8192和650分区改变DC/IP/mask组合；pre32/post96各链接一次，IQ页不变。base37+--extra22，无物理帧。

transfer145cases ASanUBSan：原4种路径、新LTM无/有Gamma、NULL LTM Gamma回退；每种18故障/成功情形，额外非法/分配失败。调用方在kmemdup后被provider改为ff，最终wire和geometry仍取副本；LTM或第二份copy失败均清理CPU副本/不分配coherent，不确定完成保留整个request和图像refs。transport/alloc/geometry是provider，404几何math另证；不冒称硬件fault/concurrency通过。source-model匹配15colour+6DMA+15request/cleanup共36真实函数。

W1/Werror构建0diag，核心{mod['bytes']}B/SHA{mod['sha256']}；共享config/outputs/symvers恢复。正式设备与adapter未动，Gamma opcode1保留，

## 下一步与既有约束

继续完整LTM数值/动态触发与输入域；尽快用固定诊断adapter验证405实际LTM组合像素和错误恢复，再恢复正式路径。不可将离线原厂packer和FW enqueue前对照当实机LTM支持。接标准media request/libcamera前明确IFE/IPE CCM/Gamma/逆Gamma职责与原HALANR440==1或topology2624==3的启用策略；当前内核API显式enable，不自动选择Chromatix。

404 geometry：仅IP&&mask用324步长/6halo/处理左右扩2，否则328/4；输出crop/plane/radial用原output范围。DC全帧继承IP条件为DC&&IP&&(((W+7)/4)&~1)>=72&&(((H+7)/4)&~1)>=54（even282x210），非288x216。full-frame1:1 port8/9/core1/2、even128..8192和合法padding；缩放/旋转/多pass未实现。403 raw LTM partition helper仅用于mask开启路径。

403 LTM ABI：13offsets0/48/304/560/816/1072/1328/1392/1456/1712/1968/2224/2480，sizes48,5x256,2x64,5x256，2736B传输；resource3296B额外560用途未证。type1/CDMDMI opcode1 reg5c08 selector1..13头156B/pretype11，IQ2096..2184/23u32/92B。原逆Gamma29输入miss/hit7424B对352sourceoracle零差，输入IFEgreen64而非IPE256。

原厂完整调校树在350／351／399私有目录，未默认激活；完整数值调校、光学与全部模式仍未完成。

'''+device
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从405继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel405/README.md。candidate '+state['branch']+' HEAD '+state['commit']+' 四文件干净未安装：新增run_ltm_status，typedLTM2800B先CPUcopy/check，几何来自副本，再IQ/DMI/LUT同request保留；NULL回旧Gamma/colour。组合IQ8944/PAGE12288，pre32 max2 CST20+LTM11，post96 max3 CC/CV20+Gamma12；旧Gamma仍6016/pre32/post64。128parcel host/ARM、145ownership、59完整FW prepare/CDM/job和W1Werror通过，无手机访问/物理LTM证明。下一步full LTM数值/动态触发/IFE-IPE输入域与启用策略，固定诊断adapter物理LTM组合pixels/recovery，再标准media request/libcamera。404 geometry关键IP&&mask324/6否则328/4，DC alignedquarter>=72x54。最后实机402-r2 Gamma20及正式395/393四摄48恢复/资源释放；历史失败保留，worker终态勿重启，host405/guard394。完整363剩余范围继续，source/build先root storage284挂原ext4，原厂/个体表私存。\n')
note='405当前：候选内核已实现类型化LTM IQ／LUT同请求所有权与组合提交接口，128参数页、145所有权、59完整固件对照及构建通过。未安装或实机验证LTM，完整调校继续，最后实机402。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel405/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel405/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel405/README.md')]:
 p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('404当前：');p.write_text(note+'[405证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[404 LTM全帧几何与原厂命令对齐](reference/kernel404/README.md)','[405 LTM类型化请求与所有权](reference/kernel405/README.md)'))
print(json.dumps(dict(stage=405,checkpoint_updated=True,last_device_stage=402,full_goal_active=True)))
