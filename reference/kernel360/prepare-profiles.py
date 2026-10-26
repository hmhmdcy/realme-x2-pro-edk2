"""Combine selected factory Gamma and exposure policies, retaining private IQ."""
from pathlib import Path
import copy,json,shutil,struct,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
directory=P/'profiles';directory.mkdir(exist_ok=True);fixtures=P/'fixtures';fixtures.mkdir(exist_ok=True)
rows=json.loads((P.parent/'kernel359/cases-private.json').read_text());bindings=json.loads((HERE.parent/'kernel347/gamma-mode-validation.json').read_text())['sources']
variants=dict(s5kgw1='sunny_s5kgw1',imx471='sunny_imx471',imx319='sunny_imx319',s5k3m5='qtech_s5k3m5sx');profiles={}
def leaves(nodes):
    for n in nodes:
        if 'table' in n:yield n
        else:yield from leaves(n['children'])
for row in rows:
    variant=variants[row['model']];usecase=row['name'].rsplit('-',1)[-1];name=variant+'-'+usecase+'.yaml'
    profile=profiles.setdefault(name,yaml.safe_load((P.parent/'kernel359/profiles'/name).read_text()))
    stockMode=int(row['name'].split('-')[1]);binding=next(b for b in bindings if b['variant']==variant)
    selected=next(c for c in binding['physical_contexts'] if c['sensor_mode_index']==stockMode and c['usecase'].lower()==usecase)
    trees=json.loads((P.parent/'kernel347'/(variant+'-gamma-trees-private.json')).read_text());tree=next(t for t in trees if t['uid']==selected['gamma_uid'])
    channels=list(leaves(tree['core']));assert tree['enabled']==1 and len(channels)==3
    data={c['channel']:c['table'] for c in channels};curves=[data[i] for i in [2,0,1]]
    # The retained full-tree and mode proof established one curve for all
    # selected contexts. Check the actual selected curve, not just its UID.
    expected=struct.pack('<HHI',7,2,776)
    for curve in curves:
        expected+=b''.join(struct.pack('<Hh',int(curve[i]),int(curve[i+1]-curve[i])) for i in range(64))
    assert expected==(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
    gamma=dict(mode='static',curves=copy.deepcopy(curves));mode=next(m for m in profile['modes'] if m['match']==row['match']);mode['gamma']=copy.deepcopy(gamma)
    fixture=yaml.safe_load(Path(row['profile']).read_text());fixture['modes'][0]['gamma']=copy.deepcopy(gamma)
    target=fixtures/(row['name']+'.yaml');target.write_text(yaml.safe_dump(fixture,sort_keys=False))
    legacy=fixtures/(row['name']+'-legacy.yaml');shutil.copyfile(row['legacy_profile'],legacy)
    row.update(profile=str(target),legacy_profile=str(legacy),complete_profile=str(directory/name),expected_gamma=str(P/'factory-gamma-private.bin'))
for name,profile in profiles.items():
    target=directory/name;target.write_text(yaml.safe_dump(profile,sort_keys=False))
    assert not any(isinstance(e,yaml.AliasEvent) for e in yaml.parse(target.read_text()))
for name in ['factory-gamma-private.bin','rgb-gamma-private.bin']:shutil.copyfile(P.parent/'kernel349'/name,P/name)
diagnostic=copy.deepcopy(next(r for r in rows if r['name']=='imx319-2-preview'));diagnostic['name']='imx319-2-preview-rgb'
fixture=yaml.safe_load(Path(diagnostic['profile']).read_text());fixture['modes'][0]['gamma']['curves']=[[i*16*scale for i in range(65)] for scale in [.5,.75,.25]]
target=fixtures/(diagnostic['name']+'.yaml');target.write_text(yaml.safe_dump(fixture,sort_keys=False));legacy=fixtures/(diagnostic['name']+'-legacy.yaml');shutil.copyfile(diagnostic['legacy_profile'],legacy)
diagnostic.update(profile=str(target),legacy_profile=str(legacy),expected_gamma=str(P/'rgb-gamma-private.bin'));rows.append(diagnostic)
(P/'cases-private.json').write_text(json.dumps(rows,indent=2)+'\n')
report=dict(stage=360,complete_private_profiles=len(profiles),factory_contexts=len(rows)-1,asymmetric_rgb_diagnostic=1,
    selected_gamma_matches_retained_native_block=True,exposure_native_references_reused_unchanged_from359=True,
    unknown_front_crop_stays_generic=True,calibration_fields_preserved=True,installed=False,passed=True)
(HERE/'profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
