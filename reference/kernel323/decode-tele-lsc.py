"""Decode retained telephoto factory LSC, retaining complete trigger topology."""
from pathlib import Path
import hashlib,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=P.parent/'kernel306/qtech-s5k3m5sx-tuning-private.bin';raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b'
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];base,size=sections[1][1:];entries={}
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode();version,incr=struct.unpack_from('<II',raw,pos+40)
 offset,nbytes=struct.unpack_from('<QQ',raw,pos+56);assert offset+nbytes<=size
 entries[str(uid)]=dict(name=name,version=version,increment=incr,offset=offset,bytes=nbytes)
assert len(entries)==length//72
# Reuse the complete typed decoder rather than creating a telephoto byte-layout fork.
text=(HERE.parent/'kernel322/decode-trigger-tree.py').read_text()
helpers=text[text.index('levels='):text.index('\nroots=[]')]
ns=dict(entries=entries,raw=raw,base=base,channels=['r','gr','gb','b'],struct=struct,json=json)
exec(helpers,ns)
roots=[]
for uid,entry in entries.items():
 if entry['name']!='lsc34_ife' or not entry['version']:continue
 words=struct.unpack_from('<'+'Q'*(entry['bytes']//8),raw,base+entry['offset'])
 refs=[dict(word=i,uid=v,name=entries[str(v)]['name']) for i,v in enumerate(words) if str(v) in entries]
 a=next(r for r in refs if r['name']=='mod_lsc34_lens_position_data');g=next(r for r in refs if r['name']=='mod_lsc34_golden_cct_data')
 roots.append(dict(uid=int(uid),core=ns['decode'](a['uid'],entries[str(a['uid'])]['bytes']//32),golden=ns['leaf'](g['uid'],entries[str(g['uid'])]['bytes']//3568)))
def leaves(nodes):
 for n in nodes:
  if 'gains' in n:yield n
  else:yield from leaves(n['children'])
all_leaves=[n for r in roots for n in leaves(r['core'])]
all_golden=[n for r in roots for n in r['golden']]
assert roots and all(len(v)==221 and all(math.isfinite(x) and x>0 for x in v) for n in all_leaves+all_golden for v in n['gains'].values())
(P/'tele-trigger-trees-private.json').write_text(json.dumps(roots,indent=2)+'\n')
(P/'tele-index-private.json').write_text(json.dumps(dict(base=base,entries=entries),indent=2)+'\n')
report=dict(stage=323,sensor='s5k3m5',source_stage=306,source_sha256=hashlib.sha256(raw).hexdigest(),factory_ife_roots=len(roots),core_regions=len(all_leaves),golden_regions=len(all_golden),
 unique_complete_profiles=len({json.dumps(dict(core=r['core'],golden=r['golden']),sort_keys=True) for r in roots}),
 reused_complete_typed_decoder_stage=322,original_reader_crosscheck_pending=True,individual_data_decoded=False,phone_changed=False,passed=True)
(HERE/'tele-lsc-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
