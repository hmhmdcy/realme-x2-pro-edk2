"""Update maintained recipes and the device checkpoint after actual installation."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
runtime=json.loads((HERE/'runtime-validation.json').read_text());install=json.loads((HERE/'install-r1-validation.json').read_text());final=json.loads((HERE/'final-state-validation.json').read_text())
assert runtime['full_candidate_validation_passed'] and install['passed'] and final['passed']
artifacts=json.loads((HERE/'package-artifact-validation.json').read_text());source=json.loads((HERE/'source-state.json').read_text());kernel=json.loads((HERE.parent/'kernel348/source-state.json').read_text())
source.update(installed=True,framework_version='99990.7.2-r29',configuration_version='0.1.0-r24',matched_module_stage=348,
    runtime_evidence='reference/kernel362/runtime-validation.json',installed_evidence='reference/kernel362/install-r1-validation.json',full_camera_goal_status='active')
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
for package in ['libcamera','samurai-camera-config']:
    recipe=HERE/'recipes'/package;state=json.loads((recipe/'source-lock.json').read_text())
    state.update(candidate_only=False,installed=True,native_install_validation='reference/kernel362/install-r1-validation.json',actual_current_payload_validation='reference/kernel362/final-state-validation.json')
    (recipe/'source-lock.json').write_text(json.dumps(state,indent=2)+'\n')
    for p in recipe.iterdir():
        if p.is_file():shutil.copyfile(p,ROOT/'linux-port/packages'/package/p.name)
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    p=ROOT/rel;old=json.loads(p.read_text());archive=ROOT/'archive'/('camera-'+p.stem+'-through361-2026-10-20.json')
    if not archive.exists():shutil.copyfile(p,archive)
    old.update(stage=362,current_camera_evidence=prefix+'reference/kernel362/README.md',current_camera_userspace_stage=362,
        current_camera_configuration_stage=362,framework_version='99990.7.2-r29',configuration_version='0.1.0-r24',
        current_camss_module_stage=348,current_camss_module_note_sha256=final['camss_note_sha256'],
        current_camss_source=kernel['source'],current_camss_source_branch=kernel['branch'],current_camss_source_commit=kernel['commit'],
        installed_ipa_source=source['source'],installed_ipa_source_stage=362,ipa_candidate_source_stage=362,ipa_candidate_source=source['source'],deployed_snapshot_is_historical=False,
        ipa_candidate_source_evidence=prefix+'reference/kernel362/source-state.json',current_device_runtime_state_verified=True,
        device_current_taint=0,device_closeout_evidence=prefix+'reference/kernel362/final-state-validation.json',
        candidate_camss_v1_isolated_ipc_verified=True,candidate_remaining_failure=None,candidate_common_dispatcher_fix_regression_passed=True,
        candidate_common_request_order_regression_passed=True,candidate_isolated_preview_modes_verified=5,
        candidate_framework_version='99990.7.2-r29',candidate_configuration_version='0.1.0-r24',candidate_package_evidence=prefix+'reference/kernel362/package-artifact-validation.json',
        in_progress_stage=362,in_progress_installed=True,in_progress_evidence=prefix+'reference/kernel362/README.md',
        factory_exposure_program_ipa_integrated=True,factory_exposure_program_default_enabled=True,factory_ife_gamma_default_enabled=True,
        current_private_tuning_source_stage=360,default_tuning_evidence=prefix+'reference/kernel362/install-r1-validation.json',
        current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
    if 'built_packages' in old:old['built_packages']=artifacts['packages']
    if 'deployed_camera_modules' in old:
        old['maintained_branch']=kernel['branch'];old['maintained_commit']=kernel['commit']
        old['deployed_camera_modules']['qcom_camss'].update(sha256=final['camss_disk_sha256'],loaded=True,loaded_note_matches_disk=True)
    p.write_text(json.dumps(old,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through361-2026-10-20.md'
if not archive.exists():shutil.copyfile(ROOT/'NEXT-SESSION.md',archive)
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：362（已部署，完整目标继续）

2026-10-20。四摄／骁龙ISP目标active，尚未完成；下一步转ICP/A5固件和IPE会话。规则见WORKING-BOUNDARIES.md。

## 当前设备与新增结果

严格原密钥USB SSH 169.254.42.1；沿用360恢复后的boot guard。当前Image仍7.3.0-rc6-rmx1931-samurai-k298+，固件boot276未改。已安装libcamera五运行包99990.7.2-r29、config/stack0.1.0-r24；CAMSS现为348 Gamma模块，note SHA256 d8c0f30d189aa8e69e377ba58c891955f3bc795abfb6b8ed6a9562a1d118333a。其余传感器及板级DT未改。

本机四份360完整Preview配置已更新/etc/libcamera/ipa/camss-vfe/{model}.yaml；原厂曝光/手动频闪和IFE Gamma成为已对应模式的默认，个体WB/CCT、动态LSC/CCM保持。五模式安装后137帧隔离请求通过；四个硬件/四个PipeWire节点，GStreamer/PipeWire各12帧通过。最终taint0、双CCI/CAMSS休眠、九路电源disabled/users0、服务各一个uid10000，无活动362 worker或ICP模块。[结果与边界](reference/kernel362/README.md)、[安装](reference/kernel362/install-r1-validation.json)。

361的分发器生命周期修复已纳入r29。362另修CAMSS同步IPC提交所有权，以及公共PipelineHandler同camera递归提交顺序。r1先越过空队列崩溃但暴露请求硬件顺序错误，已保留失败；r2/r3五模式隔离138帧+线程/实景57帧通过。不能删除断言、禁用隔离或重放旧事务。正常实景取流不等于绝对光学校准；五Preview模式不能外推所有模式/用途。

## 源码与回退

工作区E:/RealmeX2Pro edk2；Git镜像WSL /home/cy122/edk2-samurai/repo/Platform/Realme/sm8150。完整源码/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2；正式配方linux-port/packages/libcamera和samurai-camera-config已同步，0037/0038/0039补丁纳入。模块源/mnt/samurai-full282/source348，samurai-ife-gamma348、30086bae4d60abe70784a1176bbe418434833b2f。

完整13包及7运行包签名仓库私存E:/edk2-samurai-out/kernel362；手机/var/lib/samurai/k362-install-r1为成功新事务，repository/rollback保留r27/r22离线包，backup保存原338模块、四份344私有配置、APK world及仓库指针。回退必须组合恢复旧配置/模块/包，不能只降用户空间后继续使用新默认。原厂数据/私有校准/固件/密钥/原始认证日志不进公共Git。

SDK /home/cy122/x2pro-linux/libcamera214-root；进入E盘ext4先调用storage284.mounted_build()，SDK /work/libcamera bind串行且退出释放。构建及安装已终态，不重启旧handle。

## 剩余

ICP内核源/mnt/samurai-full282/source354，samurai-iommu-node-lifetime357、ba61a62293e0f6bc5838c06f2e85e033e3d702a8。357公共OF/IOMMU引用修正已构建未装；356正确Realme firmware0x9ab00000/5MiB命名memory-region第7构建未发机，错误generic0x8b700000不可复用。旧356R5无正常终态，不改写成功；360已恢复当前Linux启动。尚无完整SYS_INIT/PING/PC_ACK及真实IPE会话。继续优先原厂ELF/源码/反编译和352固定上游原型；350/351/352后级Gamma/LTM/CCM待硬件会话接入。

动态FrameDurationLimits、自动频率检测、其它模式/用途、绝对颜色/黑电平/阴影、几何/多摄同步及连续AF仍开放。IFE Gamma不是最终原厂显示色调，未知前摄裁剪保持generic，缺IQ的高分辨率不造表。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从362已部署检查点继续多摄/ISP目标。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel362/README.md。现机r29/r24、CAMSS348/k298，360完整Preview私有配置已默认；五模式137帧隔离默认+Gst/PW各12帧通过。362修公共请求顺序及CAMSS队列，361分发器修复纳入；原故障已解。目标active，继续正确板级内存下ICP/A5/HFI/IPE及后级IQ；357引用修正未装，356第7正确9ab00000/5MiB候选未发机，错误8b700000不用。保留严格360guard和私有固件/校准/密钥。SDK bind串行，storage284先挂E盘ext4。\n')
note='362已部署：r29/config-r24、CAMSS348和原厂完整Preview调校已默认；五模式隔离137帧及Gst/PW各12帧通过。公共请求顺序与CAMSS队列重入修复，ICP/IPE及绝对光学校准继续。'
entries={'linux-port/camera/README.md':'../../','linux-port/camera/kernel/README.md':'../../../','linux-port/docs/HARDWARE-STATUS.md':'../../','linux-port/packages/libcamera/README.md':'../../../','linux-port/packages/samurai-camera-config/README.md':'../../../'}
for rel,prefix in entries.items():
    p=ROOT/rel;s=p.read_text();p.write_text(note+' [362结果]('+prefix+'reference/kernel362/README.md)。以下为历史。\n\n'+s)
p=ROOT/'sessions/INDEX.md';s=p.read_text();s=s.replace('## 最新交接\n','## 最新交接\n\n- [362 隔离请求修复及原厂曝光/Gamma默认部署](../reference/kernel362/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('| 本轮收尾与续作 | [361请求链、分发器修复和交接](reference/kernel361/README.md)、[当前检查点](NEXT-SESSION.md) |','| 当前适配进展 | [362隔离请求及默认调校部署](reference/kernel362/README.md)、[当前检查点](NEXT-SESSION.md) |');p.write_text(s)
# Mirror only this task's public sources/reports and maintained recipes.
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [p for name in ['libcamera','samurai-camera-config'] for p in (ROOT/'linux-port/packages'/name).iterdir() if p.is_file()]
paths += [ROOT/r for r in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',*entries]]
paths += [archive,*ROOT.glob('archive/camera-*-through361-2026-10-20.json')]
for p in paths:
    dest=mirror/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print('Maintained recipes and checkpoint now match installed362; full hardware goal remains active.')
