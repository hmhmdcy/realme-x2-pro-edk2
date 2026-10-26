from pathlib import Path
import json,runpy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
if (HERE/'single-core-hardware-validation.json').exists():
 runpy.run_path(str(HERE/'checkpoint-recovered.py'),run_name='__main__')
 raise SystemExit(0)
for n in ['source','runtime','owner','one-core-oracle','hardware','incident','intree-build']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
s=json.loads((HERE/'source-state.json').read_text());h=json.loads((HERE/'hardware-validation.json').read_text());incident=json.loads((HERE/'incident-validation.json').read_text())
assert not h['feature_acceptance_passed'] and not incident['device_recovery_complete']
p=ROOT/'archive/NEXT-SESSION-through428-2026-10-22.md'
if not p.exists():p.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text=f'''# 当前检查点：429（PD10 已接 IPE 双遍请求；统计未验收；r3 诊断 Oops 后待硬件重启恢复）

完整多摄 ISP 目标未完成。先读 WORKING-BOUNDARIES、429/README、429/INCIDENT。428四摄PD10实拍通过；429底层接入与4作业有进展，但DC统计/重复性未通过，新增越界诊断造成Oops。当前设备健康与恢复未证。

## 优先恢复设备，禁止直接继续部署

最后健康是 same394、420 r31/r26+419 core/adapter、Image363/DT389。r2双核4direct完成并恢复正式模块/服务，taint512、资源释放。r3新增 readl(resources.ipe[n]+0x5c60) 越过受DT限制的TOP映射，造成level3 translation fault/Oops。是自身诊断错误。

r3 worker终态失败，client PID12750卡v4l2_m2m_cancel_job，SIGTERM/KILL不能结束。新taint640=512+Oops128；持锁/引用无法安全卸载。未强制卸载、退映射或回收未知DMA。root /var/lib/samurai/k429-pd10-ipe-r3，数据/console已私存kernel429/runtime-collected-r3，pre-reboot-private记录未恢复状态。正式磁盘qcom-camss24fcfa...、core63131c...、m2m46f91c...匹配420/419，未永久改/刷写/NV/OTP/persist。

确认init=/usr/bin/busybox，systemctl不存在（首次命令127，未执行）。之后/usr/sbin/reboot正常请求一次返回0。USB NCM仍Up，LastArrival仍21日04:50旧枚举，169.254.42.1 TCP22明确拒绝，保存WiFi192.168.0.114超时；未证明新启动完成。已通过异步问题请求用户方便时硬件强制重启并进入现有Linux。不要重复请求正常reboot、重授权SSH或假定旧client已退出。原密钥/known_hosts保留。

用户回复后先 raw SSH 小查询确认boot ID已变，再429/adopt-recovered-boot.py：核对compatible/release/cmdline、正式三模块磁盘hash和loaded notes、资源释放、无Oops，创建k429-recovered新guard；429/host.py会采用新guard。不可用旧394 guard跑生产实验。还要恢复/核验PW/WP及四摄默认采集，再写camera-recovery-validation.json；新启动恢复尚未做，文件不存在。prepare-runtime在incident存在后强制要求恢复验证通过，阻止直接新部署。恢复后下一实验worker还须更新其guard/taint/jobs基线（目前仍旧394/512/0），别删guard。

## 源码已修复，不再含错误读取

source354 HEAD {s['commit']}，branch {s['branch']}，parent428906a6b9d。8文件pd10-runtime.patch，源码干净、无fuzz/offset复放通过。17a47 typedcore→2e199双平面m2m（r2实际成功）→48f571单核+错误诊断（禁止再加载）→91be804移除错误诊断（当前）。build r1双核成功cohort；build r2core da4591...含错误诊断禁止加载；最新build r3 core9bdaa51fa9204719abadc174b6f202ddf35ae3b0ca331aaf24b9441bfe93bd4b、CAMSS933bda...、m2mc4d983...，10匹配模块Werror0诊断终态通过，共享配置/输出恢复。build r3未上机。

原厂双遍C限定FULL640x480 NV12/display8、DC+IP+mask；coarse160x120 PD10，stride768/slice60/46080B。corecount1/2，最终m2m coarse用1核隔离，尚未有效验收。第二pass模块配置offset必须从22移到434，stripe相对各pass基址20+412*i。native HAL+FW整512KiB命令/job与actual C零差，单/双核对应native均过；不要把offline当统计实机。

typed API会话coarse layout、帧port1、3rd DMA-BUF引用/offset/容量/disjoint与uncertain保留接通。CPU夹具PD10在owned request parcel后段。释放判据/重试含third buffer，实际函数ASAN/UBSAN+ARM64通过。legacy job struct不变，6008B参数不变；新实验QN10 OUTPUT为2 planes（连续NV12+原生PD10），CAPTURE仍1plane NV12，调用者负责源同SOF配对，非上游保留FourCC。root0400 ltm_scratch临时snapshot复制完成后的请求号/长度/CRC/changed+最多256KiB内容，非正式统计接口。

## 实际结果，严格分开

r1只是节点名应qcom-ipe-a5而非SM8150 IPE，未起FW，恢复。r2用428/main-scene同SOF17真实FULL+PD10、424 factory-contract原厂main LTM包（DC/IP/mask真），真实/中性黑PD10/中性白PD10/重复真实共4direct job；FULL hash全同、真实PD10 hash相同，输入不改、输出tail不改，源/目标DONE标志与request完成通过。jobs4=completed=direct、failed/cancel0、starts/stops4，正式模块/服务恢复，资源全释放，无新fault。

但71488B scratch4次全a7、changed0；真实0vs3输出不同152871bytes，YmeanAbs3.4047135。黑/白对照输出差不能当因果证明，因为真实repeat也不稳定。DC真实存放位置、bank、跨遍/跨核同步未证。查看输出有局部团块变化，未画质通过。r3原请求进入成功ACK后的诊断readl崩溃，上层未交付，不计成功图像或history；单核本身有效性未验收。源guard修复、软件检查passed不是硬件恢复passed。

新pd10-ipe.c已修正原来poll一次1s超时就assert的问题，改15s单调期限，静态ARM64 Werror通过，新client SHA7e3e391...未上机。client-build latest不等同r2/r3用的旧105dd4...；历史stage manifest保存旧准确hash。没有新live传感器拍摄，最后IFE实拍428144配对，最后自动IPE实拍424410帧/402history/2Focused。

## 接续原厂统计、GTM与历史

设备恢复后先安全完成单核隔离/可重复输入，确认DC实际统计写出位置与LTM消费，不再读未映射PPS。原厂LTM有DC_AVG_BANK_SEL/IP_AVG_BANK_SEL（固定源SW override默认0），本机FW自行生成两pass控制；不能据猜测填bank。scratch未改不等于所有DC存储不存在。四摄输入/原厂系数来源仍428/426，不能硬造统计或用空PD10。

接生产IPA真实PD10队列。423/424同SOF BHIST1024/曝光/gain/lux/IFEgamma→TMC11→LTM13/IPEGamma→6008B、最终成功才history、单pending/缺BG-lux hold；本轮无数学提交。GTM在IFE/BPS上游，LTM在IPE；GTM生效版本/图像因果仍缺。必须统计→后续IFE参数生效→对应图像IPE/history。front OEM TMC关保持，多模式/视频/第五2MP见363清单。

WSL每次source/build/ext4先root storage284.mounted_build，原32GiB镜像不重建/格式化；Unicorn PYTHONPATH14。所有本地构建/exec已终态，远端r3client仅在旧启动被证实D态，重启后未知。原件/ASM/系数/图像private，公共泛化代码证据。mirror上次653641f2，scoped提交保留其它index+3处工作树，不push。完整目标未完成。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从429接续。先读NEXT、429README/INCIDENT。真实PD10底层typed core+QN10双源m2m+原厂双遍已接，4个双核实际job完成但scratch全a7、真实repeat输出不一致，DC统计/LTM因果未验收。r3新增错误PPS诊断越过TOP映射触发readl Oops、taint640/client D态，未恢复正式模块/服务。已移除诊断并build r3 Werror过，HEAD91be804；build r2含错误读取禁再加载。正常busybox reboot请求返回0，但SSH拒绝、新启动未证，已请用户硬件强制重启进入Linux。用户回复后原key raw SSH查新boot，再adopt-recovered-boot.py核验正式模块/资源，恢复服务+四摄并建camera-recovery-validation，新guard/taint/jobs基线更新后才继续单核统计隔离。勿假称当前健康或同帧历史完成，GTM上游因果仍缺。私件保密，storage284先挂原盘，terminal后依赖，scoped本地提交。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;v=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 v.update(stage=429,latest_work_stage=429,latest_work_phone_accessed=True,in_progress_installed=False,
  current_device_recovery_required=True,current_device_health='Unverified after429 r3 Oops and one normal reboot request; SSH refused',
  current_device_loaded_module_state='Unknown after reboot request; r3 last observed temporary candidate',
  current_device_last_successfully_restored_experiment='429 r2; does not cover later r3',
  ipe_pd10_latest_evidence=prefix+'reference/kernel429/README.md',ipe_pd10_coarse_transport_candidate_connected=True,
  ipe_pd10_dual_pass_direct_jobs=4,ipe_pd10_dual_pass_live_capture=False,ipe_ltm_dc_statistics_verified=False,
  ipe_ltm_dc_consumption_verified=False,ipe_ltm_replay_repeatability_verified=False,
  ipe_ltm_full_dc_coarse_pass_implemented=False,ipe_full_factory_tone_pipeline_complete=False,
  latest429_ipa_math_history_commits=0,last_successful_scene_stage=428,last_successful_automatic_ipe_scene_stage=424,
  formal_disk_modules_unchanged_after429=True,unsafe429_core_build2_forbidden=True)
 if '/kernel/' in rel:v.update(maintained_branch=s['branch'],maintained_commit=s['commit'],maintained_pd10_ipe_candidate_stage=429)
 p.write_text(json.dumps(v,indent=2)+'\n')
note='429当前：真实PD10已接底层IPE双遍请求，4个双核作业完成，但DC统计与重复性未通过。随后新增越界诊断导致Oops，已修复源码；设备正常重启后SSH尚未恢复，需要硬件重启并核验，当前不能称正式驱动／服务已恢复。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel429/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel429/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel429/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith(('428当前：','429当前：'));p.write_text(note+'[429证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();old='[428 四摄DS4同帧输出与原厂裁剪纠错](reference/kernel428/README.md)';new='[429 PD10接IPE双遍与诊断故障待恢复](reference/kernel429/README.md)';assert old in t or new in t;p.write_text(t.replace(old,new))
print(json.dumps(dict(stage=429,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,device_recovery_complete=False,full_goal_complete=False,passed=True)))
