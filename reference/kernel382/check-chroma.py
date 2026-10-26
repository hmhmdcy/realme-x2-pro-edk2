"""Locate residual chroma differences without assuming their hardware cause."""
from pathlib import Path
from collections import Counter
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(P/'ipe-input-private.nv12').read_bytes();output=(P/'collected-r1/ipe-output-private.nv12').read_bytes()
assert len(source)==len(output)==460800 and source[:307200]==output[:307200]
rows={}
for channel,offset in [('U',0),('V',1)]:
 mismatches=[]
 for y in range(240):
  for x in range(0,640,2):
   p=307200+y*640+x+offset;delta=output[p]-source[p]
   if delta:
    distance=min(abs(x-b) for b in range(80,640,80)) if channel=='U' else min(abs(y-b) for b in range(60,240,60))
    mismatches.append((distance,delta))
 rows[channel]=dict(mismatch_bytes=len(mismatches),delta_histogram=dict(sorted(Counter(d for _,d in mismatches).items())),
  distance_from_input_step_histogram=dict(sorted(Counter(r for r,_ in mismatches).items())),
  max_step_distance=max(r for r,_ in mismatches),distance_unit='luma_x_pixels' if channel=='U' else 'chroma_y_rows')
assert rows['U']['max_step_distance']<=4 and rows['V']['max_step_distance']<=2
report=dict(stage=382,actual_output=True,luma_identity=True,chroma_mismatches_confined_to_input_step_neighborhoods=True,
 exact_filter_or_rounding_algorithm_not_proven=True,channels=rows,passed=True)
(HERE/'chroma-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
