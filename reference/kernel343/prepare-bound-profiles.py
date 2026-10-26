"""Merge confirmed mode calibration into private Preview/Video profiles."""
from pathlib import Path
import copy,json,yaml
import host

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
assert json.loads((HERE/'mode-selection-validation.json').read_text())['passed']
assert json.loads((HERE/'streaming-table-validation.json').read_text())['passed']
bindings=json.loads((P/'bound-mode-configs-private.json').read_text());directory=P/'profiles';directory.mkdir(exist_ok=True);rows=[]
models={'sunny_s5kgw1':'s5kgw1','sunny_imx471':'imx471','sunny_imx319':'imx319','qtech_s5k3m5sx':'s5k3m5'}
fields=['white_balance_reference','aec_lux','colour_correction','lens_shading','residual_black_subtraction','range_normalization']
def active(config):
 result=copy.deepcopy(config)
 if not result['lux']['compensate_sensitivity']:
  result['lux'].pop('reference_zero_sensitivity',None);result['lux'].pop('table_zero_sensitivity',None)
 return result
for variant,model in models.items():
 original=yaml.safe_load((P.parent/'kernel341/profiles'/(variant+'-unit.yaml')).read_text())
 for usecase in ['Preview','Video']:
  profile=yaml.safe_load((ROOT/'linux-port/packages/samurai-camera-config'/('camss-'+model+'.yaml')).read_text());bound=[];retained=[]
  contexts=[r for r in bindings if r['variant']==variant and r['usecase']==usecase]
  for mode in profile['modes']:
   size=[mode['match']['width'],mode['match']['height']]
   context=next((r for r in contexts if r['sensor_size']==size),None)
   if context is None:retained.append(size);continue
   source=next(m for m in original['modes'] if m['match']==mode['match'])
   for key in fields:
    if key in source:mode[key]=copy.deepcopy(source[key])
   mode['aec_lux']=copy.deepcopy(context['aec_lux'])
   assert active(mode['aec_lux'])==active(source['aec_lux']),'Active lux inputs changed; run a focused capture'
   bound.append(dict(sensor_size=size,sensor_mode_index=context['sensor_mode_index'],context=context['context'],
    selected_roots=context['selected'],regular_stream_table=0,active_lux_inputs_equal_tested341=True))
  label=variant+'-'+usecase.lower();target=directory/(label+'.yaml');target.write_text(yaml.safe_dump(profile,sort_keys=False))
  assert not any(isinstance(e,yaml.AliasEvent) for e in yaml.parse(target.read_text()))
  rows.append(dict(model=model,variant=variant,usecase=usecase,profile=label,modes=bound,legacy_uncalibrated_modes_retained=retained,
   all_calibration_math_and_controls_previously_verified=True,installed=False))
(P/'profile-bindings-private.json').write_text(json.dumps(rows,indent=2)+'\n')
report=dict(stage=343,profiles=len(rows),bound_mode_usecase_pairs=sum(len(r['modes']) for r in rows),
 all_existing_active_lux_configs_unchanged=True,all_non_aec_roots_match_tested_profiles=True,
 front_upstream_crop_retains_existing_generic_configuration=True,
 high_resolution_wide_tele_not_added_without_mode_profile=True,public_package_defaults_changed=False,installed=False,passed=True)
(HERE/'bound-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
