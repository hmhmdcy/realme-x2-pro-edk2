"""Publish the recovered state while retaining the unsuccessful feature evidence."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
recovery=json.loads((HERE/'camera-recovery-validation.json').read_text());single=json.loads((HERE/'single-core-hardware-validation.json').read_text())
assert recovery['passed'] and single['passed'] and not single['feature_acceptance_passed']
archive=ROOT/'archive/NEXT-SESSION-429-before-recovery-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：429（设备与正式四摄已恢复；单核双遍完成，DC／重复性仍未验收）

完整多摄／ISP 目标未完成。先读 WORKING-BOUNDARIES、reference/kernel429/README.md、INCIDENT.md。用户已硬件强制重启并进入 Linux，无需再问重启。

## 当前设备健康与实验结果

已用原密钥 raw SSH 核实 boot ID 与旧故障启动不同；adopt-recovered-boot.py 核对 compatible/release/cmdline、正式三模块磁盘摘要及 loaded notes、资源无遗留、taint 0，并创建 k429-recovered 新 guard。429/host.py 自动使用它，旧394 guard不可再用。postboot-adoption-private 在私存。

recover-cameras.py launch/observe/collect 已终态：前摄IMX471、广角IMX319、长焦S5K3M5、主摄S5KGW1各12帧，48次正式direct IPE完成，无新fault、taint0、资源全释放，PW/WP各1正常恢复。camera-recovery-validation.json passed。

随后429 r4用已移除错误诊断的build r3与修正poll的client完成4个单核双遍direct作业，无新fault、taint0，正式模块/服务/资源恢复，worker与client均退出。runtime-r4-validation.json和single-core-hardware-validation.json为证。最新正式IPE计数在模块重载后为0，PW/WP枚举owner_refs53正常，不能当DMA泄漏。当前仍正式420 r31/r26、419 core/adapter、Image363/DT389；无永久安装、刷写或NV/OTP/persist改动。

功能未通过：r4相同真实FULL/PD10输入两次输出不同138366 bytes，Y平均绝对差3.1743977865；71488B scratch四次全a7。单核未解决重复性。r2双核也不稳定（152871bytes，YmeanAbs3.4047135）。黑白PD10对照差异不能证明DC消费，因为真实重复输入也不稳定。r4复用428主摄scene SOF17图像对和424原厂LTM包，不是自动IPA新实拍；本阶段无数学历史提交、无GTM生效关联。

## 保留故障与修复事实

r3自加readl(resources.ipe[n]+0x5c60)越过DT限制的TOP映射，造成level3 translation fault/Oops，taint640，client卡v4l2_m2m_cancel_job，不能kill。未强制卸载、解映射或回收未知DMA。正常BusyBox reboot后当时SSH拒绝，后用户强制重启才恢复。故障是本轮诊断错误；历史在INCIDENT.md和archive/NEXT-SESSION-429-before-recovery-2026-10-22.md，不能抹成原厂或PD10故障。当前已恢复。

source354 HEAD91be804b74c12288d1de0f7f8a5488c9687d8a47，branch samurai-ipe-pd10-runtime429，8文件patch无fuzz/offset复放、源码干净。build r2 core da4591...含错误读取禁止再加载；build r3 core9bdaa51fa9204719abadc174b6f202ddf35ae3b0ca331aaf24b9441bfe93bd4b、CAMSS933bda...、m2mc4d983...为已上机r4的修正版cohort。10匹配模块Werror0诊断，输出/配置已恢复，无需无故重建。prepare-runtime.py 仅接受build3、429新guard、当前正式notes/taint/jobs动态基线，并要求四摄恢复通过。r4实际来源记录私存，勿再用旧394/512/0硬编码。

## 已接通的范围与下一步

typed core会话coarse layout、帧port1、第三DMA-BUF持有/容量/重叠检查与不确定完成保留；所有释放判据覆盖coarse。legacy job与6008B参数ABI不变。实验QN10 OUTPUT两planes为连续NV12与原生PD10，CAPTURE单NV12，调用者负责同SOF成组；FourCC未上游保留。root0400 ltm_scratch是完成后复制的临时快照，不是正式DC接口。

原厂双遍C只覆盖FULL640x480 NV12/display8+160x120 PD10 stride768/slice60/46080B，DC要求IP+mask。双pass模块/stripe指针按各基址编码，actual C ASAN/UBSAN+ARM64输出11472B一致，native HAL/FW完整512KiB命令与job匹配，corecount1/2各有原厂对应。离线prepare不能代替像素/统计证明。

下一步从原厂指令、配置与内存生命周期确认DC真实存放、bank初始化、遍次同步及输出不确定性；不要再读未映射PPS、猜bank，或将scratch未改当DC天然不存在。原厂LTM13固定参考含DC/IP_AVG_BANK_SEL的SW override，实际FW策略尚待证。

再接生产IPA真实PD10队列。423/424已有同SOF BHIST1024/实际曝光gain/lux/IFEgamma→TMC11→LTM13/IPEGamma→6008B，最终图像成功才提交数学历史、单pending、缺BG/lux hold。GTM在IFE/BPS上游，LTM在IPE，仍缺统计→后续IFE GTM生效版本→对应IPE图像/history因果关联。front原厂TMC关保持。428四摄已有144完整PD10配对、236simulFULL+24control；其它模式/视频/第五2MP/光学个体校准见363剩余清单，不缩小范围。

WSL任何source/build/ext4访问先root导入storage284.mounted_build，原32GiB镜像不重建。Unicorn PYTHONPATH14。私件/ASM/原厂系数/图片只私存。所有本地exec和设备worker已终态。公共镜像scoped提交保留其它index与3处工作树，勿push。完整目标未完成。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从429接续。用户已强制重启，429新boot/正式模块与四摄48帧通过，PW/WP正常、taint0。修正版build r3的r4单核双遍4direct完成且恢复正式模块服务，无新fault；但scratch仍全a7，真实重复输出差138366bytes/YmeanAbs3.1744，单核未解决重复性。DC写出/LTM消费、GTM生效版本与IPA数学历史关联未验收。先读NEXT及429README/INCIDENT，原厂数据优先从底层追踪DC真实存放/bank初始化/遍次同步，勿猜寄存器。host用429新guard，prepare-runtime动态正式基线；build r2含已修复的越界诊断禁再加载。无新增自动IPA历史，勿称完整适配。私件保密、storage284挂原盘、terminal后依赖、scoped本地提交。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(current_device_recovery_required=False,current_device_health='Verified physical restart, four formal cameras 48 IPE frames and fixed single-core r4; no new fault, taint0',
  current_device_loaded_module_state='Formal420 CAMSS and419 core/adapter restored after429 r4; loaded notes matched baseline',
  current_device_last_successfully_restored_experiment='429 r4 fixed single-core four-job replay',
  current_device_recovery429_evidence=prefix+'reference/kernel429/camera-recovery-validation.json',
  current_device_revalidation429_scope='Formal four-camera recovery: 12 frames each,48 IPE completions; fixed build3 replay:4 single-core direct jobs; DC/repeatability acceptance failed',
  ipe_pd10_dual_pass_direct_jobs=8,ipe_pd10_single_core_direct_jobs=4,
  ipe_pd10_single_core_evidence=prefix+'reference/kernel429/single-core-hardware-validation.json',
  ipe_pd10_fixed_build3_hardware_transport_verified=True,ipe_ltm_replay_repeatability_verified=False,
  ipe_ltm_dc_statistics_verified=False,ipe_ltm_dc_consumption_verified=False,latest429_ipa_math_history_commits=0)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='429当前：强制重启后正式四摄48帧恢复通过，修正版单核双遍4作业完成并恢复正式模块／服务，无新fault、taint0；DC统计、重复性、GTM与数学历史关联仍未验收。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel429/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel429/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel429/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('429当前：');p.write_text(note+'[429证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text().replace('429 PD10接IPE双遍与诊断故障待恢复','429 四摄恢复与单核双遍统计调查');p.write_text(t)
print(json.dumps(dict(stage=429,device_recovery_complete=True,formal_camera_frames=48,fixed_single_core_direct_jobs=4,full_goal_complete=False,passed=True)))
