"""Record the software candidate separately from device and full-goal status."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['ipa-contract-validation.json','agc-regression-validation.json','profile-validation.json','native-reference-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
assert json.loads((HERE/'source-state.json').read_text())['current_native_ipa_contract_passed']
limited=json.loads((HERE/'isolated-transport-validation.json').read_text());assert not limited['passed'] and limited['environment_limited']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    path=ROOT/relative;d=json.loads(path.read_text())
    d.update(current_camera_evidence=prefix+'reference/kernel359/README.md',in_progress_stage=359,
        in_progress_evidence=prefix+'reference/kernel359/README.md',in_progress_installed=False,
        factory_antibanding_ipa_integrated=True,factory_exposure_program_ipa_integration_pending=False,
        candidate_factory_ae_software_verified=True,candidate_factory_ae_hardware_verified=False,
        candidate_factory_ae_evidence=prefix+'reference/kernel359/ipa-contract-validation.json',
        candidate_camss_ipa_pipeline_version=1,candidate_camss_v1_isolated_ipc_verified=False,
        candidate_dynamic_frame_duration_pending=True,candidate_gamma349_merge_pending=True,
        current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
    path.write_text(json.dumps(d,indent=2)+'\n')
entry='''359当前：实际CAMSS IPA曝光程序已接入342 r27完整候选，源在E ext4的libcamera359-exposure-built/src/libcamera-v0.7.2。345/346 table/FPS/EV +358 antibanding进入libipa/HardwareAgc；公共AgcMeanLuminance新增拆分前滤波目标接口，旧calculateNewEv继续原分配器。使用真实V4L2曝光/gain范围、默认VBLANK帧预算和原传感器helper行/增益量化。标准ExposureValue[-8,8]、FlickerOff/Manual和period微秒；无自动频率检测/数字gain/动态FrameDurationLimits。table knee不是硬件上限，最终限幅可能破坏严格周期对齐，不能宣称消除实机频闪。

核心库、签名IPA和worker实际构建通过（最后build5 81.42s；生产Meson werror=false，不冒充全库Werror）。applyIspControls新增firstSof，CAMSS pipeline版本1，核心/IPA/worker须配套。按SOF保留EV/flicker策略，延迟统计及正常统计/缺统计恢复两条元数据路径均取历史；当前策略无需每帧重建表。AE独立请求不增加ISP版本，WB合并仍按参数ACK生效。常规合成统计需ROI面积/4总数，线程参数ACK异步，测试使用后续stats回执确认，不把发送当完成。

8份私有Preview/Video完整IQ配置保留WB/CCM/LSC/lux，已有5个物理模式/10用途上下文新增选定原厂曝光程序。4个更高分辨率上下文没有完整IQ暂不拼造，未知前摄裁剪模式保留generic。原指令组合60组/47086指令；真实ARM64 DSO四颗sensor10上下文全部60组raw分配逐位一致，主摄线程代理再6组；控制历史/延迟统计/类型与范围原子拒绝/convert不提交/AE不改ISP版本/WB合并ACK/重启复位等通过。V4L2和统计来自合成夹具，范围依据当前driver源码，未访问手机。公共AGC baseline342/new359各自匹配头/库独立构建，10上下文480帧15360bytes零差；原quantizer和sensor helper源相同。独立进程proxy因QEMU clone3 ENOSYS未启动，明确失败待真机，不用线程成功替代IPC。补丁43981bytes/15files，source-state哈希，未安装/未改运行默认配置。

主机重复首次挂载竞态曾使同一E构建镜像双loop挂载；两调用都在修改前assert退出，确认无工作进程后卸载，storage284发现/挂载段增加flock串行化，之后真实构建/测试正常。不能并发绑定同一个SDK /work/libcamera；同一运行句柄yield后继续poll，勿重启。不要重放prepare/adjust脚本到已完成候选，复现可用最终patch对342基线。

手机本轮没有新操作，最后USB查询仍9008/COM16、USB SSH不可连/WiFi超时；现场强制重启请求pending。已向用户如实解释356错误通用物理地址8b700000（板级应9ab00000）、CPU5 stall、357一次EUD硬件reset后进9008及一次Sahara reset有ACK未恢复。无programmer/分区/NV/boot替换。private357认证采集和后续pstore可能含秘密字节，勿打印/镜像。Kernel source354路径仍branch357 commitba61...，356正确内存区build7未发机。恢复先boot/pstore/R5state与资源，不重复复位脚本。

下一步继续完整目标：先把349 Gamma候选与359曝光收敛到同一实际IPA/软件包；推进动态帧长预算、缺完整IQ的模式及原厂参数。设备恢复后再验当前v1隔离IPC/曝光时序与画质，完成修正后的ICP/HFI启动、IPE会话/IO/IQ及350/351/352 Gamma/LTM/CCM接入、统一kernel Image，继续光学/几何同步/连续AF。全目标active，不用本轮软件通过替代完整ISP与实机校准。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text();s=re.sub(r'^# 当前检查点：\d+','# 当前检查点：359',s,count=1)
at=s.index('\n\n',s.index('\n\n')+2)+2;path.write_text(s[:at]+entry+s[at:])
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel359/README。359实际曝光表/FPS/EV/防频闪接入IPA，E ext4 libcamera359-exposure-built/src/libcamera-v0.7.2；15文件43981byte最终patch。真实ARM64 DSO10模式用途60原指令对照逐位一致，线程再6组，公共AGC 480frames零差。合成V4L2/stats，未装未实机验证；QEMU clone3阻止isolated worker，当前v1隔离IPC仍未验。核心/IPA/worker须配套，CAMSS版本1。静态frame预算，无动态FrameDuration/自动频率检测/digital gain；未知前摄裁剪generic保留。下一步合并349 Gamma到359实际候选并统一包，再推进帧长/更多模式；完整ICP/IPE及光学同步连续AF保持。手机最后仍9008 COM16，用户不在现场；已解释356错物理8b700000、正确9ab00000、CPU5stall和357 EUD reset后9008，Sahara reset未恢复。无programmer/partition/NV/boot写。现场强制重启请求pending，不重放reset或打印private357认证/pstore秘密。storage284加flock防双mount；同SDK绑定别并发，已有运行句柄只poll。kernel source354 branch357 ba61...，356修正build7从未发机。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('359当前：原厂曝光程序与手动防频闪已接入实际CAMSS IPA候选，ARM64 DSO及公共AGC回归通过，未安装；当前v1隔离IPC和实机画质仍待验证，手机最后仍9008。[359详情](../../reference/kernel359/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','reference/kernel284/storage.py']]
for source in paths:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded359 tested software candidate, explicit isolated IPC limit, unchanged device9008 state, and full active goal.')
