"""Validate the LTM partition and fetch rule against retained original output."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[]
for name in ['striping-probe.json','striping-boundary-probe.json','striping-extreme-probe.json']:
 d=json.loads((HERE/name).read_text());assert d['completed']
 for row in d['cases']:
  w,h,p,c,dc,ip=[row[k] for k in ['width','height','port','cores','data_collection','image_processing']];slug=f'{w}x{h}-p{p}-c{c}-dc{dc}-ip{ip}';raw=(P/(slug+'-original-stripe-private.bin')).read_bytes()
  tile=324 if ip else 328;halo=6 if ip else 4;expected=((w+tile-1)//tile+c-1)//c*c;count=struct.unpack_from('<H',raw,428)[0];assert expected==count and len(raw)==2268+624*count
  ranges=[]
  for i in range(count):
   j=count-1-i;first=(w*j//count)&~1;end=((w*(j+1)//count)&~1)-1;fetch=max(0,first-halo);last=min(w-1,end+halo);off=2268+624*i
   actual=struct.unpack_from('<2H',raw,off+4)+struct.unpack_from('<2H',raw,off+(24 if p==9 else 20));assert actual==(fetch,last,first,end),(slug,i,actual,(fetch,last,first,end));ranges.append((first,end))
  ranges.sort();assert ranges[0][0]==0 and ranges[-1][1]==w-1 and all(a[1]+1==b[0] for a,b in zip(ranges,ranges[1:]));rows.append(dict(width=w,height=h,port=p,cores=c,data_collection=dc,image_processing=ip,stripes=count,observed_tile_step=tile,observed_fetch_halo=halo,all_boundaries_equal=True))
report=dict(stage=403,original_hal_outputs_checked=True,cases=rows,ltm_image_processing_partition_step=324,ltm_image_processing_fetch_halo=6,bypass_step=328,bypass_halo=4,core_rounding_and_chroma_alignment_match=True,full_frame_coverage_without_overlap_or_gap=True,scope='Observed full-frame1:1 NV12 in30 offline cases only; not hardware support.',evidence_kind='Original HAL output rule check, separate from native C validation',phone_accessed=False,passed=True)
(HERE/'partitions-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
