"""Record the verified production PD10 path without claiming GTM completion."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['source','session','bank','ipa','hardware','build','intree-build','gtm-location']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
h=json.loads((HERE/'hardware-validation.json').read_text());ks=json.loads((HERE/'kernel-source-state.json').read_text());assert h['numeric_history_commits']==48
archive=ROOT/'archive/NEXT-SESSION-through430-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：431（原厂 bank 策略确认；生产 IPA 同帧 PD10 自动双遍 48 帧通过）

完整多摄／ISP目标未完成。先读 WORKING-BOUNDARIES 与 reference/kernel431/README.md。429硬件重启与正式四摄48帧恢复保留；430已解决丢DC和重复性，431接生产自动双遍。GTM生效版本/history、片内平均表字节读出、画质/其它模式仍未完。

## 当前设备与候选

431 r4终态passed，普通／隔离IPA各24主摄scene，48direct双遍+48数学提交；另4个旁路/DC会话转换，jobs=completed=direct52，failed/cancel/first_error0。正式模块/服务/媒体图/资源已恢复，无新fault，taint0，worker/client死。当前仍正式420 r31/r26、419 core/adapter、Image363/DT389，无永久安装、刷写或NV/OTP/persist访问。正式模块重载计数0，PW/WP枚举owner_refs53正常，非DMA泄漏。

host431沿用429新guard与原SSH key/known_hosts；prepare-runtime动态正式notes/taint/jobs基线。所有本地build/exec和远端worker终态。此前自加MMIO越界Oops在429/INCIDENT保留，危险429build2 core da4591...禁止加载，当前未加任何MMIO读取。

维护kernel source354 HEAD52127e558704de6a640d076ef605182fe6fff0d7，branch samurai-ipe-request-coarse431，parent430 d4ac27ac。只改m2m23增9减：use_coarse来自已校验当前params的LTM/DC；ensure_session匹配单/双遍，模式改变先用原destroy保护再create/configure，第三平面仅在需要DC时导入；VB2一直持有两个提交平面。core/板级DT/传感器/电源/UAPI/6008B/不确定DMA保留策略未变。

intree build1十匹配模块W1/Werror零诊断，m2m141624B e6828a0ca8069181f3f7f9818fdfe888d141c140d0ea753f52af2de00500dcb5；core d391fa...和CAMSS933bda...与430相同。共享build输出/config/symvers已恢复。session-validation执行实际ensure_session C，ASAN/UBSAN和ARM64 qemu七转换/失败保持用例通过。无需无故重建。

## 原厂平均值表策略

trace-banks/check-banks执行原firmware handle mapping/context store和最终LTM序列化，非默认夹具值推断。m2m RT type2→kind0→DC/IP bank0，非RT type3→kind1→bank1离线反例；本机HAL原位插入确认bit14/15。粗级DC1/IP0/sum-clear1，全尺寸DC0/IP1/sum-clear0，同bank。实际r4内核日志确认type2；仍无片内bank读回或平均值表逐字节导出。sum-clear是命令策略，不能称已读到所有SRAM单元为0。scratch46128仍不是已验统计导出。

保留430原厂DistributeJob/BLGenerator最终同步与program/heap/队列一致证据；当前paired用1核，DC→IP由固件控制，未加CPU bank切换。431同一开流旁路/DC/旁路/DC四请求成功，两个旁路/两个DC各相同，DC还等于430新主摄SOF5真实输入输出。初始化/转换行为稳定。

## 生产用户空间与实拍

候选/mnt/samurai-full282/libcamera431-pd10-auto/src/libcamera-v0.7.2，基424，9文件patch0046。IPA4私有SensorControlConfiguration增加pd10能力（proxy/core/module同版），按模式解析可选ife_ds4，上传零flags16B typed DS4 block，actual IPA bytes等于428原厂块。私有factory-s5kgw1只在4608x3456模式插入原厂426/428 sensorMode2 Preview coeff；另4608x2592模式未加。前摄TMC关保持。旧profile无能力不强启粗级。

pipeline链接/配置/分配内部DS4，在FULL前streamon；真实kernelSOF配对FULL640x480和PD10160x120 stride768/46080B。NV12两个逻辑Y/UV同FD连续offset和容量检查后合成FULL内存plane，再加PD10；两个FD及原SOF持有至双DQ+requestDONE，stop先join。single-pending数值串行在最终frameProcessed发送后派发下一图像；每张arrival判断250ms，sensorContexts有界保留至迟到统计，不放宽AE校验。

最终用户build7 libcamera SHA d03e076e8211026a3c663d217f73ab9998e91f81c57d109ca5e7af4ec0668a8f，IPA62505f0...、proxy3cb416...；IPA与build3后相同，actual IPA4 Werror合约+签名通过，缺lux/busy/失败/旧回执/停止重启历史复用并验证，数学/历史实现与424字节不变。source-validation两个patch零fuzz/offset，产物hash匹配。

r4普通24帧/24commit/23种参数摘要，隔离24/24/22；每次previous-ltm-lux等于上一成功提交lux。硬件审计匹配PD10_READY SOF、真实BHIST/lux/exposure/gain、6008B新包、实际请求成功及最终数值回执，图像实际Y均值/大小匹配元数据；无IMAGE_PAIR_TIMEOUT或AE拒绝。隔离多1份无应用图像的观测停止时abort，不提交数值。

r1/r2/r3失败保留私存：r1误将NV12两个逻辑视图当1plane，提交前本地拒绝，0commit；r2首帧成功/1commit，busy导致下一空旁路在旧paired session被拒；r3转换4job+13commit过，但旧global deadline提前处理新图并删曝光上下文，AE拒绝。均恢复正式环境/taint0。不得将它们写为整链通过。r4才通过完整本轮。

看过未调色NV12解码样本：场景可辨认，仍雾感/偏色，未画质验收、未重做AF/光学矩阵。原图/完整日志/系数/ASM均在private kernel431。

## GTM接续

inspect-gtm已定位本机IFEGTM10::Execute0x31fc00(2200B)和IQInterface::GTM10CalculateSetting0x37c818(10324B)，私存asm。四原厂文件GTM IFE/BPS45module roots，不把180内部目录项当roots。14普通IFE模式查询与原stock-selection-manager全部一致，私存*-gtm-directory/selections。尚未执行GTM数学、恢复typed参数块或应用到IFE。

下一步优先原厂GTM parse/tree/math→IFE参数/真实ACK生效版本→对应图像ADRC/LTM/history。GTM在IFE/BPS上游，不能用本图hist逆因果；原厂GTM份额非零不能清零伪完整。当前48次数学提交只覆盖已有TMC/LTM+真实PD10，绝不称GTM关联通过。其它四摄自动/尺寸/视频/第五2MP/个体光学/几何同步见363剩余清单。

WSL每次source/build/ext4先root storage284.mounted_build，原32GiB镜像不重建。Unicorn PYTHONPATH14。私件保密，公共仅自有代码/脱敏证据，scoped mirror保留无关index与3处工作树，不push。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从431接续：原厂RT type2→context0→DC/IP bank0、粗级sum-clear1/全尺寸0指令确认，无SRAM字节导出。生产IPA4真实同SOF PD10自动双遍普通/隔离各24帧，48真实math commits；旁路/DC切换4job通过且输出重复一致。修复NV12逻辑plane合并、底层按请求选单/双遍session、single-pending派发和每图arrival超时/曝光context保留。r4正式模块/服务/资源已恢复，无新fault、taint0，无永久安装；r1/r2/r3失败保留。维护kernel HEAD52127e55，libcamera431候选build7，先读NEXT/431README。GTM已核对45 IFE/BPS模块roots/14模式选择及两本机入口，但原数学、IFE块/ACK生效版本/对应图像history仍未接；不能把48次LTM提交称完整GTM或画质校准。继续原厂优先、底层收敛，不猜MMIO，不清零GTM份额。429新guard，storage284先挂原盘，私件保密、终态后依赖、scoped本地提交。\n')
for attempt in ['r1','r2','r3']:
 p=HERE/('runtime-'+attempt+'-validation.json');d=json.loads(p.read_text());d['state']['failure']='Integration acceptance failed; original traceback and client logs retained privately.';d['state']['failure_details_private']=True;p.write_text(json.dumps(d,indent=2)+'\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=431,latest_work_stage=431,in_progress_installed=False,current_device_recovery_required=False,
  current_device_health='431 r4: 48 real same-SOF automatic PD10 IPE jobs and48 numeric commits plus4 bypass/DC transitions; restored formal modules/services/resources, no new fault, taint0',
  current_device_loaded_module_state='Formal420 CAMSS and419 core/adapter restored after431 r4; loaded notes matched baseline',
  current_device_last_successfully_restored_experiment='431 r4 automatic native/isolated IPA4 main scenes',last_successful_scene_stage=431,last_successful_automatic_ipe_scene_stage=431,
  ipe_pd10_latest_evidence=prefix+'reference/kernel431/README.md',ipe_auto_tone_latest_evidence=prefix+'reference/kernel431/README.md',ipe_candidate_private_ipa_version=4,
  ipe_real_same_sof_pd10_production_ipa_candidate_connected=True,ipe_automatic_dual_pass_main_hardware_verified=True,
  ipe_automatic_dual_pass_candidate_installed=False,ipe_numeric_tmc_ltm_history_installed=False,
  ipe_ltm_rt_bank0_native_command_policy_verified=True,ipe_ltm_dc_sum_clear_then_ip_same_bank_verified=True,
  ipe_ltm_dc_sram_bank_reset_readout_complete=False,ipe_ltm_dc_statistics_verified=False,
  latest431_live_dual_pass_frames=48,latest431_ipa_math_history_commits=48,latest431_transition_direct_jobs=4,
  ipe_auto_dual_pass_evidence=prefix+'reference/kernel431/hardware-validation.json',ipe_bank_policy_evidence=prefix+'reference/kernel431/bank-validation.json',
  ipe_gtm_applied_version_math_history_association_verified=False,ipe_full_factory_tone_pipeline_complete=False,formal_disk_modules_unchanged_after431=True)
 if '/kernel/' in rel:d.update(maintained_branch=ks['branch'],maintained_commit=ks['commit'],maintained_pd10_ipe_candidate_stage=431)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='431当前：确认原厂RT bank0与DC清和→IP策略；生产IPA同SOF PD10自动双遍普通/隔离各24帧，48次数学成功提交，旁路/DC切换通过。正式环境已恢复，无新fault、taint0。GTM硬件生效版本/历史关联、片内表字节读出与画质校准仍未完成。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel431/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel431/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel431/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith(('430当前：','431当前：'));p.write_text(note+'[431证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();old='[430 DC遍次修复与LTM粗级消费](reference/kernel430/README.md)';new='[431 生产IPA同帧PD10自动双遍](reference/kernel431/README.md)';assert old in t or new in t;p.write_text(t.replace(old,new))
print(json.dumps(dict(stage=431,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
