"""Compare normalized Gamma interpolation with the complete retained HAL function."""
from pathlib import Path
import itertools,json,shutil,struct,subprocess,sys
import host
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('fragment350',Path(__file__).with_name('check-hal-fragment.py'))
fragment=module_from_spec(spec);spec.loader.exec_module(fragment)
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
OBJECT,STACK,STOP,OUT=fragment.OBJECT,fragment.STACK,fragment.STOP,fragment.OUT

class Interpolation(fragment.GammaFragment):
 def __init__(self,source):
  super().__init__(source);self.begin=0x483c58;self.end=0x4841dc;self.memcpy_calls=0
 def _step(self,uc,pc,size,user):
  if pc==0x5b1290:
   dest=uc.reg_read(UC_ARM64_REG_X0);source=uc.reg_read(UC_ARM64_REG_X1);length=uc.reg_read(UC_ARM64_REG_X2)
   assert length==1028
   uc.mem_write(dest,bytes(uc.mem_read(source,length)));self.memcpy_calls+=1;self.instructions+=1
   uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  return super()._step(uc,pc,size,user)
 def evaluate(self,a,b,weight,same_pointer=False):
  for address,channels in [(OBJECT,a),(OBJECT+0x4000,b)]:
   self.write(address,'<IIQ',len(channels),0,address+0x100)
   self.uc.mem_write(address+0x100,b''.join(struct.pack('<I257f',kind,*curve) for kind,curve in channels))
  self.write(OBJECT+0x8000,'<IIQ',0,0,OUT);self.uc.mem_write(OUT,b'\xa5'*3096)
  self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xf000);self.uc.reg_write(UC_ARM64_REG_LR,STOP)
  self.uc.reg_write(UC_ARM64_REG_X0,OBJECT);self.uc.reg_write(UC_ARM64_REG_X1,OBJECT if same_pointer else OBJECT+0x4000)
  self.uc.reg_write(UC_ARM64_REG_X2,OBJECT+0x8000);self.uc.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',weight))[0])
  self.uc.emu_start(self.begin,STOP,timeout=2000000,count=100000)
  assert self.uc.reg_read(UC_ARM64_REG_PC)==STOP
  valid=self.uc.reg_read(UC_ARM64_REG_W0);self.calls+=1
  assert self.read(OBJECT+0x8000,'<I')[0]==3
  assert [self.read(OUT+i*1032,'<I')[0] for i in range(3)]==[0,1,2]
  return valid,[bytes(self.uc.mem_read(OUT+i*1032+4,1028)) for i in range(3)]

