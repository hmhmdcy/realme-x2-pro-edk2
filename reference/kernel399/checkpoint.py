"""Keep the complete goal and distinguish the399 candidate from397 device proof."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];state=json.loads((HERE/'source-state.json').read_text())
for n in ['factory-conversion-validation.json','native-leaf-validation.json','mode-conversion-validation.json','parcel-validation.json','transfer-validation.json','firmware-parcel-validation.json','intree-build-validation.json']:assert json.loads((HERE/n).read_text())['passed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for k in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[k]=state['branch']
 for k in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[k]=state['commit']
 for k in ['stage','in_progress_stage','latest_work_stage']:d[k]=399
 assert d['current_device_revalidated_stage']==397 and d['ipe_latest_hardware_stage']==397
 d.update(current_camera_evidence=prefix+'kernel399/README.md',latest_stage_device_mutated=False,latest_stage_phone_accessed=False,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,kernel_source_scope='Maintained399 typed CST/CC/CV chain, copied before allocation and owned in the existing IQ page; not loaded or installed. Last runtime evidence397 remains core395/adapter393/CAMSS389/Image363/board389.',in_progress_installed_scope='399 offline only: factory decode, target HAL/FW execution, actual C/lifetime checks and normal core build. No phone access or transition.',ipe_cc_parcel_evidence=prefix+'kernel399/parcel-validation.json',ipe_cc_candidate_build_evidence=prefix+'kernel399/intree-build-validation.json',ipe_colour_chain_api_integrated=True,ipe_colour_chain_api='camss_a5_ipe_run_colour_chain_status',ipe_colour_chain_candidate_source_commit=state['commit'],ipe_colour_chain_iq_bytes=2860,ipe_colour_chain_new_dma_allocations=0,ipe_colour_chain_ownership_evidence=prefix+'kernel399/transfer-validation.json',ipe_colour_chain_firmware_evidence=prefix+'kernel399/firmware-parcel-validation.json',factory_ipe_conversion_evidence=prefix+'kernel399/factory-conversion-validation.json',factory_ipe_conversion_mode_evidence=prefix+'kernel399/mode-conversion-validation.json',ipe_cv_native_order_evidence=prefix+'kernel399/native-leaf-validation.json',ipe_cv_previous398_am_ap_labels_withdrawn=True,ipe_colour_chain_hardware_verified=False,ipe_cc_rgb_domain_established=False,ipe_cc_factory_rgb_matrices_ready_for_default=False,ipe_cc_colour_conversion_pair_enabled=False,icp_next_step='Temporarily verify typed CST/CV pair and identity/zero/half/off-diagonal/signed-offset CC on synthetic hardware pixels, including channel/range/saturation/rounding. Then standard V4L2 request/libcamera and factory interpolation, full Gamma/LTM, and remaining363 optical/multi-camera scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through398-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：399（类型化CST／CC／CV链已构建，离线；设备最后证据397）

先读WORKING-BOUNDARIES.md、reference/kernel399/README.md。398交接归档archive/NEXT-SESSION-through398-2026-10-21.md。完整多摄／ISP目标active。用户已开灯出门，现场样本重新核实照明／曝光。

## 原厂恢复与字段纠正

五份保留调校BIN完整恢复17 CST根、71 CV根/1350叶，与原厂XML读取器逐项一致；原payload不改，数据只私存399。原选择管理器与独立mode reader在14 Preview/Video上下文、28查询一致。参数enable不能等同Android运行时enable或当前插值叶。

本机cv12 Parse真实片段1350叶+1逐字段不同值用例证明8B槽→4B浮点，无重排。native数据顺序rToY,gToY,bToY,yoffset,ap,am,bp,bm,cp,cm,dp,dm,kcr,kcb；packet低chroma槽ap/bp/cp/dp、高槽am/bm/cm/dm、末字cb/cr。398从新版寄存器名推测am/ap标签撤回，按位置数值验证不变。所选原厂CV很多不对称，不能交换。

继续保持398更正：actualIPE CC type2、offsetsigned11(-1024…1023)，不是396 type1/13位。397四个zerooffset固定矩阵实像素观察仍有效，不证明负offset。CST实际type2，matrixsigned13/Q10，subtractsigned11，addoffset/clamp0…1023。CST IQ2092→5a60/data5a68(12w)；CC2188→5e60/data5e68(9w)；CV2200→6460/data6468(8w)，勿用2196。CVcoefQ8signed12，yoffset/kcb/kcr数值clampsigned11，kcb/kcr字段13。

## 内核候选与验证

新增camss_a5_ipe_run_colour_chain_status：typed module mask/cst/cc/cv，锁内复制并检查启用模块，allocation/MAP前拒绝错误，禁用字段忽略。固定寄存器包由驱动生成，无任意CDM/IQ指针。旧job/frame及旁路/独立CC API保持；free/unknownDMA/quiesce/stop/reset函数体不变。

IQ2860B仍在原4096B页：2592共同空array，2624pre(1项CST)，2656post(最多CC、CV两项)；2720/56B CST、2776/44B CC、2820/40B CV。frame40=IQbase+2592，44preoffset32，48postoffset64。零独立DMA分配，跟随原request MAP/retain/reset回收。

实际C完整2860页2232组：17CST+737CC+1350CV+128mask/random，全6383520B与本机原HAL数值/完整CDM零差，主机ASan/UBSan和AArch64QEMU；2956非法无写。64 actual transfer/DMA模型覆盖旧旁路、独立CC、新链及未知MAP/FRAME/UNMAP/cleanup错误和分配前拒绝。未新注入硬件故障。

完整原HAL striping和原FW CONFIG_IO/帧准备：三尺寸×port8/9×cores1/2共12全模块组+其余7mask。actual C页 pre/post各链接一次；current production native C stripe在开启转换时与原HAL产生相同整512KiB CDM+32Bjob，19组零差，停enqueue前。限定1:1 NV12；新转换组合NV21/缩放/物理像素未验证。

source354 branch samurai-ipe-conversions399，HEADde94e65e7ab4ae2ec23ee1665f981d0aeb7395e7，父3988b1e8903a550ffc20a2d8f1de574c37f2260fff3，仅4文件，干净未装。正常核心W1/Werror成功诊断0，380760B/SHA6927c4c34d40871f420e29dda2f04b0a1722a3ce76007588304243e6f01256ba。共享配置/outputs/symvers恢复，build handle54050已观察exit0终态。

下一步临时固定参数adapter+合成颜色块，先CST/CV pair再单位/零/半幅/非对角/负offsetCC实像素，核对通道/范围/饱和/舍入并建立RGB域；不能只凭ACK或近似恒等验收。再标准media request/libcamera、原厂触发插值、Gamma/LTM组合。399无phone操作，不默认启用调校，不能当已完成完整IQ。

## 正式部署：最后证据397，非399复验

core395354864B/SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88；adapter393SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1；CAMSS389SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389/logdump365、FW、SGownerAPI、r30/r25保持。

397临时4 CC帧后恢复395/393默认四摄各12/48direct、starts-stops4/error0，epoch不混。最终CPU/IRQ/PM/backing/maps/import释放，ICP/CAMSS/双CCI suspended，17clks0、9railsdisabled/users0、taint0；PW10681/WP10684各一uid10000，owner_refs53为桌面CAMSS句柄。worker10439/client/collector10536终态，无test_cc_mode/dropACK参数，不重启旧runtime。

host399委托398…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，原USBkey/knownhosts。状态切换先核实实际设备。395失ACK恢复和394失败/reboot/206061Bramoops及旧回退副本保持；SSC/旋转未全面复验。

363/REMAINING-CAMERA-SCOPE.md完整继续：第五2MP身份/mux、多模式、帧长/防频闪、几何/多摄同步、连续AF和光学；异步implicitfence未证明。source/build先root storage284挂原32GiB ext4，不格式化重建；rootPython复用PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。FW/HAL/OEM/ASM/CDM/图像/个体表仅private399及前序；公共mirror只本地提交、不push/PR、保留其它改动。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从399继续完整多摄/骁龙ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel399/README.md。17CST根/71CV根1350叶已原XML核对、14mode上下文28选择匹配；actual Parse证明CV ap/am等native顺序，398新版reg名的am/ap标签撤回，数值位置验证保持。新增内核typed CST/CC/CV链同原IQ页2860B，2232参数页+64生命周期+19原FW/native整CDM-job检查和W1构建通过；source de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7 branch samurai-ipe-conversions399干净未部署。下一步临时adapter合成像素验证pair及identity/zero/half/offdiag/负offsetCC，建立RGB域，再标准媒体请求/libcamera/原厂插值和完整Gamma/LTM、363全部范围。399无手机操作，最后实机397正常395/393四摄48，guard394/host399；旧runtime全终态。用户已开灯出门。source/build先root mounted_build()挂原ext4，保护密钥/个体数据。\n')
note='399当前：原厂CST/CV完整模式树与实际native字段顺序已恢复，内核类型化CST/CC/CV逐帧链及同IQ页所有权已构建；参数/生命周期/原FW整命令检查通过。399离线，转换组合实像素尚待验证，正式设备最后证据397的395/393四摄48。完整目标active。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel399/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel399/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel399/README.md')]:
 p=ROOT/rel;p.write_text(note+'[399证据]('+link+')。以下为历史。\n\n'+p.read_text())
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[398 IPE分支纠正与颜色转换契约](reference/kernel398/README.md)','[399 原厂转换模式树与内核逐帧链](reference/kernel399/README.md)'))
print(json.dumps(dict(stage=399,checkpoint_updated=True,device_last_verified397=True,full_goal_active=True)))
