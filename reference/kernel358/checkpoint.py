from pathlib import Path
import hashlib, json, re, shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['antibanding-validation.json','tuning-binding-validation.json','mode-program-binding-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
source=dict(stage=358,component='portable_libipa_antibanding',
    files=[dict(path=str(p.relative_to(HERE)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((HERE/'libipa').glob('*'))],
    exposure_allocation_header_reused_from346=True,libcamera_source_integration_pending=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    path=ROOT/relative;d=json.loads(path.read_text())
    d.update(current_camera_evidence=prefix+'reference/kernel358/README.md',in_progress_stage=358,
        in_progress_evidence=prefix+'reference/kernel358/README.md',in_progress_installed=False,
        factory_antibanding_math_implemented=True,factory_antibanding_math_evidence=prefix+'reference/kernel358/antibanding-validation.json',
        factory_antibanding_ipa_integrated=False,factory_exposure_program_ipa_integration_pending=True,
        current_adaptation_goal_status='active')
    path.write_text(json.dumps(d,indent=2)+'\n')
entry='''358当前：原厂CArbitrator::processAntibandingAdjust完整2a438..2a79c已恢复，新增reference/kernel358/libipa/aec_antibanding.cpp/h，复用346 exposure allocation头。原库SHA3f8d12e8...，9407次原函数815558条指令，仅日志/strrchr桩，无算术桩；主机/ARM各9419项188380bytes0diff（另12非法输入只验新API拒绝）。224原厂表按threshold/method/blanking去重19政策，50/60周期及三FPS策略边界等距均测。SDK临时bind释放，本轮无手机操作。

算法阈值float32严格大于才启；上下整周期候选按mingain和min/max时长可用性，最近者、等距选UPPER。Legacy0/Maximize2允许max+minVblank，Strict1不加；Max2选后若超过原max则夹max，gain先乘后除（普通候选先除后乘），因此不保证最终周期整数倍。没有maxGain/传感器行帧限幅；API不复现超32bit周期计数/uint64溢出。无候选保持输入，禁用/短帧同原厂。index保留。

已沿DataMgr vtable160 RELR到getArbTuning1dfc8，模块+72指针、CArb模块+64的+8匹配；param+128为FPS政策、+56为minVblank，与336兼容旧schema核对（未找到原完整C++头）。原ApplyActiveTableEVFPSKnees片段2d508..2d584实际把所选table+24 threshold复制到CExpTable+32=CArb+48，3种原厂比例逐位一致，仅memcpy桩。已整理7物理模式14Preview/Video上下文私有mode-exposure-programs-private.json，完整knee、EV开关、cap和防频闪三字段来自343正确Arb根/Streaming表0。没有启用IPA或改YAML；frequency和真实sensor limits必须运行时提供，不能从table knee当硬件范围。

下一步359直接接入曝光程序与真实sensor行/帧/增益预算，不停在表库存：基于342 r27完整源（可参考349 Gamma候选但未装），345/346/358共同进入libipa/HardwareAgc；mean-luminance目标/滤波和原厂分配政策分层，取得拆分前的目标曝光值，不能先按generic mode拆完再倒推。提供标准手动flicker能力，不冒充自动频率检测；未知前摄裁剪模式保留原行为。候选先实际DSO构建/相关合同，手机357最后仍9008，现场强制重启请求pending，恢复后先查实际状态和R5/boot/pstore。勿重复EUD/Sahara reset marker；private357认证日志/后续pstore可能含敏感输入，不打印。full ICP/IPE/libcamera调校、光学/更多模式/同步/连续AF等全目标active。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text();s=re.sub(r'^# 当前检查点：\d+','# 当前检查点：358',s,count=1)
at=s.index('\n\n',s.index('\n\n')+2)+2;path.write_text(s[:at]+entry+s[at:])
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel358/README。358原厂完整防频闪数学9407调用815558指令，host/ARM各9419项0diff，无算术桩；正确Arb字段绑定和14模式用途数据私存。下一步359把345/346/358接入真实IPA自动曝光分配，补sensor行/帧/gain限幅和标准手动flicker；取得mean-luma拆分前目标EV，不从generic已拆结果倒推。source libcamera342-r27-built/src/libcamera-v0.7.2在E ext4，storage284先mount；不要复制大SDK到C。358只是math/数据未集成IPA/未安装。手机357最后9008、现场电源+音量上>10秒重启请求pending，先查实际USB；不要重复EUD/Sahara reset。私有357认证采集和后续pstore可能含秘密字节，严禁原样输出镜像。kernel源source354路径branch357 commitba61...，356修9ab00000固件区build7从未发机。全目标包括真实ICP/IPE会话、Gamma/LTM/CCM、AE防频闪/模式/光学/同步/AF，保持active。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('358当前：原厂防频闪曝光分配数学已在主机/ARM对照通过，参数按正确模式根整理；尚未接IPA或安装，设备恢复状态沿用357。[358详情](../../reference/kernel358/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded358 native anti-banding math and selected mode data; IPA integration and full goal remain pending.')
