"""Save the completed offline work without changing the installed product."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
decode=json.loads((HERE/'factory-lsc-decode-validation.json').read_text())
packing=json.loads((HERE/'lsc-hardware-packing-validation.json').read_text())
assert decode['direct_decoder_and_original_reader_match'] and packing['packing_independent_expression_matches']
banner='''317离线进展（用户已关灯休息）：从本机原厂BIN取得7个IFE LSC根的7个golden／75个基础区域，独立解码与原厂解析器按5位小数一致。通用golden/unit合成、GR/GB均衡与Titan17x Q10/DMI编码已实现，75表33,150字独立核对通过；未接IPA或内核、未改手机。候选个体表发现4个零节点；Sunny/Qtech描述均得到同样结果，未补造或应用。下一步按[317源码与证据](reference/kernel317/README.md)做公共CAMSS LSC参数和内部图案验证，不依赖室内灯光；正式光学校准后做。默认系统仍316的r25/config-r20＋314 CAMSS，完整目标active。所有本轮工具已终态。

'''
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:
 path=ROOT/name
 old=path.read_text()
 if not old.startswith('317离线进展'):path.write_text(banner+old)
path=ROOT/'linux-port/camera/deployment-lock.json';state=json.loads(path.read_text())
state.update(in_progress_stage=317,in_progress_evidence='../../reference/kernel317/README.md',in_progress_installed=False,
    factory_lsc_ife_roots=7,factory_lsc_golden_regions=7,factory_lsc_core_regions=75,
    factory_lsc_tables_independently_decoded=True,
    lsc_generic_calibration_and_packing_implemented=True,lsc_kernel_parameter_block_implemented=False,
    lsc_unit_candidate_zero_nodes=4,lsc_unit_candidate_zero_nodes_repaired=False,
    lsc_individual_values_applied=False,lsc_hardware_programmed=False,
    night_work_scope='User switched lights off; continue offline/source/internal-pattern work. Do not treat ambient dark-room frames as normal-light calibration.',
    goal_status='active_incomplete',current_adaptation_goal_status='active',goal_complete=False)
path.write_text(json.dumps(state,indent=2)+'\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [ROOT/'NEXT-SESSION.md',ROOT/'NEXT-SESSION-PROMPT.md',path]
for source in files:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Saved317 offline LSC progress;316 installed product unchanged, full goal active.')
