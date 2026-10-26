"""Close verified239 progress and record the researched Linux usage routes."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel239')
read = lambda name: json.loads((R / name).read_text())
health = read('final-health-validation.json')
evidence = read('evidence-validation.json')
assert health['installed_r15_r10'] and health['taint'] == 0
assert evidence['all_members_verified'] and evidence['native_members'] == 153
assert read('r15-installed-startup-analysis.json')['initial_parameters_correct_on_both_starts']
assert read('odm-gps-comparison-validation.json')['actual_current_odm_gps_conf_equals_locked_community_bytes']
assert read('s5k3m5-crosscheck-validation.json')['init_register_records_verified'] == 917
assert read('recipe-promotion-validation.json')['frozen_r15_r10_recipes_promoted']
assert not read('r15-installed-startup-validation.json')['passed']
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
assert helper.snapshot() == json.loads((P.parent / 'kernel228/canonical-after-private.json').read_text())

checkpoint = '''# Realme X2 Pro 当前检查点

2026-10-16，239为progress：r15/r10完整构建及七包默认安装完成，实际同相机两次start首参正确；光学/颜色、后摄全零帧和GNSSfix仍开放，goal active。[239](reference/kernel239/README.md)、[Linux使用与近机型](reference/kernel239/RELATED-LINUX-SOLUTIONS.md)、[238归档](archive/NEXT-SESSION-through238-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与状态

仍236启动，guard /var/lib/samurai/k236-runtime/boot-id-private.txt，233及更早无效。运输reference/kernel239/host.py、私人239/current-work-private.json。所有root构建/worker/export终态，无切换待决；239 trace/临时挂载已清。三只读代理研究已完成；手机仍主线程串行操作。

boot235 44c6a215…/100663296B，DTB469e1456…、Image183 bfa72dd9…、logdump183 e73754c7…；MFD6021a359…/22208B、lab5198e2bd…/17992B、provider2223f337…/9744B、IMX319176f68d7…/36624B、前摄e49dab26…/29536B、CAMSSff9fdfa3…/777680B、FastRPC2abde0ea…/50192B、BT185f6c5ed35…保持。775ko/789文件权威清单k237-camss-install/module-inventory-after-private.json，默认和加载note匹配。

系统libcamera/IPA/tools/GStreamer/V4L2=99990.7.2-r15，config/stack0.1.0-r10。49payload记录及944包总数/937无关记录核验；默认无候选环境取流、WirePlumber新库重载均通过，PipeWire/Phosh/Phoc/session身份保持。旧236 userspace-check含r13库hash，不可盲套；239 final-health按新49路径验证、其余旧hash与loader不变。

两sensor/CCI0/CCI1/CAMSS suspended、四camera rails OFF/users0、MCLK1/2关；三DSP running、SensorProxy三Has、Wi-Fi/chrony正常，taint/fault0。BT Powered=true/Discovering=false/1连接只观察，不pair/connect/disconnect。GNSS idle0/Signalsfalse/rate30，watch idle/timeprepared/dataworker0；MM−1/reason2/power1，用户无SIM。239无GNSS搜星/SET，无刷写/重启。

## 源码、产物与回退依据

0021 IMX319 helper已随r15安装：gain=1024/(1024-code)，8倍896。0022 0150a091…在同步IPA start后saveIspParams，并发布初始combinedMatrix、加入CPU真实frame/sequence/timestamp日志；不改BLC/调校/控制延迟/异步逐帧API。22补丁/全管线/Qt/Python/GStreamer/5IPA保持，13签名包/34AArch64 ELF/5IPA验签和ARM入口QA通过；实际仅装七运行包。原214的2254文件/链接/模式恢复，r14缓存2269不变。

SDK /home/cy122/x2pro-linux/libcamera214-root；r15源/对象 /work/libcamera239-r15-built/src/libcamera-v0.7.2，输出/packages239-r15及/packages-config239-r15、QA /candidate239-r15。主机QA /home/cy122/x2pro-linux/libcamera239-r15-qa-prefix；私人239/camera-forward-repo-r15完整13包、camera-runtime-repo-r15实际七包，RAM /run/samurai-camera239-r15。主配方/部署锁已更新r15/r10。

持久仓库 /var/lib/samurai/k239-r15-package-candidates/forward/packages.adb；原生r15→r13/r8七包降级模拟通过，未完整往返。旧实际七包k225-r13-package-candidates/forward、事务前world/repos/config/DB在k239-r15-package-transaction。r13→r11旧回退保持。239原生153成员私有归档逐一核对，无场景像素；ODM2文件另导出，不公开payload/指纹。

canonical精确after228（16798符号/772顺序），旧216相机/旧CAMSS输出不能整刷。设备k237-camss-install/before旧fae1+metadata、235-stage/before旧232 MFD/config、236-lab-fix/before旧lab；私人235boot、23245f398f2…、219156f0370…保持。lab有消费者不能复演未绑定/ref0卸载，不热卸有children的MFD。未知VIN不猜。

## 续作与已知风险

239配对12request：RAW1632x1224/stride2048与RGB1624x1224/stride4872，同seq/time；一处源seq跳5但严格递增，不强求seq=requestidx。全有效像素统计与LUT边界重算通过，不声称不同ROI逐像素等价。RAW约63–72DN/mean63.965、BLC16时RGB几乎0，BLC12后约37；噪声/非零不证明光学正常。r14旧FIFO参数0→16→12、gamma1→1/2.2已证。

r15候选和默认各同Camera configure一次/stop-start两次各12帧，Processing身份逐帧匹配，首BLC16/gamma1/2.2/gains1/identity均正确，无旧参残留。严格全非零仍失败：候选run0q0–1/run1q0–3，默认run0q0–3/run1q0–2；program0/diagnostictrue不抹passedfalse。非identityCCM未运行测。前摄r15候选RAW/RGB各6帧通过，用户纯色测试延期，不再索要。后摄朝向可选问题未答，不能断言桌面遮挡；只RAM统计不存图/加光。

S5K3M5两schema投影和独立原BINdecoder已全核917init+4x53模式；末0x0101 WRITE8、row5 delay5微秒、6f12重复写保留，原BIN不变。append relative=EOF-dataoff124448保留24B section2尾；两reader已终态，XML initSettings/initSetting层级修正后复用结果不重跑。模式3=2104x1560/4lane/LLP9648/FLL1663，无PDAF流，OEMclk481930000只是元数据。资源：CCI1 master0 0x2d/reset23/MCLK3 19.2M/CSIPHY3，VIOpm8150l_l1/VANA P L6 2.8V/VDIG P L2实际1.056V，AF P L3另路。现lab mask9 L1/L4；下一步严格L2/L6 mask0x22/shared lease/复位隔离及S5K驱动离线适配，不能整抄Hotdog24M/602.5M。canonical S5K get_selection height=width bug仍在。

最新上游S5K3M5已OF但仅24M，IMX471为ACPI笔记本1928模式，不覆盖本机e49；OV02A10有endpoint修复但本机物理身份未验，GW1未找到可直接用驱动。Hotdog四摄可参考、GNSS仍只启停；X3未启相机端点，OPPO有不同电源/时钟，samurai Halium camera/GPS未勾。SurfaceDuo同SM8150通过vendorHAL+binder+GeoClue取得fix，移植须匹配ABI依赖，不单拷so。

GNSS实际ODM gps.conf已ro采/卸载/前后hash同，Android16/SDK36；与205社区e7c13逐字节一致，39启用/34数值。实际libloc_core35表默认GPS_LOCK3/LPP0/CAP7/MODEM2不等于运行值；ODM无GPS_LOCK/LPP2/CAP23/MODEM1。libgps.utils固定vendor/etc/gps.conf无ODM回退，尚无Android映射/注入证据。RF_LOSS日志在reportSv不证LNA供电；不从AOSP缺键推运行0。MM SUPL字节序修复本机已含；gnss-share MM无自动XTRA。未得到新RF SET依据，不重跑已覆盖同CID/GSV/unlock/辅助矩阵。GNSS真fix、其它后摄/蜂窝业务/蓝牙传感器长稳及完整kernel/rootfs仍待完成。
'''
assert len(checkpoint.encode()) <= 6500, len(checkpoint.encode())
backup = P / 'checkpoint-transitional-before-close-private.md'
assert not backup.exists()
backup.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
(ROOT / 'NEXT-SESSION.md').write_text(checkpoint)

status = ROOT / 'linux-port/docs/HARDWARE-STATUS.md'
text = status.read_text()
a = text.index('用途：')
b = text.index('\n\n', a)
text = text[:a] + '用途：当前硬件验收清单。最后核对2026-10-16，239。libcamera r15/config r10已默认部署；两次start初始参数同步修复验证，前摄RAW/RGB回归通过，后摄近黑/全零帧和光学颜色仍开放。实际ODM配置来源及S5K3M5模式已核，GNSS无fix/新RF修复。taint/fault0，完整goal active。[239](../../reference/kernel239/README.md)、[近机型Linux使用](../../reference/kernel239/RELATED-LINUX-SOLUTIONS.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。' + text[b:]
lines = text.splitlines()
for i, line in enumerate(lines):
    if line.startswith('| 摄像头 |'):
        lines[i] = '| 摄像头 | boot235/236启动、前摄e49/IMX319176f/CAMSSff9保持；默认r15/r10七包升级与49payload/944总包/937无关记录通过。候选及默认各两次start/24帧首参正确，前摄候选RAW/RGB各6帧回归，全图/控制/rails/PM/MCLK恢复，taint/fault0。S5K3M5离线917init/212模式表已核 | 后摄RGB仍有全零帧，严格失败保留；RAW接近黑电平，光学/颜色未验。S5K3M5本机19.2M供电/驱动尚未实体采集，GW1/人像、GPU ISP、方向/性能/冷启长稳和完整kernel/rootfs开放。前摄纯色按用户延期，16MP实验关 |'
    elif line.startswith('| GNSS定位 |'):
        cells = line.split(' | ')
        cells[1] += '；239当前ODM gps.conf与锁定社区源逐字节相同，来源已补齐；只读挂载前后摘要同且卸载'
        cells[2] = '真实fix/正CNR仍未解决。实际库固定vendor路径，尚无ODM配置运行采用证据；库默认不当modem状态，RF_LOSS报告逻辑不证RF/LNA初始化。室内窗边、无SIM，无无遮挡户外/同机Android接收基线；同CID/辅助已覆盖，不以安装gpsd/补GSV当修复。厂商HAL路线须匹配ABI和依赖，完整radio/rootfs/冷启SSR开放 |'
        lines[i] = ' | '.join(cells)
status.write_text('\n'.join(lines) + '\n')

camera = ROOT / 'linux-port/camera/README.md'
(P / 'camera-readme-before239-private.md').write_bytes(camera.read_bytes())
camera.write_text('''# Realme X2 Pro 相机接入

当前236启动/boot235、前摄e49/IMX319176f/CAMSSff9，默认libcamera r15/config-r10。239补IPA首参数同步与初始combinedMatrix，候选和默认各两次start/24帧逐帧身份验参通过，候选前摄RAW/RGB各六帧回归；七包安装、策略新库加载与全清理通过。[当前部署锁](deployment-lock.json)、[22补丁配方](../packages/libcamera/README.md)、[239证据](../../reference/kernel239/README.md)。

后摄真实RAW/RGB同request统计已取得，RAW仍接近黑电平，BLC剪裁能解释部分RGB零值。严格全非零失败保留；噪声和非零灰底不证明正常光学/颜色。前摄纯色按用户延期，仍只RAM统计、不保存/展示场景、不加光。16MP双实验默认关，GPU ISP退出WARN仍开放。

S5K3M5本机917初始化/212模式写入已离线交叉核验，下一项是本机19.2MHz、CCI/供电/复位隔离适配；没有实体取流验收。GW1/人像、光学/颜色/方向、实时性能及完整kernel/rootfs未完成。[近机型与上游传感器使用路线](../../reference/kernel239/RELATED-LINUX-SOLUTIONS.md)。

当前r15→r13/config-r8回退用225实际七包及239事务前world/repo/配置，原生降级模拟通过、未完整往返；内核模块保持。更早r13大规模控制矩阵见[225](../../reference/kernel225/README.md)，IMX319电源/实体首次出帧见[235](../../reference/kernel235/README.md)、[236](../../reference/kernel236/README.md)、[237](../../reference/kernel237/README.md)，48帧曝光控制见[238](../../reference/kernel238/README.md)。canonical仍after228，旧相机输出不能整刷。
''')

deployment = ROOT / 'linux-port/camera/deployment-lock.json'
(P / 'deployment-lock-before239-private.json').write_bytes(deployment.read_bytes())
packages = json.loads((P / 'camera-forward-repo-r15/package-manifest.json').read_text())['packages']
runtime = json.loads((P / 'camera-runtime-repo-r15/forward-manifest.json').read_text())['packages']
lock = dict(stage=239, kernel_changed_in239=False, kernel_boot_stage=235, current_boot_guard_stage=236,
    kernel_image_stage=183, upstream_version='0.7.2', framework_version='99990.7.2-r15',
    configuration_version='0.1.0-r10', package_recipe='../packages/libcamera/APKBUILD',
    package_source_lock='../packages/libcamera/source-lock.json', configuration_recipe='../packages/samurai-camera-config/APKBUILD',
    installed_packages=sorted(p['name'] for p in runtime),
    built_packages=[{k:p[k] for k in ['name','version','file','sha256','bytes']} for p in packages],
    installed_payload_records=49, all_original_feature_subpackages_built=True,
    five_ipa_signatures_verified_against_new_core=True, actual_default_runtime_without_overrides=True,
    same_camera_twice_initial_parameters_verified=True, front_candidate_raw_rgb_six_frames_each=True,
    rear_strict_all_nonzero_passed=False, scene_optical_response_and_colour_open=True,
    default_and_loaded_modules=health['default_and_loaded_modules'], current_module_manifest_stage=237,
    experimental_16mp_default_off=True, gpu_isp_open=True, full_kernel_rootfs_integration_open=True,
    package_install_evidence='../../reference/kernel239/r15-package-install-validation.json',
    actual_default_parameter_evidence='../../reference/kernel239/r15-installed-startup-analysis.json',
    policy_reload_evidence='../../reference/kernel239/wireplumber-reload-validation.json',
    final_health_evidence='../../reference/kernel239/final-health-validation.json',
    rollback_framework='99990.7.2-r13', rollback_configuration='0.1.0-r8',
    native_seven_package_downgrade_simulation_passed=True, full_downgrade_round_trip_not_tested=True)
deployment.write_text(json.dumps(lock, indent=2) + '\n')

state_path = P / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='239 progress closed: r15/r10 installed; default initial params verified; rear optical black-field and GNSS fix open',
    active_native_context=None, active_native_session=None, active_build_session=None, active_evidence_session=None,
    transition_pending=False, previous_goal_turn_classification='progress', full_peripheral_goal_active=True,
    installed_libcamera='r15', installed_config='r10', r15_default_installed=True,
    default_runtime_verified=True, policy_reload_verified=True, rear_rgb_strict_pass=False,
    next='Prepare S5K3M5 offline driver and strict local P L2/L6 shared power profile using verified OEM 19.2MHz tables; preserve optical acceptance and GNSS zero-CNR investigation as open.')
state_path.write_text(json.dumps(state, indent=2) + '\n')
for p in R.glob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
suffixes = {'.py', '.cpp', '.patch', '.md', '.yaml', '.rules', '.conf', '.desktop'}
files = {str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(R.rglob('*')) if p.is_file() and (p.suffix in suffixes or p.name == 'APKBUILD')}
(R / 'source-lock.json').write_text(json.dumps(files, indent=2) + '\n')
report = dict(stage=239, checkpoint_utf8_bytes=len(checkpoint.encode()), active_goal_classification='progress',
    r15_r10_default_installed_and_initial_parameters_verified=True, strict_zero_frame_failure_preserved=True,
    source_files_locked=len(files), python_syntax_files=len(list(R.glob('*.py'))),
    canonical_matches_after228=True, all_root_workers_terminal=True, native_members=153,
    public_recipes_and_deployment_lock_current=True, full_peripheral_goal_active=True)
(R / 'source-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
