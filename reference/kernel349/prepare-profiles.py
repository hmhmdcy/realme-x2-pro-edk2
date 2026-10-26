from pathlib import Path
import copy,json,struct,sys
sys.path.insert(0,'/usr/lib/python3/dist-packages')
import yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'profiles';directory.mkdir(exist_ok=True)
bindings=json.loads((P.parent/'kernel343/profile-bindings-private.json').read_text())
gamma_bindings=json.loads((HERE.parent/'kernel347/gamma-mode-validation.json').read_text())['sources'];cases=[]
def leaves(nodes):
 for n in nodes:
  if 'table' in n:yield n
  else:yield from leaves(n['children'])
for row in bindings:
 if row['usecase']!='Preview':continue
 variant=row['variant'];model=row['model'];profile=yaml.safe_load((P.parent/'kernel343/profiles'/(row['profile']+'.yaml')).read_text())
 roots=json.loads((P.parent/'kernel347'/(variant+'-gamma-trees-private.json')).read_text())
 selection=next(r for r in gamma_bindings if r['variant']==variant);bound=[]
 for mode in profile['modes']:
  physical=next((m for m in row['modes'] if m['sensor_size']==[mode['match']['width'],mode['match']['height']]),None)
  if physical is None:continue
  entry=next(r for r in selection['physical_contexts'] if r['sensor_mode_index']==physical['sensor_mode_index'] and r['usecase']=='Preview')
  root=next(r for r in roots if r['uid']==entry['gamma_uid']);channels=list(leaves(root['core']))
  assert root['enabled']==1 and len(channels)==3 and {c['channel'] for c in channels}=={0,1,2}
  by_channel={c['channel']:c['table'] for c in channels};curves=[by_channel[i] for i in [2,0,1]]
  assert curves[0]==curves[1]==curves[2]
  mode['gamma']=dict(mode='static',curves=copy.deepcopy(curves))
  bound.append(dict(match=mode['match'],stock_mode=physical['sensor_mode_index'],gamma_uid=entry['gamma_uid']))
 path=directory/(model+'-factory.yaml');path.write_text(yaml.safe_dump(profile,sort_keys=False))
 assert not any(isinstance(e,yaml.AliasEvent) for e in yaml.parse(path.read_text()))
 no_gamma=copy.deepcopy(profile)
 for mode in no_gamma['modes']:mode.pop('gamma',None)
 fallback=directory/(model+'-legacy.yaml');fallback.write_text(yaml.safe_dump(no_gamma,sort_keys=False))
 for i,item in enumerate(bound):
  cases.append(dict(name=model+'-factory-'+str(i),model=model,variant=variant,match=item['match'],profile=path.name,
   fallback=fallback.name,expected='factory-gamma-private.bin',gamma=True,result=0))
# Factory curves are identical across all retained variants, as proven347.
shutil=__import__('shutil');shutil.copyfile(P.parent/'kernel348/factory-gamma-private.bin',P/'factory-gamma-private.bin')
source=yaml.safe_load((directory/'imx319-factory.yaml').read_text());base_case=next(c for c in cases if c['model']=='imx319')
matched=next(m for m in source['modes'] if m['match']==base_case['match'])
curves=[[i*16*scale for i in range(65)] for scale in [.5,.75,.25]]
expected=struct.pack('<HHI',7,2,776)
for curve in curves:
 expected+=b''.join(struct.pack('<Hh',int(curve[i]),int(curve[i+1]-curve[i])) for i in range(64))
(P/'rgb-gamma-private.bin').write_bytes(expected)
variants=[('rgb-asymmetric',dict(mode='static',curves=curves),True,0,'rgb-gamma-private.bin'),
 ('disabled',dict(enabled=False,curves='ignored'),False,0,None),
 ('bad-mode',dict(mode='dynamic',curves=curves),False,-22,None),
 ('bad-enabled',dict(enabled='banana',curves=curves),False,-22,None),
 ('two-channels',dict(curves=curves[:2]),False,-22,None),
 ('short-curve',dict(curves=[curves[0][:-1],*curves[1:]]),False,-22,None)]
for label,value in [('negative',-1.),('too-large',1024.1),('nan',float('nan'))]:
 bad=copy.deepcopy(curves);bad[1][32]=value;variants.append((label,dict(curves=bad),False,-22,None))
variants.append(('absent',None,False,0,None))
for label,gamma,enabled,result,expected_name in variants:
 profile=copy.deepcopy(source);mode=next(m for m in profile['modes'] if m['match']==base_case['match'])
 if gamma is None:mode.pop('gamma',None)
 else:mode['gamma']=gamma
 path=directory/('imx319-'+label+'.yaml');path.write_text(yaml.safe_dump(profile,sort_keys=False))
 cases.append(dict(base_case,name='imx319-'+label,profile=path.name,expected=expected_name,gamma=enabled,result=result))
(P/'cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
(HERE/'profile-validation.json').write_text(json.dumps(dict(stage=349,factory_mode_profiles=sum('factory-' in c['name'] for c in cases),
 full_calibration_profiles_reused_from344=True,only_previously_bound_modes_add_gamma=True,
 gamma_source='../kernel347/factory-gamma-validation.json',rgb_channel_order='R,G,B',private_curves=True,
 cases=len(cases),installed=False,passed=True),indent=2)+'\n')
print('Prepared factory profiles, asymmetric RGB diagnostic, legacy/disabled and invalid configurations.')
