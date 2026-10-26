"""Execute the complete original enable aggregator after DS4/precrop/depth."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('ds426',HERE.parent/'kernel426/ds4-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n);m=n.Machine();D=n.h.DATA
index=json.loads((P.parent/'kernel333/sunny_s5kgw1-index-private.json').read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
root=next(r for r in json.loads((P.parent/'kernel426/sunny_s5kgw1-ds4-reserves-private.json').read_text()) if r['tag']=='ds4to1v10_ife_full_dc4')
def blob(uid):
 e=index['entries'][str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
data=blob(root['uid']);rev=struct.unpack_from('<Q',data,32)[0];parsed,_=m.parse(root['tag'],root['uid'],data,rev,blob(rev))
m.execute(parsed,640,480);m.producer_crops_and_round(640,480)
node=D+0x100000;m.u.mem_map(node,0x40000);m.u.mem_write(node,bytes(0x40000));before=len(m.writes)
m.u.mem_write(node+0xff74,struct.pack('<2I',1,1))
result=m.call(0x2a8900,node,D+0x20000,phase='whole-original-ife-module-enable-aggregation')
writes=m.writes[before:];(P/'module-enable-native-writes-private.json').write_text(json.dumps([dict(address=hex(a),data=b.hex()) for a,b in writes],indent=2)+'\n')
calculated=bytes(m.u.mem_read(D+0x40000+960,128));(P/'module-enable-calculated-private.bin').write_bytes(calculated)
print(json.dumps(dict(result=result,write_count=len(writes),writes=[dict(address=hex(a),bytes=len(b)) for a,b in writes])))
