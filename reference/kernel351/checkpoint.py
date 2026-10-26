from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['factory-colour-chain-validation.json','mode-colour-chain-validation.json','selected-profile-analysis.json','static-flags-validation.json','vendor-settings-validation.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text());d.update(current_camera_evidence=prefix+'reference/kernel351/README.md',in_progress_stage=351,
  in_progress_evidence=prefix+'reference/kernel351/README.md',in_progress_installed=False,
  factory_ipe_ltm_and_ccm_full_tree_extracted=True,factory_ipe_colour_chain_evidence=prefix+'reference/kernel351/factory-colour-chain-validation.json',
  factory_ltm_static_defaults_verified_in_original_hal=True,factory_ltm_static_defaults_evidence=prefix+'reference/kernel351/static-flags-validation.json',
  factory_front_downstream_ccm_identified=True,factory_front_downstream_ccm_evidence=prefix+'reference/kernel351/selected-profile-analysis.json',
  factory_final_tone_default_pending=True,factory_downstream_gamma_role_pending=True,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
entry='''351最新：5原BIN完整解LTM13_IPE149roots/2135regions、CC13_IPE43roots/737regions，与OEM parser全部树/控制轴/开关/reserve/数值一致；private351，parser E ext4 /mnt/samurai-full282/parser351。LTM root872/reserve88+768，DRC/HDR/AEC3层；核心4数组schema int但tool_hint float，首版int解析XML不匹配已修，首份unmatched私存。CCroot144/CCTleaf72，同形状不等于同处理级。factory-colour-chain-validation passed。

351沿用349 physical contexts：7模式*Preview/Video14context，28 LTM/CCM查询与原manager0diff，完整选根private351/mode-profiles-private.json。LTM均uid42，module/ltm/igamma/data_collect/img_process=1，CCM均enable1/q0；main mode2CCM47/mode4CCM176，其余47。preview/video完整profiles相同。main/wide/tele所选CCM均identity；front28regions/25nonidentity matrices，offset0，说明front原IFE CCMdisabled与后级CCM安排相吻合，不能盲启IFE原配置。各所选LTM有nonzero strength/scale，不能当直通。mode/selected-profile报告已记录。

351实际HAL staticflags：执行HwInitializeDefaultSettings3c2720..3c2764，zero/ff输入低22bits=0x33c91；constructor片段35e450..35e468读manager+15632 bit18/19→LTM+620/624，logW6/W7原format确认ignoreChromatixRGammaFlag/useHardcodedGamma，各compileddefaultFALSE。完整HwLoadOverrideSettings3c2770..3c3090执行，仅virtualsettingreader桩（44reads/call），恢复keys821ea2c2/a6abb46e，四组合构造读取通过，31601原指令。原HAL未native运行，未证明Androidproperties覆盖后值。参考titan17xsettings.xml已取固定9f17f1b源码仅对照，数据来源原HAL。static-flags-validation passed。

351手机只为找fileoverride执行ro/noload/noexec vendor挂载，etc/camera与etc无camx名，两明确候选camxoverridesettings.txt/camxsettings.xml均不存在；已卸载/移除/run/k351-vendor-settings-ro，缓存private351/vendor-settings-private.json，未读NV/OTP/EEPROM/persist、未改安装文件/模块、未重启。文件缺失不证明所有override不存在。其余手机状态继续引用349最后观察，未重测未改组件。一次gitgrep过宽在无输出后中断；之后只ls-tree目录名和gitshow三个所需源，无活动git/sourcefetch。

351无构建/采集/SDKbindworker，通用代码与脱敏报告已镜像，所有table/XML/vendor/asm私存。下一步352优先LTM inverseGamma/核心数学与front IPE CCM13输出域，评估真实IPE硬件或明确近似后级方案，不能Gamma15∘Gamma16/强挪CCM冒充OEMfinal。348kernel与349GammaIPA已测未安装，deployed仍338+r27/r22+344etc。完整goalactive，AE/防频闪/sensorlimits/其它模式/光学/同步/连续AF等仍待。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：350','# 当前检查点：351',1);at=s.index('\n\n',s.index('\n\n')+2)+2;s=s[:at]+entry+s[at:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel351/README。351完整LTM149roots/2135regions与IPECCM43roots/737regions OEM XML一致；14contexts/28原manager查询一致。LTM/inverseGamma调校开，实际HAL compiled flags ignoreChromatixRGamma/useHardcodedGamma均FALSE（default+override+constructor原指令已核），Android最终property未观察。main/wide/tele所选IPECCM identity，front有25不同非单位矩阵，勿盲启原disabled IFE CCM或挪位置声称等价。手机仅vendor只读查明确settings文件（没有找到），已卸载；未改安装/模块/默认、未重启，仍349最后观察338+r27/r22+344etc。350 Gamma177roots/898curves/插值编码已核；348kernel/349IPA已实测但未安装。下一步352继续LTM inverseGamma核心数学及front CCM13域，评估后级硬件/明确近似方案后再组合发布。无活动worker/build/SDKbind/gitfetch，private351所有调校/vendor/asm不镜像，parser大目录E ext4。完整AE/防频闪/模式/光学/同步/连续AF目标尚未完成。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('351当前：原厂LTM/后级CCM完整树及实际HAL逆Gamma默认开关已恢复，识别前摄25组后级矩阵；继续处理后级输出域，默认未改。[351详情](../../reference/kernel351/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded351 factory LTM/CCM/compiled-default progress; no new camera deployment; goal active.')
