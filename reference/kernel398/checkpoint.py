"""Record corrected candidate evidence while retaining the last device epoch."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
state=json.loads((HERE/'source-state.json').read_text())
for n in ['caller-validation.json','colour-validation.json','parcel-validation.json','intree-build-validation.json','conversion-routing-validation.json','cv-numerical-validation.json']:assert json.loads((HERE/n).read_text())['passed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for k in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[k]=state['branch']
 for k in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[k]=state['commit']
 for k in ['stage','in_progress_stage','latest_work_stage']:d[k]=398
 assert d['current_device_revalidated_stage']==397 and d['ipe_latest_hardware_stage']==397
 d.update(current_camera_evidence=prefix+'kernel398/README.md',latest_stage_device_mutated=False,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,kernel_source_scope='Maintained398 corrects undeployed IPE CC signed offsets to actual caller type2/11 bits. Runtime last verified397 remains core395/adapter393/CAMSS389/Image363/board389.',in_progress_installed_scope='398 offline only: no phone access, no install, no runtime transition. Last device evidence remains397 restored normal395/393 four-camera48.',ipe_cc_encoder_evidence=prefix+'kernel398/colour-validation.json',ipe_cc_encoder_arm64_evidence=prefix+'kernel398/parcel-validation.json',ipe_cc_parcel_evidence=prefix+'kernel398/parcel-validation.json',ipe_cc_candidate_build_evidence=prefix+'kernel398/intree-build-validation.json',ipe_cc_actual_hal_caller_type=2,ipe_cc_offset_signed_bits=11,ipe_cc_previous396_type1_ipe_scope_withdrawn=True,ipe_cc_caller_type_evidence=prefix+'kernel398/caller-validation.json',ipe_cst_cv_contract_evidence=prefix+'kernel398/conversion-routing-validation.json',ipe_cv_numerical_evidence=prefix+'kernel398/cv-numerical-validation.json',ipe_cc_rgb_domain_established=False,ipe_cc_factory_rgb_matrices_ready_for_default=False,ipe_cc_colour_conversion_pair_enabled=False,icp_next_step='Recover factory selected-mode CST/CV parameters; use verified target caller contracts to add typed same-request conversion programs and establish RGB domain with synthetic hardware pixels. Then off-diagonal/signed offsets, standard media request/libcamera, full Gamma/LTM and remaining363 scope.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through397-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：398（IPE分支／偏移位宽纠正，离线；设备最后核对397）

先读WORKING-BOUNDARIES.md、reference/kernel398/README.md。397完整交接归档archive/NEXT-SESSION-through397-2026-10-21.md。完整多摄／骁龙ISP目标active；关灯黑场／噪点按低照度，正常照明光学校准后做。

## 本轮纠正与验证

实际IPE CC调用者输出type2（常量及真实初始化指令执行确认）。396误用type1，13位offset作为IPE契约的结论撤回；398候选改signed11、范围-1024…1023、掩码0x7ff。矩阵signed12/Q(7+shift)、GBR排列、固定9word包0x5e68保持。397实机单位／零／半幅全部zerooffset，既有观察仍有效，但不证明负offset。

重跑实际type2完整CC13CalculateSetting+原CDM编码：737原厂叶+384合成=1121，49324B零差，72非法无写。实际完整2700B IQ页1121组/3026700B与正确oracle零差，2730非法无写，主机ASan/UBSan和AArch64 QEMU通过。只改colour.c/.h；job/frame、分配、DMA/未知完成/复位函数未改，复用397生命周期模型。

source354 branch samurai-ipe-offset398，HEAD8b1e8903a550ffc20a2d8f1de574c37f2260fff3，父3976a6451dd1fa14534e5c805d8ca8e9a588b42016d，干净未部署。正常in-tree核心W1/Werror成功、诊断0，370152B/SHAf479b291bb64e24af0c3b8b7285eb7c60c1ee474917f717827abe7f037182744；共享输出和配置恢复。398无phone操作，不把离线结果称为新实机通过。

## 转换链新事实与下一步

现有CamxChi固定提交及本机HAL／FW原件复用。完整CST计算141组通过：actualtype2，matrixsigned13/Q10，subtractsigned11，addoffset0…1023，clamp10。HAL模块片段实际调用原CDM，FW片段消费enable，开／关及低位测试通过：CST pre-LTM/index3，IQ2092→0x5a60，data0x5a68/12words；CV post-LTM/index4，IQ2200→0x6460，data0x6468/8words。此前猜CV2196撤回，勿按邻项名称套用。

CV实际Execute内联OEM数值片段282组/9024B零差，无算术stub。coefQ8/signed12；yoffset及KCB/KCR数值钳位signed11，KCB/KCR寄存器field13。本机OEM14floats顺序rToY,gToY,bToY,yoffset,am,ap,bm,bp,cm,cp,dm,dp,kcr,kcb，包末顺序cb/cr相反。新参考源范围不能覆盖本机实际契约。完整CV Execute、工厂插值和RGB物理处理域尚未验证。

接续先从保留原厂调校恢复所选模式CST/CV参数及范围，类型化内核转换配置与程序同request存储，保持既有DMA生命周期；合成输入实测转换组合，再非对角/负offset、标准媒体请求与libcamera、351触发树及完整Gamma/LTM/CCM。产品仍旁路，禁止直接把原厂RGB矩阵乘当前conversion-disabled NV12路径。

首CST路由夹具漏enable load，修正入口后通过，失败脚本/说明私存398。WSL默认用户锁属主及root依赖路径问题已核实修复；storage284挂原backing，无格式化/重建。以后访问source/build先mounted_build()，root配现有PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。

## 最后实机证据：397，非398复验

正式仍core395354864B/SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88、adapter393SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1、CAMSS389SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389、logdump365、SG ownerAPI、FW、r30/r25保持。

397临时core/fixedadapter四模式4direct，随后恢复395/393默认四摄各12共48direct/starts-stops4/error0。两epoch分开，实验前48另存。最终CPU/IRQ/PM/backing/map/import释放，ICP/CAMSS/双CCI suspended、17clks0、9railsdisabled/users0、taint0；PW10681/WP10684各一uid10000，owner_refs53是桌面CAMSS句柄。worker10439/client/collector10536终态，无test_cc_mode或dropACK参数；不重启旧runtime脚本。

host398委托397…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，原USB密钥/known_hosts；转换状态前按规则核实设备，不沿用已失效390guard。395失ACK恢复及394失败/reboot/206061B ramoops仍私存，回退副本均保留。SSC/旋转未全面复验。

363/REMAINING-CAMERA-SCOPE.md完整继续：第五2MP身份/mux、多模式、帧长/防频闪、几何/多摄同步、连续AF与正常光照画质，异步implicitfence未证明。私人FW/HAL/原厂源/ASM/CDM/图像/个体数据仅/mnt/e/edk2-samurai-out/kernel398及前序。公共mirror只本地提交、不push/PR、保留其它改动。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从398继续完整多摄/骁龙ISP目标，先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel398/README.md。398纠正396选错HAL分支：实际IPEtype2/offsetsigned11，候选8b1e8903a550ffc20a2d8f1de574c37f2260fff3 branch samurai-ipe-offset398未部署，1121正确oracle/参数页及W1构建通过。CST141组、CV内联282组与模块/FW映射已核实；CST IQ2092→5a60/data5a68，CV IQ2200→6460/data6468，勿用2196。继续恢复原厂CST/CV参数、内核typed同request转换程序、合成像素RGB域，再offdiag/负offset/标准request-libcamera及完整Gamma/LTM/363范围。398无手机操作，最后设备证据397正式395/393恢复四摄48、资源释放，guard394/host398。旧runtime均终态不得重启。关灯按低照度；source/build先root调用storage284挂原ext4，保护密钥/个体数据。\n')
note='398当前：纠正未部署IPE候选的实际HAL分支及11位偏移；原厂737叶与合成参数、完整参数页及构建通过，CST/CV契约已核对。398离线未动手机；实机最后证据仍397正式395/393四摄48。完整ISP/多摄目标active。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel398/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel398/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel398/README.md')]:
 p=ROOT/rel;p.write_text(note+'[398证据]('+link+')。以下为历史。\n\n'+p.read_text())
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[397 逐帧CC参数与硬件像素](reference/kernel397/README.md)','[398 IPE分支纠正与颜色转换契约](reference/kernel398/README.md)'))
print(json.dumps(dict(stage=398,checkpoint_updated=True,last_device_stage=397,full_goal_active=True)))
