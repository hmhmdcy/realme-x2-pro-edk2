from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
build=json.loads((HERE/'build-validation.json').read_text());assert build['exit_code']==0 and build['original_work_restored']
for name in ['ipa-contract-validation.json','cct-metadata-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel332/README.md',in_progress_stage=332,
  in_progress_evidence=prefix+'reference/kernel332/README.md',in_progress_installed=False,
  colour_temperature_inverse_gain_estimation=True,dynamic_colour_temperature_estimation=True,
  dynamic_colour_temperature_evidence=prefix+'reference/kernel332/cct-metadata-validation.json',
  dynamic_colour_temperature_source='applied quantized AWB/manual gains and calibrated refPt locus; existing grey-world AWB',
  colour_temperature_ccm_linked=False,normal_light_colour_temperature_calibration_verified=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：331','# 当前检查点：332')
s=s.replace('reference/kernel331/host.py提供raw_ssh。','reference/kernel332/host.py提供raw_ssh。')
s=s.replace('330后PW/WP pid15580/15583、uid10000。','332后PW/WP pid16618/16621、uid10000。')
start=s.index('下一步332从330候选源集成可选refPt模型')
end=s.index('继续动态AEC/CCT触发',start)
s=s[:start]+'''332：331反向CCT已接候选IPA，white_balance_reference新增可选reference_points10对，使用unit/golden因子校准，选UID79 refPt/UID117 MWB诊断。硬件量化effective ColourGains取倒数为ratio，每revision准备时计算estimatedColourTemperature，与manual标签分开存ParameterContext，仅SOF ack后的历史帧输出；manualCCT标签优先，任意手动增益/AWBon均可估计。没有refPt的330forward-only配置保留旧行为，旧默认无假CCT。现有灰世界AWB+个体轨迹估计，不是整套OEM AWB场景算法或光学测量精度。

332候选源/home/cy122/x2pro-linux/libcamera214-root/work/libcamera332-cct-built/src/libcamera-v0.7.2，330基础+0032增量（reference/kernel332），仅IPA/libipa改动，核心复用330且内核不变。签名IPA67秒构建成功/SDK原work恢复；DSO/probe Werror，完整IPA沿用werror=false。真实AArch6415项全过：10factory/unit、forward-only、legacy、invalid/disabled、合成RGB真实AWB反馈及SOF历史。kernel332/ipa-contract-validation.json。

332手机临时candidatecore/signed IPA，五unit配置覆盖四摄（主Q/S分别），手动1.25/.75→AWBon并实际锁定，观察153帧、10稳定图，五自动图均异手动。153帧色温元数据与独立原厂指令完整wrapper一致、K舍入误差0。无固定帧数门槛，kernel332/cct-metadata-validation.json。private profiles含reference_points及*expected-private.txt，*points-private.bin、cases-private.json、images-r1和完整日志禁止镜像，公共cases已去私有数值。

332手机/var/lib/samurai/k332-cct-r1 worker16581终态，媒体/控制/服务恢复，相关faultdelta0/taint0、CAMSS/CCI suspended、九rails disabled/users0。PW/WP16618/16621各一个uid10000进程。没有安装、重启、刷写或NV/OTP/persist/EEPROM写入。设备仍r26/config-r21+298/305/318/325；默认配置不变，供应商未绑定。

下一步333提取原厂CCM数据/触发树，复用已有CAMSS_PARAMS_COLOR_CORRECT=3接口，补ColourTemperature/ColourGains→CCM和显式矩阵控制；当前没有CCM联动，部分标准语义仍欠缺。然后由有效CCT衔接动态LSC、确认AEC lux输入语义。发布r27必须从332累计源开始，勿旧321生成器覆盖。正常光线光学、供应商绑定/几何同步等范围继续。

'''+s[end:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel332/README.md。332已接个体refPt反向CCT，真实AArch6415项、四摄五配置手动→AWB153帧和10图通过，逐帧K对独立OEM指令误差0；临时candidate，尚未安装。最新源libcamera332-cct-built，累计0031+0032；下一步CCM原厂数据/触发和现有CAMSS矩阵接口，之后动态LSC/lux。自动CCT来自已应用AWB增益+单位参考，并非整套OEM AWB/正常照明精度；CCM未联动。部署仍r26/config-r21+325/318/305/298，默认无个体表。用户关灯继续，worker全终态恢复；无需旧全量回归或重读EEPROM。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='332当前：候选IPA已支持个体参考点驱动的手动/自动增益色温估计，15项AArch64及四摄153帧对照通过；仅临时加载，系统部署不变。CCM和动态LSC/lux继续。[332实现](../../reference/kernel332/README.md)。以下为历史记录。\n\n'
if not s.startswith('332当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded332 calibrated per-frame CCT estimation; CCM/dynamic LSC pending, installed versions unchanged, goal active.')
