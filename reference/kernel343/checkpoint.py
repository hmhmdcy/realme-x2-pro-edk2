from pathlib import Path
import json,shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['mode-selection-validation.json','streaming-table-validation.json','bound-profile-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel343/README.md',in_progress_stage=343,
  in_progress_evidence=prefix+'reference/kernel343/README.md',in_progress_installed=False,
  normal_factory_mode_selector_verified=True,normal_factory_mode_selector_evidence=prefix+'reference/kernel343/mode-selection-validation.json',
  normal_factory_mode_selector_scope='seven register/geometry-matched stock modes; explicit Preview/Video, no Feature1/Feature2/Scene/Effect; target Android runtime metadata not observed',
  regular_streaming_factory_table_zero_verified=True,regular_streaming_factory_table_evidence=prefix+'reference/kernel343/streaming-table-validation.json',
  existing_profile_active_lux_parameters_preserved=True,private_bound_profiles_prepared=True,private_bound_profiles_installed=False,
  private_bound_profile_evidence=prefix+'reference/kernel343/bound-profile-validation.json',current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：342','# 当前检查点：343',1)
old='下一步343优先恢复实际Sensor mode/Scenario到调校根及AEC曝光表的选择，复用336的完整Arbitration/关键Metering解码和原厂库；现有Metering106/Arbitration110/table0为显式参考，不是物理模式绑定。其他DRC/HDR/LED/lens坐标仍显式参考。个体LSC主表0已验证，长焦light2原descriptor低字节异常未修，不混用未知光源。不因未找到checksum禁止其它可回退实验。'
new='''343已完成普通上下文模式选择：从保留ParameterParser的ELF数据指针恢复12个通用模板（私有），编译未改的模式读取/GetModule，平台头/字符串shim及Generic模块只保存name/UID/mode、不解析全部IQ。独立mode_tree.py直接读v1.1 mode节点与symbol entry真实ModeId，5份BIN全部节点上下文+实际模式3584项/7类根与原管理器0差；无v2link覆盖，不冒充target Android HAL运行metadata。公开源固定CamxChi 9f17f1b...CHI enum/FillTuningModeData，来源reference/kernel343/primary-sources.json。主摄Sunny普通mode2 Arb110、mode4 Arb190；前mode1 Meter139，Preview Arb144、Video Arb441；广mode0/2和长焦0/3默认106/110。7个已有几何/register依据的模式*Preview/Video明确context，无附加Feature/Scene/Effect。LSC25/CCM37/MWB117/ref79/cal97均与已测配置相同。

343原厂AEC UtilGetExpTableID(operation)完整0x27c30..27e78用329venv Unicorn执行，真实table count/nonempty knee、virtual custom query stub。14个normal Streaming返回table0，customoverride诊断返回100；没有宣称Flash/Fast/Aggressive/Snapshot分支完成。前摄所选根/SCF与Default不同，但anchor相同且lux灵敏度补偿disabled，变化字段不被读取；已有10模式/用途实际参与计算配置全部等价，没有重复手机采集。full Arbitration表/knee不同，后续完整曝光编程须选正确根。报告reference/kernel343/streaming-table-validation.json。

343已生成私有kernel343/profiles八份（四摄*Preview/Video），从r22默认YAML只合并已测WB/AEC/CCM/LSC等字段，实际match对应5模式*2用途=10。front1928x1088无stock对应保留generic；wide3264/tele4208虽模式树已选择但没有已有完整IQ mode profile，本轮未新增。无alias，现有activeLux等价。profile-bindings-private.json含选择依据；bound-mode-configs-private.json含完整table，勿公开。没有安装这些profile、没有新源/包/模块/相机worker/SDK bind，现机仍342r27/r22，最后已验证PW/WP27345/27348。主机失败只是最初无elftools与模板长度断言，已改stdlib/删除任意长度；fullsize无旧profile时明确None，没有伪称比较通过。

下一步344：优先部署可回退的本机私有校准基线以让默认应用实际使用已验证参数。源码已核IPAProxy::configurationFile→ipaConfigurationFile：module-specific env最高，其次config_paths，再已安装IPA_CONFIG_DIR（系统etc优先data）；342 output/config.h根/etc/libcamera和/usr/share/libcamera。先核IPA_CONFIG_DIR与现机服务env/现有private配置，然后考虑/etc/libcamera/ipa/camss-vfe/{model}.yaml，四摄Preview版，未知frontcrop保留generic；不向公共APK放个体值。使用既有r27、无需重编。安装验证默认配置确实从etc加载、TPG四摄相关模式与PW/Gst恢复，不能以内部图案宣称真实光学完成。需要正常光学、更多场景/knee曝光编程、几何同步、连续AF，完整goal仍active。不要因先前身份/全量hash习惯重复验证，不因checksum未知禁独立可回退实验。'''
assert old in s;s=s.replace(old,new,1);path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel343/README.md。现机342 r27/r22+298/305/325/338，PW/WP最后27345/27348；343纯离线。5BIN mode selector3584项与保留原manager0差；7stock模式明确Preview/Video，GW1 mode4 Arb190、front1 Meter139/PreviewArb144/Video441。原厂AEC helper完整指令确认normal Streaming table0；10已有profile activeLux等价，LSC/CCM/WB根仍同已测。私有343八份bound profiles覆盖5模式/10用途，front1928裁剪保留generic，wide/tele fullsize未新增IQprofile。下一步344优先可回退部署本机private baseline到标准IPA config路径，让默认应用使用已测校准；先核IPA_CONFIG_DIR/现有etc文件/服务env，实际加载+四摄TPG/Gst/PW，勿重编无变代码。默认路径源码etc/data，根/etc/libcamera及/usr/share/libcamera。正常光学/完整曝光/几何同步/连续AF仍未完。用户关灯，无需确认；私有表不公开，C近满，源继续E ext4342 candidate。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('343当前：恢复原厂模式树与普通持续取流table0选择；五BIN3584项核对通过，生成按明确模式/用途选择的私有校准配置，尚未启用为默认。现机仍342 r27/r22。[343详情](../../reference/kernel343/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded343 real mode/table selection and private profiles; full goal remains active.')
