from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();n=module('native425',HERE/'native-model.py')
m=n.Native();image,descriptor=m.pd10(160,120)
(P/'pd10-160x120-image-private.bin').write_bytes(image);(P/'pd10-160x120-io-private.bin').write_bytes(descriptor)
print('PD10',json.dumps(dict(plane=struct.unpack_from('<8I',image,24),plane_size=struct.unpack_from('<Q',image,56)[0],io=struct.unpack('<21I',descriptor))),flush=True)
config=bytearray(1216)
for port in [0,8]:
 off=port*84;struct.pack_into('<III',config,off,20,640,480);struct.pack_into('<4I',config,off+52,640,480,640,240)
config[84:168]=descriptor;struct.pack_into('<I',config,1192,1)
iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes()
stripe,bl,capacity=m.striping(bytes(config),640,480,2,iq)
for name,raw in [('config',bytes(config)),('iq',iq),('stripe',stripe)]:(P/('640-multipass-'+name+'-private.bin')).write_bytes(raw)
passes=struct.unpack_from('<I',stripe,20)[0]
row=dict(passes=passes,bytes=len(stripe),capacity=capacity,bl=bl,
 pass_summary=[dict(index=i,tail_word412=struct.unpack_from('<I',stripe,412+i*412)[0],ltm_ip=struct.unpack_from('<I',stripe,416+i*412)[0],stripes=struct.unpack_from('<H',stripe,428+i*412)[0],stripe_offset=struct.unpack_from('<I',stripe,432+i*412)[0]) for i in range(passes)],
 native_instructions=m.instructions,providers=m.providers)
(P/'multipass-probe-private.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row,indent=2))
