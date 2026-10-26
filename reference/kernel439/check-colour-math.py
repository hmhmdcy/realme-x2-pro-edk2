"""Compare floating CCM13 with original target instructions and IPE encoder."""
from pathlib import Path
import hashlib, importlib.util, json, math, random, shutil, struct, subprocess, sys
import host, storage
from unicorn.arm64_const import UC_ARM64_REG_S0
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
spec=importlib.util.spec_from_file_location('colour396',HERE.parent/'kernel396/colour-model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
oracle=m.Colour();inputs=bytearray();expected=bytearray();counts={}
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
round_away=lambda x:math.floor(x+.5) if x>=0 else math.ceil(x-.5)
def add(a,b,weight,q,kind):
 a=list(map(f32,a));b=list(map(f32,b));weight=f32(weight)
 inputs.extend(struct.pack('<25fI',*a,*b,weight,q))
 base=m.DATA+0x8000
 oracle.u.mem_write(base,struct.pack('<12f',*a));oracle.u.mem_write(base+0x100,struct.pack('<12f',*b));oracle.u.mem_write(base+0x200,bytes([0xa7])*64)
 oracle.u.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',weight))[0])
 assert oracle.call(0x47ebf0,base,base+0x100,base+0x200,phase='original-cc13-do-interpolation')==1
 region=bytes(oracle.u.mem_read(base+0x200,48));assert bytes(oracle.u.mem_read(base+0x230,16))==bytes([0xa7])*16
 values=struct.unpack('<12f',region);scale=1<<(7+q)
 coefficients=[round_away(f32(v*scale)) for v in values[:9]];offsets=list(map(round_away,values[9:]))
 assert all(-2048<=v<=2047 for v in coefficients) and all(-4096<=v<=4095 for v in offsets)
 command=oracle.command(oracle.calculate(values[:9],values[9:],q))
 expected.extend(region+struct.pack('<12hI',*coefficients,*offsets,q)+struct.pack('<9f',*(v/scale for v in coefficients))+command)
 counts[kind]=counts.get(kind,0)+1
def region(leaf):return leaf['matrix']+leaf['offsets']
for path in sorted((P.parent/'kernel351').glob('*-cc13_ipe-trees-private.json')):
 for root in json.loads(path.read_text()):
  for leaf in m.leaves(root['core']):add(region(leaf),region(leaf),0,root['qfactor'],'all-factory-leaves')
front=next(x for x in json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())['sunny_imx471'] if x['sensor_mode_index']==1 and x['usecase']=='Preview')['modules']['cc13_ipe']
front_leaves=list(m.leaves(front['core']));assert len(front_leaves)==28 and front['enabled']==1
for a,b in zip(front_leaves,front_leaves[1:]):
 for w in [0.,.000001,.125,.25,.5,.75,.875,.999999,1.]:add(region(a),region(b),w,front['qfactor'],'front-interpolation')
for q in range(4):
 scale=1<<(7+q)
 for v in [-2048,-1024,-1.5,-.5,0.,.5,1.5,1023,2047]:
  a=[v/scale]*9+[-4096.,4095.,-.5];add(a,a,.5,q,'quantization-boundaries')
 a=[1.1,-.125,.02,-.5,.75,.0625,.375,-.25,.875]+[-4095.5,1024.25,-.75]
 b=[-.875,.25,-.375,.5,-.75,-.0625,-.25,.125,-1.]+[4094.5,-1025.75,.5]
 for w in [0.,.125,.5,.875,1.]:add(a,b,w,q,'fractional-offset-interpolation')
rng=random.Random(439)
for _ in range(128):
 q=rng.randrange(4);scale=1<<(7+q)
 a=[rng.uniform(-1900,1900)/scale for _ in range(9)]+[rng.uniform(-4000,4000) for _ in range(3)]
 b=[rng.uniform(-1900,1900)/scale for _ in range(9)]+[rng.uniform(-4000,4000) for _ in range(3)]
 add(a,b,rng.random(),q,'signed-random-interpolation')
