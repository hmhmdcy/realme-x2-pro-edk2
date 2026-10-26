"""Strict bounded observer-log decoding; returned raw exception values stay private."""
from pathlib import Path
import json,re,struct

def decode(text,profile):
 start=text.rfind('A5 pre-reset snapshot begin ranges=')
 if start<0:raise ValueError('No pre-reset snapshot start')
 text=text[start:];end=text.find('A5 pre-reset snapshot end')
 if end<0:raise ValueError('Incomplete pre-reset snapshot')
 text=text[:end];expected={w['offset']+4*i for w in profile['windows'] for i in range(w['words'])}
 if len(expected)>384:raise ValueError('Oversized profile')
 if int(re.match(r'A5 pre-reset snapshot begin ranges=(\d+)',text)[1])!=len(profile['windows']):raise ValueError('Range count differs')
 if not re.search(r'A5 pre-reset snapshot code-match=1(?:\s|$)',text):raise ValueError('Code page was not confirmed')
 values={}
 for offset,count,raw in re.findall(r'A5 pre-reset snapshot data offset=([0-9a-f]+) count=(\d+) values=([^\s]+)',text):
  base=int(offset,16);n=int(count);words=raw.split(',')
  if not 1<=n<=8 or len(words)!=8 or any(not re.fullmatch('[0-9a-f]{8}',w) for w in words):raise ValueError('Malformed row')
  for i in range(n):
   address=base+4*i
   if address not in expected or address in values:raise ValueError('Out-of-profile or duplicate field')
   values[address]=int(words[i],16)
 if values.keys()!=expected:raise ValueError('Missing snapshot field')
 layout=profile['field_layout'];pointer=values[layout['context_pointer']]
 result=dict(far=values[layout['far']],fsr=values[layout['fsr']],exception_type=values[layout['type']],
  context_pointer=pointer,context_pointer_matches_original=pointer==layout['initial_context'],code_page_match=True,complete=True,words=len(values),fault_pc=None)
 if result['context_pointer_matches_original']:
  sp=values[pointer+layout['abt_sp_offset']];result['saved_abt_sp']=sp
  result['stack_pc_candidate']=values.get(sp+layout['fault_pc_stack_offset'])
  result['stack_pc_candidate_not_authoritative_after_c_handler']=True
 # The original C handler overwrites its popped PC slot with its own saved
 # LR. Only accept a formatted PC when the same bounded text also agrees
 # with the directly saved FAR/FSR and exception kind.
 window=next(w for w in profile['windows'] if w['role']=='original-abort-stack-tail')
 stack=b''.join(struct.pack('<I',values[window['offset']+4*i]) for i in range(window['words']))
 matches=[]
 for kind,pc,fsr,far in re.findall(rb'(Data|Prefetch) Abort Exception at 0x([0-9a-fA-F]+), FSR=0x([0-9a-fA-F]+) FAR=0x([0-9a-fA-F]+)',stack):
  if int(fsr,16)==result['fsr'] and int(far,16)==result['far'] and result['exception_type']==(3 if kind==b'Data' else 1):matches.append(int(pc,16))
 if len(set(matches))>1:raise ValueError('Ambiguous formatted exception PC')
 if matches:result.update(fault_pc=matches[0],fault_pc_source='bounded original handler text agreeing with FAR/FSR/type')
 result['raw_values']={hex(k):v for k,v in values.items()}
 result['a5_dirty_cache_visibility_not_guaranteed']=True
 return result
