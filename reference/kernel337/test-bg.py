from pathlib import Path
import json,random,shutil,struct,subprocess
import host
from stock_bg import StockBayer
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
engine=StockBayer(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');input=bytearray();expected=bytearray();counts={1:0,2:0,3:0};factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());randomizer=random.Random(337)
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
def config(n,bits,high,weights,normalization):return struct.pack('<II4I4f',n,bits,*high,*weights,normalization)
def add(mode,data,result):
 input.extend(struct.pack('<I',mode)+data);expected.extend(result);counts[mode]+=1
weights=[]
for source in factory.values():
 for root in source['roots']['Metering']:
  t=root['data']['lumaWeight'];base=t['weight'];reference=t['refGain']
  for current,enabled in [([1.,1.,1.],False),([2.25,1.,1.75],True),([0.,1.,1.],True)]:
   result=engine.weights(base,reference,current,enabled)
   add(1,struct.pack('<9fI',*base,*reference,*current,int(enabled)),struct.pack('<3f',*result));weights.append(result)
# Distinguish non-unit weight sums, integer green truncation and normalization.
weights=[(.2988,.5869,.1137),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.),(1.7,.5,2.25),*weights[:8]]
for bits in [8,10,12,14]:
 for pixels in [1,625,49152]:
  high=[(1<<bits)-1-i for i in range(4)]
  for base in weights:
   base=[f32(v) for v in base]
   for normalization in [1.,2.5]:
    engine.region_setup(pixels,bits,high,base,normalization)
    for mode in ['full','empty','mixed','random']:
     region_counts=[pixels]*4 if mode=='full' else [0]*4 if mode=='empty' else [pixels,pixels//2,max(0,pixels-1),0] if mode=='mixed' else [randomizer.randint(0,pixels) for _ in range(4)]
     sums=[randomizer.randint(0,n*h) for n,h in zip(region_counts,high)]
     result=engine.region(sums,region_counts)
     add(2,config(pixels,bits,high,base,normalization)+struct.pack('<4I4H',*sums,*region_counts),struct.pack('<2f',*result))
# End-to-end region processing, all-valid stride1 original16x16 pooling and lux.
grids=[]
for columns,rows in [(16,16),(32,16),(32,32),(64,48)]:
 for compensated in [False,True]:
  n=625;bits=14;high=[16383]*4;base=[f32(v) for v in ((.2988,.5869,.1137) if not compensated else (1.7,.5,2.25))]
  engine.region_setup(n,bits,high,base);data=bytearray(config(n,bits,high,base,1)+struct.pack('<II',columns,rows))
  for index in range(columns*rows):
   c=[randomizer.randint(0,n) for _ in range(4)];s=[randomizer.randint(0,v*16383) for v in c]
   engine.region(s,c,index);data.extend(struct.pack('<4I4H',*s,*c))
  grid=engine.pool(columns,rows);engine.configure(False,0,0,0);index,luma=engine.cells(200,[cell[0] for cell in grid])
  output=struct.pack('<512f2f',*[v for cell in grid for v in cell],index,luma);add(3,data,output)
  grids.append(dict(columns=columns,rows=rows,colour_compensated_weights=compensated,lux_luma=luma,lux_index=index))
(P/'bg-input-private.bin').write_bytes(input);(P/'bg-expected-private.bin').write_bytes(expected)
relative=Path('/private/camss337-luma');stage=SDK/str(relative).lstrip('/');(stage/'libipa').mkdir(parents=True,exist_ok=True)
for name in ['bg-runner.cpp','libipa/aec_bayer_luma.h','libipa/aec_bayer_luma.cpp','libipa/aec_lux.h','libipa/aec_lux.cpp']:shutil.copyfile(HERE/name,stage/name)
shutil.copyfile(P/'bg-input-private.bin',stage/'input-private.bin');results=[]
for architecture in ['host','aarch64']:
 flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror'];exe=P/('bg-'+architecture)
 cmd=['g++',*flags,str(HERE/'bg-runner.cpp'),str(HERE/'libipa/aec_bayer_luma.cpp'),str(HERE/'libipa/aec_lux.cpp'),'-o',str(exe)] if architecture=='host' else ['chroot',str(SDK),'g++',*flags,str(relative/'bg-runner.cpp'),str(relative/'libipa/aec_bayer_luma.cpp'),str(relative/'libipa/aec_lux.cpp'),'-o',str(relative/'bg-aarch64')]
 q=subprocess.run(cmd,capture_output=True);(P/(architecture+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(architecture+'-output-private.bin');cmd=[str(exe),str(P/'bg-input-private.bin'),str(output)] if architecture=='host' else ['chroot',str(SDK),str(relative/'bg-aarch64'),str(relative/'input-private.bin'),str(relative/'output-private.bin')]
 q=subprocess.run(cmd,capture_output=True);assert not q.returncode,(architecture,q.returncode,q.stderr.decode())
 if architecture=='aarch64':shutil.copyfile(stage/'output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected),(architecture,len(actual),len(expected));differences=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
 if differences:(P/(architecture+'-mismatches-private.json')).write_text(json.dumps([dict(byte=i,word_actual=struct.unpack_from('<f',actual,i//4*4)[0],word_expected=struct.unpack_from('<f',expected,i//4*4)[0]) for i in differences[:30]],indent=2))
 row=dict(architecture=architecture,records=sum(counts.values()),compared_bytes=len(actual),differing_bytes=len(differences));results.append(row);assert not differences,row
report=dict(stage=337,architectures=results,case_modes=counts,pooled_grids=grids,original_region_full_function=True,original_weight_and_pooling_fragments=True,full_original_lux_wrapper=True,
 raw_rgb_without_explicit_saturated_sums=True,green_sum_integer_truncation_preserved=True,subsampling_stride=1,default_compiler_fma_supported=True,current_32_by_24_grid_compatible=False,
 current_camera_bayer_input_bits=14,current_camera_statistics_changed=False,ipa_integrated=False,phone_changed=False,passed=True)
(HERE/'bayer-luma-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
