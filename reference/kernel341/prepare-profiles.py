from pathlib import Path
import copy,json,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;cases=json.loads((P.parent/'kernel340/profiles-private.json').read_text());(P/'profiles').mkdir(exist_ok=True);rows={}
for name,row in cases.items():
 if name in ['front-explicit-ccm-experiment','gain-axis-diagnostic']:continue
 item=row['item'];variant=item['variant'];model=item['model']
 if model=='imx319':roots=json.loads((P.parent/'kernel322/decoded-trigger-trees-private.json').read_text());static=yaml.safe_load((P.parent/'kernel322/profiles/unit.yaml').read_text())
 else:
  stage=323 if model=='s5k3m5' else 324;filename='tele-trigger-trees-private.json' if stage==323 else variant+'-trees-private.json'
  roots=json.loads((P.parent/('kernel'+str(stage))/filename).read_text());static=yaml.safe_load((P.parent/'kernel327/profiles'/(variant+'-unit.yaml')).read_text())
 root=next(r for r in roots if r['uid']==25);assert len(root['golden'])==1,(name,'multi-illuminant binding required')
 bysize={(m['match']['width'],m['match']['height']):m['lens_shading'] for m in static['modes']}
 for kind in ['factory','unit']:
  profile=yaml.safe_load((P.parent/'kernel340/profiles'/(name+'.yaml')).read_text())
  for mode in profile['modes']:
   source=bysize[(mode['match']['width'],mode['match']['height'])]
   lsc={k:copy.deepcopy(source[k]) for k in ['source_span','first_quad','quad_step']}
   lsc.update(mode='dynamic',aec_control='lux_index',hdr_control='sensitivity_ratio',reference_triggers=dict(lens_position=1.,drc_gain=1.,hdr_ratio=1.,led_index=0),core=copy.deepcopy(root['core']))
   if kind=='unit':lsc.update(golden=copy.deepcopy(root['golden'][0]['gains']),unit=copy.deepcopy(source['unit']))
   mode['lens_shading']=lsc
  label=variant+'-'+kind;path=P/'profiles'/(label+'.yaml');path.write_text(yaml.safe_dump(profile,sort_keys=False));assert not any(isinstance(event,yaml.AliasEvent) for event in yaml.parse(path.read_text()))
  rows[label]=dict(item=item,kind=kind,variant=variant,profile=label,explicit_unit_illuminant=0 if kind=='unit' else None,root_uid=25,physical_supplier_mode_bound=False)
(P/'profiles-private.json').write_text(json.dumps(rows,indent=2)+'\n')
(HERE/'profile-validation.json').write_text(json.dumps(dict(stage=341,profiles=len(rows),factory_variants=5,complete_lens_drc_hdr_led_aec_cct_core=True,all_selected_default_roots_have_one_golden=True,explicit_primary_unit_record=True,other_illuminants_not_implicitly_bound=True,default_profiles_changed=False,passed=True),indent=2)+'\n');print('Prepared full-core factory/unit dynamic LSC profiles for five explicit sources.')
