"""Execute the retained HAL GTM parser against unmodified stock payloads."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage432native',HERE.parent/'kernel284/storage.py').mounted_build()
n=module('native426',HERE.parent/'kernel426/ds4-model.py');D=n.h.DATA
layout=json.loads((P/'gtm-layout-private.json').read_text())
def packed(values,fields):
 return b''.join(struct.pack('<'+str(f['count'])+f['format'],*(values[f['name']] if f['count']>1 else [values[f['name']]])) for f in fields)
def leaves(nodes):
 for row in nodes:
  if 'children' in row:yield from leaves(row['children'])
  else:yield row['data']
reports=[]
for variant in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes();entries=index['entries']
 def blob(uid):
  e=entries[str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
 for root in json.loads((P/(variant+'-gtm-trees-private.json')).read_text()):
  m=n.Machine();u=m.u;uids=[root['uid']];data=blob(root['uid']);uids.append(struct.unpack_from('<Q',data,40)[0])
  def children(uid,count,level):
   uids.append(uid)
   if level==2:return
   data=blob(uid);trigger=[2,6][level]*8;stride=trigger+16;assert len(data)==count*stride
   for off in range(0,len(data),stride):
    number,child=struct.unpack_from('<2Q',data,off+trigger);children(child,number,level+1)
  count,uid=struct.unpack_from('<2Q',data,104);children(uid,count,0);uids=list(dict.fromkeys(uids))
  prototype=D+0x1000;table=D+0x2000;table_entries=D+0x3000;at=D+0x10000
  u.mem_write(prototype,bytes(128));u.mem_write(prototype+16,root['tag'].encode()+b'\0');u.mem_write(prototype+56,struct.pack('<Q',1));u.mem_write(table,struct.pack('<I',len(uids)));u.mem_write(table+16,struct.pack('<Q',table_entries))
  for i,uid in enumerate(uids):
   entry=table_entries+i*88;payload=blob(uid);u.mem_write(entry,bytes(88));u.mem_write(entry,struct.pack('<QI',table,uid));u.mem_write(entry+12,entries[str(uid)]['name'].encode()+b'\0');u.mem_write(entry+45,struct.pack('<Q',1));u.mem_write(entry+68,struct.pack('<IQQ',len(payload),at,0));u.mem_write(at,payload);at+=(len(payload)+31)&~31
  assert at<D+0x100000
  parsed=m.call(0x2085f0,prototype,0,table_entries,8,phase='whole-target-gtm-parse')
  if not parsed:
   (P/'native-parse-failure-private.json').write_text(json.dumps(dict(providers=m.providers,pcs=[hex(x) for x in sorted(m.pcs)],allocations=m.allocations,cursors=[(uid,m.read64(table_entries+i*88+80),len(blob(uid))) for i,uid in enumerate(uids)]),indent=2));raise AssertionError('Native GTM parser returned null; diagnostic retained privately')
  assert all(m.read64(table_entries+i*88+80)==len(blob(uid)) for i,uid in enumerate(uids))
  expected=[packed(v,layout['region']) for v in leaves(root['core'])];assert all(len(v)==360 for v in expected)
  matches=[]
  for address,length in m.allocations.items():
   allocation=bytes(u.mem_read(address,length))
   for leaf in expected:
    off=allocation.find(leaf)
    if off>=0:matches.append(dict(address=address,offset=off,bytes=len(leaf)))
  assert len(matches)==len(expected),(variant,root['uid'],matches,m.allocations)
  out=bytes(u.mem_read(parsed,m.allocations[parsed]));assert m.read32(parsed+96)==root['enabled']
  assert out[164:172]==packed(root['reserve'],layout['reserve'])
  (P/(variant+'-'+str(root['uid'])+'-native-parse-private.json')).write_text(json.dumps(dict(root=out.hex(),allocations={hex(a):bytes(u.mem_read(a,b)).hex() for a,b in m.allocations.items()},matches=matches,providers=m.providers),indent=2)+'\n')
  reports.append(dict(variant=variant,uid=root['uid'],tag=root['tag'],enabled=bool(root['enabled']),leaves=len(expected),root_bytes=len(out),allocation_sizes=sorted(m.allocations.values()),native_instructions=m.instructions))
  print(json.dumps(reports[-1]),flush=True)
r=dict(stage=432,roots=len(reports),regions=sum(r['leaves'] for r in reports),all_original_entry_cursors_exhausted=True,all_regions_binary_exact=True,root_enable_and_reserve_binary_exact=True,native_parser_entry='0x2085f0',runtime_region_bytes=360,phone_accessed=False,algorithm_stubbed=False,passed=True)
(HERE/'native-parse-validation.json').write_text(json.dumps(r,indent=2)+'\n');(P/'native-parse-records-private.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(r))
