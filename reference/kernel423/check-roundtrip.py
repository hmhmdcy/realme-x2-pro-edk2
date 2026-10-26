"""Compare saved real sensor patterns in a fixed manual sensor/IFE state."""
from pathlib import Path
import hashlib,json,re,struct,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r2'
def render(raw,path):
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 rows=bytearray();clamp=lambda n:max(0,min(255,n))
 for y in range(480):
  rows.append(0)
  for x in range(640):
   a=raw[y*640+x]-16;at=307200+(y//2)*640+(x//2)*2;u=raw[at]-128;v=raw[at+1]-128
   rows.extend((clamp((298*a+409*v+128)>>8),clamp((298*a-100*u-208*v+128)>>8),clamp((298*a+516*u+128)>>8)))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',640,480,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))
assert json.loads((HERE/'runtime-r2-validation.json').read_text())['passed']
images={};contexts={}
for mode in ['bypass','colour-roundtrip','gamma-roundtrip']:
 name='pattern-'+mode;log=(root/(name+'.log')).read_text()
 lines=[x for x in log.splitlines() if 'ADAPT_FRAME ' in x];sample=[x for x in log.splitlines() if 'SAMPLE ' in x][-1]
 fields=dict(re.findall(r'([a-z-]+)=([^ ]+)',sample));assert [int(fields[k]) for k in ['width','height','stride','bytes']]==[640,480,640,460800]
 frames=sorted((root/name).glob('*.nv12'));assert len(frames)==1
 raw=frames[0].read_bytes();assert len(raw)==460800;images[mode]=raw
 ctx=dict(re.findall(r'([a-z-]+)=([^ ]+)',lines[-1]));contexts[mode]={k:ctx[k] for k in ['exposure','gain','red','blue','read-lines','read-code','matrix']}
 # Conversion is for inspection only; comparison below uses original bytes.
 render(raw,P/(name+'-private.png'))
base=images['bypass'];rows=[]
for mode in ['colour-roundtrip','gamma-roundtrip']:
 raw=images[mode];slices=[('Y',range(0,307200)),('U',range(307200,460800,2)),('V',range(307201,460800,2))];planes=[]
 for name,indices in slices:
  delta=[abs(raw[i]-base[i]) for i in indices];planes.append(dict(plane=name,mean_absolute=sum(delta)/len(delta),maximum=max(delta),different=sum(v!=0 for v in delta),over8=sum(v>8 for v in delta)))
 rows.append(dict(mode=mode,planes=planes,manual_sensor_and_ife_context_equal=contexts[mode]==contexts['bypass']))
(P/'roundtrip-contexts-private.json').write_text(json.dumps(contexts,indent=2)+'\n')
r=dict(stage=423,real_sensor_test_pattern=2,nv12_original_bytes_compared=True,manual_exposure_us=5004,analogue_gain=1,contexts_equal=all(v==contexts['bypass'] for v in contexts.values()),rows=rows,
 compare_to_bypass=True,absolute_optical_quality_not_claimed=True,passed=all(r['manual_sensor_and_ife_context_equal'] and all(p['mean_absolute']<=3 for p in r['planes']) for r in rows))
(HERE/'roundtrip-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
