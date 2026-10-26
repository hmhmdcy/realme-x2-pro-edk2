from pathlib import Path
import base64,hashlib,json,shlex,subprocess,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2'
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='5609244b81d2a417f374683abb79b42d4d47f1d7'
for row in json.loads((HERE.parent/'kernel437/source-state.json').read_text())['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
sys.path.append(str(storage.SDK/'usr/lib/python3.14/site-packages'));import yaml
proof=json.loads((P.parent/'kernel420/install-proof-private.json').read_text())['private_defaults']
code='''from pathlib import Path
import base64,json
names=['s5kgw1','imx319','s5k3m5','imx471']
print(json.dumps({n:base64.b64encode(Path('/etc/libcamera/ipa/camss-vfe',n+'.yaml').read_bytes()).decode() for n in names}))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);q.check_returncode();data=json.loads(q.stdout)
rows=[]
for model,encoded in data.items():
 raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==proof[model+'.yaml'];(P/('formal-'+model+'-private.yaml')).write_bytes(raw)
 profile=yaml.safe_load(raw);assert profile['version']==2 and profile['sensor_model']==model
 rows.append(dict(model=model,modes=[dict(match=m['match'],black=m['residual_black_subtraction'],normalization=m['range_normalization'],existing_tone='ipe_tone' in m) for m in profile['modes']]))
 print(json.dumps(rows[-1]),flush=True)
sources={}
for stage in [350,351,412]:sources[stage]=json.loads((P.parent/('kernel'+str(stage))/'mode-profiles-private.json').read_text())
variants=['sunny_s5kgw1','sunny_imx319','qtech_s5k3m5sx','sunny_imx471'];selected=[]
def leaves(nodes):
 for n in nodes:
  if 'children' in n:yield from leaves(n['children'])
  else:yield n
for variant in variants:
 for lp in sources[351][variant]:
  if lp['usecase']!='Preview':continue
  mode=lp['sensor_mode_index'];tp=next(p for p in sources[412][variant] if p['sensor_mode_index']==mode and p['usecase']=='Preview')
  gamma=next(p for p in sources[350][variant] if p['sensor_mode_index']==mode and p['usecase']=='Preview')['root'];ltm=lp['modules']['ltm13_ipe'];tmc=tp['modules']['tmc11_sw'];ccm=lp['modules']['cc13_ipe']
  selected.append(dict(variant=variant,mode=mode,ltm=dict(enabled=ltm['enabled'],reserve=ltm['reserve'],control=ltm['control_method'],drc_nodes=len(ltm['core'])),tmc=dict(enabled=tmc['enabled'],reserve=tmc['reserve'],control=tmc['control_method'],drc_nodes=len(tmc['core'])),gamma=dict(enabled=gamma['enabled'],control=gamma['control_method']),ipe_ccm_identity=all(n['matrix']==[1,0,0,0,1,0,0,0,1] and n['offsets']==[0,0,0] for n in leaves(ccm['core']))))
(P/'selected-tone-input-inventory-private.json').write_text(json.dumps(dict(formal=rows,selected=selected),indent=2)+'\n')
public=dict(stage=438,source437_matches=True,formal420_profile_hashes_match=True,models=[dict(model=r['model'],modes=len(r['modes'])) for r in rows],selected_preview_contexts=[dict(variant=r['variant'],mode=r['mode'],ltm_enabled=r['ltm']['enabled'],tmc_enabled=r['tmc']['enabled'],tmc_use_gtm=r['tmc']['reserve']['use_gtm'],tmc_use_ltm=r['tmc']['reserve']['use_ltm'],ipe_ccm_identity=r['ipe_ccm_identity']) for r in selected],factory_math_and_modes_reused=True,new_firmware_read=False,passed=True)
(HERE/'existing-inventory-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public,indent=2))
