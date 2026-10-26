from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['kernel-build-validation.json','style-validation.json','install-r3-validation.json','main-image-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
for run in ['r1','r2','r3']:
 d=json.loads((host.PRIVATE/('install-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live']
install=json.loads((HERE/'install-r3-validation.json').read_text());final=json.loads((HERE/'final-state-validation.json').read_text());source=json.loads((HERE/'source-commit-validation.json').read_text());build=json.loads((HERE/'kernel-build-validation.json').read_text())
scope='sensor/dependency module outputs plus listed configuration, generated metadata and source/Makefile links; no Image target'
build['restoration_scope']=scope;(HERE/'kernel-build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
patch=ROOT/'linux-port/camera/kernel/0006-s5kgw1-test-pattern.patch';shutil.copyfile(HERE/'s5kgw1-test-pattern.patch',patch)
gw1=dict(stage=325,tree=source['tree'],branch=source['branch'],commit=source['commit'],module_sha256=final['module_sha256'],module_note_sha256=final['loaded_note_sha256'])
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text());d.update(stage=325,
 current_camera_evidence='../../reference/kernel325/README.md',final_health_evidence='../../reference/kernel325/final-state-validation.json',
 in_progress_stage=325,in_progress_evidence='../../reference/kernel325/README.md',in_progress_installed=True,
 current_gw1_source_tree=gw1['tree'],current_gw1_source_branch=gw1['branch'],current_gw1_source_commit=gw1['commit'],current_gw1_module_stage=325,
 current_gw1_module_note_sha256=gw1['module_note_sha256'],gw1_standard_test_pattern_control_implemented=True,gw1_test_pattern_menu={'0':'Disabled','1':'Color Bars','2':'Shade Color Bars'},gw1_test_pattern_default=0,
 gw1_test_pattern_evidence='../../reference/kernel325/install-r3-validation.json',lsc_main_hardware_profile_verified=True,lsc_main_factory_profile_temporarily_applied=True,
 lsc_main_hardware_evidence='../../reference/kernel325/main-image-validation.json',lsc_main_verified_sensor_modes=[[4608,3456],[4608,2592]],lsc_main_individual_values_applied=False,
 all_four_camera_factory_lsc_runtime_verified=True,all_four_camera_factory_lsc_default_enabled=False,
 system_services=dict(stage=325,services={k:[x['pid'] for x in v] for k,v in final['services'].items()},evidence='../../reference/kernel325/final-state-validation.json'))
d['kernel_modules']['s5kgw1'].update(sha256=gw1['module_sha256'],loaded=True,loaded_note_matches_disk=True,intree='Y')
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=json.loads(p.read_text());d.update(stage=325,maintained_branch=source['branch'],maintained_commit=source['commit'],
 source_worktree=source['tree'],source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],source_worktree_full_image_deployed=False,
 kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],current_camera_userspace_stage=321,
 current_camera_evidence='../../../reference/kernel325/README.md',current_boot_evidence='../../../reference/kernel325/final-state-validation.json',final_health_evidence='../../../reference/kernel325/final-state-validation.json',
 gw1_module_build_evidence='../../../reference/kernel325/kernel-build-validation.json',gw1_standard_test_pattern_control=True,gw1_module_stage=325,gw1_source=gw1,
 gw1_test_pattern_patch='0006-s5kgw1-test-pattern.patch',gw1_test_pattern_evidence='../../../reference/kernel325/install-r3-validation.json',
 current_camss_module_stage=318,current_camss_module_note_sha256='6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863',
 module_build_evidence='../../../reference/kernel318/kernel-build-validation.json',default_product_hardware_isp_selected=True,
 spectra_hardware_image_processing_supported_scope='Installed r26 camss-vfe hardware NV12/AE/AWB plus RAW; six-mode factory LSC runtime tests through325, optical calibration incomplete',
 in_progress_stage=325,in_progress_evidence='../../../reference/kernel325/README.md',in_progress_installed=True)
d['deployed_camera_modules']['s5kgw1'].update(sha256=gw1['module_sha256'],loaded=True,loaded_note_matches_disk=True,intree='Y')
d['deployed_camera_modules']['qcom_camss'].update(sha256='2f8a94f5bd34694d52a0ff262f7df668d5cbea46a2109fa5b195d510f50547fa',loaded=True,loaded_note_matches_disk=True,intree='Y')
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/kernel/README.md';s=p.read_text();p.write_text('325当前（2026-10-20）：GW1标准测试图案控制已部署，主摄两模式factory LSC渐变彩条与默认GStreamer/PipeWire通过；四摄均有LSC运行配置实机证据，广角另含真实unit，默认仍未启用。298 Image＋305长焦＋318 CAMSS＋325 GW1，libcamera r26/config-r21。维护源samurai-gw1-tpg325/'+source['commit']+'；只更新GW1模块，未重建/部署完整Image。[325证据](../../../reference/kernel325/README.md)。正式光学/个体/多摄完整校准仍active。以下按历史阅读。\n\n'+s)
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：324','# 当前检查点：325')
s=s.replace('298 Image＋305 S5K3M5＋318 CAMSS。','298 Image＋305 S5K3M5＋318 CAMSS＋325 GW1。')
begin=s.index('当前所有321～324');end=s.index('\n\n已部署CAMSS318',begin)
s=s[:begin]+'''当前所有321～325构建/安装/采集worker终态。325 R1卸载因媒体引用被拒后恢复；R2 Color Bars功能通过但图案饱和，无法证明LSC增益；R3 Shade Color Bars六案例及正常消费者全部通过并部署最终GW1。/var/lib/samurai/k325-install-r3终态。PW/WP pid10734/10737、uid10000，TEST_PATTERN最终0，相机/两CCI休眠、九相机供电关闭用户0、相关故障增量0、taint0。原严格密钥USB SSH169.254.42.1；reference/kernel325/host.py提供raw_ssh。状态切换沿用305 guard /var/lib/samurai/k305-geometry-r2/boot-id-private.txt；普通只读不逐条检查。仅GW1模块更新，软件包/Image/DT未改；无刷写、重启或EEPROM/OTP/NV/persist写入。'''+s[end:]
begin=s.index('下一步可立即做GW1标准TEST_PATTERN控制：');end=s.index('\n\n其它摄像头EEPROM前缀',begin)
s=s[:begin]+f'''325已部署：GW1标准TEST_PATTERN菜单0Disabled/1ColorBars/2ShadeColorBars，映射16-bit0x0600值0/2/3，依据真我同GW1官方源码。15+行传感器补丁沿用PM缓存/group hold/启动setup，不改板级DT、SoC或IQ表。源码{source['tree']}，分支{source['branch']}，提交{source['commit']}，tracked clean，父318；旧318树保持。最终GW1模块SHA{gw1['module_sha256']}，noteSHA{gw1['module_note_sha256']}。模块Werror/ABI/intree及格式通过。原9f1a模块在k325-install-r2/s5kgw1-before.ko，中间509c在k325-install-r3/s5kgw1-before.ko，不能重放旧前置的安装脚本。

325 R3两主摄模式off/Qtech/Sunny各实际稳定3帧，ACTIVE尺寸读回确认、控制缓存及流中0→2切换、媒体/控制恢复成功。四个factory均产生可辨效果，基准梯度确定的彩条内部区近似独立模型p99约1.67～1.78、max3.24～3.40/255；不是RAW光学精度。默认Gst主摄640x480和PW各12帧、四摄/四PW节点通过。四摄工厂LSC运行配置链路至此齐全，广角另有真实unit；默认工厂/单位LSC仍未启用。参考reference/kernel325/README.md。下一步继续主/前/长焦个体读取/布局/绑定以及动态触发，不需要再次卡在主摄图案。'''+s[end:]
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP完整goal。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel325/README.md。已部署325 GW1标准Disabled/ColorBars/Shade控制；r26/config-r21、298 Image、305长焦、318 CAMSS保持。主摄两模式factory LSC已用渐变彩条验证，322广角unit、323长焦factory、324前摄两模式也通过；默认未启用。当前GW1 SHA61c81f47…/note b80626da…、源samurai-gw1-tpg325/4318dd1c…；本轮全终态。下一步继续主/前/长焦个体EEPROM读取/布局/绑定及动态调校。用户关灯可独立工作，未知checksum不是所有可回退实验硬门槛；正式光学和多摄完整校准仍未完成。不要重放旧模块前置的安装脚本。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/kernel/README.md','linux-port/camera/kernel/0006-s5kgw1-test-pattern.patch']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded325 GW1 module/source deployment and six-mode factory LSC runtime coverage; full calibration goal active.')
