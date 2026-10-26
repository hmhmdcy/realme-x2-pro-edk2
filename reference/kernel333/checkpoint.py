from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['factory-ccm-validation.json','math-validation.json']:assert json.loads((HERE/name).read_text())['passed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel333/README.md',in_progress_stage=333,in_progress_evidence=prefix+'reference/kernel333/README.md',in_progress_installed=False,
  factory_ccm_complete_trigger_trees_verified=True,factory_ccm_evidence=prefix+'reference/kernel333/factory-ccm-validation.json',
  ccm_generic_interpolation_and_encoding_implemented=True,ccm_math_evidence=prefix+'reference/kernel333/math-validation.json',
  ccm_supported_by_deployed_camss_backend=False,colour_temperature_ccm_linked=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：332','# 当前检查点：333').replace('reference/kernel332/host.py提供raw_ssh。','reference/kernel333/host.py提供raw_ssh。')
start=s.index('下一步333提取原厂CCM数据/触发树')
end=s.index('继续动态AEC/CCT触发',start)
s=s[:start]+'''333：五份保留BIN全部IFE cc12_ife共28根/567区的矩阵、偏移、DRC/HDR/LED/AEC/CCT完整树与原厂XML一致。Qtech GW1 1/18、Sunny GW1 12/204、IMX471 1/12、tele5/141、wide9/192；偏移全0，Default根37。private kernel333/*-ccm-trees-private.json，factory-ccm-validation.json含选择器，不要混淆UID相同/表相同与实际模组绑定。解码脚本decode-and-export.py，ParameterTuningTypes留schema输入目录已沿用正确路径。全保留payload/模式树不变。

333通用colour_correction.cpp/h已实现固定CamxChi源码的整数/小数分开插值、整数offset每次混合截断、矩阵RGB→GBR与Q7..Q10编码。主机/ARM Werror各2866例/182756bytes对选定原始源码片段编译oracle完全相同（567工厂区域、2255插值＋符号/舍入/四Q格式）；不是目标HAL逐指令oracle，不把两类证据混说。primary-sources.json与math-validation.json，私有oracle/矩阵数据不镜像。331/332现有CCT候选不变。

333关键纠正：现机318 CAMSS只预留COLOR_CORRECT=3 UAPI，vfe_175_params_info验证仍unsupported，必须补SoC backend，不能直接称复用已支持接口。复用296双来源相同header：COLOR_EN寄存器0x48/bit1，coeff0x760..780、offset0x784..78c、Q0x790；12s系数/11s偏移，左右位域复制，Q7..Q10。kernel333/hardware-protocol.json。UAPI“通常9s”及schema13s均不能直接当Titan175限制。数学层输出参数a/b/c/k按GBR；硬件bits原厂顺序矩阵[4,5,3,7,8,6,1,2,0]，offset[1,2,0]。

下一步334从325内核源clean提交4318dd1c2f7b8971b267cc50d9129e86e99bccdb隔离添加VFE175 CCM，保持318 LSC/305/325模块其它改动。只SoC专用后端/常规参数队列、enable/disable和生命周期，不改板级DT/传感器。内部图验证后，再从332 IPA源链接CCT/增益/手动矩阵及SOF元数据。333无手机操作/worker，复用332最终状态PW/WP16618/16621，安装r26/config-r21+298/305/318/325不变。继续动态LSC/lux及完整范围。

'''+s[end:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active，读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel333/README.md。333已完成CCM28根/567区全触发树与原厂XML对应，通用插值/编码主机ARM各2866例完全对固定公开CamX源码。现机318实际拒绝COLOR_CORRECT块（虽有UAPI），下一步334补VFE175后端而非板级，再接332 CCT/显式矩阵。已证COLOR_EN0x48 bit1、coeff0x760/offset0x784/Q0x790，12s/11s及GBR/左右字段。当前部署不变r26/config-r21+325/318/305/298，332候选CCT实机已过；默认无单位表。用户关灯继续独立工作，不重读EEPROM或全量回归。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='333当前：原厂CCM完整28根/567区与XML对应，通用插值/编码主机和ARM各2866例通过。确认现机VFE175仍拒绝矩阵参数，下一步补SoC后端再联动CCT。[333数据与实现](../../reference/kernel333/README.md)。以下为历史记录。\n\n'
if not s.startswith('333当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded333 complete factory CCM trees and portable math; deployed backend still rejects CCM, goal active.')
