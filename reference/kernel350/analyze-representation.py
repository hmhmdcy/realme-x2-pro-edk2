"""Assess IPE257->IFE65 sampling without claiming processing-graph equivalence."""
from pathlib import Path
import json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def leaves(nodes):
 for n in nodes:
  if 'table' in n:yield n
  else:yield from leaves(n['children'])
def knots(values):
 # All extracted factory knots are nonnegative. Half-away rounding therefore
 # agrees with the previously checked native encoder, including its endpoint.
 return [min(1024 if i==len(values)-1 else 1023,math.floor(x+.5)) for i,x in enumerate(values)]
def sample(values,position):
 n=len(values)-1;i=min(int(position*n),n-1);weight=position*n-i
 delta=max(-512,min(511,values[i+1]-values[i]))
 return values[i]+weight*delta
unique={};references={};selected=[]
for row in json.loads((HERE/'factory-gamma-validation.json').read_text())['sources']:
 name=row['variant'];roots=json.loads((P/(name+'-gamma-trees-private.json')).read_text())
 for root in roots:
  for c in leaves(root['core']):
   key=struct.pack('<257f',*c['table']);unique[key]=c['table'];references.setdefault(key,set()).add((name,root['uid']))
metrics=[]
for key,values in unique.items():
 fine=knots(values);coarse=knots(values[::4]);assert len(coarse)==65
 clipped=sum(not -512<=b-a<=511 for a,b in zip(coarse,coarse[1:]));fine_clipped=sum(not -512<=b-a<=511 for a,b in zip(fine,fine[1:]))
 error=[sample(coarse,i/256)-sample(fine,i/256) for i in range(257)]
 maximum=max(abs(x) for x in error);rms=math.sqrt(sum((a*a+a*b+b*b)/3 for a,b in zip(error,error[1:]))/256)
 metrics.append(dict(max_output_dn_error=maximum,normalized_8bit_max_error=maximum*255/1023,rms_output_dn_error=rms,
  coarse_clipped_deltas=clipped,fine_clipped_deltas=fine_clipped,source_references=[dict(variant=n,uid=u) for n,u in sorted(references[key])]))
assert not any(r['coarse_clipped_deltas'] or r['fine_clipped_deltas'] for r in metrics)
binding=json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())
mode_profiles={}
for row in binding['sources']:
 name=row['variant'];roots=json.loads((P/(name+'-gamma-trees-private.json')).read_text());out=[]
 for item in row['physical_contexts']:
  root=next(r for r in roots if r['uid']==item['uid']);assert root['enabled']==1
  out.append(dict(sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],root=root))
 mode_profiles[name]=out
(P/'mode-profiles-private.json').write_text(json.dumps(mode_profiles,indent=2)+'\n')
(P/'representation-cases-private.json').write_text(json.dumps(metrics,indent=2)+'\n')
report=dict(stage=350,unique_ipe_curves=len(unique),exactly_representable_by_direct_every_fourth_node_sampling=sum(r['max_output_dn_error']==0 for r in metrics),
 maximum_10bit_output_dn_error=max(r['max_output_dn_error'] for r in metrics),maximum_normalized_8bit_error=max(r['normalized_8bit_max_error'] for r in metrics),
 max_rms_10bit_output_dn_error=max(r['rms_output_dn_error'] for r in metrics),all_coarse_and_fine_deltas_representable=True,
 maximum_is_exact_for_continuous_piecewise_linear_curves=True,hardware_integer_interpolation_not_modelled=True,
 igamma_ltm_ccm_adrc_not_part_of_this_sampling_comparison=True,
 mode_contexts_exported=sum(len(r) for r in mode_profiles.values()),mode_binding_reused_from349=True,
 no_curve_uploaded_or_default_changed=True,passed=True)
(HERE/'representation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
