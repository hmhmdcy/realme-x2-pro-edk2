"""Feed original complete TMC11 output into original complete GTM calculation."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage432adrc',HERE.parent/'kernel284/storage.py').mounted_build();n=module('gtm432adrc',HERE/'gtm-model.py');t=module('tmc416gtm',HERE.parent/'kernel416/execute-model.py')
profiles=json.loads((P.parent/'kernel412/mode-profiles-private.json').read_text());records=[]
for variant in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 context=next(c for c in profiles[variant] if c['usecase']=='Preview');tmc=t.ExecuteMachine();tmc.reset();root=context['modules']['tmc11_sw']
 selections=json.loads((P.parent/'kernel431'/(variant+'-gtm-selections-private.json')).read_text());selected=next(s for tag,c,s in selections if c[1]==context['sensor_mode_index'] and c[2]==0)
 gtm_root=next(r for r in json.loads((P/(variant+'-gtm-trees-private.json')).read_text()) if r['uid']==selected['uid'])
 previous=None
 for step,triggers in enumerate([[2,1.2,2,140,3,4],[4,2,3,210,3,8],[8,4,4,280,4,16]]):
  output=tmc.request(root,triggers,1,[0,0],1 if step!=1 else 2);adrc=output['adrc']+bytes(4)
  enabled=bool(struct.unpack_from('<I',adrc,8)[0]);assert enabled==bool(root['enabled'] and root['reserve']['use_gtm'])
  if not enabled:
   assert not gtm_root['enabled'];records.append(dict(variant=variant,step=step,enabled=False,front_disable_preserved=True));continue
  assert gtm_root['enabled'] and struct.unpack_from('<f',adrc,60)[0]>0
  m=n.Machine();chromatix,_=m.load_parsed(P/(variant+'-'+str(selected['uid'])+'-native-parse-private.json'));lut,inp,interpolated=m.calculate(chromatix,drc_gain=triggers[0],sensitivity=triggers[2],lux=triggers[3],gain=triggers[4],adrc=adrc)
  assert m.adrc_gain is not None
  name=variant+'-'+str(step);(P/(name+'-adrc-private.bin')).write_bytes(adrc);(P/(name+'-adrc-lut-private.bin')).write_bytes(lut);(P/(name+'-adrc-gain-private.bin')).write_bytes(m.adrc_gain)
  axis=bytes(m.u.mem_read(0xd7cb8,260));integer_axis=bytes(m.u.mem_read(0xd7dbc,260));contrast_axis=bytes(m.u.mem_read(0xd8ed8,4096));(P/'gtm-normalized-axis-private.bin').write_bytes(axis);(P/'gtm-integer-axis-private.bin').write_bytes(integer_axis);(P/'gtm-contrast-axis-private.bin').write_bytes(contrast_axis)
  records.append(dict(variant=variant,step=step,enabled=True,native_tmc_instructions=output['instructions'],native_gtm_instructions=m.instructions,gtm_providers=m.providers,changed_from_preceding=previous is not None and lut!=previous))
  previous=lut
  print(json.dumps(dict(variant=variant,step=step,native_gtm_instructions=m.instructions)),flush=True)
(P/'adrc-records-private.json').write_text(json.dumps(records,indent=2)+'\n');active=[r for r in records if r['enabled']];assert len(active)==9 and sum(r['changed_from_preceding'] for r in active)>=3
r=dict(stage=432,mode_contexts=4,original_tmc_execute_calls=len(records),active_gtm_calculations=len(active),disabled_front_calls=sum(not r['enabled'] for r in records),stock_tmc_gtm_percentage_preserved=True,tmc11_version1_adrc_pointer_assigned_by_native_gtm=True,nontrivial_input_changes_change_lut=True,original_parser_objects_used=True,packing_platform_selector_fixture=2,packing_swap_fixture=False,phone_platform_not_read=True,histograms_synthetic=True,host_libm_not_bionic=True,phone_accessed=False,hardware_application_verified=False,passed=True)
(HERE/'adrc-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
