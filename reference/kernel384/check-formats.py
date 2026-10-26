from pathlib import Path
import importlib.util,json,struct,subprocess,sys
HERE=Path(__file__).resolve().parent
from engine384 import prepare
s=importlib.util.spec_from_file_location('sl383',HERE.parent/'kernel383/trace-striping.py');sl=importlib.util.module_from_spec(s);s.loader.exec_module(sl)
P=Path('/mnt/e/edk2-samurai-out/kernel384');rows=[]
cases=[(640,480,8,1,True),(1920,1080,9,2,True),(4608,3456,8,1,True),(8192,480,9,2,True),
 (128,8192,8,1,False),(8192,8192,9,2,False)]
q=subprocess.run([str(P/'serializer-model/probe')],input=b''.join(struct.pack('<5I',*r) for r in cases),capture_output=True);assert not q.returncode,q.stderr.decode();pos=0
for w,h,p,c,swap in cases:
 n=struct.unpack_from('<I',q.stdout,pos)[0];pos+=4;native=q.stdout[pos:pos+n];pos+=n
 a,_,_,info=sl.execute(w,h,p,c,dirty=0xa5,uv_swap=swap);b,_,_,_=sl.execute(w,h,p,c,dirty=0x5a,uv_swap=swap)
 canonical=bytes(x&~(x^y)&255 for x,y in zip(a,b))
 for padded in [False,True]:
  stride=w+16 if padded else w;slice_height=h+8 if padded else h
  original=prepare(a,w,h,p,c,swap,stride,slice_height);normalized=prepare(canonical,w,h,p,c,swap,stride,slice_height)
  actual=prepare(native,w,h,p,c,swap,stride,slice_height);assert original==normalized==actual,(w,h,p,c,swap,padded)
  rows.append(dict(width=w,height=h,output_port=p,max_cores=c,uv_swap=swap,stride=stride,slice_height=slice_height,
    whole_original_cdm_bytes_compared=len(original[1]),job_equal=True,different_cdm_bytes=0,passed=True))
  print(json.dumps(rows[-1]),flush=True)
 slug=f'{w}x{h}-p{p}-c{c}-swap{int(swap)}'
 for name,data in [('native-stripe',native),('canonical-stripe',canonical)]: (P/(slug+'-'+name+'-private.bin')).write_bytes(data)
assert pos==len(q.stdout)
report=dict(stage=384,additional_original_hal_full_algorithm_cases=len(cases),tests=rows,nv21_configuration_and_padded_io_original_firmware_preparation=True,
 hardware_execution=False,no_pixel_output_claim=True,passed=True)
(HERE/'formats-validation.json').write_text(json.dumps(report,indent=2)+'\n')
