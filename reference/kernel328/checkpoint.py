"""Record source/format progress without claiming an installed camera change."""
from pathlib import Path
import json, shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['factory-wb-validation.json','unit-wb-format-validation.json',
             'wb-reference-binding-validation.json','algorithm-source-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),
                        ('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel328/README.md',
  in_progress_stage=328,in_progress_evidence=prefix+'reference/kernel328/README.md',in_progress_installed=False,
  all_four_factory_wb_reference_golden_mwb_decoded=True,
  factory_wb_evidence=prefix+'reference/kernel328/factory-wb-validation.json',
  unit_wb_format_evidence=prefix+'reference/kernel328/unit-wb-format-validation.json',
  unit_wb_cct_binding_evidence=prefix+'reference/kernel328/wb-reference-binding-validation.json',
  exact_oem_awb_aec_algorithm_evidence=prefix+'reference/kernel328/algorithm-source-validation.json',
  individual_white_balance_values_applied=False,dynamic_colour_temperature_estimation=False,
  factory_wb_schema_320_bytes_verified=True)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：327','# 当前检查点：328')
s=s.replace('当前所有321～327构建/安装/采集worker终态。','当前所有321～327构建/安装/采集worker终态；328无新的相机worker、仅离线分析与vendor算法只读补取/卸载。')
s=s.replace('reference/kernel327/host.py提供raw_ssh。','reference/kernel328/host.py提供raw_ssh。')
insert='''328：五份工厂调校（两GW1分支/IMX471/长焦/广角）共43个AWB根完整与原厂XML/选择树对应：19refPt、19MWB、5sensorCal。factory-wb-validation.json。sensorCal实际320bytes，不是schema不兼容：6个头Q+计数Q+紧密6float CCT(24bytes)+15复合rg/bg(240bytes)；初始误算344已纠正，R4全过。R1/R2缺输入schema目录内ParameterTuningTypes导致Scenario.0覆盖，不当绑定证据；R4恢复真实路径。每golden启用/count5，参考点后5对零是未用槽位，别修补。正确私有kernel328/*-factory-wb-private.json。

328个体WB复用299/326全部读回，按HAL实际ISA确认float32 R/Gb、B/Gb、Gr/Gb分别除q；当前q1、mirror掩码0，主/前/长焦invert1也不倒置，广角invert0。光源枚举0..4=D65/TL84/A/D50/H，所有正值。formatted-unit-wb-private.json。HAL FillIlluminant函数0x405878..405d84从VA0xdd800读取CCT=[6500,3800,2850,5000,2300]并原样复制比值；工厂golden CCT主=[6500,3900,2800,5000,2300]，前=[6500,3800,2850,5000,2300]，广角/长焦=[6500,4100,2850,5000,2300]。不要按同slot盲配或伪造运行CCT，真实对应需要算法分组。wb-reference-bundle-private.json保留两套坐标和全部参考，未应用WB。

328已只读补取本机vendor三算法：kernel328/stats-source/com.qti.stats.awb.so(338864bytes,SHAf1ca21304b2e05ff8bb554fec21b123d11697566b44e9902266a4c90d0b2629e)、awbwrapper(19848)、aec(382672,SHA3f8d12e8a907d90a7c5025db457bca50450b6eb15e74fc7a90d98fbe66080ac7)。已卸载，未执行。manifest kernel328/oem-stats-source.json；手机/var/lib/samurai/k328-oem-stats-source/source.json已完成，不必重采。算法来源/函数定位reference/kernel328/algorithm-source-validation.json。私有反汇编kernel328/{awb,aec}-functions-0x*.txt已取得，别重新反汇编整个HAL。

继续算法追踪的具体入口：AWB SetCalibrationData0x2ab90..2af88、golden/MWB0x85b8..935c、校准数量/光源分组0x9e30..a8fc、GetGainFromCCT0x9bc0..9d70、GetCCTFromGain0x9d70..9e30。AEC CalculateLuxIndex0x4b088..4b220和4b238..4b5a8、EstimateLuxIndexForSlave0x46990..46ac4。已读AEC小函数发现50常量、log10和某只读double比例系数，但调用输入/offset语义及参考域未证明，不能直接以曝光EV替代；尚未写实现/宣称完成。下一步从这些小函数推进动态CCT/lux和WB校准，不回退到已解的320bytes问题。

'''
place=s.index('继续动态AEC/CCT触发');s=s[:place]+insert+s[place:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel328/README.md。部署保持325/318/305/298与r26/config-r21；四摄unit LSC临时链路327已过。328补齐43 AWB根/五光源个体WB语义，并只读取得本机AWB/AEC算法，准确定位标定/CCT/lux函数；下一步从私有小函数反汇编推进数学/输入语义和动态IPA实现，非重复读EEPROM/全量回归。sensorCal320源于6float紧密数组，R4完整核对，别当版本阻塞；HAL TL84=3800K与部分golden3900/4100不同，未应用WB/动态CCT。用户关灯继续离线工作，全部相机worker终态。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text()
banner='328当前：327四摄unit LSC证据保持；四摄及两主摄分支43个AWB参考/golden/MWB根完成解码、个体WB格式与HAL色温传递确认，原厂AWB/AEC算法只读取回并定位。动态CCT/lux和个体WB尚未接入，部署不变。[328来源与语义](../../reference/kernel328/README.md)。以下为历史记录。\n\n'
if not s.startswith('328当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded328 complete AWB-source/format evidence and exact algorithm entry points; no new deployed camera change, goal active.')
