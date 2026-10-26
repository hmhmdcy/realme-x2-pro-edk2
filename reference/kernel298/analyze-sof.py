"""Check frame-event identity, independent ROI effects, and starvation gaps."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent
capture=json.loads((HERE/'blc-capture-validation.json').read_text())
text=capture['tool_output']
events=[];images=[];stats=[];params=[];errors=[]
def numbers(line):
 return {k:int(v) for k,v in re.findall(r'\b(epoch|context|number|frame|phase|index|sequence|event_sequence|pending|timestamp_ns|timestamp_us|sum|flags)=(\d+)',line)}
for line in text.splitlines():
 if line.startswith('SOF '):events.append(numbers(line))
 elif line.startswith('FRAME number='):images.append(numbers(line))
 elif line.startswith('STATS frame='):stats.append(numbers(line))
 elif line.startswith('PARAM_DQ '):params.append(numbers(line))
 elif line.startswith('STATS_ERROR '):errors.append(numbers(line))
event_map={(r['epoch'],r['sequence']):r for r in events}
epoch=lambda r:0 if r.get('frame',r.get('number',0))<72 else 1
for rows in [images,stats]:
 for r in rows:r['epoch']=epoch(r)
image_map={(r['epoch'],r['sequence']):r for r in images}
unmatched_images=[r for r in images if (r['epoch'],r['sequence']) not in event_map]
unmatched_stats=[r for r in stats if (r['epoch'],r['sequence']) not in event_map]
early=[]
for r in images+stats:
 event=event_map.get((r['epoch'],r['sequence']))
 if event and r['timestamp_us']*1000+1000<event['timestamp_ns']:early.append(r)
paired=[]
for s in stats:
 i=image_map.get((s['epoch'],s['sequence']))
 if i:paired.append(dict(epoch=s['epoch'],sequence=s['sequence'],statistics_completion_minus_image_us=s['timestamp_us']-i['timestamp_us']))
transitions=[]
for phase,population in [(1,410280),(3,2),(4,820560),(5,2),(6,820560)]:
 p=next((p for p in params if p['phase']==phase),None)
 candidates=[] if p is None else [s for s in stats if s['epoch']==0 and s['sequence']>=max(0,p['sequence']-2) and s['sum']==population]
 first=min(candidates,key=lambda s:s['sequence']) if candidates else None
 transitions.append(dict(phase=phase,expected_population=population,parameter_sequence=None if p is None else p['sequence'],
                         first_matching_statistics_sequence=None if first is None else first['sequence'],
                         exact_match=p is not None and first is not None and p['sequence']==first['sequence']))
before=[s for s in stats if 99<=s['frame']<=101]
after=[s for s in stats if s['frame']>=108]
gap=min(s['sequence'] for s in after)-max(s['sequence'] for s in before) if before and after else None
late=[s for s in stats if s['frame']==90]
report=dict(stage=298,physical_capture_passed=capture['passed'],image_frames=len(images),valid_statistics_packets=len(stats),
 statistics_error_packets=errors,sof_events=len(events),images_missing_sof_event=unmatched_images,statistics_missing_sof_event=unmatched_stats,
 completions_earlier_than_shared_sof=early,paired_image_statistics_frames=len(paired),
 unique_event_keys=len(event_map)==len(events),unique_image_keys=len(image_map)==len(images),
 unique_statistics_keys=len({(s['epoch'],s['sequence']) for s in stats})==len(stats),
 statistics_starvation_sequence_gap=gap,late_tiny_roi_first_packet=late,
 roi_parameter_transitions=transitions,all_five_observable_roi_transitions_exact=all(t['exact_match'] for t in transitions),
 completion_delta_us_range=[min(r['statistics_completion_minus_image_us'] for r in paired),max(r['statistics_completion_minus_image_us'] for r in paired)] if paired else None,
 measurement_scope='S5K3M5 GRBG10 2104x1560 pattern2, FULL320x240, standard frame events; two image epochs and independent stats stop/start/starvation',
 multiple_unobserved_sof_edges_not_proven=True,request_api_and_full_ipa_not_proven=True,ready_for_automatic_exposure=False)
report['shared_sof_contract_passed']=bool(capture['passed'] and not unmatched_images and not unmatched_stats and not early and len(paired)>80 and gap is not None and gap>=4 and late and late[0]['sum']==2 and report['unique_event_keys'] and report['unique_image_keys'] and report['unique_statistics_keys'])
(HERE/'sof-association-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['shared_sof_contract_passed'] and report['all_five_observable_roi_transitions_exact']
