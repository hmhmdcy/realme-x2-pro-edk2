from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();fw=module('fw425',HERE/'firmware-model.py')
config=(P/'640-multipass-config-private.bin').read_bytes();stripe=(P/'640-multipass-stripe-private.bin').read_bytes();iq=(P/'640-multipass-iq-private.bin').read_bytes()
m,job,cmd,meta=fw.prepare(config,stripe,iq,640,480,46080)
for name,raw in [('job',job),('commands',cmd),('frame',meta.pop('frame'))]:(P/('640-multipass-'+name+'-private.bin')).write_bytes(raw)
controls=[dict(offset=i,value=struct.unpack_from('<I',cmd,i+4)[0]) for i in range(0,len(cmd)-4,4) if struct.unpack_from('<I',cmd,i)[0]==0x5c60]
row=dict(stage=425,**meta,passes=struct.unpack_from('<I',stripe,20)[0],job_words=struct.unpack('<8I',job),ltm_control_writes=controls,cache=m.cache,external_arrays=m.external,
 native_instructions=m.instructions,providers=m.providers,frame_enqueue_not_executed=True,phone_accessed=False)
(P/'firmware-probe-private.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row,indent=2))
