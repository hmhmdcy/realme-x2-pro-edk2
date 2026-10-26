"""Record corrected Gamma pixels and keep failed r1 and normal epochs distinct."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel402')
current=json.loads((HERE/'current-state-validation.json').read_text());source=json.loads((HERE/'source-state.json').read_text());pixels=json.loads((HERE/'pixels-validation.json').read_text());assert current['passed'] and pixels['passed']
failed=json.loads((HERE/'pixels-validation-r1.json').read_text());assert not failed['passed'] and failed['transport_and_resource_recovery_passed']
down=json.loads((P/'downstream-probe-private.json').read_text());assert len(down)==2 and all(not r['providers'] and r['cache_bank']==1 and r['program_pairs'][0]['words']==[0x04000002,0x6058,1,0x605c,1] for r in down)
(HERE/'downstream-validation.json').write_text(json.dumps(dict(stage=402,complete_original_addbls_and_accumulator_functions_executed=True,provider_count=0,uid0_and_uid1_both_program_lut=True,lut_bank_registers=[0x6058,0x605c],initial_bank=1,uid0_skip_hypothesis_rejected=True,private_full_packets_retained=True,hardware_cache_behaviour_not_broadly_claimed=True,passed=True),indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for k in ['stage','in_progress_stage','latest_work_stage','current_device_revalidated_stage','icp_latest_device_experiment_stage','ipe_latest_hardware_stage']:d[k]=402
 for k in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[k]=source['branch']
 for k in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[k]=source['commit']
 d.update(current_camera_evidence=prefix+'kernel402/README.md',current_readonly_device_evidence=prefix+'kernel402/current-state-validation.json',ipe_installed_default_camera_recovery_evidence=prefix+'kernel402/runtime-validation.json',latest_stage_device_mutated=True,latest_stage_phone_accessed=True,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,
 kernel_source_scope='402 Gamma DMI opcode1 correction, temporarily hardware tested with unchanged fixed402 adapter; formal restored core395/adapter393/CAMSS389/Image363/board389. No permanent installation.',in_progress_installed_scope='402 two distinct private-load transactions: r1 opcode10 failed Gamma pixels, restored normal; r2 opcode1 passed fixed diagnostics, restored normal. On-disk module files unchanged.',
 ipe_gamma_candidate_api='camss_a5_ipe_run_gamma_status',ipe_gamma_dmi_opcode=1,ipe_gamma_source_command_type=1,ipe_gamma_previous401_opcode10_factory_claim_withdrawn=True,ipe_gamma_hardware_verified=True,ipe_gamma_hardware_evidence=prefix+'kernel402/pixels-validation.json',ipe_gamma_hardware_scope=pixels['hardware_scope'],ipe_gamma_first_physical_attempt_failed=True,ipe_gamma_failed_attempt_evidence=prefix+'kernel402/pixels-validation-r1.json',ipe_gamma_factory_interpolation_activated=False,ipe_gamma_forced_fault_reset_hardware_verified=False,ipe_generic_type20_hardware_verified=True,
 ipe_program_tag_correction_scope='401 original HAL submit proved generic20/Gamma12/skip255;402 generic20 conversion output byte-equal400. Gamma opcode1 separately corrected402 using real sourceCmdType1, replacing false401 fixture type3/opcode10.',
 ipe_colour_chain_hardware_evidence=prefix+'kernel402/pixels-validation.json',ipe_colour_chain_hardware_scope='402 corrected generic20 fixed CST/identityCC/CV pair and Gamma640x480 NV12/NV21;400 other CC modes remain prior physical evidence. Complete automatic factory interpolation not enabled.',
 ipe_latest_stage_actual_frames=136,ipe_latest_stage_RT_frames=136,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=40,ipe_latest_stage_normal_restored_frames=96,ipe_latest_stage_frames_scope='Two distinct402 epochs each20 synthetic +48 restored formal direct frames. r1 16 Gamma frames failed pixels despite transport success; r2 all20 fixed diagnostics passed. Final normal epoch48 only.',ipe_gamma_latest_successful_test_frames=16,
 ipe_current_cumulative_counters={k:current['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']},ipe_current_counter_epoch='402-r2 restored normal395 module lifetime;48 direct,starts/stops4. r1 and private native epochs separate.',
 current_health_scope='402-r2 corrected Gamma fixed diagnostics and restored normal four-camera/resource checks. Full LTM/automatic tuning/optical/AF/SSC/rotation not broadly revalidated.',
 icp_next_step='Recover original LTM enable/DMI/inverseGamma/full typed parameters and ownership, then full IQ chain. Resolve existing IFE CCM/Gamma vs IPE roles, standard media request/libcamera/factory interpolation and complete remaining363 scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through401-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：402（Gamma命令修正及实像素通过，正式恢复395/393）

先读WORKING-BOUNDARIES.md、reference/kernel402/README.md。完整多摄／骁龙ISP目标active，用户已开灯出门；现场样本按实际照明与曝光。401交接归档archive/NEXT-SESSION-through401-2026-10-21.md。

## 最新Gamma实机与修正

402两次独立事务。r1=/var/lib/samurai/k402-gamma-r1，worker15169/collector15245终态，401核心opcode10，20direct传输无错但16个Gamma请求像素失败：线性最大差194，零/常量不是预期、两格式不等；之后正式395/393四摄48通过。失败pixels-validation-r1.json/runtime-validation-r1.json保留，transport passed不冒称像素通过，不重启旧事务。

原Gamma FillCmdBufferManagerParams初始化片段证明sourceCmdType=1 CDMDMI，3072B。401夹具擅设3 CDMDMI32，完整WriteDMI落legacy10；原厂opcode10结论撤回。使用真实类型1，原模块片段+完整WriteDMI+AddNested生成opcode1，同三条12B/每通道1024B，reg6008，selector1/2/3=G/B/R，offset0/1024/2048。原HAL不改。原FW完整AddBLs/accumulator无provider，UID0和1都编LUT并写bank6058/605c=1，UID0强制编程，排除UID0跳过假设。

只把内核固定DMI头0a0003ff改010003ff，branch samurai-ipe-gamma-dmi402，HEAD195f81dd30ca8865d440bafa32c7397006a436ef，父401 b8ce3ce92745a11b039e1335e87bbb2dd783c2c7，一个文件，干净未永久装。正常核心388520B/SHA31d203159178b413fd247aa240910558c566417ad424f5e4ab4f274cc069c5d2；W1/Werror诊断0，共享配置/outputs/symvers恢复。3450参数页/6040非法、85生命周期、19原FW/原HAL与当前C整512KiB CDM+32Bjob比较通过，均正确opcode1。

r2=/var/lib/samurai/k402-gamma-r2，worker15997/collector16092/client均终态，使用同一adapter114384B/SHA4bfbb80fcfefc50aa770b0c39c49f4c016093dda95da82c11e43144030fefe5a与同一client，只换修正核心。640x480 NV12/NV21各10模式20direct/starts-stops20/error0：generic20转换对全460800B等400；linearGamma仅100B差/最大1，zero全Y0UV128，constant512全128，half全Y/UV的2half-linear-zero仅-1/0/1。单通道G/B/R各8灰阶对已知CV系数最大Y误差1；首条保留原厂曲线8灰阶对原HAL量化LUT误差0。十模式格式归一化全等、主机CRC/输入/canary/seq/timestamp通过。厂曲线诊断不是当前场景触发插值，完整rounding/saturation/尺寸/Gamma故障复位未证明。

## 最后实际部署与状态

两次均临时加载/卸载，磁盘模块与四私有配置未改。第二次恢复正式core395/adapter393，r30四摄各12共48direct/starts-stops4/error0/extra0；CPU/IRQ/PM/backing/maps/import释放，ICP/CAMSS/双CCI suspended，17clks0、9railsdisabled/users0、taint0。PW16240/WP16247各一uid10000，owner_refs53桌面句柄；无test_cc_mode/test_chain_mode/test_gamma_mode/dropACK，无新相关fault/dump/timeout/reboot。两次合计136direct分epoch：native20+正常48各两轮，首轮Gamma像素失败不可混成全通过。最终正常计数48。

正式core395 SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88，adapter393 SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1，CAMSS389 SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389/logdump365、SGownerAPI、FW、r30/r25保持，模块781沿用差量依据无全扫。host402→401…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，原USBkey/knownhosts。395失ACK复位恢复及394失败reboot/206061Bramoops/回退副本保护。

## 实现契约与接续

typed Gamma3072B，base10/signeddelta10，先锁内CPU堆复制和校验，再coherent/MAP，线数据在同retained request，未知DMA整request保留，CPU副本所有出口释放，无新独立coherent BO。IQ6016/PAGE_ALIGN8192：2592empty/2624pre/2656post3项；2752CST/2808CC/2852CV/2896DMI36B/2944LUT3072B。generic20/Gamma12/skip255。旧job/frame/colour布局及free/reset/quiesce/stop保持。401IFE/IPE职责审查可复用：IFE已有CCM/64段Gamma参数路径，IPE用户空间目前仅图像队列；不冒称当前每配置开关已核。正式默认高级IQ仍旁路。

下一步原厂LTM完整enable/DMI/inverseGamma/typed参数和所有权，再完整IQ链；之后明确IFE传递函数/CCM位置与LTM输入，避免重复CCM/Gamma，接标准media request/libcamera和原厂触发插值。不得以固定test_gamma_mode作为产品API。350全Gamma、351CCM/LTM树、352inverseGamma数值工具可复用；继续验证实际本机ABI和sourceCmdType，不能再用未核实夹具枚举冒充原厂契约。

399/400转换证据继续：CC actualtype2/offsetsigned11；CSTQ10signed13/subtractsigned11/addclamp10；CSTIQ2092→5a60、CC2188→5e60、CV2200→6460。CV Parse原native顺序r/g/b/yoff/ap/am/bp/bm/cp/cm/dp/dm/kcr/kcb；packet低ap/bp/cp/dp高am/bm/cm/dm末cb/cr。400固定RGB域/offdiag/signedoffset成立但完整公式舍入未证，不能直接默认激活全厂矩阵。

363/REMAINING-CAMERA-SCOPE.md全部继续：第五2MP身份/mux、多模式、帧长/防频闪、连续AF/光学、几何/多摄同步；implicit异步fence、SSC/旋转未全面复验。source/build先root storage284.mounted_build挂原32GiB ext4，勿格式化重建；rootPython PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原厂FW/HAL/OEM/ASM/CDM/图像/个体表私存402与前序，公共mirror只本地提交、不push/PR、保护无关index。r2主机分析一度把400历史目录误替r2报FileNotFound，修路径后复用样本，无重复实机。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从402继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel402/README.md。Gamma首次r1 opcode10传输完成但像素失败已保留；原资源初始化证明sourceCmdType1/CDMDMI，旧401夹具type3错，修opcode1后r2同adapter/client20帧：zero全Y0UV128、constant512全128、linear最大差1、half误差半LSB、G/B/R与原厂曲线灰阶通过、两格式全等。随后恢复正式395/393四摄48与资源释放，worker15997/collector16092全终态勿重启。候选源码195f81dd30ca8865d440bafa32c7397006a436ef branch samurai-ipe-gamma-dmi402干净未永久装；W1Werror/3450页/85生命周期/19FW通过。下一步原厂LTM完整ABI/DMI/inverseGamma/typed所有权，再fullIQ、IFE/IPE分工、标准request/libcamera/动态插值和全部363范围。guard394/host402，PW16240/WP16247单例。用户已开灯，source/build先root storage284挂原ext4，所有原厂表/日志/图像/密钥私存。\n')
note='402当前：修正原厂Gamma源缓冲类型／DMI opcode，第二轮20帧固定Gamma实像素通过；首轮失败保留。随后恢复正式395/393四摄48和资源释放。完整LTM／自动调校与多摄范围继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel402/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel402/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel402/README.md')]:
 p=ROOT/rel;text=p.read_text();old=text.split('\n\n',1);assert old[0].startswith('401当前：');p.write_text(note+'[402证据]('+link+')。以下为历史。\n\n'+old[1])
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[401 原厂Gamma与LUT所有权候选](reference/kernel401/README.md)','[402 Gamma命令修正与实像素](reference/kernel402/README.md)'))
p=ROOT/'reference/kernel401/README.md';p.write_text('**402更正：401夹具把Gamma源缓冲设为CDMDMI32（type3），错误选中opcode10。实际原厂初始化为CDMDMI（type1），应使用opcode1；修正后Gamma实像素通过。[402证据](../kernel402/README.md)。下文保留401当时结果与范围。**\n\n'+p.read_text())
print(json.dumps(dict(stage=402,checkpoint_updated=True,failed_attempt_retained=True,formal395_restored=True,full_goal_active=True)))
