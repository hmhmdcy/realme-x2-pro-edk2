"""Cross-check the C++ sampler with a Hermite-basis Python implementation."""
from pathlib import Path
import json,math,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tables=[row['gains'] for root in json.loads((P.parent/'kernel317/factory-lsc-decoded-private.json').read_text())['factory'] for row in root['core']]
channels=['r','gr','gb','b']
raw=b''.join(struct.pack('<884f',*[v for c in channels for v in row[c]]) for row in tables)
(P/'factory-input.bin').write_bytes(raw)
rounded=[struct.unpack_from('<884f',raw,i*3536) for i in range(len(tables))]
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(HERE/'libipa/lsc_resample.cpp'),str(HERE.parent/'kernel317/libipa/lens_shading.cpp'),str(HERE/'resample-tables.cpp'),'-o',str(P/'resample-tables')],capture_output=True)
(P/'factory-tool-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()

def geometry(w,h):
 for level in range(3,-1,-1):
  scale=2**level
  cw=math.ceil((w/2)/16/scale)*scale;ch=math.ceil((h/2)/12/scale)*scale
  ox=cw*16-w//2;oy=ch*12-h//2;x=(ox+1)//2;y=(oy+1)//2
  if not(18<=cw<=2048 and 9<=ch<=1024 and cw/scale>=9 and ch/scale>=9):continue
  if ox>=cw or oy>=ch or cw-x<18 or cw//scale-x%(cw//scale)<9:continue
  return cw,ch,x,y,level
 raise ValueError('Unsupported geometry')

def extend(m,x,y):
 bx=min(16,max(0,x));by=min(12,max(0,y));v=m[by*17+bx]
 if bx==x and by==y:return v
 nx=bx+(1 if x<0 else -1 if x>16 else 0);ny=by+(1 if y<0 else -1 if y>12 else 0)
 return 2*v-m[ny*17+nx]

def hermite(v,t):
 a,b,c,d=v;left=(c-a)/2;right=(d-b)/2
 return (2*t**3-3*t*t+1)*b+(t**3-2*t*t+t)*left+(-2*t**3+3*t*t)*c+(t**3-t*t)*right

def predict(m,g,mapping):
 cw,ch,ox,oy,_=g;spanx,spany,firstx,firsty,stepx,stepy=mapping;values=[]
 for y in range(13):
  for x in range(17):
   sx=(firstx+(x*cw-ox)*stepx)/spanx*16;sy=(firsty+(y*ch-oy)*stepy)/spany*12
   ix=min(16,math.floor(sx));iy=min(12,math.floor(sy));tx=sx-ix;ty=sy-iy
   if x in (0,16) or y in (0,12) or not(0<=ix<16 and 0<=iy<12):
    a=extend(m,ix,iy)*(1-tx)+extend(m,ix+1,iy)*tx
    b=extend(m,ix,iy+1)*(1-tx)+extend(m,ix+1,iy+1)*tx;v=a*(1-ty)+b*ty
   else:
    v=hermite([hermite([extend(m,ix+i-1,iy+j-1) for i in range(4)],tx) for j in range(4)],ty)
   values.append(min(8191/1024,max(1,v)))
 return struct.unpack('<221f',struct.pack('<221f',*values))

cases=[('full',4608,3456,[4607,3455,0,0,2,2]),
 ('crop',4608,2592,[5000,4000,100,500,2,2]),
 ('front_size',2304,1728,[2303,1727,0,0,2,2]),
 ('asymmetric_crop',1928,1088,[2303,1727,100.5,200.25,2,2]),
 ('wide_size',1632,1224,[1631,1223,0,0,2,2]),
 ('flip',2104,1560,[2103,1559,2103,1559,-2,-2])]
results=[]
for name,w,h,mapping in cases:
 out=P/(name+'-resampled.bin');q=subprocess.run([str(P/'resample-tables'),str(P/'factory-input.bin'),str(out),str(w),str(h),*[str(v) for v in mapping]],capture_output=True)
 assert not q.returncode,q.stderr.decode();g=geometry(w,h);actual=out.read_bytes();assert len(actual)==len(tables)*5304
 maximum=0.;word_errors=0
 for i,table in enumerate(rounded):
  expected=[predict(table[c*221:(c+1)*221],g,mapping) for c in range(4)]
  floats=struct.unpack_from('<884f',actual,i*5304)
  maximum=max(maximum,max(abs(a-b) for a,b in zip(floats,[v for c in expected for v in c])))
  codes=[[math.floor(v*1024+.5) for v in c] for c in expected]
  words=[r+gr*8192 for r,gr in zip(codes[0],codes[1])]+[b+gb*8192 for b,gb in zip(codes[3],codes[2])]
  word_errors+=sum(a!=b for a,b in zip(words,struct.unpack_from('<442I',actual,i*5304+3536)))
 assert maximum<1e-6 and not word_errors
 results.append(dict(case=name,output_size=[w,h],grid=g,tables=len(tables),max_float_error=maximum,packed_word_errors=word_errors))
report=dict(stage=319,cases=results,passed=True,actual_sensor_mode_mapping_not_claimed=True,individual_values_applied=False,phone_changed=False)
(HERE/'factory-resample-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
