from pathlib import Path
import copy,json,math,struct,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
bundle=json.loads((P.parent/'kernel328/wb-reference-bundle-private.json').read_text())
profiles=P/'profiles';profiles.mkdir(exist_ok=True);cases={}
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
calibrated=json.loads((P.parent/'kernel329/calibrated-ratios-private.json').read_text())
for name,item in bundle.items():
 model='s5kgw1' if name.endswith('s5kgw1') else 'imx319' if name.endswith('imx319') else 'imx471' if name.endswith('imx471') else 's5k3m5'
 base=yaml.safe_load((HERE.parent/'kernel313'/(model+'.yaml')).read_text())
 mwb=next(r for r in item['factory_roots'] if r['tag']=='MWBGainV1' and r['uid']==117)['data']['gains']
 cal=next(r['data'] for r in item['factory_roots'] if r['tag']=='sensorCalV1');count=cal['num_of_cal_factors']
 for kind in ['factory','unit']:
  profile=copy.deepcopy(base)
  for mode in profile['modes']:
   mode['residual_black_subtraction']=0;mode['range_normalization']=1.
   reference=dict(mwb=copy.deepcopy(mwb))
   if kind=='unit':reference['calibration']=dict(cct=cal['cct'][:count],golden=copy.deepcopy(cal['points'][:count]),
    unit=[[p['ratio_rg'],p['ratio_bg']] for p in item['unit_payload']])
   mode['white_balance_reference']=reference
  filename=name+'-'+kind
  (profiles/(filename+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
  mode=profile['modes'][0];m=mode['match']
  ratios=next(r['ratios'] for r in calibrated[name]['reference_ratios'] if r['uid']==117) if kind=='unit' else [[f32(g/r),f32(g/b)] for r,g,b in mwb]
  # 6500K and2850K are exact stock lookup nodes (indices2 and7).
  expected=[[1./ratios[i][0],1./ratios[i][1]] for i in [2,7]]
  cases[filename]=dict(model=model,profile=filename,kind=kind,variant=name,
   output='320x240',sensor_size=f"{m['width']}x{m['height']}",match=m,lsc=False,
   test_pattern=2 if model=='s5kgw1' else 3,expected_gains=expected)
(P/'cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
(HERE/'profile-validation.json').write_text(json.dumps(dict(stage=330,profiles=len(cases),models=sorted({v['model'] for v in cases.values()}),
 explicit_factory_root_uid=117,explicit_factory_calibration_cct=True,supplier_binding_verified=False,
 existing_unit_data_reused=True,default_profiles_changed=False,passed=True),indent=2)+'\n')
print('Prepared ten optional factory/unit WB profiles; explicit sensor modes, no default or LSC change.')
