"""Test which groups of disabled-module fields affect original CDM output."""
from pathlib import Path
import json
from engine_model import prepare
import host
P=host.PRIVATE;original=(P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin').read_bytes()
_,gold_job,gold,_=prepare(original,640,480)
groups=[('header-module-fields',[(24,300)]),('header-ica-zoom',[(344,376)]),('header-reference-crop',[(380,420)]),
 ('stripe-module-fields',[(2268+48,2268+324),(2892+48,2892+324)]),('stripe-ica-and-extra',[(2268+368,2268+624),(2892+368,2892+624)]),
 ('stripe-crops',[(2268+324,2268+368),(2892+324,2892+368)]),('header-extra-format',[(0,20)]),
 ('header-fe-we-ranges',[(300,344)]),('header-ica-input-range',[(372,420)]),('stripe-output-scopes',[(2268+8,2268+44),(2892+8,2892+44)])]
rows=[];minimal=bytearray(original)
for name,ranges in groups:
 data=bytearray(original)
 for a,b in ranges:data[a:b]=bytes(b-a)
 try:
  _,job,commands,_=prepare(bytes(data),640,480);same=job==gold_job and commands==gold
  row=dict(name=name,identical_original_generated_cdm_and_job=same,different_cdm_bytes=sum(a!=b for a,b in zip(gold,commands)))
 except BaseException as e:row=dict(name=name,identical_original_generated_cdm_and_job=False,error=str(e))
 if row['identical_original_generated_cdm_and_job']:
  for a,b in ranges:minimal[a:b]=bytes(b-a)
 rows.append(row)
_,job,commands,_=prepare(bytes(minimal),640,480);assert job==gold_job and commands==gold
(P/'640-group-minimal-private.bin').write_bytes(minimal);(P/'group-influence-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
