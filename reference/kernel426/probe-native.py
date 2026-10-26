from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();n=module('ds426',HERE/'ds4-model.py');m=n.Machine()
variant='sunny_s5kgw1';index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
root=next(r for r in json.loads((P/(variant+'-ds4-reserves-private.json')).read_text()) if r['tag']=='ds4to1v10_ife_full_dc4')
def blob(uid):
 e=index['entries'][str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
data=blob(root['uid']);revision_uid=struct.unpack_from('<Q',data,32)[0]
parsed,output=m.parse(root['tag'],root['uid'],data,revision_uid,blob(revision_uid))
assert output[136:200]==struct.pack('<16I',*[v for row in root['passes'] for v in row])
(P/'parsed-ds4-class-private.bin').write_bytes(output)
regs=m.registers(parsed,480);(P/'ds4-480-registers-private.bin').write_bytes(regs)
executed,enable,obj=m.execute(parsed,640,480);assert executed==regs
(P/'ds4-execute-object-private.bin').write_bytes(obj)
crop,rounding,packing,combined=m.producer_crops_and_round(640,480)
(P/'ds4-crops-round-private.json').write_text(json.dumps(dict(crop=[(hex(a),b.hex()) for a,b in crop],rounding=[(hex(a),b.hex()) for a,b in rounding],packing=[(hex(a),b.hex()) for a,b in packing],enable_bits=hex(combined)),indent=2))
print(json.dumps(dict(parsed_class_bytes=len(output),all_four_passes_match=True,register_bytes=len(regs),full_execute_matches=True,enable_bits=hex(enable),crop_writes=[hex(a) for a,b in crop],round_writes=[hex(a) for a,b in rounding],combined_enable_bits=hex(combined),selected_names=m.selections,providers=m.providers,native_instructions=m.instructions)))
