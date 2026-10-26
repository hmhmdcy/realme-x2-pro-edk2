from pathlib import Path
import json, shutil
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
build=json.loads((HERE/'build-validation.json').read_text())
assert build['exit_code']==0 and build['original_work_restored']
for name in ['ipa-contract-validation.json','image-validation.json','final-state-validation.json']:
 d=json.loads((HERE/name).read_text()); assert d['passed'],name
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel330/README.md',in_progress_stage=330,
  in_progress_evidence=prefix+'reference/kernel330/README.md',in_progress_installed=False,
  awb_calibration_math_integration=True,manual_colour_temperature_control_integrated=True,
  individual_white_balance_values_applied=True,individual_white_balance_default_enabled=False,
  manual_colour_temperature_hardware_verified=True,manual_colour_temperature_evidence=prefix+'reference/kernel330/image-validation.json',
  dynamic_colour_temperature_estimation=False,colour_temperature_inverse_gain_estimation=False,colour_temperature_ccm_linked=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：329','# 当前检查点：330')
s=s.replace('reference/kernel329/host.py提供raw_ssh。','reference/kernel330/host.py提供raw_ssh。')
s=s.replace('PW/WP pid12864/12867、uid10000。','330后PW/WP pid15580/15583、uid10000。')
start=s.index('下一步330从已部署r26源隔离副本')
end=s.index('继续动态AEC/CCT触发',start)
s=s[:start]+'''330：从321已部署r26源隔离副本集成329数学、white_balance_reference可选模式配置、ColourTemperature1500..12000 K输入、参数队列及SOF元数据。候选源/home/cy122/x2pro-linux/libcamera214-root/work/libcamera330-wb-built/src/libcamera-v0.7.2，0031补丁reference/kernel330。核心/签名IPA成功构建，SDK原work/libcamera已恢复。完整核心沿用基线werror=false；DSO/probe工具Werror。13项真实AArch64 IPA测试全过（五来源factory/unit、startup6500/runtime2850、包编码、SOF前后/统计元数据、旧AWB、禁用/错误配置）。

330手机进程临时加载候选core/signed IPA，14组内部图采集观察95帧、24稳定图；四旧unity基线逐字节相同，20张色温图增益元数据与硬件Q7量化匹配，五来源factory/unit在两个K均有图像差异。近似独立模型均值0.316..0.457/255、p99约1.21..1.45，不是RAW/光学精度。kernel330/image-validation.json。私有profiles/{五来源}-{factory,unit}.yaml无LSC；cases-private.json包含私有expected_gains，images-r1为图像，禁止镜像这两类数据。主摄两供应商仍分别试验，未绑定。

330 /var/lib/samurai/k330-cct-r1 worker15501完成，所有采集/控制/媒体恢复，相关故障delta0/taint0，CAMSS/CCI suspended、九相机rails disabled/users0；PW/WP各一个uid10000进程15580/15583。没有安装包/模块或刷写，系统版本不变。默认无WBreference/个体LSC，默认AWB不变。候选ColourTemperature控制direction改inout，但任意ColourGains反推CCT及CCM联动未实现，属于部分语义；不能称自动测量CCT。显式ColourGains优先、单独增益清手动CCT标签、AWBon忽略手动CCT；SOF前不提前报告新标签。

下一步逆向CCT估计/CCM、动态LSC/AEC输入语义，或在补齐控制语义后由330隔离源发布r27；不要用旧321生成器覆盖新源，不重复读EEPROM或全包回归。GetCCTFromGain0x9d70通过对象vtable+32间接调用实际分类/估计函数，目标仍未解析。vtable文件9bc0 Q位置0x4ed50、9d70 0x4ed58，VA+0x10000；起点未证实，不盲套。328原厂source小函数与AEC反汇编保留。

'''+s[end:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel330/README.md。330已把329 WB数学接入可选IPA/ColourTemperature控制，真实AArch64 DSO13项和四摄内部图14组24图通过，实际unit WB产生预期差异；临时core/IPA，尚未安装。部署仍r26/config-r21＋325/318/305/298，默认无个体表。候选源libcamera330-wb-built，0031；逆向CCT估计/CCM、动态LSC/lux继续，部分手动CCT不能称完整标准/自动CCT。用户关灯继续独立工作，所有相机worker终态、恢复成功。无需重复旧全量验证或重读EEPROM。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='330当前：可选个体WB和启动/运行中色温控制已接入候选IPA，四摄内部图与13项AArch64测试通过；临时加载，系统部署及默认配置未变。自动CCT/CCM/动态校正继续。[330实现与验证](../../reference/kernel330/README.md)。以下为历史记录。\n\n'
if not s.startswith('330当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded330 candidate WB/CCT hardware integration; installed versions unchanged, goal active.')
