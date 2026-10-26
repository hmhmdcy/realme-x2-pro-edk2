from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
install=json.loads((HERE/'install-r1-validation.json').read_text());iq=json.loads((HERE/'default-iq-validation.json').read_text())
assert install['passed'] and iq['passed']
scope={'s5kgw1':[[4608,3456],[4608,2592]],'imx471':[[2304,1728]],'imx319':[[1632,1224]],'s5k3m5':[[2104,1560]]}
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 if 'deployment-lock' in relative:d['stage']=344
 d.update(current_camera_evidence=prefix+'reference/kernel344/README.md',in_progress_stage=344,
  in_progress_evidence=prefix+'reference/kernel344/README.md',in_progress_installed=True,
  device_private_tuning_installed=True,device_private_tuning_stage=344,device_private_tuning_directory='/etc/libcamera/ipa/camss-vfe',
  device_private_tuning_mode_scope=scope,device_private_tuning_context='Preview; no extra Feature1/Feature2/Scene/Effect',
  device_private_tuning_evidence=prefix+'reference/kernel344/install-r1-validation.json',device_private_tuning_iq_evidence=prefix+'reference/kernel344/default-iq-validation.json',
  private_bound_profiles_installed=True,private_bound_profile_usecase='Preview',
  lsc_individual_default_enabled=True,lsc_enabled_by_default=True,all_four_camera_factory_lsc_default_enabled=True,
  lsc_individual_values_applied_scope='device private Preview defaults in five confirmed modes; unbound front crop retains generic tuning',
  aec_lux_default_enabled=True,aec_lux_default_mode_scope=scope,
  all_four_camera_factory_default_scope=scope,individual_white_balance_default_enabled=True,
  colour_temperature_ccm_default_scope=['s5kgw1','imx319','s5k3m5'],front_factory_ccm_enabled=False,
  public_package_profiles_contain_individual_calibration=False,public_package_default_profiles_changed=False,
  optional_calibration_profiles_enabled_by_default=True,optional_calibration_default_scope=scope,
  default_calibration_verified_with_internal_patterns=True,normal_light_optical_calibration_verified=False,
  current_camera_configuration_stage=344,camera_spa_service='wireplumber',
  final_health_evidence=prefix+'reference/kernel344/install-r1-validation.json',current_adaptation_goal_status='active')
 d['system_services']=dict(stage=344,services={name:[row['pid'] for row in rows] for name,rows in install['final_services'].items()},evidence=prefix+'reference/kernel344/install-r1-validation.json')
 path.write_text(json.dumps(d,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：343','# 当前检查点：344',1)
s=s.replace('默认四摄YAML未改，个体/原厂参数只在私有显式profile使用，不能说默认已完成画质校准。','公共四摄YAML未改；344已在/etc/libcamera/ipa/camss-vfe安装四份私有Preview基线，五个已对应模式默认启用个体WB/CCT、动态LSC和CCM（前CCM仍禁用）。真实光学校准未完成。',1)
s=s.replace('没有安装这些profile、没有新源/包/模块/相机worker/SDK bind，现机仍342r27/r22，最后已验证PW/WP27345/27348。','343当时未安装这些profile；344已部署Preview四份，现机包仍342r27/r22，当前PW/WP28486/28492。',1)
start=s.index('下一步344：');end=s.index('\n\n原严格密钥USB',start)
s=s[:start]+'''344已部署本机private baseline：/etc/libcamera/ipa/camss-vfe/{s5kgw1,imx471,imx319,s5k3m5}.yaml，来自343 Preview profiles。IPA_CONFIG_DIR已核/etc/libcamera/ipa:/usr/share/libcamera/ipa，原无四份文件、服务LIBCAMERA env无覆盖。事务/var/lib/samurai/k344-calibration-r1成功终态，backup-state.json和backup保留，过程中失败会自动撤回；不能重放已执行事务。未换APK/Image/模块/DT/写工厂存储。未知前1928crop保留generic，wide/tele fullsize未新增IQ profile。公共包不放个体数据。

344默认无profile环境变量实际5模式（main2/4，front1，wide2，tele3）各4phase通过，47+47+43+42+50=229帧/20TPG图；102LSC应用状态追踪匹配原函数+独立重采样，186帧CCM矩阵6696bytes零差，实际内核SOF配对，5组AWB锁定、前factoryCCM禁用保持。路径日志确认/etc；default-iq-validation.json。默认4HW/4PWnodes，Gstwide640x480 NV12、PWwide各12帧通过。相机SPA实际由WirePlumber承载，最终maps系统/usr/lib/libcamera.so.0.7.2、ipa_camss_vfe.so、libspa-libcamera.so，WP启动日志确认etc路径，LD_LIBRARY_PATH无override。初collector错以为SPA在pipewire而false，修成按实际SPA宿主，复用同一次maps观察，没有重启/重采；service-host-assumption-r1.json保留原错判。两服务uid10000、PID28486/28492，故障delta0、taint0、CAMSS/2CCI suspended、9rails disabled/users0。无本轮worker/host build/SDK bind。343 Video备用尚未安装；活跃Lux配置等价不代表完整knee表编程完成。

下一步345：继续原厂AEC knee曝光分配/完整曝光表编程、其它模式和场景；优先本机保留com.qti.stats.aec.so和现有符号，CExpTable::ExpTableEntryLookUp在0x2d9a0起、CalculateExposureIndexForManualMode0x2dbd8，336/343已有anchor与table选择。正确选Arb（mainmode4=190，frontPreview144/Video441）不能因anchor相同继续Default全表。先恢复数学/增益-时间优先/FPS/antibanding相关语义，再接可选libipa/IPA，保持实际传感器限幅。也可补缺失wide/tele fullsize IQ模式，但需完整match/geometry。正常光学颜色/阴影/黑电平/畸变、多摄同步/连续AF仍未完，内部TPG不替代。用户关灯继续离线，无需额外确认，不要重测未改组件或复制大树到C。
'''+s[end:]
path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel344/README.md。344已将四份private Preview调校部署/etc/libcamera/ipa/camss-vfe，5模式默认使用WB/CCT/动态LSC/CCM，frontCCM禁用、未知crop仍generic。无env强制，229帧/102LSC状态/6696bytesCCM及默认Gst/PW通过；SPA宿主实际wireplumber，maps系统r27核心/IPA，错误初collector保留并修正无重采。PW/WP28486/28492 uid10000，camera idle/fault0/taint0。包仍r27/r22、内核298/305/325/338。下一步345原厂AEC knee曝光分配/完整table编程；参考336/343与CExpTable::ExpTableEntryLookUp0x2d9a0，mainmode4Arb190、frontPreview144/Video441，normalStreamingtable0。正常光学/多摄同步/连续AF未完；用户关灯，继续独立源码/TPG。私有值不公开，C近满源继续E ext4342树，无活动worker/bind。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('344当前：本机四份私有调校已通过标准/etc路径成为默认；五模式229帧动态参数、默认GStreamer/PipeWire通过，正常光学校准仍未完成。框架r27/config-r22、CAMSS338保持。[344详情](../../reference/kernel344/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded344 default device calibration and actual SPA host; full goal remains active.')
