"""Record fixed conversion pixels and the restored formal395/393 deployment."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];current=json.loads((HERE/'current-state-validation.json').read_text());source=json.loads((HERE/'source-state.json').read_text())
assert current['passed'] and json.loads((HERE/'pixels-validation.json').read_text())['passed'] and json.loads((HERE/'runtime-validation.json').read_text())['state']['passed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for k in ['stage','in_progress_stage','latest_work_stage','current_device_revalidated_stage','icp_latest_device_experiment_stage','ipe_latest_hardware_stage']:d[k]=400
 for k in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[k]=source['branch']
 for k in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[k]=source['commit']
 d.update(current_camera_evidence=prefix+'kernel400/README.md',current_readonly_device_evidence=prefix+'kernel400/current-state-validation.json',ipe_installed_default_camera_recovery_evidence=prefix+'kernel400/runtime-validation.json',latest_stage_device_mutated=True,latest_stage_phone_accessed=True,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,kernel_source_scope='Maintained399 source tested temporarily400 with private fixed-chain adapter; no new permanent400 source changes and no permanent installation. Runtime restored core395/adapter393/CAMSS389/Image363/board389.',in_progress_installed_scope='400 privately loaded399 core/fixed400 adapter,16 conversion/CC synthetic frames, then unloaded and restored normal395/393 four-camera48; disk module files unchanged.',ipe_colour_chain_hardware_verified=True,ipe_colour_chain_hardware_evidence=prefix+'kernel400/pixels-validation.json',ipe_colour_chain_hardware_scope='640x480 NV12/NV21,one retained CST/CV diagnostic pair,identity/zero/half/R-B-swap and one signed offset vector/opposite; no complete automatic factory interpolation or all rounding/saturation claim.',ipe_cc_actual_pixel_effect_scope='400 fixed CST/CV pair: identity all bytes equal pair,zeroY0UV128,half scales about black,swap/signed offsets change pixels; NV12/NV21 normalized outputs identical.',ipe_cc_runtime_evidence=prefix+'kernel400/pixels-validation.json',ipe_cc_rgb_domain_established=True,ipe_cc_rgb_domain_scope='400 tested fixed CST->CC->CV pair only; full transfer equation and general range/rounding remain unproven.',ipe_cc_factory_rgb_matrices_ready_for_default=False,ipe_cc_colour_conversion_pair_hardware_tested=True,ipe_cc_colour_conversion_pair_enabled=False,ipe_cc_colour_conversion_pair_enabled_scope='Temporary400 experiment only; restored formal395 default still bypasses advanced IQ.',ipe_full_factory_interpolation_activated=False,ipe_latest_stage_actual_frames=64,ipe_latest_stage_RT_frames=64,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=16,ipe_latest_stage_normal_restored_frames=48,ipe_latest_stage_frames_scope='400 temporary399-core/400-adapter16 direct synthetic frames,then restored normal395/393 four-camera48; pre-experiment48 separate.',ipe_current_cumulative_counters={k:current['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']},ipe_current_counter_epoch='400 restored normal395 module lifetime; temporary16 and pre-experiment48 separate.',current_health_scope='400 fixed conversion/CC pixels plus restored normal camera and resource checks. Full Gamma/LTM/optical/AF/SSC/rotation not broadly revalidated.',icp_next_step='Recover actual target Gamma IQ enable,DMI packet and complete LUT ownership; then LTM/full chain. Before product integration audit existing IFE CCM/Gamma/conversion to avoid duplicate processing; add standard request/libcamera/factory interpolation and complete remaining363 scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through399-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：400（转换链固定模式实像素通过，正式恢复395/393）

先读WORKING-BOUNDARIES.md、reference/kernel400/README.md。399交接归档archive/NEXT-SESSION-through399-2026-10-21.md。完整多摄/骁龙ISP目标active，用户已开灯出门；现场样本按实际照明与曝光。

## 本轮实机与像素

一次root=/var/lib/samurai/k400-chain-r1，worker12945/client13157/collector13040全部终态且cmdline不活跃，不重启旧事务。临时正常399core+固定400adapter，640x480 NV12/NV21各8模式共16direct、starts/stops16/error0，无CPU图像处理。参数取已原XML核对的SunnyIMX319 mode0/Preview CST/CV根，CV第一保留叶只作诊断，不声称当前运行时插值叶。

48平坦色块模式：0旁路Y等输入；1 CST+CV；2加单位CC，全460800B等1；3零CC全部Y0/UV128；4半CC围绕模式3编码黑色缩放，全Y/UV的2half-unit-black仅-1/0/1；5 R/B交换相对单位358968B变；6 RGBoffset(-64,+32,+96)425675B变；7相反offset360759B变。八模式NV12/NV21归一化UV后所有字节相同。主机CRC/输入生成器/尾canary/seq/timestamp通过，灰阶块Y精确，中色块offset正向Y+1/opposite和误差<=1。

支持所测固定CST->CC->CV RGB域及offdiag/signed offset路径。完整通道方程、所有尺寸/矩阵/饱和/舍入、完整Gamma/LTM/自动原厂调校尚未证明。luma拟合19训练块/29留出块首best最大误差1，但3模型训练同分有歧义，只是推断，非独立硬件公式/offset量纲证明。不能直接启用所有原厂矩阵默认调校。

之后卸临时模块恢复正式core395/adapter393，默认r30四摄各12=48direct/starts-stops4/error0/extra0，fixture恢复。临时16、恢复48及实验前48不同epoch分开。collector13.015s终态无dump/timeout，无新相关fault、未重启/刷写/永久安装。

最终实际核对400：正式磁盘/加载notes及四私有配置一致；CPU/IRQ/PM/backing/map/import释放，ICP/CAMSS/双CCI suspended，17clks0、9railsdisabled/users0、taint0。PW13169/WP13172各一uid10000，owner_refs53是桌面CAMSS句柄。test_chain_mode/test_cc_mode/dropACK均无。

## 源码构建、正式部署

永久源仍399 branch samurai-ipe-conversions399，HEADde94e65e7ab4ae2ec23ee1665f981d0aeb7395e7，干净未永久装；400无新增永久源改。正常399core380760B/SHA6927c4c34d40871f420e29dda2f04b0a1722a3ce76007588304243e6f01256ba与test核心逐字节同。400fixedadapter111296B/SHA719aa4858b29f4bd3a6efbcb4ed7f56f59ad87067c714424ae9f28220b9c67f8，宏CAMSS_A5_TEST_CHAIN/八固定选择，无任意CDM；原厂数值头私有。W1/Werror诊断0，辅助模块只构建未安装，临时源/私有头撤回、共享配置/outputs/symvers恢复。build handle81149已观察exit0。

首次client编译相邻if误导缩进被Werror拒绝，分行修复；夹具OFFSET/YOFFSET标记冲突在adapter构建前纠正。初始日志/夹具私存，非硬件失败，adapter首次构建和runtime首次事务均通过。

正式core395354864B/SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88；adapter393SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1；CAMSS389SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389/logdump365、SGownerAPI、FW、r30/r25保持。host400委托399…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，原USBkey/knownhosts。395失ACK恢复/394失败reboot/206061Bramoops与旧回退副本保持。

## 接续优先级与契约

下一步本机HAL确认Gamma真实enable、DMI包及完整LUT，纳入同request所有权，再LTM/完整IQ。产品用户空间整合前核对现IFE已做CCM/Gamma/颜色转换，避免重复应用，定义输入输出颜色域；接标准media request/libcamera与原厂触发插值，再正常光照校准。不要把固定test_chain_mode当产品API。

399已恢复17CST根/71CV根1350叶，与原XML一致、14mode上下文28选择匹配。nativeParse证明CV顺序r/g/b/yoffset/ap/am/bp/bm/cp/cm/dp/dm/kcr/kcb，packet低chroma ap/bp/cp/dp高am/bm/cm/dm，末cb/cr；398新版reg名am/ap推测撤回。actualIPECC type2、offsetsigned11，不是396type1/13位。CSTQ10signed13、subtractsigned11、add/clamp10；CSTIQ2092→5a60/data5a68/12w，CC2188→5e60/data5e68/9w，CV2200→6460/data6468/8w。Gamma位置必须从实际模块核实，勿沿用早期邻字段猜测。

内核API camss_a5_ipe_run_colour_chain_status：enabledtyped参数锁内复制/检查，allocation/MAP前拒绝；旧job/frame/API和free/unknownDMA/reset函数体保持。IQ2860在原4096页，2592empty、2624pre、2656post、2720CST56B/2776CC44B/2820CV40B；frame40base、44/48相对32/64。399的2232参数页/2956拒绝、64生命周期和19原FW/native整512KiB CDM+32Bjob零差复用。

363/REMAINING-CAMERA-SCOPE.md完整继续：第五2MP身份/mux、多模式、帧长/防频闪、几何/多摄同步、连续AF和光学；异步implicitfence未证明、SSC/旋转未全面复验。source/build先root mounted_build()挂原32GiB ext4，不格式化重建；rootPython复用PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。FW/HAL/OEM/ASM/CDM/图像/个体表私存400及前序，公共mirror只本地提交、不push/PR、保留其它改动。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从400继续完整多摄/ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel400/README.md。固定CST/CV+CC八模式NV12/NV21共16实像素通过：identity=pair、zeroY0UV128、half绕黑缩放误差半LSB、swap/signedoffset有效、两格式归一化全等；随后恢复正式395/393四摄48与资源释放。RGB域结论限该配置，luma拟合有3同分模型不作公式证明；完整Gamma/LTM/自动插值/光学待做。下一步核实原HAL Gamma真实enable/DMI/LUT并接同request，再LTM；产品接入前避免现IFE重复CCM/Gamma，接标准request/libcamera和363全部范围。永久源仍399 de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7 branch samurai-ipe-conversions399干净未永久装。400 worker12945/client13157/collector13040全终态不可重启；PW13169/WP13172单例。guard394/host400，用户已开灯，source/build先storage284挂原ext4，保护私有原厂表/密钥。\n')
note='400当前：固定CST/CV+CC组合NV12/NV21各八模式实像素通过，单位/零/半幅/通道交换/有符号偏移及格式等价已验证；随后恢复正式395/393四摄48、资源释放。399候选未永久装，完整Gamma/LTM与自动/光学校准继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel400/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel400/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel400/README.md')]:
 p=ROOT/rel;p.write_text(note+'[400证据]('+link+')。以下为历史。\n\n'+p.read_text())
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[399 原厂转换模式树与内核逐帧链](reference/kernel399/README.md)','[400 转换链组合实像素与恢复](reference/kernel400/README.md)'))
print(json.dumps(dict(stage=400,checkpoint_updated=True,full_goal_active=True)))
