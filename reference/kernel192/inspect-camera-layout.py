from pathlib import Path
import struct, json, subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel192')
p=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin')
b=p.read_bytes();section_offset,section_count=struct.unpack_from('<II',b,0x98)
sections=[struct.unpack_from('<QQQ',b,section_offset+i*24) for i in range(section_count)]
print('sections',sections)
_,symoff,symsize=sections[0];_,dataoff,datasize=sections[1]
assert symsize%72==0
entries=[]
for off in range(symoff,symoff+symsize,72):
 ident=struct.unpack_from('<Q',b,off)[0];name=b[off+8:off+40].split(b'\0')[0].decode()
 flags=struct.unpack_from('<II',b,off+40);mode=struct.unpack_from('<Q',b,off+48)[0]
 data,sz=struct.unpack_from('<QQ',b,off+56)
 assert data+sz<=datasize
 entries.append(dict(id=ident,name=name,flags=flags,mode=mode,offset=data,size=sz))
(out/'imx471-symbol-table-private.json').write_text(json.dumps(entries,indent=2))
for e in entries:
 if e['flags'][0] or e['name'] in ['sensorName','powerSetting','sensorSlaveAddress','sensorI2CFrequencyMode']:
  print(e)
  data=b[dataoff+e['offset']:dataoff+e['offset']+min(e['size'],0x400)]
  for n in range(0,len(data),16):
   d=data[n:n+16];print(f" {n:04x} {d.hex(' '):48} "+''.join(chr(x) if 32<=x<127 else '.' for x in d))
binary=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/tools/buildbins/linux64/ParameterParser')
for name,start,end in [('read-symbols',0x41c6e8,0x41d256),('read-data',0x41d588,0x41dfac)]:
 dis=subprocess.check_output(['objdump','-d','-C','--start-address='+hex(start),'--stop-address='+hex(end),str(binary)],text=True)
 (out/('parser-'+name+'-private.txt')).write_text(dis)
schema=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor/camxsensorcommon.xsd').read_text().splitlines()
for i,s in enumerate(schema):
 if any(t in s for t in ['name="PowerSequenceInfo"','name="PowerSetting"']):print('\n'.join(schema[max(0,i):i+50]))
