"""Publish the tested r27 recipes and the actual installed checkpoint."""
from pathlib import Path
import hashlib,json,shutil
import storage

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(name):return json.loads((HERE/name).read_text())
for name in ['package-source-validation.json','module-variant-validation.json','install-r1-validation.json','installed-iq-validation.json','final-state-validation.json']:
 assert read(name)['passed'],name
artifacts=read('package-artifact-validation.json');health=read('final-state-validation.json')
changed=[]
for package in ['libcamera','samurai-camera-config']:
 for source in (HERE/'recipes'/package).iterdir():
  if not source.is_file() or source.name in ['README.md','source-lock.json']:continue
  target=ROOT/'linux-port/packages'/package/source.name
  if not target.exists() or source.read_bytes()!=target.read_bytes():
   shutil.copyfile(source,target);changed.append(target)
lock_path=ROOT/'linux-port/packages/libcamera/source-lock.json';lock=json.loads(lock_path.read_text())
for source in (ROOT/'linux-port/packages/libcamera').iterdir():
 if source.is_file() and (source.name in lock['source_files_sha256'] or source.suffix=='.patch'):
  lock['source_files_sha256'][source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
lock.update(stage=342,build_stage=342,package_version='99990.7.2-r27',matched_camss_driver_stage=338,
 actual_signed_build_validation='reference/kernel342/package-build-validation.json',native_install_validation='reference/kernel342/install-r1-validation.json',
 actual_current_payload_validation='reference/kernel342/installed-iq-validation.json',lsc_dynamic_mode_upload=True,
 calibrated_white_balance_and_cct=True,colour_correction_runtime_aec=True,aec_lux_runtime_integrated=True,
 optional_calibration_profiles_enabled_by_default=False,factory_mode_exposure_table_binding_verified=False,
 maintained_source=str(storage.candidate()/'src/libcamera-v0.7.2'))
lock_path.write_text(json.dumps(lock,indent=2)+'\n');changed.append(lock_path)
shutil.copyfile(lock_path,HERE/'recipes/libcamera/source-lock.json')
path=ROOT/'linux-port/packages/samurai-camera-config/source-lock.json';config=json.loads(path.read_text())
config['source_files_sha256']['APKBUILD']=hashlib.sha256((path.parent/'APKBUILD').read_bytes()).hexdigest()
config.update(stage=342,build_stage=342,package_version='0.1.0-r22',matched_camss_driver_stage=338,
 actual_signed_build_validation='reference/kernel342/package-build-validation.json',native_install_validation='reference/kernel342/install-r1-validation.json',
 actual_current_payload_validation='reference/kernel342/installed-iq-validation.json',default_profiles_unchanged=True,private_factory_tables_packaged=False)
path.write_text(json.dumps(config,indent=2)+'\n');changed.append(path);shutil.copyfile(path,HERE/'recipes/samurai-camera-config/source-lock.json')
for package in ['libcamera','samurai-camera-config']:
 path=ROOT/'linux-port/packages'/package/'README.md'
 path.write_text('342当前：r27/config-r22已部署，CAMSS338保持。已合入个体WB/CCT、实时lux驱动CCM及动态LSC；四摄安装后显式配置通过，默认YAML无个体表。实际模式曝光表选择及正常光学校准继续。[342证据](../../../reference/kernel342/README.md)。以下为历史。\n\n'+path.read_text())
 changed.append(path);shutil.copyfile(path,HERE/'recipes'/package/'README.md')
source=str(storage.candidate()/'src/libcamera-v0.7.2')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 # Keep the kernel source/build identity at338; this release changes userspace.
 if relative.endswith('deployment-lock.json'):
  d.update(stage=342,framework_version='99990.7.2-r27',configuration_version='0.1.0-r22',built_packages=artifacts['packages'])
 d.update(current_camera_userspace_stage=342,current_camera_evidence=prefix+'reference/kernel342/README.md',
  in_progress_stage=342,in_progress_evidence=prefix+'reference/kernel342/README.md',in_progress_installed=True,
  dynamic_lsc_deployed=True,dynamic_lsc_evidence=prefix+'reference/kernel342/installed-iq-validation.json',
  lsc_dynamic_scene_trigger_integration=True,colour_temperature_ccm_deployed=True,ccm_runtime_aec_deployed=True,aec_lux_runtime_deployed=True,
  ccm_non_cct_trigger_inputs='runtime lux index or analogue gain; DRC/HDR/LED remain explicit references',
  ipa_candidate_source_stage=342,ipa_candidate_source=source,ccm_candidate_userspace_source=source,
  installed_ipa_source=source,installed_ipa_source_stage=342,
  ipa_candidate_source_evidence=prefix+'reference/kernel342/package-source-validation.json',
  installed_userspace_evidence=prefix+'reference/kernel342/install-r1-validation.json',
  installed_dynamic_iq_evidence=prefix+'reference/kernel342/installed-iq-validation.json',
  main_observed_actuator_factory_variant='sunny_s5kgw1',main_factory_variant_binding_conditional_on_retained_inventory=True,
  main_factory_variant_evidence=prefix+'reference/kernel342/module-variant-validation.json',manufacturer_eeprom_id_verified=False,
  factory_mode_exposure_table_binding_verified=False,optional_calibration_profiles_enabled_by_default=False,
  final_health_evidence=prefix+'reference/kernel342/final-state-validation.json',current_adaptation_goal_status='active')
 if 'system_services' in d:d['system_services']=dict(stage=342,services={k:[v['pid'] for v in values] for k,values in health['services'].items()},evidence=prefix+'reference/kernel342/final-state-validation.json')
 path.write_text(json.dumps(d,indent=2)+'\n');changed.append(path)

iq=read('installed-iq-validation.json');frames=sum(row['frames'] for row in iq['cases']);states=sum(row['applied_lsc_states'] for row in iq['cases'])
body=f'''# 当前检查点：342

2026-10-20，完整多摄/骁龙 ISP goal active。用户关灯休息，继续源码与内部图案；正常照明光学、几何同步、连续AF及完整系统目标仍未完成。遵循 WORKING-BOUNDARIES.md，复用未改组件结果。

342已部署 libcamera99990.7.2-r27、config/stack0.1.0-r22。内核保持 Image298/S5K3M5 305/GW1 325/CAMSS338；PW/SPA/Gst1.6.9-r3。新包包含330～341个体WB/CCT、完整树CCM、实时lux/AEC以及动态LSC，LSC/WB/CCM按同一revision冻结并随内核确认SOF生效。默认四摄YAML未改，个体/原厂参数只在私有显式profile使用，不能说默认已完成画质校准。MemFd，非端到端zero-copy。四摄HW NV12/AE/AWB、RAW/双流、主摄单次AF/取消旧实现保持。

正式源 {source}，配方 linux-port/packages/libcamera/APKBUILD、samurai-camera-config/APKBUILD。0031～0036已从r26顺序零fuzz应用，32个相关源码与341实测源完全一致；完整签名包/六IPA/Python/qcam/GStreamer/V4L2保留。安装事务 /var/lib/samurai/k342-install-r1，七运行包r26/r21离线回退与world/repo备份在同目录。只能观察已有事务，不能重放旧版本前置的安装脚本。无需重编未改内核。

342安装后默认4HW/4PW节点、Gst/PW取流通过；已安装core/IPA以四个显式unit profile完成4相位取流，共{frames}帧、{states}个LSC应用状态、{iq['ccm_matrix_metadata_compared_bytes']}字节CCM元数据核对，四摄AWB锁定、前摄原厂CCM禁用保留。前/广用既有PN9，不把随机图差异当校准精度。独立原厂函数模型对LSC诊断追踪与CCM全矩阵匹配，实际kernel SOF配对。动态算法的全包字节与factory/unit图像对继续复用341已有结果，未重复完整采集。详细数据 reference/kernel342/README.md。

当前主摄lens-focus phandle→LC898219XI/0x72，结合274实际光学响应及已匹配326源hash的两份原厂描述，在保留Sunny/Qtech清单内对应Sunny方案。Qtech描述用BU64253/0x0c。证据 reference/kernel342/module-variant-validation.json；这是库存范围内的执行器对应，manufacturer EEPROM ID仍未认证，不自动宣称所有模组或曝光表已识别。本轮main显式Sunny测试，不再把Qtech诊断参数当本机供应商证明。

下一步343优先恢复实际Sensor mode/Scenario到调校根及AEC曝光表的选择，复用336的完整Arbitration/关键Metering解码和原厂库；现有Metering106/Arbitration110/table0为显式参考，不是物理模式绑定。其他DRC/HDR/LED/lens坐标仍显式参考。个体LSC主表0已验证，长焦light2原descriptor低字节异常未修，不混用未知光源。不因未找到checksum禁止其它可回退实验。

原严格密钥USB SSH169.254.42.1；reference/kernel342/host.py raw_ssh沿用既有305transport和boot guard。相机worker均终态，相关故障0/taint0、CAMSS/两CCI休眠、九路相机电源关闭/users0，PW/WP各一uid10000。未刷写/重启/写NV或工厂数据。相机结果不代表全系统健康；旧GPU/modem/SSC等独立问题不伪装已解决。

C盘近满，新源继续既有E盘ext4镜像。每个WSL脚本用storage.py→284 mounted_build()挂载；需要SDK时以342/storage.py sdk_candidate临时bind，退出卸载。不要在C复制大型源码，不重放338磁盘恢复。342构建已完成、无活动SDK bind/host build。私有表、样本、vendor算法及密钥不镜像。

以下保留历史阶段，版本/当前状态以342开头为准。

'''
p=ROOT/'NEXT-SESSION.md';old=p.read_text();p.write_text(body+old);changed.append(p)
p=ROOT/'NEXT-SESSION-PROMPT.md';p.write_text('继续完整多摄/骁龙ISP goal active。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel342/README.md。342已安装r27/r22：动态LSC/WB/CCT/实时lux/CCM，内核仍298/305/325/338。四摄安装后显式unit profile 4相位及默认Gst/PW通过，默认YAML未放私有表。主摄已按LC898219XI实际光学协议在保留两方案内对应Sunny，EEPROM manufacturer ID及实际模式曝光表仍未认证。下一步343真实模式/Scenario选择、物理AEC表绑定；正常光学/几何同步/连续AF等仍未完。源在E ext4 libcamera342-r27-built，临时SDK bind；C近满勿复制大树。所有worker终态，用户关灯，继续离线/TPG。\n');changed.append(p)
p=ROOT/'linux-port/camera/README.md';p.write_text('342当前：已安装r27/r22，包含个体WB/CCT、实时lux驱动CCM与动态LSC；四摄已安装版本通过显式配置测试，默认个体校准仍未开启。模式曝光表绑定及正式光学等继续。[342详情](../../reference/kernel342/README.md)。以下为历史记录。\n\n'+p.read_text());changed.append(p)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
for source in [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+changed:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Published342 recipes and installed evidence; full adaptation goal remains active.')
