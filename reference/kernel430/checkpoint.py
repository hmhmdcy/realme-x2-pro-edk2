"""Record verified DC execution and the remaining automatic/GTM gaps."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['source','runtime','io','native-bl','intree-build','hardware']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
h=json.loads((HERE/'hardware-validation.json').read_text());s=json.loads((HERE/'source-state.json').read_text())
assert h['corrected_direct_jobs']==12 and h['cold_and_persistent_session_outputs_byte_identical']
archive=ROOT/'archive/NEXT-SESSION-through429-recovered-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：430（DC 遍次修复；同输入重复性与 LTM 粗级消费通过）

完整多摄／ISP目标未完成。先读 WORKING-BOUNDARIES、reference/kernel430/README.md。用户已强制重启，429四摄正式恢复48帧通过；不要再请求重启。430完成底层修复和主摄新实拍输入验证，尚未完成自动IPA双遍与GTM/history。

## 当前设备与维护源码

430 r1/r2/r3均终态通过，正式模块／服务／资源恢复，无新fault、taint0，worker/client死。正式420 r31/r26＋419 core/adapter、Image363/DT389保持，磁盘模块未改、无永久安装。当前正式IPE计数在卸载候选后重置为0；PW/WP枚举owner_refs53正常，非DMA泄漏。host.py沿用429新guard，原key/known_hosts保留；prepare-runtime动态核对当前正式notes、taint和jobs基线。

source354 branch samurai-ipe-dc-topology430、HEAD d4ac27ac5cf595c9fc7c612dfdfdbcc1a002675a，parent429 91be804b。仅2文件14行dc-topology.patch：有coarse时IO config+1200 topology3；粗级pass/stripe补6个Y/chroma写出范围半字。UAPI、6008B、DMA/m2m所有权、传感器/DT/电源不变。源码干净、哈希和零fuzz/offset回放通过。

build r1十匹配模块W1/Werror零诊断，core439608B d391fa248a2c56c7f1a7e65760dc3cc0be599e6fd3120982bc19915797df2cf3；CAMSS933bda...和m2mc4d983...与429候选相同。共享构建输出/配置/symvers恢复。无需无故重建。429 r2错误MMIO诊断build core da4591...禁止加载；430没有新MMIO读取。自身诊断Oops及恢复历史保留429/INCIDENT，别归因原厂。

## 根因、原厂证据与实机结果

旧oracle仅到HardwareDriver_EnqueueJob，遗漏后续DistributeJob和BLGenerator_GenerateBL。本轮probe-native-bl.py执行原厂BL初始化/最终调度：旧topology0粗级mask[0,0]、FULL[3,0]，DC被丢弃。仅topology3仍不够；补6范围后粗级[1,0]、FULL[3,0]。原HAL PostPipelineCreate 0x2cd8b0..0x2cd8d8片段16条件确认PPSprofile2且passes>=2用3，不是猜常量。

native-bl-validation：compiled C IO/stripe对全native HAL，完整512KiB程序、2MiBheap、全部存活分配/work/context和队列一致，40二进制对象；unused stripe脏padding不复制。OS/queue provider是夹具非原厂OS；窄READ观察不改程序/heap。C ASAN/UBSAN+ARM64输出11472B一致，legacy DCoff不变、invalid no-write/overlap检查通过。固定FULL640x480/display8＋PD10160x120 stride768/slice60/46080B，DC需IP+mask；其它尺寸未泛化。

control：正式FULL-only4jobs，LTMoff重复0byte；单遍IP/DC0重复164373bytes/YmeanAbs4.73536，证明旧不稳依赖LTM。
r1：复用428/main同SOF17 FULL/PD10和424原厂6008B包，4个real/black/white/repeat-real，首尾0byte；只变PD10输出改变。
r2：scene-pair.c新主摄pattern0，6对FULL/PD10完整同SOF、tail0，选SOF5后4个双遍jobs；首尾0byte，黑对照332742bytes/Y26.2614，白352298bytes/Y13.2961。
r3：同r2真实输入，在一次open/STREAMON内4连续request，序号0..3、scratch request1..4、requestDONE poll；四种输出各自与r2逐字节一致、首尾0byte。starts/stops1。没有依赖每帧重启来清历史。
总16direct，修复候选12；hardware-validation.json自动核对。ANR/TFoff、FULL固定，粗级变化→输出变化且重复相同，为LTM实际消费粗级输入的因果证据。

## 统计与自动链路仍缺什么

scratch原厂所需从71488变46128（46080+48），r1/r2/r3仍全a7；不是已验证DC表导出。固定参考独立LTMAverageLUT/avg3d DMI pingpong与13调校LUT不同；真正片内average RAM的具体bank、reset和字节读出尚未完成。当前恢复DC遍次后的冷/连续行为稳定，不等同已逐字节导出内部统计。不要读未映射PPS或凭猜bank改寄存器。

本轮仍固定424包，IPA数学提交0。下一步把生产libcamera424的FULL/PD10同SOF成组队列接CamssIpe：OUTPUT QN10两planes，CAPTURE NV12，保持两源FD到双DQ+requestDONE，stop先join再释放，完整缺帧/旧SOF/epoch失败不提交历史。生产源码在/mnt/samurai-full282/libcamera424-tone-domains/src/libcamera-v0.7.2，pipeline/camss-vfe，IPA/camss-vfe。本轮只读取，没有修改或克隆它。

423/424已有BHIST1024/真实曝光gain/lux/IFEgamma→TMC11→LTM13/IPEGamma→6008B和最终成功提交、single pending、缺lux hold。GTM在IFE/BPS，LTM在IPE；本机IFEGTM10::Execute0x31fc00、IQInterface::GTM10CalculateSetting0x37c818已定位但原树/数学/寄存器应用未恢复。原厂非零GTM份额不能清零。统计→后续IFE GTM生效版本→对应图像IPE→最终成功history，不能逆因果。同帧关联未验收，自动链路最后成功仍424，前摄TMC关保持。

其余四摄模式/视频/第五2MP/光学个体校准/多摄同步见363剩余清单。普通新scene已拍但没宣布画质校准通过。

## 工具和接续

所有WSL source/build/ext4操作前root导入reference/kernel284/storage.py并mounted_build；原32GiB镜像不重建。Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。私件kernel430有build、bl-*、control-collected-r1、runtime-collected-r1/r2/r3，所有worker/build/exec终态。原件/ASM/系数/图像不出私存。公共自有脚本+脱敏证据，scoped mirror保护无关index和3处工作树，不push。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从430接续：内核2文件修复PPS topology3与6粗级写出范围，原厂最终调度由丢DC变粗级[1,0]/FULL[3,0]，不是旧enqueue前oracle。512KiB程序/2MiBheap/队列等40对象一致。修复12direct含新主摄6同SOF对；真实repeat0byte，黑白PD10单变有输出差；同一次开流4请求与分别开流各输出逐字节一致。正式模块/服务/资源已恢复，无新fault、taint0，无永久安装。scratch46128仍a7，不是统计表导出；bank/reset逐字节未证，勿猜MMIO。当前自动IPA双遍尚未接、本轮数学提交0，GTM上游生效版本/同图像history关联未做，完整目标未完成。先读NEXT与430README；优先复用原厂，从生产libcamera424接同SOF PD10双源生命周期，再补GTM真实树/数学/寄存器及因果。429越界诊断build2禁止加载；新guard429，原key保留。storage284先挂原盘、私件保密、终态后依赖、scoped提交。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=430,latest_work_stage=430,current_boot_guard_stage=429,in_progress_installed=False,
  current_device_recovery_required=False,current_device_health='430 topology/extents fixed; 12 corrected direct jobs including fresh main pair and persistent session; restored formal modules/services, no new fault, taint0',
  current_device_loaded_module_state='Formal420 CAMSS and419 core/adapter restored after430 r3; loaded notes matched baseline',
  current_device_last_successfully_restored_experiment='430 r3 persistent-session four-request replay',
  last_successful_scene_stage=430,last_successful_automatic_ipe_scene_stage=424,
  ipe_pd10_latest_evidence=prefix+'reference/kernel430/README.md',ipe_pd10_dual_pass_live_capture=True,
  ipe_ltm_full_dc_coarse_pass_implemented=True,ipe_ltm_coarse_pd10_pixel_producer_implemented=True,
  ipe_ltm_dc_statistics_verified=False,ipe_ltm_dc_consumption_verified=True,ipe_ltm_replay_repeatability_verified=True,
  ipe_ltm_dc_consumption_scope='Fixed640x480 stock LTM; fixed FULL and real/black/white/repeat real PD10, deterministic cold and persistent session. Causal coarse consumption, not bytewise DC table export or automatic IPA.',
  ipe_ltm_coarse_latest_evidence=prefix+'reference/kernel430/README.md',
  ipe_ltm_final_native_pass_distribution_verified=True,ipe_ltm_dc_topology_and_write_extents_corrected=True,
  ipe_ltm_cold_and_persistent_session_outputs_identical=True,ipe_ltm_dc_sram_bank_reset_readout_complete=False,
  latest430_ipe_corrected_direct_jobs=12,latest430_ipe_control_direct_jobs=4,latest430_fresh_same_sof_pairs=6,
  latest430_ipa_math_history_commits=0,ipe_full_factory_tone_pipeline_complete=False,
  ipe_gtm_applied_version_math_history_association_verified=False,formal_disk_modules_unchanged_after430=True)
 if '/kernel/' in rel:d.update(maintained_branch=s['branch'],maintained_commit=s['commit'],maintained_pd10_ipe_candidate_stage=430)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='430当前：修复IPE粗级DC遍次被丢弃；相同FULL/PD10重复输出0差异，黑白PD10单变和连续请求确认LTM粗级消费。含新主摄同SOF采集，共12个修复候选作业；正式环境已恢复，无新fault、taint0。统计表读出、自动IPA双遍与GTM/历史关联仍未完成。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel430/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel430/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel430/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith(('429当前：','430当前：'));p.write_text(note+'[430证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();old='[429 四摄恢复与单核双遍统计调查](reference/kernel429/README.md)';new='[430 DC遍次修复与LTM粗级消费](reference/kernel430/README.md)';assert old in t or new in t;p.write_text(t.replace(old,new))
print(json.dumps(dict(stage=430,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
