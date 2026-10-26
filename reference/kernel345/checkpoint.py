from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['math-validation.json','fps-knee-validation.json']:assert json.loads((HERE/name).read_text())['passed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel345/README.md',in_progress_stage=345,in_progress_evidence=prefix+'reference/kernel345/README.md',in_progress_installed=False,
  factory_exposure_table_lookup_math_implemented=True,factory_exposure_table_lookup_math_evidence=prefix+'reference/kernel345/math-validation.json',
  factory_frame_time_knee_math_implemented=True,factory_frame_time_knee_math_evidence=prefix+'reference/kernel345/fps-knee-validation.json',
  factory_exposure_program_ipa_integrated=False,factory_active_ev_fps_table_construction_implemented=False,
  factory_exposure_program_actual_sensor_limit_application_pending=True,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：344','# 当前检查点：345',1)
start=s.index('下一步345：');end=s.index('\n\n原严格密钥USB',start)
s=s[:start]+'''345已新增独立通用math reference/kernel345/libipa/aec_exposure_table.{h,cpp}，尚未进342完整源/IPA。完整原厂CExpTable::ExpTableEntryLookUp0x2d9a0..2dbd8与UpdateFPSKnee0x2d178..2d350已恢复。224tables去重42knee程序；lookup主机/ARM各1314case26280bytes零差，267项原始/active入口相同；FPS helper+嵌套lookup各905case21720bytes零差。均C++17/O2/Wall/Wextra/Werror，SDK仅小工具，无work bind。原函数Unicorn执行，powf host libm float桩、log10 host double桩、日志桩，无Android loader或原厂服务。新函数非法配置/未表示uint64溢出拒绝，负增量按FCVTZU→0。lookup首末夹取按原厂fcsel含负0，upper_bound等值取最后knee；1.03f^delta，Gain优先与非零(Time/Maximum)分支，exact uint64 base + trunc(float增量)，不能整体float时间相乘。FPS helper先首个time>=cap前段，Gain时加nextGain/baseGain的index偏移，再cap/baseNs偏移，最后原lookup，priorityGain。scale精确77.898529052734375。复用输出的rounding观察：904有效中90低于表firstTime；其余203超过cap，最大48ns，不能替代真实sensor行/帧限幅。报告reference/kernel345/README.md与math/FPS JSON。345没有手机状态切换、配置/包/驱动/内核改动；手机仍344私有默认基线，r27/r22+298/305/325/338，最近服务28486/28492 uid10000/待机/故障0/taint0复用344；无本轮活动build/worker/SDK bind。

下一步346：继续UpdateEVKnee0x2d350..2d508和ApplyActiveTableEVFPSKnees0x2d508..2d9a0，私有345已有ev-knee/active-knees/fps-knee/set-table/lookup asm，无需重新下载或全扫描。stock_exposure.py是可复用Unicorn封装，lookup()/frame_knee()、begin重设、allowed区间明确；需扩展memcpy@0x58720、exp2@0x58820桩及新区间。对象CExpTable当前已证明：sourceTableQ@0；active inline header@8(count12/pointer24)，source header kneeCount4/kneePtr16，runtime knee24bytes(gain0/ns8/priority16/index20)。FPSknee@1240/EVknee@1264（各24bytes），EV settingfloat@1320、maxTimeQ1328、capFlagI1336、capGainF1340、EVdeltaIndexF1344、另一个policyFlagI1348；后几项须沿caller核实含义，不直接当schema字段。active数组可给OBJECT+40等独立空间，原函数经pointer24 memcpy source n*24；后半段若末gain<原表lastgain，还会追加同time的gain段恢复原表最大gain，不能误以为只截短到FPSknee。EVhelper用exp2(double(ev))→f32、可能min(factor,capGain/FPSgain)，log10缩放到delta；negative走原lookup、positive有policyFlag行为未完全对应。SetExpTable和SetParamEV caller继续追踪字段。345 math_host/output与cases私有E kernel345，SDK/private/camss345-math小工具；oracle用/home/cy122/x2pro-linux/private-k329-venv/bin/python。不要把部分math通过当整个AEC完成；待active表/antibanding/真实sensor limits清楚后再接可选libipa/IPA自动曝光。模式binding343正确Arb mainmode4=190/frontPreview144/Video441 normaltable0；344默认相机校准保持。正常光学、多摄同步、连续AF及更多模式完整goal仍active，用户关灯可继续离线。
'''+s[end:]
path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel345/README.md。345新增通用曝光table lookup与FPS knee math未接IPA，主机ARM各1314+905case/48000bytes与原完整指令参考0差，224tables去重42程序。powf/log10为明确hostmath桩，原Android未运行。原FPS舍入最多超cap48ns，真实sensor limit仍待。下一步346 EV/active table构造：UpdateEVKnee2d350..2d508、ApplyActive2d508..2d9a0；345私有asm和stock_exposure可复用，对象字段/后段恢复原maxgain细节见NEXT。手机345无改，仍344etc默认private calibration五模式，r27/r22+298/305/325/338，PW/WP28486/28492最近已验证idle。无build/bind/worker，源342 E ext4，C近满勿大复制。不要重复未改验证；用户关灯继续离线/TPG。完整光学/其它模式/同步/连续AF未完。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('345当前：新增原厂曝光表分配与FPS knee通用数学，两架构对照通过；尚未接IPA，344默认四摄私有校准保持。[345详情](../../reference/kernel345/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded345 exposure lookup/FPS math; deployed344 calibration preserved and full goal active.')
