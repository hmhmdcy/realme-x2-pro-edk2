"""Check that tested C bodies match the maintained proposal after formatting."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
proposal=(P/'camss-icp-a5-ipe.c.proposed').read_text()
names=['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping']
def body(text,name):
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert match,name
 return re.sub(r'\s+','',match[0])
rows=[]
for model in ['serializer-model.c','layout-model.c','iq-geometry-model.c']:
 text=(P/model).read_text()
 for name in names:assert body(text,name)==body(proposal,name),(model,name)
 assert 'booldata_collection,image_processing,mask_filter;' in re.sub(r'\s+','',text)
 rows.append(dict(model=model,native_function_bodies_match_ignoring_whitespace=True,passed=True))
assert body((P/'serializer-model.c').read_text(),'camss_a5_ipe_encode_bypass_striping')==body(proposal,'camss_a5_ipe_encode_bypass_striping')
report=dict(stage=404,models=rows,native_source_sha256=hashlib.sha256((P/'camss-icp-a5-ipe.c.proposed').read_bytes()).hexdigest(),only_formatting_differs_in_iq_model=True,passed=True)
(HERE/'model-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
