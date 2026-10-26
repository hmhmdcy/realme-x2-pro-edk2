"""Record the installed 338 component, preserving older per-component history."""
from pathlib import Path
import json, shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(name):return json.loads((HERE/name).read_text())
for name in ['hardware-statistics-validation.json','awb-grid-validation.json','install-r1-validation.json','final-state-validation.json']:
 assert read(name)['passed'],name
install=read('install-r1-validation.json');transaction=install['transaction'];health=read('final-state-validation.json')
assert transaction['installed'] and not transaction['rollback']
state=read('source-state.json');state.update(installed=True,installation_evidence='install-r1-validation.json',module_sha256=transaction['module_sha256'])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(stage=338,current_camera_evidence=prefix+'reference/kernel338/README.md',in_progress_stage=338,in_progress_evidence=prefix+'reference/kernel338/README.md',in_progress_installed=True,
  maintained_branch=state['branch'],maintained_commit=state['commit'],source_worktree_branch=state['branch'],source_worktree_commit=state['commit'],source_worktree=state['source'],kernel_source_commit=state['commit'],kernel_source_branch=state['branch'],
  current_camss_source_tree=state['source'],current_camss_source_branch=state['branch'],current_camss_source_commit=state['commit'],current_camss_module_stage=338,current_camss_module_sha256=transaction['module_sha256'],current_camss_module_note_sha256=transaction['loaded_camss_note_sha256'],
  current_camss_install_evidence=prefix+'reference/kernel338/install-r1-validation.json',current_camss_original_backup='/var/lib/samurai/k338-install-r1/qcom-camss-before.ko',
  source_and_deployment_split='298 Image; 305 S5K3M5; 325 S5KGW1; 338 CAMSS; other modules and r26/r21 userspace reused',module_build_evidence=prefix+'reference/kernel338/kernel-build-validation.json',candidate_source_evidence=prefix+'reference/kernel338/source-state.json',final_health_evidence=prefix+'reference/kernel338/final-state-validation.json',
  ccm_supported_by_deployed_camss_backend=True,aec_lux_actual_hardware_statistics_verified=True,aec_current_grid_compatible=True,aec_current_bg_grid=[32,16],aec_bg_maximum_regions=768,aec_bg_packet_bytes=16424,aec_bg_capacity_bytes=22568,aec_lux_runtime_integrated=False,
  source_requires_build_image_mounted=True,full_kernel_rebuild_with338_camss_pending=True,
  current_adaptation_goal_status='active',whole_system_healthy=False)
 modulekey='kernel_modules' if 'kernel_modules' in d else 'deployed_camera_modules'
 d.setdefault(modulekey,{}).setdefault('qcom_camss',{}).update(sha256=transaction['module_sha256'],loaded=True,loaded_note_matches_disk=True,intree='Y',parameters={})
 if 'system_services' in d:d['system_services']=dict(stage=338,services=transaction['services'],evidence=prefix+'reference/kernel338/final-state-validation.json')
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text();start=s.index('最新完整r26包源')
opening='''# 当前检查点：338

2026-10-20，完整多摄/骁龙 ISP goal active。用户关灯休息，继续源码与内部图案，正常照明光学校准仍待后续。遵循 WORKING-BOUNDARIES.md，按本次改动验证，复用未变结果。

已部署：298 Image＋305 S5K3M5＋325 GW1＋338 CAMSS；libcamera 99990.7.2-r26、config/stack 0.1.0-r21，PW/SPA/Gst1.6.9-r3。四摄硬件 NV12/AE/AWB、RAW/RAW+NV12、主摄单次 AF/取消已有证据。默认仍无个体 LSC/WB/CCM 配置，335 CCT/CCM 候选 IPA 未安装。MemFd，非端到端 zero-copy。

338 只改 SoC CAMSS VFE175 BG 默认 rows24→16，网格32×16满足原厂16×16池化约束；容量仍768regions/22568bytes，真实packet16424bytes。四摄真实2048regions到1024cells主机/ARM与原指令各8224bytes零差；新网格四摄AWB收敛、稳定图像，共95观察帧。安装后4硬件/4PW节点、Gst/PW取流通过。相关故障0/taint0，CAMSS/两CCI休眠、9rails关闭/users0，PW/WP22627/22630 uid10000。没有活动构建/采集/安装worker。

338 已安装 CAMSS SHA c7ebd3b6d4e288530d88455e3a2504b23f627fa12bb34efeac6659365c6f256f，loaded note SHA0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297。源码 /mnt/samurai-full282/source338，branch samurai-lux-grid338，commit e3aa81b109e44735161036a2adede105e437ed01，clean，父3346c762e...；包含334CCM硬件支持。原318模块在 /var/lib/samurai/k338-install-r1/qcom-camss-before.ko。原严格密钥USB SSH169.254.42.1，reference/kernel338/host.py raw_ssh；切换沿用305boot guard，普通只读不重复guard。只换CAMSS模块，没有包/Image/DT/刷写/重启/NV写入。详见 reference/kernel338/README.md。

C盘近满曾使首次338 checkout失败/WSL只读，已恢复；新源码改放既有E盘32GB ext4镜像。每个访问此树的WSL脚本先用 reference/kernel284/storage.py mounted_build()，不要格式化或向C盘新增大型副本。后续IPA副本也放E ext4，用临时bind mount接SDK构建路径。私有host恢复记录在kernel338/host-recovery，不镜像。

下一步339：将337 libipa/aec_bayer_luma.{h,cpp}+aec_lux.{h,cpp}接335候选IPA，使用实际每帧曝光/增益、明确配置的参考anchor/权重/补偿，SOF对应统计与元数据。不能把诊断参考index200或未绑定的曝光表声称真实场景校准。之后模式/供应商绑定、lux→动态LSC/CCM与统一发布。光学、几何同步、连续AF等仍未完成。

以下保留历史阶段，出现“当前/下一步”以本段338为准。

'''
p.write_text(opening+s[start:])
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读 NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel338/README.md。338 CAMSS32x16+334CCM后端已经安装，四摄统计/原指令数学/AWB以及安装后Gst/PW通过，PW/WP22627/22630、待机taint0。335候选IPA未安装，系统r26/r21。下一步339把337四个libipa文件接335IPA，曝光/增益/统计关联与明确参考配置，不冒充未绑定曝光表或物理lux；再动态LSC/CCM/模式供应商绑定。C盘近满，新IPA源放E ext4；用284/storage.py mounted_build后访问，临时bind进SDK构建。相机338源/mnt/samurai-full282/source338 commit e3aa81b...。用户睡觉关灯，继续内部TPG，复用不变证据。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();s='338当前：已部署CAMSS32×16统计网格及CCM硬件后端，四摄真实统计、AWB收敛与安装后Gst/PW取流通过；实时lux与动态调校IPA仍待接入。[338详情](../../reference/kernel338/README.md)。以下为历史记录。\n\n'+s;p.write_text(s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded installed338 CAMSS grid and CCM backend; runtime IPA integration remains active.')
