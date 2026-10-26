"""Publish the geometry checkpoint while keeping last phone evidence402."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];state=json.loads((HERE/'source-state.json').read_text());build=json.loads((HERE/'intree-build-validation.json').read_text())
for name in ['serializer','layouts','iq-geometry','model-source','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert not build['diagnostics'] and state['clean'] and not state['installed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=404
 for key in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[key]=state['branch']
 for key in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[key]=state['commit']
 assert d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==402
 d.update(current_camera_evidence=prefix+'kernel404/README.md',latest_stage_device_mutated=False,latest_stage_phone_accessed=False,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,
 kernel_source_scope='404 shared native full-frame 1:1 LTM/bypass geometry, including IP/mask and DC quarter-pass conditions. Not LTM IQ/LUT runtime support. Gamma402 opcode1 retained; candidate built, not deployed.',
 in_progress_installed_scope='404 offline only; no phone access, capture, installation or transition. Last hardware402-r2 formal395/393 restored, four cameras48 and resources released.',
 ipe_ltm_native_full_striping_complete=True,ipe_ltm_native_full_striping_scope='Full-frame 1:1 NV12/NV21 port8/9,core1/2,valid even128..8192 layouts.126 complete target-HAL/FW CDM/job comparisons; not scaling,rotation,multiple passes,runtime or tuning math.',
 ipe_ltm_native_full_striping_evidence=prefix+'kernel404/serializer-validation.json',ipe_ltm_native_layouts_evidence=prefix+'kernel404/layouts-validation.json',ipe_ltm_native_iq_geometry_evidence=prefix+'kernel404/iq-geometry-validation.json',
 ipe_ltm_geometry_mask_filter_required_for324_and6=True,ipe_ltm_geometry_partition_rule='IP && mask: step324,halo6; otherwise328,4. Both use descending chroma-aligned ranges rounded to cores.',
 ipe_ltm_geometry_dc_condition='DC && IP && aligned_quarter_width>=72 && aligned_quarter_height>=54; quarter=((dimension+7)/4)&~1. Even full-frame threshold282x210.',
 ipe_ltm_runtime_submission_enabled=False,ipe_ltm_hardware_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
 ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
 ipe_latest_stage_frames_scope='404 offline only,0frames.402-r2 fixed Gamma20 and normal48 remain the last physical evidence;402-r1 failed pixels retained.',
 current_health_scope='404 native geometry and build only; last phone402. No claim of new hardware health or full LTM/automatic tuning/optical/AF/SSC/rotation verification.',
 icp_next_step='Implement typed full LTM IQ and13LUT layout plus same-request ownership using404 checked geometry. Expand pre array for CST+LTM11, preserve post CC/CV/Gamma12; complete factory numeric math/interpolation,input-domain audit,then hardware pixels/recovery and standard request/libcamera,remaining363 scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through403-2026-10-21.md';assert not archive.exists();old=(ROOT/'NEXT-SESSION.md').read_text();archive.write_text(old)
device=old[old.index('## 最后设备402'):].replace('（403无访问／帧／安装）','（404无访问／帧／安装）').replace('403只复用该历史证据','403／404只复用该历史证据').replace('host403→402','host404→403→402').replace('私存403与前序','私存404与前序')
module=build['modules'][0]
text=f'''# 当前检查点：404（原生LTM全帧几何对齐，最后实机402）

先读WORKING-BOUNDARIES.md、reference/kernel404/README.md。完整多摄／骁龙ISP目标active。用户已开灯出门，后续现场样本按实际照明／曝光判断。403交接归档archive/NEXT-SESSION-through403-2026-10-21.md。

## 最新源码与实证

404 branch {state['branch']}，HEAD {state['commit']}，父403 {state['parent']}，两文件干净未部署。新增类型化geometry bool data_collection/image_processing/mask_filter，camss_a5_ipe_ltm_size和encode_ltm_striping；旧bypass通过全关闭flags调用同一内部ipe_encode_striping，ABI保留。完整全帧1:1 NV12/NV21 port8/9、core1/2、even128..8192及合法padding；不支持缩放/旋转/多pass，不激活LTM运行时。

mask=IP&&mask_filter：仅此时324/6并将内部处理区域左右扩2；否则328/4。403的324/6发现仅适用于mask开启夹具，勿继续以IP alone决定。grid起点/length/处理crop使用扩展区域；输出port/full/half crops、plane lengths/radial仍用原outputfirst/length。fetch/workload按实际新分区。DC全帧继承IP条件为DC&&IP&&(((W+7)/4)&~1)>=72&&(((H+7)/4)&~1)>=54，即even282x210临界，不能用288x216。

实际C：serializer78、padding layouts16、independentIQ16+explicitDC/IP/mask16＝126次完整原HAL/FW512KiB CDM和32B job对照零差，共66060288B+4032B；hostASanUBSan和AArch64QEMU均执行。serializer每架构373152B一致，非法/短容量/参数/tail保护通过。mask-off会改变条数，650双核由4降2，8192单核26降25。IQ几何随机合法字段含bin count/termination/RGamma/LA/mask等，未将全零LUT夹具实际提交。所有测试函数与候选源码匹配，见model-source-validation.json。

原型失败均保留：首个全crop/radial扩展在640差19B；最初DC阈值在286/288附近6cases各差1B，serializer-r1-validation；遗漏mask条件的IQ随机16中多例失败，iq-geometry-r1-validation。追踪真实HAL写入/复制/分配得到quarter检查，再补mask typed字段；未改HAL指令。模型源码检查发现IQ模型尚未更新本地mask变量重构，重新编译/执行32cases后通过，不拿旧模型冒称当前源码。

W1/Werror构建0diag，核心{module['bytes']}B/SHA{module['sha256']}，共享config/outputs/symvers恢复，未安装。构建及源码状态见404对应JSON。DMA/map/unknown-DMA/reset/typed Gamma原路径未新增改变，Gamma opcode1保留，板级/传感器/产品用户空间不变。

## 下一步与组合边界

接完整类型化LTM IQ92B/13LUT2736B与同request ownership，再用本轮geometry；pre数组扩为CST generic20+LTM11两项，post CC/CV generic20+Gamma12最多3项。当前Gamma pre仅容一项，不能直接追加覆盖。保留map/unknownDMA/reset/free，LUT不能压栈。继续full LTM数值与动态触发插值；再物理像素/错误恢复、标准media request/libcamera及IFE/IPE输入域核对，避免双重CCM/Gamma。

403 ABI证据继续：resource3296B但传输2736B，额外560用途未证；13tables offsets0/48/304/560/816/1072/1328/1392/1456/1712/1968/2224/2480，sizes48,5x256,2x64,5x256；sourceCmdType1/CDMDMI opcode1 reg5c08 selectors1..13 heads156B，pre type11 disabled255。IQ2096..2184/23u32/92B；原HAL enable还受ANR440==1或topology2624==3约束。原逆Gamma29输入miss/hit7424B与352sourceoracle零差，IFEgreen64→14bit64段，不可把IPE256代入。完整factory动态math尚未完成。

原厂完整树在350Gamma、351LTM149roots/2135regions和CCM43/737、399CST/CV17/71roots1350leaves，全私有未默认激活。CC actualtype2 offsetsigned11；CST2092→5a60、CC2188→5e60、CV2200→6460、Gamma2192→6060（DMI6008 G/B/R），原有固定诊断证据不外推完整产品自动调校。

'''+device
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从404继续完整多摄/骁龙ISP目标active。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel404/README.md。原生全帧1:1 LTM几何已和完整原HAL/FW126次CDM/job对齐，hostASanUBSan/ARMQEMU及W1Werror通过；mask条件关键：IP&&mask才324/6/处理扩2，否则328/4。DC条件为alignedquarter>=72x54，即even282x210。branch '+state['branch']+' HEAD '+state['commit']+'，两文件干净未部署；共享bypass原API，runtime/DMA/reset/Gamma opcode1保持。下一步完整typed LTM IQ92B/13LUT2736B、same-request ownership、pre扩CST+LTM11，再full数值/动态插值和实机pixels/recovery、标准media request/libcamera与IFE/IPE职责。404无手机访问，最后402-r2 Gamma20与恢复正式395/393四摄48/资源释放，历史失败保留，旧worker均终态勿重启。host404/guard394，全部363剩余范围继续。source/build先root storage284挂原ext4，保护原厂/个体表与密钥。\n')
note='404当前：原生LTM全帧1:1几何与原厂完整命令126次对照零差，补齐mask／DC边界并共用旁路编码，构建通过。完整LTM数值／运行时仍待做，本轮无手机访问，最后实机402。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel404/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel404/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel404/README.md')]:
 p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('403当前：');p.write_text(note+'[404证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[403 LTM契约／逆Gamma与原生分区](reference/kernel403/README.md)','[404 LTM全帧几何与原厂命令对齐](reference/kernel404/README.md)'))
print(json.dumps(dict(stage=404,checkpoint_updated=True,last_device_stage=402,full_goal_active=True)))
