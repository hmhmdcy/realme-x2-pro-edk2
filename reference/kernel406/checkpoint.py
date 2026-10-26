"""Record corrected physical LTM evidence and restored formal camera state."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];state=json.loads((HERE/'source-state.json').read_text());runtime=json.loads((HERE/'runtime-validation.json').read_text());current=json.loads((HERE/'current-state-validation.json').read_text())
for name in ['ip-enable','pixels','current-state','intree-build','test-intree-build','client-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert runtime['state']['passed'] and runtime['state']['terminal'] and not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
assert not json.loads((HERE/'pixels-validation-r1.json').read_text())['passed']
state.update(r2_pixels_pending=False,hardware_fixed_diagnostics_verified=True,hardware_fixed_diagnostics_scope='R2 fixed52 at640/650x480 NV12/NV21 with44 LTM and8 combinedGamma; not full tuning/DCstats/fault recovery',candidate_permanently_installed=False,normal395_393_restored=True,phone_accessed=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=406
 for key in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[key]=state['branch']
 for key in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[key]=state['commit']
 d.update(current_device_revalidated_stage=406,ipe_latest_hardware_stage=406,current_camera_evidence=prefix+'kernel406/README.md',latest_stage_device_mutated=True,latest_stage_phone_accessed=True,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,
 kernel_source_scope='406 one SoC geometry file corrects physical full-pass IP_EN to explicit request,not HAL DC/coarse policy. Fixed52 hardware diagnostics passed; temporary candidate removed. Formal395/393 remains on disk/loaded.',
 in_progress_installed_scope='406-r2 normal395/393 restored,four cameras48 direct,error0,resources released,no test parameters,taint0. Candidate source b4f382a built/tested privately,not permanently installed.',
 ipe_ltm_hardware_verified=True,ipe_ltm_hardware_scope='Fixed640/650x480 NV12/NV21 port8/core2,CST/identityCC/CV,zero-scale IP/mask identity,LAzero/constant gray,reverseGammalinear/zero,and combinedGamma. Not full tuning,all geometry,DCstatistics or forced fault recovery.',
 ipe_ltm_hardware_evidence=prefix+'kernel406/pixels-validation.json',ipe_ltm_hardware_fixed_diagnostics_verified=True,ipe_ltm_hardware_fixed_diagnostics_frames=52,ipe_ltm_latest_enabled_frames=44,ipe_ltm_combined_gamma_frames=8,
 ipe_ltm_full_pass_ip_from_explicit_request=True,ipe_ltm_geometry_dc_condition='Full-pass stripe+416 equals explicit image_processing,independent ofDC/coarse quarter geometry. Original HAL DC&&IP&&quarter>=72x54 gate is historical and intentionally not used by this explicit single-pass API.',
 ipe_ltm_ip_enable_evidence=prefix+'kernel406/ip-enable-validation.json',ipe_ltm_native_full_striping_evidence=prefix+'kernel406/ip-enable-validation.json',ipe_ltm_native_full_striping_scope='404 geometry retained;406 intentionally changes only full-pass IP field.32 native/target-FW checks and52 fixed hardware diagnostics;not all supported geometry pixels verified.',
 ipe_ltm_r1_failed_pixels_retained=True,ipe_ltm_r1_pixel_evidence=prefix+'kernel406/pixels-validation-r1.json',ipe_ltm_data_collection_statistics_verified=False,ipe_ltm_nonzero_scale_lce_math_verified=False,ipe_ltm_forced_fault_reset_verified=False,
 ipe_ltm_full_factory_numeric_math_verified=False,ipe_ltm_product_default_enabled=False,ipe_ltm_runtime_submission_enabled=False,ipe_ltm_temporary_hardware_submission_verified=True,ipe_ltm_runtime_submission_scope='Candidate internal API physically exercised via private fixed adapter;formal395/393 restored,no product/default/libcamera LTM activation.',
 ipe_latest_stage_actual_frames=200,ipe_latest_stage_RT_frames=200,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=104,ipe_latest_stage_normal_restored_frames=96,
 ipe_latest_stage_frames_scope='Two406 epochs,each52 fixed diagnostics+48 restored formal direct frames. R1 mask/LA semantics failed;R2 corrected52 passed.200 is transport total,not all pixel success. Final normal epoch48 only.',
 current_health_scope='406-r2 physical corrected fixedLTM52 and restored normal four cameras48;CPU/IRQ/PM/maps/imports released,17clocks0,9railsdisabled/users0,taint0,single PW/WP. Full optics/AF/SSC/rotation/multicam tuning not newly verified.',
 icp_next_step='Complete original LTM numeric/dynamic interpolation and nonzero scale/LCE,DC statistics/input-domain handling;test continuous requests and LTM/Gamma fault recovery as needed. Then standard media request/libcamera and full363 camera scope. Preserve explicit IP bit correction;do not reinstate HAL coarse/DC gate.')
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through405-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text=f'''# 当前检查点：406（LTM固定实像素通过，显式IP修正，正式395／393恢复）

先读WORKING-BOUNDARIES.md、reference/kernel406/README.md。完整多摄／骁龙ISP目标active。用户已开灯出门，后续按实际照明判断；本轮LTM诊断为合成输入。405交接归档archive/NEXT-SESSION-through405-2026-10-21.md。

## 源码与关键修正

candidate branch {state['branch']}，HEAD {state['commit']}，父405 {state['parent']}；仅ipe.c一个SoC编码文件，干净未永久安装。芯片板级/传感器/主线框架/产品用户空间不变。405 typed接口与所有权保留，旧CC/Gamma ABI及opcode1不变。

最关键：stripe+416驱动物理LTM IP_EN（reg5c60 bit10）。原HAL把它绑定DC和quarter>=72x54，造成当前显式单全帧DC0/IP1时硬件IP仍关闭、但处理crop按IP+mask扩2。R1 mask-only后续条带恰好移位2px，LAzero/1024/2048无效。原HAL完整多pass流程不据此判错；是移植策略不适合当前接口。406直接令字段416=image_processing。勿再把404原quarter/DC规则恢复为显式IP语义。

IP&&mask仍324step/6halo/处理扩2，否则328/4；输出crop/plane/radial用原output。32组actualC hostASanUBSan/ARMQEMU及完整FW准备证明至多只改5c60 bit10，其余CDM/job不变，IP0与bypass全字节一致。小尺寸128/282只有本轮离线证据。

W1/Werror0diag；正确R2核心415720B/SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4，private406/qcom-camss-icp-a5-core-intree-r1.ko。406/test-intree旧核心仍是405 SHAec8bf38d…，勿误用为修正核心。R1/R2 adapter和client完全相同：adapter5036ef88…/113952B，client5af0eba2…/976936B。test源码/共享build config/outputs/symvers均恢复。

## 两轮实机与像素

R1 root k406-ltm-r1，core405，worker20269/collector20313终态，52transport+正常48恢复，但mask-only640差5736B、650差10703B，后续条带Y/UV等于左移2px输入；LA几种表全无效。pixels-validation-r1 passed=false保留。命令定位DC0/1仅blob416和5c60 bit10不同；原字节一致不等于期望功能正确。

R2 root k406-ltm-r2，core406，worker21352/collector21413/client均终态。52诊断/starts-stops52/error0，44LTM、8组合Gamma，port8/core2，width640/650,H480,NV12/NV21,13固定模式。mode0旁路；1转换对；2LTM子模块off；3IP零scale；4IP+mask；5LAzero；6LA2048；7RGammazero；8RGammalinear；9LA1024；10DC+IP+mask；11同4+linearGamma；12同4+zeroGamma。

R2 mode2/3/4/8/10与mode1全图零差，2px位移消失；mode5/7/12全Y0 UV128；LA2048/1024在每尺寸/格式8灰阶块所有内部像素分别128/64，误差0，不称整张彩色图恒定。mode11较mode4最大差1（640为100B、650为160B）；全部13模式NV12/21归一化所有字节相同。640转换对与402旧460800B一致，R1未受修正影响的控制图像也一致。host CRC/输入生成器，client输入不变/canary/sequence/timestamp通过。两轮各52+48=200direct，不能称200全像素通过；最后正常epoch只48。

本轮没有非零LTMscale/LCE全公式、DC统计读回、动态factory插值、全部尺寸、连续参数变化或LTM强制丢ACK/故障复位证明。不能把DC flag提交成功叫完整统计支持。新接口只是暂时在固定adapter使用，正式默认仍旁路高级IPE IQ。

## 当前正式设备

已恢复formal core395/adapter393/CAMSS389，r30/r25四摄IMX471/IMX319/S5K3M5/GW1各12共48direct，error/cancel/extra0，starts-stops4。CPU/IRQ/PM/backing/maps/import释放，ICP/CAMSS/双CCI suspended，17clks0，9railsdisabled/users0，taint0；PW21581/WP21584单例uid10000，owner_refs53桌面CAMSS句柄。无test_cc/chain/gamma/ltm/dropACK、dump/timeout/新相关fault/reboot/刷写。current-state-validation.json有正式notes/文件/profile核对。

host406→405…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，同一boot394。保留394 ACK丢失失败reboot及206061Bramoops、395 reset assert2us/deassert/readback与双IPE新ACK后释放修复。旧worker全终态，不重启旧事务。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389/logdump365、SGownerAPI、FW不变；正常回退文件/个体备份保护。

## 后续与既有契约

继续原厂完整LTM数值/动态触发、非零scale/LCE、统计与输入域；接标准media request/libcamera，厘清IFE/IPE CCM/Gamma/逆Gamma职责。原HAL ANR440==1或topology2624==3是上层选择策略，当前内核显式接口不自动复刻。需要时做LTM/Gamma连续请求及强制故障恢复。不得以本轮固定诊断替代完整调校。

405 LTM类型2800B，先lock内CPU copy/check再coherent/MAP，IQ/DMI/LUT同request保留，临时copy所有出口释放。NULL LTM回旧Gamma/colour。组合IQ8944/PAGE12288，arraybase2592，pre32最多CST20+LTM11，post96最多CC/CV20+Gamma12；旧Gamma6016/pre32/post64仍独立。CST2784/CC2840/CV2884，GammaDMI2928/LUT2976，LTMDMI6048/LUT6208。13LUT2736B，type1/opcode1/reg5c08/selectors1..13；resource3296额外560用途仍未证。原逆Gamma29输入miss/hit7424B对352oracle零差，输入IFEgreen64，不可用IPE256。

原厂完整树在350/351/399私有目录；factory完整LTM/ADRC math和插值未完成。363/REMAINING-CAMERA-SCOPE.md全范围继续：第五2MP身份/mux，多模式，帧长/防频闪，连续AF/光学，几何/多摄同步；异步implicit fence、SSC/旋转未全面复验。source/build先root storage284.mounted_build挂原32GiB ext4，勿格式化/重建；rootPython PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原FW/HAL/OEM/ASM/CDM/表/日志/图像/密钥私存406及前序；公共mirror只本地提交、不push/PR、保护无关index。
'''
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从406继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel406/README.md。R1固定LTM52发现DC0/IP1/mask1后续条带移位2px、LA无效；实际FW从stripe416写5c60bit10 IP_EN，原HAL DC/quarter策略错误用于当前显式单全帧。406修为416=image_processing（不改crops/分区/所有权），32native/FW检查及R2相同adapter/client52实像素通过：mask位移消失、LAzero黑/2048与1024灰块128与64、RGammazero/linear、组合Gammalinear最大1/zero黑，NV12/21全等；完整factory/非零scale/LCE/DC统计和fault仍未完成。candidate '+state['branch']+' HEAD '+state['commit']+' 一文件干净未永久安装，正确核心b0fbf678…415720B；test-intree旧核心是405勿误用。R2worker21352/collector21413等终态，正式395/393恢复，四摄48/资源释放、taint0、PW21581/WP21584单例、guard394。同阶段200direct非全像素通过，r1失败保留。下一步full原厂数值/动态触发/输入域、统计和标准media request/libcamera，全部363剩余范围继续。source/build先root storage284挂原ext4，保护原厂/个体表和密钥。\n')
note='406当前：LTM固定实像素通过；修正原HAL策略用于单全帧时的IP启用耦合，消除2像素位移并恢复LA效果。R2诊断52及正式四摄48通过，正式395／393已恢复；完整调校与多摄目标继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel406/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel406/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel406/README.md')]:
 p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('405当前：');p.write_text(note+'[406证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[405 LTM类型化请求与所有权](reference/kernel405/README.md)','[406 LTM实像素与显式IP修正](reference/kernel406/README.md)'))
print(json.dumps(dict(stage=406,checkpoint_updated=True,last_device_stage=406,full_goal_active=True)))