assert counts['all-factory-leaves']==737
(P/'ccm-input-private.bin').write_bytes(inputs);(P/'ccm-expected-private.bin').write_bytes(expected)
flags=['-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror'];include=P.parent/'kernel396/include'
q=subprocess.run(['gcc','-std=c11','-O2','-I'+str(include),'-c',str(HERE.parent/'kernel396/colour-codec.c'),'-o',str(P/'colour-codec.o')],capture_output=True);assert not q.returncode,q.stderr.decode()
results=[]
stage=storage.SDK/'private-k439-math';stage.mkdir(exist_ok=True);(stage/'libipa').mkdir(exist_ok=True)
for rel in ['ccm-runner.cpp','libipa/colour_correction.cpp','libipa/colour_correction.h','libipa/tuning_interpolation.h']:shutil.copyfile(HERE/rel,stage/rel)
shutil.copytree(include,stage/'include',dirs_exist_ok=True);shutil.copyfile(HERE.parent/'kernel396/colour-codec.c',stage/'colour-codec.c');shutil.copyfile(P/'ccm-input-private.bin',stage/'input.bin')
for arch in ['host','aarch64']:
 if arch=='host':
  cmd=['g++',*flags,'-fsanitize=undefined','-I'+str(HERE),'-I'+str(include),str(HERE/'ccm-runner.cpp'),str(HERE/'libipa/colour_correction.cpp'),str(P/'colour-codec.o'),'-o',str(P/'ccm-host')]
 else:
  q=subprocess.run(['chroot',str(storage.SDK),'gcc','-std=c11','-O2','-I/private-k439-math/include','-c','/private-k439-math/colour-codec.c','-o','/private-k439-math/colour-codec.o'],capture_output=True);assert not q.returncode,q.stderr.decode()
  cmd=['chroot',str(storage.SDK),'g++',*flags,'-I/private-k439-math/include','/private-k439-math/ccm-runner.cpp','/private-k439-math/libipa/colour_correction.cpp','/private-k439-math/colour-codec.o','-o','/private-k439-math/ccm-arm64']
 q=subprocess.run(cmd,capture_output=True);(P/(arch+'-math-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 cmd=[str(P/'ccm-host'),str(P/'ccm-input-private.bin'),str(P/'ccm-host-output-private.bin')] if arch=='host' else ['chroot',str(storage.SDK),'/private-k439-math/ccm-arm64','/private-k439-math/input.bin','/private-k439-math/output.bin']
 q=subprocess.run(cmd,capture_output=True);assert not q.returncode,(arch,q.stderr.decode())
 actual=(P/'ccm-host-output-private.bin' if arch=='host' else stage/'output.bin').read_bytes()
 if actual!=expected:
  first=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b);raise AssertionError((arch,'first mismatch byte',first,'case',first//156,'offset',first%156))
 results.append({'architecture':arch,'cases':sum(counts.values()),'compared_bytes':len(actual),'different_bytes':0})
# Preserve the established IFE struct and exact integer-offset arithmetic.
cmd=['g++',*flags,'-I'+str(HERE),str(HERE.parent/'kernel333/ccm-runner.cpp'),str(HERE/'libipa/colour_correction.cpp'),'-o',str(P/'ife-legacy')]
q=subprocess.run(cmd,capture_output=True);assert not q.returncode,q.stderr.decode()
subprocess.run([str(P/'ife-legacy'),str(P.parent/'kernel333/math-input-private.bin'),str(P/'ife-legacy-output-private.bin')],check=True)
assert (P/'ife-legacy-output-private.bin').read_bytes()==(P.parent/'kernel333/stock-expected-private.bin').read_bytes()
report={'stage':439,'passed':True,'cases':counts,'front_regions':len(front_leaves),'architectures':results,'target_hal_interpolation_entry':'0x47ebf0','complete_original_cc13_calculation_and_cdm_executed':True,'float_offsets_retained_through_interpolation':True,'ipe_offset_signed_bits':13,'ife_offset_signed_bits':11,'invalid_inputs_leave_outputs_unchanged':True,'legacy_ife_cached_oracle_byte_identical':True,'host_ubsan':True,'phone_changed':False}
(HERE/'colour-math-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
