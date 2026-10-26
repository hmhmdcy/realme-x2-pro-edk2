from pathlib import Path
import importlib.util,json,struct
HERE=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('halmachine',HERE/'hal-machine.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
machine=m.Machine();u=machine.u;D=m.DATA;P=m.P
config=bytearray(1216)
for port in [0,8]:
 offset=port*84;struct.pack_into('<III',config,offset,20,640,480);struct.pack_into('<4I',config,offset+52,640,480,640,240)
struct.pack_into('<I',config,1192,1);u.mem_write(D,bytes(config))
ret=machine.call(0x144348,D,0,0x10705,0x10000,D+0x2000,D+0x2010,D+0x2014,phase='create')
context=machine.read64(D+0x2000);print(json.dumps(dict(create_ret=ret,context=hex(context),stripe_bytes=machine.read32(D+0x2010),bl_bytes=machine.read32(D+0x2014),allocations=machine.allocations,instructions=machine.instructions)))
assert ret==0 and context
u.mem_write(D+0x3000,struct.pack('<5QI',D+0x10000,D+0x12000,D+0x14000,D+0x16000,D+0x18000,1))
for zoom in [D+0x16000,D+0x18000]:u.mem_write(zoom,struct.pack('<6I',640,480,0,0,640,480))
ret=machine.call(0x1448f0,context,D+0x3000,D+0x20000,D+0x70000,D+0x80000,phase='execute')
(P/'striping-first-output-private.bin').write_bytes(bytes(u.mem_read(D+0x20000,machine.read32(D+0x2010))));(P/'striping-first-metadata-private.bin').write_bytes(bytes(u.mem_read(D+0x70000,512)))
(P/'striping-first-probe-private.json').write_text(json.dumps(dict(ret=ret,instructions=machine.instructions,providers=machine.providers,pcs=sorted(machine.pcs),allocations=machine.allocations),indent=2)+'\n')
print(json.dumps(dict(execute_ret=ret,instructions=machine.instructions,providers=machine.providers)))
