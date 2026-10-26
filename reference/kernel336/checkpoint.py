from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['factory-aec-validation.json','math-validation.json']:assert json.loads((HERE/name).read_text())['passed']
state=dict(stage=336,source=str(HERE/'libipa'),changed_sources=['libipa/aec_lux.h','libipa/aec_lux.cpp'],generic_math_compiled_on_host_and_aarch64=True,
 candidate_ipa_source='/home/cy122/x2pro-linux/libcamera214-root/work/libcamera335-ccm-built/src/libcamera-v0.7.2',ipa_integrated=False,
 raw_bayer_to_oem_luma_equivalence_verified=False,physical_exposure_table_mode_binding_verified=False,kernel_board_sensor_changes=False,phone_changed=False,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());d.update(current_camera_evidence=prefix+'reference/kernel336/README.md',in_progress_stage=336,in_progress_evidence=prefix+'reference/kernel336/README.md',in_progress_installed=False,
  aec_lux_math_oem_instruction_verified=True,aec_lux_math_evidence=prefix+'reference/kernel336/math-validation.json',aec_lux_runtime_integrated=False,aec_lux_raw_stats_equivalence_verified=False,aec_exposure_table_mode_binding_verified=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：335','# 当前检查点：336').replace('reference/kernel335/host.py提供raw_ssh。','reference/kernel336/host.py提供raw_ssh。')
needle='下一步从335/334源继续AEC lux实际语义、动态LSC与CCM非CCT触发、模组供应商绑定与统一发布；无需重跑未变的335四摄/20DSO或334模块测试。'
assert needle in s
s=s.replace(needle,'''336离线已恢复AEC曝光索引/lux原语并实现通用libipa/aec_lux.{h,cpp}，未接入335 IPA。原库328/com.qti.stats.aec.so保持原指纹；解压.gnu_debugdata得真实符号：2dbd8 CExpTable::CalculateExposureIndexForManualMode完整，272b8..27300 QuerySensitivity2ExpIndex数学片段，4b088..4b220 CLuxLumaCalculator::CalculateLuxIndex完整，4aee0..4b088 calculateLuma完整包装。原库log10@plt58740用主机math.log10桩、586f0/LOGGER日志桩，无Androidloader/API/系统调用。0xf50 double精确77.898529052734375，不重新高精度算1/log10(1.03)。

336公式：manualIndex=anchor.index+float(log10(float(float(ns)/float(anchor.ns)*float(gain/anchor.gain)))*scale)；sensitivity分母按float(correction*anchor.gain)*float(anchor.ns)。lux先index+log50/luma项，comp开启加log(tableZeroSens/refZeroSens)项，max0，过滤previous+factor*(current-previous)。factor0直接current，init/reset直接current。filter处volatilefloat强制独立乘加，默认compilerFMA仍精确。平均已处理的256个8bitlux单元并floor.1；没有证明当前CAMSS BG转这些单元等价，不把green/BHIST归一化直接塞入当真lux。

336精确取6公开XSD/接口，来源primary-sources.json。对原厂五BIN只保留Metering/Arbitration目录项作analysis，载荷/mode不变。r1仅Metering导出因Arbitration1.0.0旧版vs公开1.0.1；r2私有兼容schema删除末尾disableBandingGainCapping且revision0，明确推导而非找到原厂schema。独立decoder旧Arb176全部运行slots+曝光tables/knees+ISO数组均与stockXML相同，Metering关键lux字段/采样/RGBweight/refGain也匹配。动态float数组packed4+8byte尾padding，Meteringweight3float@72、enable@88、refGain3float@96，不能按每float8byte读。89Metering+164Arb=253roots，224tables/1140knees，全firstkneeindex0。private336/factory-aec-bundle-private.json含完整Arb及关键Metering，selectors/default_field_matches仅“对应已解码字段”，不证明全Metering相同/物理模式选择。

336两张非默认主摄表Qtech root599/table1与Sunny root473/table1 correction0，原值保留，6个sensitivity0/0排除正常数值比对/通用API拒绝，manual照测；不是repair/通用门槛。主机/ARM默认FMA、Werror各2554cases30648bytes零差：1212manual+1134sens+32config+140lux+36fullprocessedluma-wrapper。Unicorn venvprivate-k329-venv；test-math.py输出/math-validation.json，stock_lux.py从329StockMath继承，全部终态无活动session。没有phone操作，仍335PW/WP19667/19708及r26/r21+298/305/318/325，复用335 final-state。

下一步337从335 IPA候选+334内核源继续，先恢复CStatsProcessor::ProcessBGStatsRegion 4e5d0..4ed60（GetLegacyYRegionStats4e578）与真实rawstats亮度关系、再物理曝光表选择和runtime lux→LSC/CCM。模式/供应商绑定未确认处保持明确诊断；不要以算出一个近似曝光指数就宣称真实lux语义已集成。之后动态LSC与CCM非CCT触发、模组供应商绑定与统一发布。无需重跑未变的335四摄/20DSO或334模块测试。''')
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel336/README.md。336已恢复原厂AEC真实符号/五份253配置根、224曝光表1140拐点、通用曝光index/lux数学主机ARM各2554case零字节差；未接IPA，raw BG→原厂256单元8bitlux亮度和物理模式曝光表绑定仍需证明。下一步337先分析AEC CStatsProcessor::ProcessBGStatsRegion4e5d0/GetLegacyYRegionStats4e578，再runtime lux→LSC/CCM。候选仍335 libcamera+334kernel，335四摄CCM六阶段已过，phone未再操作，PW/WP19667/19708，安装r26/r21+298/305/318/325。两张原厂表correction0保留，不编造修复；原厂Arb旧schema是明确推导兼容版，不能冒充找到完整原schema。用户关灯继续，复用不变证据。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='336当前：原厂AEC曝光索引/lux数学在主机及ARM各2554组逐字节一致，五份曝光表与关键lux字段完成解码；实时Bayer亮度转换/模式绑定尚未完成，未改手机。[336曝光触发语义](../../reference/kernel336/README.md)。以下为历史记录。\n\n'
if not s.startswith('336当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded336 exact AEC index/lux primitives; runtime statistics integration remains next.')