def main():
 raw=(P/'oracle-input-private.bin').read_bytes()
 curves=[list(struct.unpack_from('<257f',raw,i*1028)) for i in range(75)]
 assert len({struct.pack('<257f',*c) for c in curves})==75
 cases=[]
 for index,curve in enumerate(curves):
  for weight in [0.,.125,.5,.875,1.]:
   cases.append(dict(a=[(3,curve)],b=[(3,curves[(index+17)%75])],weight=weight,kind='factory-common'))
 permutations=list(itertools.permutations(range(3)))
 for i,order in enumerate(permutations):
  a=[(c,curves[c*7+i]) for c in order];b=[(c,curves[c*11+13+i]) for c in permutations[(i+1)%6]]
  for weight in [0.,.37,1.]:cases.append(dict(a=a,b=b,weight=weight,kind='three-channel-permutation'))
  for reverse in [False,True]:
   cases.append(dict(a=[(3,curves[50+i])] if reverse else a,b=b if reverse else [(3,curves[50+i])],weight=.63,kind='mixed-common-rgb'))
 for weight in [0.,.37,1.]:cases.append(dict(a=[(3,curves[0])],b=[(3,curves[0])],weight=weight,same_pointer=True,kind='pointer-identity'))
 for weight in [-.1,1.1,float('nan'),float('inf')]:cases.append(dict(a=[(3,curves[0])],b=[(3,curves[1])],weight=weight,kind='invalid-weight'))
 engine=Interpolation(P.parent/'kernel281/camera.qcom.so-private');inputs=bytearray();expected=bytearray()
 def normalized(channels):return [channels[0][1]]*3 if len(channels)==1 else [dict(channels)[c] for c in range(3)]
 categories={}
 for case in cases:
  valid,tables=engine.evaluate(case['a'],case['b'],case['weight'],case.get('same_pointer',False))
  assert valid==(case['kind']!='invalid-weight')
  for first,second,table in zip(normalized(case['a']),normalized(case['b']),tables):
   inputs+=struct.pack('<515f',case['weight'],*first,*second)
   expected+=struct.pack('<I',valid)+(table if valid else struct.pack('<257f',*([-99.]*257)))
  categories[case['kind']]=categories.get(case['kind'],0)+1
 # The portable API deliberately rejects non-finite/out-of-domain curves even
 # in endpoint copies; these are separate from valid HAL-domain comparisons.
 for bad in [-1.,1024.1,float('nan'),float('inf')]:
  first=curves[0].copy();first[128]=bad;inputs+=struct.pack('<515f',.5,*first,*curves[1])
  expected+=struct.pack('<I257f',0,*([-99.]*257))
 (P/'interpolation-input-private.bin').write_bytes(inputs);(P/'interpolation-expected-private.bin').write_bytes(expected)
 work=SDK/'private/camss350-math';work.mkdir(exist_ok=True)
 for source in [HERE/'gamma-interpolation-runner.cpp',HERE/'libipa/gamma_interpolation.h',HERE/'libipa/gamma_segments.h',HERE.parent/'kernel341/libipa/tuning_interpolation.h',P/'interpolation-input-private.bin']:
  shutil.copyfile(source,work/source.name)
 rows=[]
 for arch in ['host','aarch64']:
  command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),'-I'+str(HERE.parent/'kernel341/libipa'),str(HERE/'gamma-interpolation-runner.cpp'),'-o',str(P/'interpolation-host')] if arch=='host' else ['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss350-math/gamma-interpolation-runner.cpp','-o','/private/camss350-math/interpolation-aarch64']
  q=subprocess.run(command,capture_output=True);(P/('interpolation-'+arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
  output=P/('interpolation-'+arch+'-private.bin')
  command=[str(P/'interpolation-host'),str(P/'interpolation-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(SDK),'/private/camss350-math/interpolation-aarch64','/private/camss350-math/interpolation-input-private.bin','/private/camss350-math/interpolation-output-private.bin']
  subprocess.run(command,check=True,timeout=20)
  if arch=='aarch64':shutil.copyfile(work/'interpolation-output-private.bin',output)
  actual=output.read_bytes();assert len(actual)==len(expected)
  different=sum(a!=b for a,b in zip(actual,expected));rows.append(dict(architecture=arch,records=len(actual)//1032,compared_bytes=len(actual),differing_bytes=different,passed=not different))
 report=dict(stage=350,complete_original_hal_function=['0x483c58','0x4841dc'],source_retained_from281=True,
  hal_calls=engine.calls,categories=categories,hal_instructions=engine.instructions,memcpy_stub_calls=engine.memcpy_calls,
  math_stub_calls=0,system_calls_rejected=True,original_binary_runtime_channel_stride=1032,serialized_tuning_stride=1040,
  canonical_hal_channel_order=['G','B','R'],portable_api_operates_on_normalized_single_channel=True,
  validation_rejects_invalid_curves_separately=True,portable_weight_domain=[0,1],
  original_near_outside_endpoint_tolerance_not_adopted=True,architectures=rows,
  trigger_tree_selection_and_hal_runtime_enable_not_verified=True,phone_changed=False,passed=all(r['passed'] for r in rows))
 (HERE/'gamma-interpolation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
