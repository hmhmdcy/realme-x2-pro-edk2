"""Use complete paired data for LUT bounds; do not equate differently cropped histograms."""
from pathlib import Path
import json,math,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239')
report=json.loads((R/'paired-validation.json').read_text());logs=json.loads((P/'paired-parameter-log-lines-private.json').read_text())
assert report['diagnostic_capture_completed'] and len(report['frames'])==len(logs['debayer'])==len(logs['captured'])==12
rows=[]
for i,(frame,line,captured) in enumerate(zip(report['frames'],logs['debayer'],logs['captured'])):
 assert frame['queued_index']==i and frame['sequence']==frame['raw_sequence'] and frame['timestamp_ns']==frame['raw_timestamp_ns']
 if i:assert frame['sequence']>report['frames'][i-1]['sequence'] and frame['timestamp_ns']>report['frames'][i-1]['timestamp_ns']
 assert list(map(int,re.search(r'Captured request (\d+) from sequence (\d+), control sequence (\d+)',captured).groups()))==[i,frame['sequence'],frame['sequence']]
 for key,count in [('raw',1632*1224),('rgb',1624*1224*3)]:
  stats=frame[key];hist=dict(stats['histogram']);assert sum(hist.values())==stats['samples']==count
  mean=sum(v*n for v,n in hist.items())/count;variance=sum(v*v*n for v,n in hist.items())/count-mean*mean
  assert abs(stats['mean']-mean)<.0001 and abs(stats['stddev']-math.sqrt(max(0,variance)))<.0001
 raw=frame['raw'];rgb=frame['rgb'];high8=dict(raw['high8_histogram']);assert sum(high8.values())==raw['samples']
 m=re.search(r'blackLevel=Vector \{ ([^}]+)\}; gamma=([^;]+); contrastExp=([^;]+); gains=Vector \{ ([^}]+)\}',line);assert m
 black=[float(x.strip()) for x in m[1].split(',')];gains=[float(x.strip()) for x in m[4].split(',')];gamma=float(m[2]);assert float(m[3])==1
 assert 'matrix=Matrix { [ 1, 0, 0 ], [ 0, 1, 0 ], [ 0, 0, 1 ] }' in line
 def lut(value,b,g):
  black_index=b*256;index=int(max(0,min(1023,g*(value-black_index)*1024/max(1,256-black_index))))
  return int(255*math.pow(index/1023,gamma))
 bounds=[lut(value,b,g) for value in [min(high8),max(high8)] for b,g in zip(black,gains)]
 assert min(bounds)<=rgb['min']<=rgb['max']<=max(bounds)
 rows.append(dict(queued_index=i,source_sequence_equal=True,source_timestamp_equal=True,raw_samples=raw['samples'],rgb_samples=rgb['samples'],
                  raw_min=raw['min'],raw_max=raw['max'],raw_mean=raw['mean'],raw_high8_at_most16_fraction=sum(n for v,n in high8.items() if v<=16)/raw['samples'],
                  applied_blc_8bit=round(black[0]*255),applied_gamma_exponent=gamma,lut_output_bound_min=min(bounds),lut_output_bound_max=max(bounds),
                  rgb_min=rgb['min'],rgb_max=rgb['max'],rgb_mean=rgb['mean'],rgb_zero_fraction=dict(rgb['histogram']).get(0,0)/rgb['samples']))
result=dict(stage=239,twelve_same_request_raw_rgb_pairs_verified=True,full_active_pixel_histograms_recomputed=True,
            source_sequences=[f['sequence'] for f in report['frames']],initial_offline_request_equals_source_sequence_assumption_corrected=True,
            runtime_parameters_associated_by_complete_single_worker_fifo=True,all_observed_rgb_ranges_within_cpu_lut_bounds=True,
            raw1632_and_rgb1624_different_roi=True,no_pixelwise_histogram_equivalence_claimed=True,
            nonzero_output_alone_not_scene_or_colour_acceptance=True,previous_single_rgb_zero_failure_not_overwritten=True,frames=rows)
(R/'paired-lut-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(stage=239,pairs=12,raw_nonzero_all=True,blc16_indices=[f['queued_index'] for f in rows if f['applied_blc_8bit']==16],blc16_rgb_means=[f['rgb_mean'] for f in rows if f['applied_blc_8bit']==16],lut_bounds_verified=True,scene_optical_response_still_open=True)))
