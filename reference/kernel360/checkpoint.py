"""Publish candidate evidence and the newly recovered live-device state."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['merge-validation.json','package-source-validation.json','ipa-contract-validation.json','package-build-validation.json','package-artifact-validation.json','recovery-cleanup-validation.json','recovered-camera-validation.json','recovered-baseline-capture-validation.json']:
    assert json.loads((HERE/name).read_text())['passed'],name
artifacts=json.loads((HERE/'package-artifact-validation.json').read_text());boot=json.loads((HERE/'recovered-boot-validation.json').read_text());state=json.loads((HERE/'source-state.json').read_text())
for package in ['libcamera','samurai-camera-config']:
    directory=HERE/'recipes'/package;p=directory/'source-lock.json';lock=json.loads(p.read_text())
    lock.update(candidate_only=True,installed=False,combined_candidate_hardware_verified=False,optional_gamma_requires_camss_parameter_abi_stage=348,
        candidate_package_validation='reference/kernel360/package-artifact-validation.json',camss_pipeline_version=1)
    p.write_text(json.dumps(lock,indent=2)+'\n')
    p=directory/'README.md';p.write_text('360候选：libcamera r28／config r23已完整构建和签名检查，尚未安装。包含349 Gamma与359原厂曝光程序，启用私有Gamma配置需348参数ABI；公共默认YAML不变。原r27／r22配方仍为已安装版本。[360记录](../../README.md)。以下为历史。\n\n'+p.read_text())
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    p=ROOT/relative;d=json.loads(p.read_text())
    d.update(current_camera_evidence=prefix+'reference/kernel360/README.md',in_progress_stage=360,in_progress_evidence=prefix+'reference/kernel360/README.md',in_progress_installed=False,
        ipa_candidate_source_stage=360,ipa_candidate_source=state['source'],ipa_candidate_source_evidence=prefix+'reference/kernel360/source-state.json',
        candidate_framework_version='99990.7.2-r28',candidate_configuration_version='0.1.0-r23',candidate_package_evidence=prefix+'reference/kernel360/package-artifact-validation.json',
        candidate_gamma349_merge_pending=False,candidate_gamma_and_factory_ae_combined=True,candidate_combined_hardware_verified=False,
        candidate_camss_ipa_pipeline_version=1,candidate_camss_v1_isolated_ipc_verified=False,candidate_dynamic_frame_duration_pending=True,
        device_current_ssh_status='strict_original_key_usb_restored',device_current_usb_mode='NCM',device_current_kernel='7.3.0-rc6-rmx1931-samurai-k298+',
        device_current_taint=0,device_recovered_boot_evidence=prefix+'reference/kernel360/recovered-boot-validation.json',device_recovered_baseline_capture_evidence=prefix+'reference/kernel360/recovered-baseline-capture-validation.json',
        current_boot_guard_stage=360,current_boot_guard_evidence=prefix+'reference/kernel360/recovery-cleanup-validation.json',
        device_recovered_camera_count=4,device_force_restart_currently_needed=False,icp_r5_old_terminal_report_missing=True,icp_r5_orphan_firmware_removed=True,
        current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
    if 'system_services' in d:d['system_services'].update(observed_before_recovered360_boot=True,current_boot_revalidated=False)
    p.write_text(json.dumps(d,indent=2)+'\n')
entry='''360当前：349 Gamma与359曝光合并为E ext4 libcamera360-combined-r28-built/src/libcamera-v0.7.2，r28/config-r23候选完整包已构建签名、未安装。三方共同基线342；camss.cpp/公共Meson自动合并，camss源数组人工合并新增cpp。Gamma/曝光算法源与父阶段相同。0037 Gamma+0038曝光从r27零fuzz顺序应用，23文件逐字一致；全量差分combined-r28-against-r27.patch59753bytes，source-state有哈希。生产werror=false沿用；核心签名IPA/worker构建177.45s，全框架包294.85s/config8.44s。

私有8完整Preview/Video profile已有5物理模式/10用途上下文同时带Gamma和原厂曝光，未知前摄裁剪generic保留，高分辨率缺完整IQ未造。实际ARM64 DSO合成合同12路径：10factory、主摄线程、IMX319非对称RGB；72次原指令曝光分配逐位比较、108次完整776byte Gamma块核对，以及EV/flicker历史、延迟stats、合并WB ACK、开流重传、legacy复位等通过。Gamma后续不重传。公共AGC/量化源未改，复用359 480帧零差。完整13APK保持全部消费包/6IPA/py/qcam/Gst/V4L2，七运行包签名forward及r27/r22 rollback仓库在private360/runtime-repository。剥离后的打包IPA+core又过main/非对称RGB两组，IPA签名用打包core核过；公共默认YAML无factory/unit表，canonical配方r27/r22没改。候选recipes在reference360/recipes，尚无安装实测或新v1隔离IPC证明，QEMU clone3限制沿用。

重要手机状态已更新：收尾Pnp发现9008消失/NCM出现，原严格密钥USB169.254.42.1 SSH成功，观察boot3501...是新启动。k298、CAMSS338 note0227...、八核在线/taint0，17ICP/BPS/IPE clocks refs0，CAMSS suspended，无ICP core/test或临时DT节点。启动时已约72min；未确认9008退出触发方式，不把恢复归因本轮主机操作。pstore为空，CPU5精确PC仍未知。旧R5state存在/terminalfalse/phase load-boot-test，worker无；原state不改成成功。仅删lib/firmware/qcom/sm8150/samurai-icp356.elf这个专用孤儿副本，先比352原件与R5保留firmware.elf全哈希相同；保留R5backup和旧失败状态。新360guard /var/lib/samurai/k360-recovered/boot-id-private.txt，host360.ssh使用它/原guard305/356保留，P360 recovered-boot-adoption-private.json保存当前boot。此时无需再请用户强制重启。

已读实际installed七包仍r27/r22，cam --list四颗物理相机与342 hardware_cameras4一致（不要与四PipeWire节点相加变8；本轮初始夹具期望误用8已依据342改正，复用原观察没重跑）。再以当前实际ID每摄cam capture4、不写文件，请求640x480 NV12共16帧/退出0/帧错0，相关新故障0、taint0、CAMSS/两CCI suspended。仅为原r27/338重启后基础取流，不能写成新r28/光学校准成功。private360 recovered-inventory-secret-private.json、recovered-pstore-secret-private、current-dmesg等及旧private357认证日志可能含秘密，不能原样输出/镜像。所有主机build/测试终态/SDK binds释放，无活动capture。

下一步361优先用新boot和host360新guard准备r28+348参数ABI临时组合实测；不要重放349/356旧事务，准备新目录，核当前core338和service实际状态后复用已测348 SoC Gamma模块/当前r28载荷，保持单次失败也可收敛恢复。旧338不能启动带Gamma profile，349已有ENOSPC负对照。先证明新EV/flicker请求/真实sensor delay/同包Gamma等；完整ISP仍需正确9ab00000内存后的ICP/HFI/真实IPE会话IO/IQ和350/351/352后级Gamma/LTM/CCM，不能把IFE线性曲线当原厂显示色调。静态frame预算/无自动频率/数字gain约束继续，动态FrameDuration/更多mode/光学/同步/连续AF与统一kernel Image仍在完整goal内。Kernel source354路径branch357 ba61...，356修正build7未发机，本轮没有再触发ICP启动。

'''
p=ROOT/'NEXT-SESSION.md';s=p.read_text();s=re.sub(r'^# 当前检查点：\d+','# 当前检查点：360',s,count=1);at=s.index('\n\n',s.index('\n\n')+2)+2;p.write_text(s[:at]+entry+s[at:])
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/ISPgoal。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel360/README。360合并349 Gamma+359原厂AE，E ext4 libcamera360-combined-r28-built/src/libcamera-v0.7.2，13个r28/r23完整签名APK/7runtime及r27回退准备，未装；12合成路径72AE/108Gamma包+两打包载荷通过。下一步361新事务临时用348 ABI模块配r28真机组合，不重放旧事务。重要手机已恢复NCM/原严格USB SSH169.254.42.1，boot3501...新启动k298/CAMSS338、8CPU/taint0，r27/r22四摄各4帧通过/相关故障0/PM休眠；无需再强制重启。host360.ssh读取private360/recovered-boot-adoption-private.json和360独立guard，旧305/356不改。R5仍原非终态load-boot-test、worker已无；孤儿firmware校验后删除且保留R5备份，未再触发ICP。pstore空/退出9008触发未确认，不把恢复归因主机。私有357认证及360 raw/dmesg可能含秘密，勿打印/镜像。全目标仍含ICP/HFI/IPE完整会话、后级Gamma/LTM/CCM、动态帧长/更多mode/光学同步连续AF/统一Image；kernel source354 branch357 ba61...、356正确9ab00000 build7未发机。SDK临时bind别并发、已有handle只poll，storage284含mount flock，C近满不复制大树。\n')
p=ROOT/'linux-port/camera/README.md';p.write_text('360当前：Gamma与原厂曝光已合并、r28/r23完整包构建签名及组合检查通过，未装；手机已恢复原密钥USB SSH，原r27/338四摄各4帧正常、taint0。新候选实机及完整ICP/IPE等继续。[360详情](../../reference/kernel360/README.md)。以下为历史。\n\n'+p.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded360 complete candidate packages and verified recovered original-boot capture; full goal remains active.')
