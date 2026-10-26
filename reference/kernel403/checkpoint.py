"""Record verified LTM ABI/inverse math and native partitions, last phone402."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];state=json.loads((HERE/'source-state.json').read_text())
for name in ['contract','inverse-hal-29','partitions','native-partitions','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for k in ['stage','in_progress_stage','latest_work_stage']:d[k]=403
 for k in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[k]=state['branch']
 for k in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[k]=state['commit']
 assert d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==402
 d.update(current_camera_evidence=prefix+'kernel403/README.md',latest_stage_device_mutated=False,latest_stage_phone_accessed=False,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,
 kernel_source_scope='403 native LTM partition primitive and shared bypass checks only; not full LTM serializer or runtime support. Gamma402 opcode1 kept. Candidate built, not deployed; last physical402 formal395/393 restored.',in_progress_installed_scope='403 no phone access, capture, install or transition. Last device evidence402-r2, normal core395/adapter393/CAMSS389/Image363/board389.',
 ipe_ltm_target_abi_verified=True,ipe_ltm_target_abi_evidence=prefix+'kernel403/contract-validation.json',ipe_ltm_dmi_opcode=1,ipe_ltm_source_cmd_type=1,ipe_ltm_program_type=11,ipe_ltm_iq_offset=2096,ipe_ltm_iq_bytes=92,ipe_ltm_dmi_bytes=156,ipe_ltm_lut_transfer_bytes=2736,ipe_ltm_factory_resource_bytes=3296,ipe_ltm_resource_extra560_purpose_unproven=True,
 ipe_ltm_native_partitions_added=True,ipe_ltm_native_partitions_evidence=prefix+'kernel403/native-partitions-validation.json',ipe_ltm_native_partition_step=324,ipe_ltm_native_fetch_halo=6,ipe_ltm_native_full_striping_complete=False,ipe_ltm_runtime_submission_enabled=False,ipe_ltm_hardware_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
 ipe_ltm_inverse_gamma_original_hal_verified=True,ipe_ltm_inverse_gamma_original_hal_evidence=prefix+'kernel403/inverse-hal-29-validation.json',ipe_ltm_inverse_gamma_original_hal_scope='29 valid64-node IFE green inputs; actual inlined inverse math and cache hit/miss,7424bytes match352 retained source oracle; not entire LTM Execute or current product tuning activation.',
 ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,ipe_latest_stage_frames_scope='403 offline only; no new frames. Latest hardware remains402-r2 fixed Gamma20 plus restored normal48, failed402-r1 retained separately.',
 current_health_scope='403 offline LTM ABI/math/partition checks only. Last device402 Gamma fixed pixels and restored normal camera/resource checks; full LTM/automatic tuning/optical/AF/SSC/rotation not broadly revalidated.',
 icp_next_step='Complete native LTM processing crops/grid/DC metadata and whole-stripe serialization using403 original HAL/FW CDM oracle, then full factory LTM math and typed IQ/LUT same-request ownership. Expand pre array for CST+LTM11 and preserve post CC/CV/Gamma12. Hardware test full chain; resolve IFE/IPE roles, standard request/libcamera/factory interpolation and remaining363 scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through402-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：403（LTM契约／逆Gamma核实，原生分区基础，最后实机402）

先读WORKING-BOUNDARIES.md、reference/kernel403/README.md。完整多摄／骁龙ISP目标active。用户已开灯出门，现场样本按实际照明／曝光判断。402完整交接归档archive/NEXT-SESSION-through402-2026-10-21.md。

## 最新源码与实证

403源码branch samurai-ipe-ltm-partitions403，HEAD37040a4a11e5e3197268bdbc0c64f17e5337b592，父402195f81dd30ca8865d440bafa32c7397006a436ef，两文件，干净未部署。原生camss_a5_ipe_ltm_partitions选择324步长/6halo，旧bypass选择328/4，复用检查范围计算。只计算fetch/output范围，尚未生成完整LTM条带或接运行时。Gamma402 opcode1、旧API/layout/reset/DMA清理均保留。W1/Werror构建通过诊断0，核心390248B/SHA9b7488b41798872ca07d9d93bf33f8b07b38fc951228cc48d5e2b934c16d300d，共享config/outputs/symvers恢复，build60864已观察exit0。

本机LTM原HALInitialize初始化13个offset0/48/304/560/816/1072/1328/1392/1456/1712/1968/2224/2480。13表长度48、5x256、2x64、5x256，实际传输2736B；原资源3296B，额外560用途未证，勿假定平均表或丢弃。原resource片段sourceCmdType1/CDMDMI，完整WriteDMI/AddNested执行13次，opcode1、reg5c08、selectors1..13、头156B，3IOVA边界和disabled通过。原提交器type11 pre-LTM（off2096 enable），disabled255，6描述符片段case通过。

IQ2096..2184共23u32/92B，字段名/宽度见contract-validation.json；86组独立随机源寄存器和全位边界通过，邻字段保持。原HAL模块开关还受ANR IQ440==1或inputTopology2624==3约束，30组合通过。ignoreChromatixRGammaFlag==1只清RGamma；不能仅根据调校module_en推断当前产品最终启用。

逆Gamma原始inlined片段3618a4..362320，29输入各miss/hit，88882448指令/58memcmp provider，无数学桩；7424B与352保存sourceoracle零差，复用352旧portable host/AArch64结果，不冒称重跑SDK。IFEgreen64节点→LTM14bit64段，不能输入IPE256。原厂/linear/reverse/black/white/alternate/plateau/impulse/随机含非单调全通过。初始Initialize夹具缺已有buffer指针转posix_memalign，不是HAL错误；补合法buffer后通过，旧夹具私存，原HAL不改。

完整原HAL条带+原FW CONFIG_IO/frameprepare止220a2前：12常规(128/640/1920/4608,port8/9,core1/2,DC/IP开关)+16边界(324/326/328/330/648/650/656/658 xcore1/2)+2上界8192宽共30。全零LUT仅离线几何fixture，从未实机调校。IP启用后324/6、色度对齐/向core倍数取整、右到左分区被实际原HAL核对；326单核LTM2条/bypass1，650双核LTM4条/bypass2。条数相同时也有processing crops/grid/radial/workload差异，不能直接用旧bypass blob开LTM。640DC+IP旧条带CDM差19B；650双核差1127B且job不同。私存stripe-differences-private.json和stripe-boundary-differences-private.json及全原blob/CDM/job供后续推导。

实际候选C hostASan/UBSan与AArch64QEMU各92组/3352B零差：26LTM+66bypass(含383原62cases)。非法/短容量/count/尾保护通过。production helper已提交但完整LTMserializer/runtime尚无，不将此当LTM已支持。

## 下一步与组合边界

优先完成native LTM处理裁剪/网格/DC字段和整blob，用403完整原HAL/FW CDM作oracle；分区已就绪，勿再从头研究324/6。继续完整LTM数值输入/输出复现，然后typed完整IQ/LUT和同request所有权；pre需CSTgeneric20+LTM11两项，现Gamma布局pre只有32B一项不能直接追加；post为CC/CVgeneric20+Gamma12最多3项。保留map/unknownDMA/复位所有权，避免大LUT压内核栈。再物理LTM组合/错误恢复和标准media request/libcamera，明确IFE CCM/Gamma和LTM inverse输入域，避免重复处理，接原厂动态触发树。

原厂完整树仍在350Gamma、351LTM149roots/2135regions和CCM43/737、399CST/CV17/71roots1350leaves；个体/工厂表全私有，未默认激活。CC actualtype2 offsetsigned11，CSTIQ2092→5a60、CC2188→5e60、CV2200→6460；CV native r/g/b/yoff/ap/am/bp/bm/cp/cm/dp/dm/kcr/kcb，packet低ap/bp/cp/dp高am/bm/cm/dm末cb/cr。400固定RGB域/offdiag/offset效应仍成立，完整一般公式舍入未证。

## 最后设备402（403无访问／帧／安装）

402-r1 opcode10的Gamma16帧像素失败但20传输正常，随后正式四摄48恢复；r1worker15169/collector15245终态，不重启。401fixture误sourceCmdType3，实际Gamma资源type1/CDMDMI，修opcode1后402-r2同adapter/client20帧通过：linear最大差1、zeroY0UV128、constant512全128、half误差半LSB、G/B/R各8灰阶误差1、原厂曲线8灰阶误差0、NV12/NV21十模式归一化全等。失败历史保留。

402-r2root=/var/lib/samurai/k402-gamma-r2，worker15997/collector16092/client全终态。恢复正式core395/adapter393，r30四摄各12共48direct/starts-stops4/error0/extra0；CPU/IRQ/PM/backing/maps/import释放、ICP/CAMSS/双CCI suspended、17clks0、9railsdisabled/users0、taint0。PW16240/WP16247单例uid10000，owner_refs53桌面句柄。无test_cc/chain/gamma/dropACK，无新fault/dump/timeout/reboot。最终normal epoch48；两次402总136direct不可写全像素通过。403只复用该历史证据。

正式core395 SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88，adapter393 SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1，CAMSS389 SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389/logdump365、SGownerAPI、FW、r30/r25不变，module781差量沿用。host403→402…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，原USBkey/knownhosts。395失ACK恢复及394失败reboot/206061Bramoops与旧回退副本保护。

363/REMAINING-CAMERA-SCOPE.md全部继续：第五2MP身份/mux、多模式、帧长/防频闪、连续AF/光学、几何/多摄同步；implicit异步fence、SSC/旋转未全面复验。source/build先root storage284.mounted_build挂原32GiB ext4，勿格式化重建；rootPython PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原FW/HAL/OEM/ASM/CDM/图像/个体表私存403与前序，公共mirror只本地提交、不push/PR、保护无关index。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从403继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel403/README.md。LTM原HAL已证type1/opcode1/reg5c08/13LUT2736B头156B/pretype11、IQ2096..2184共92B及ANR==1或topology3的enable约束；原逆Gamma29输入miss/hit/7424B对352oracle零差。原HAL/FW30几何发现IP步长324/halo6，旧bypass328/4错误用于LTM；326单核和650双核条数也变。native分区helper已加入候选37040a4a11e5e3197268bdbc0c64f17e5337b592 branch samurai-ipe-ltm-partitions403，两文件干净未部署，host/ARM92cases和W1Werror通过。下一步完整LTM处理crops/grid/DC/整blob、full数值和typed请求所有权，再实机组合；不可称已有LTM运行支持。pre扩两项CST+LTM，postCC/CV+Gamma。403无手机访问，最后402-r2 Gamma20和恢复正式395/393四摄48/资源释放，r1失败保留，worker15997/collector16092等全终态勿重启。guard394/host403，PW16240/WP16247单例。全部363范围继续，source/build先root storage284挂原ext4，原厂表/日志/图像/密钥私存。\n')
note='403当前：本机LTM命令／IQ／enable与原HAL逆Gamma已核实；324步长／6像素halo原生分区加入候选，构建与92组对照通过。完整LTM条带／运行时待做，本轮无手机访问，最后实机402。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel403/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel403/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel403/README.md')]:
 p=ROOT/rel;old=p.read_text().split('\n\n',1);assert old[0].startswith('402当前：');p.write_text(note+'[403证据]('+link+')。以下为历史。\n\n'+old[1])
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[402 Gamma命令修正与实像素](reference/kernel402/README.md)','[403 LTM契约／逆Gamma与原生分区](reference/kernel403/README.md)'))
print(json.dumps(dict(stage=403,checkpoint_updated=True,last_device_stage=402,full_goal_active=True)))
