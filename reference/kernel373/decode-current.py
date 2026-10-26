"""Decode only the saved pre-reset record; raw words and logs remain private."""
from pathlib import Path
import importlib.util,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('decoder372',HERE/'decode-ramoops.py');decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
profile=json.loads((HERE/'firmware-context-validation.json').read_text());text=(P/'a5-ramoops-excerpt-private.txt').read_text()
report=dict(stage=373,pre_reset_begin_observed='A5 pre-reset snapshot begin' in text,
 code_page_match_observed='A5 pre-reset snapshot code-match=1' in text,
 code_page_mismatch_observed='A5 pre-reset snapshot code-match=0' in text,
 pre_reset_end_observed='A5 pre-reset snapshot end' in text,complete_exception_snapshot=False,
 raw_words_public=False,firmware_handshake_passed=False)
try:
 data=decoder.decode(text,profile);(P/'pre-reset-decoded-private.json').write_text(json.dumps(data,indent=2)+'\n')
 functions=[]
 for line in (P.parent/'kernel352/icp-symbols-private.txt').read_text().splitlines():
  m=re.match(r'\s*\d+:\s+([a-fA-F0-9]+)\s+(\S+)\s+FUNC\s+\S+\s+\S+\s+\S+\s+(\S+)',line)
  if m:
   address=int(m[1],16)&~1;size=int(m[2],16 if m[2].startswith('0x') else 10)
   if size and data['fault_pc'] is not None and address<=data['fault_pc']<address+size:functions.append((size,m[3]))
 name=min(functions)[1] if functions else None
 far=data['far'];area='firmware-iova' if far<0x500000 else 'shared-iova-window' if 0x07400000<=far<0x10a00000 else 'heap-iova' if 0x10a00000<=far<0x10b00000 else 'local-mmio' if 0xe0000000<=far<0xe1000000 else 'other'
 report.update(complete_exception_snapshot=True,words=data['words'],context_pointer_matches_original=data['context_pointer_matches_original'],
  exception_type_name={0:'none-or-not-visible',1:'prefetch-abort',2:'undefined-or-syscall',3:'data-abort'}.get(data['exception_type'],'other'),
  fault_pc_available=data['fault_pc'] is not None,fault_pc_function=name,fault_address_class=area,
  exception_fields_nonzero=bool(data['far'] or data['fsr'] or data['exception_type']),a5_dirty_cache_visibility_not_guaranteed=True)
except ValueError as error:report['decode_status']=str(error)
(HERE/'pre-reset-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
