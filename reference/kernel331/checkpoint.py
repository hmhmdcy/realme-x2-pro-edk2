from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
report=json.loads((HERE/'inverse-validation.json').read_text())
assert report['passed'] and report['calibrated_reference_point_transform_verified']
assert all(not r['different_queries'] for r in report['architectures'])
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel331/README.md',in_progress_stage=331,
  in_progress_evidence=prefix+'reference/kernel331/README.md',in_progress_installed=False,
  inverse_colour_temperature_math_implemented=True,inverse_colour_temperature_math_evidence=prefix+'reference/kernel331/inverse-validation.json',
  calibrated_awb_reference_point_transform_verified=True,colour_temperature_inverse_gain_estimation=False,
  dynamic_colour_temperature_estimation=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：330','# 当前检查点：331')
s=s.replace('reference/kernel330/host.py提供raw_ssh。','reference/kernel331/host.py提供raw_ssh。')
start=s.index('下一步逆向CCT估计/CCM、动态LSC/AEC输入语义，或在补齐控制语义后')
end=s.index('继续动态AEC/CCT触发',start)
s=s[:start]+'''331：反向色温与参考点校准通用数学已实现，reference/kernel331/libipa/awb_colour_temperature.{h,cpp}，不是正向MWB查表反插值。已证明实际vptr=0x5ecb8（构造0x81b8/0x8228），+32→8380，+160→9d70。solver工厂25fa0设置vptr5f750，+24→264c0；调用方360b8..360f8交8368安装到main+de6b8。包装9d70→8380→264c0、分类26578、距离/插值267f8；最终参数由frame+44(distance)/48(CCT)/52(illum)给wrapper。

331反向参考必须refPtV1，非MWBGainV1。25da0..25ef0确认refPt前10对逐通道乘329 unit/golden因子，写main+91e，然后260f8配置估计器。已完整指令仿真和通用C++验证，别把单位参考点对应继续当未知。solver八段连接[0,1],[1,2],[2,3],[3,5]重复,[5,7],[7,8],[8,9]，边界经垂直线，二维投影权重后线性K。端点CCT12000/1500却illum1/8，不能自行改成0/9。

331五来源19refPt根factory/unit共38模型，每架构760参考值+10450节点/区间/离轨/随机查询，主机/AArch64 Werror与原厂包装函数色温/距离/分类完全一致。kernel331/inverse-validation.json，私有input/cases/output与完整反汇编不镜像。仿真无native OEM/Androidloader/手机运行；memcpy只仿真内存、sqrt数学/log stub，syscall/exception拒绝。331无手机切换/worker/安装，330最终状态复用。

下一步332从330候选源集成可选refPt模型、任意增益反推与AWB色温元数据，必须按已应用SOF历史；当前331只有数学，尚未接入自动场景CCT。再推进CCM和动态LSC/lux（不要ExposureEV假充OEM lux）。发布r27应从330及后续源，不要旧321生成器覆盖。默认表及系统版本不变。正常照明光学校准、供应商绑定/几何同步等仍继续。

'''+s[end:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel331/README.md。330可选单位WB/手动CCT候选已通过13项AArch64和四摄内部图14组24图，未安装；331新增refPt校准和反向CCT数学，每架构760参考值及10450查询对原厂指令完全一致。下一步从330候选源集成可选refPt/增益反推及AWB色温元数据，再动态LSC/lux/CCM。反向参考refPt与正向MWB不同，已证明按unit/golden修正，别重复追未解vtable。部署仍r26/config-r21＋325/318/305/298。用户关灯继续，手机worker全终态恢复；无需旧全量回归或重读EEPROM。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='331当前：已提取个体refPt校准、反向CCT/距离/分类通用数学，每架构10450组查询与原厂指令一致；尚未接入IPA自动估计。330手动色温候选和系统部署保持。[331实现](../../reference/kernel331/README.md)。以下为历史记录。\n\n'
if not s.startswith('331当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded331 calibrated reference-point and inverse CCT math; runtime integration pending, goal active.')
