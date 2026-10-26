from pathlib import Path
import json, shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
report=json.loads((HERE/'math-validation.json').read_text())
assert report['passed'] and all(not r['differing_values'] for r in report['host_and_aarch64'])
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),
                        ('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel329/README.md',in_progress_stage=329,
  in_progress_evidence=prefix+'reference/kernel329/README.md',in_progress_installed=False,
  awb_generic_calibration_math_implemented=True,awb_calibration_math_integration=False,
  awb_calibration_math_evidence=prefix+'reference/kernel329/math-validation.json',
  unit_wb_calibration_correspondence_verified=True,
  unit_wb_calibration_correspondence='index-paired unit/golden followed by factory-CCT grouping; payload CCT ignored at this stage',
  manual_colour_temperature_lookup_implemented=True,manual_colour_temperature_control_integrated=False,
  individual_white_balance_values_applied=False,dynamic_colour_temperature_estimation=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：328','# 当前检查点：329')
s=s.replace('reference/kernel328/host.py提供raw_ssh。','reference/kernel329/host.py提供raw_ssh。')
s=s.replace('真实对应需要算法分组。wb-reference-bundle-private.json保留两套坐标和全部参考，未应用WB。',
 '328当时未确认真实对应；329已由本机算法确认按索引配对、按工厂CCT分组，payload CCT不参与。wb-reference-bundle-private.json保留两套坐标和全部参考，未应用WB。')
insert='''329：通用C++17 WB校准、MWB比值转换及正向CCT查表已写在reference/kernel329/libipa/awb_calibration.{h,cpp}，未接入/安装IPA。校准按unit/golden同记录索引配对，按工厂CCT（不是HAL payload CCT）分组；五真实来源改payload CCT999后输出不变，328对应语义已解除未知，不要继续当阻塞。输出比值因子unit/golden，与LSC方向相反；MWB先G/R、G/B，再乘因子，结果是比值，非直接颜色增益。

329用Unicorn ARM64 2.1.4对保留原厂小函数做指令仿真；无Android加载器/原厂native加载/手机运行，日志stub、系统调用/异常拒绝。原厂校准0x9e30..a8fc、MWB纯算术8f24..9114、CCT正向9bc0..9d70，与独立C++主机/AArch64 SDK Werror结果每架构3118值完全一致。覆盖63分组子集+边界/真实5份=78校准条件、19真实MWB、589CCT查询，证据reference/kernel329/math-validation.json。新数据kernel329/calibrated-ratios-private.json等只留私有。没有新相机worker、包/模块/默认配置改动。

329仿真环境/home/cy122/x2pro-linux/private-k329-venv/bin/python；check-math.py可复跑相关数学。ARM SDK/private/camss329-math/math-aarch64已成功，主机无aarch64-linux-gnu-g++，不要因此装整套新工具链，现有SDK chroot g++即可。源码8f24算术将实际MWB(R,G,B)转G/R,G/B并乘factor；CCT查表节点[12000,7500,6500,5000,4000,2850,2300,1500]→索引[0,1,2,3,5,7,8,9]，在线性Kelvin中插值，非mired；仅正向lookup，非测得CCT。

下一步330从已部署r26源隔离副本接入可选awb calibration/mwb配置和标准ColourTemperature手动控制，真实DSO/内部图验证后再决定发布，保持默认无个体表；继续逆向CCT估计/动态LSC/AEC输入语义，不重复读EEPROM或已通过的全部包回归。若继续逆向GetCCTFromGain0x9d70，它通过对象vtable+32间接调用实际分类/估计函数，当前尚未解析其目标；不要把正向查表当逆向估计。vtable文件中9bc0 Q位置0x4ed50、9d70 0x4ed58，对应VA+0x10000；此前随手推算vtable起点未证实，不盲套。328原厂source小函数与AEC反汇编保留。

'''
place=s.index('继续动态AEC/CCT触发');s=s[:place]+insert+s[place:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel329/README.md。部署不变r26/config-r21＋325/318/305/298；四摄unit LSC327已过。329新增通用WB校准/MWB比值/CCT正向lookup数学，主机ARM各3118值对本机原厂指令仿真完全一致，源码reference/kernel329/libipa。下一步接入可选IPA/标准ColourTemperature手动控制和实际DSO/内部图，再推进估计与动态LSC/AEC。校准按记录索引配对且用factory CCT分组，unit payload CCT不参与，方向unit/golden；328疑问已解除。正向lookup不是运行CCT估计。用户关灯继续独立工作，所有相机worker终态，无需重复全量回归或重读EEPROM。\n')
p=ROOT/'reference/kernel328/README.md';s=p.read_text()
note='329后续已确认：按记录索引配对unit/golden，再按factory CCT分组，payload CCT在该步骤不参与；328尚未确认的对应语义已解决。[329实现](../kernel329/README.md)。下文为328当时记录。\n\n'
if not s.startswith('329后续已确认：'):p.write_text(note+s)
p=ROOT/'linux-port/camera/README.md';s=p.read_text()
banner='329当前：新增通用WB校准、MWB比值转换与正向CCT查表，主机/ARM各3118值与本机原厂指令仿真完全一致；尚未接入IPA或安装，动态CCT/完整校准继续。四摄unit LSC及现有部署保持。[329数学实现](../../reference/kernel329/README.md)。以下为历史记录。\n\n'
if not s.startswith('329当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','reference/kernel328/README.md',
 'linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded329 verified portable WB calibration and CCT lookup math; IPA integration pending, goal remains active.')
