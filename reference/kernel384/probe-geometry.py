from pathlib import Path
import json,struct,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'kernel383'))
import engine_model
P=Path('/mnt/e/edk2-samurai-out/kernel383');OUT=P.parent/'kernel384'
rows=[];lines=[]
for w,h,p,c in [(640,480,8,1),(1920,1080,8,1),(4608,3456,8,1)]:
 slug=f'{w}x{h}-p{p}-c{c}'
 b=(P/(slug+'-canonical-stripe-private.bin')).read_bytes()
 count=struct.unpack_from('<H',b,428)[0]
 lines.append(slug)
 for off in [80,82,84,86,132,134,136,138,140,324,326,328,330,568,576,580,582,600,618,620]:
  fmt='<I' if off in [576,600] else '<H'
  lines.append(str(off)+': '+','.join(str(struct.unpack_from(fmt,b,2268+624*i+off)[0]) for i in range(count)))
(OUT/'all-stripes-fields-private.txt').write_text('\n'.join(lines)+'\n')
print('Retained all-stripe geometry comparison.')
