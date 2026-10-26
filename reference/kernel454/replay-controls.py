"""Compare actual cached AArch64 sensor callbacks with the candidate C packer."""
from pathlib import Path
import hashlib,importlib.util,json,random,struct,subprocess,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
storage.mount.mounted_build()
P=Path('/mnt/e/edk2-samurai-out/kernel454');P.mkdir(mode=0o700,exist_ok=True)
sys.path.insert(0,'/home/cy122/.local/lib/python3.14/site-packages')
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_CPACR_EL1,UC_ARM64_REG_PC
binary=P.parent/'kernel115/vendor-camera-modules/com.qti.sensor.ov02a1b.so'
raw=binary.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01'
mu=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
mu.mem_map(0,0x4000);mu.mem_map(0x1000000,0x20000)
phoff=struct.unpack_from('<Q',raw,32)[0];phsize,phcount=struct.unpack_from('<HH',raw,54)
for i in range(phcount):
 kind,flags,offset,va,pa,size,mem,align=struct.unpack_from('<IIQQQQQQ',raw,phoff+i*phsize)
 if kind==1:assert va+mem<=0x4000;mu.mem_write(va,raw[offset:offset+size])
mu.reg_write(UC_ARM64_REG_SP,0x101f000);mu.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20)
output,input_address,stop=0x1000000,0x1004000,0x101e000
def hook(uc,address,size,unused):
 word=struct.unpack('<I',uc.mem_read(address,4))[0]
 assert word&0xfc000000!=0x94000000,'No external calls may substitute for native callback instructions'
mu.hook_add(UC_HOOK_CODE,hook)
def call(address,first,second):
 mu.reg_write(UC_ARM64_REG_X0,first);mu.reg_write(UC_ARM64_REG_X1,second);mu.reg_write(UC_ARM64_REG_X30,stop)
 mu.emu_start(address,stop,count=5000);assert mu.reg_read(UC_ARM64_REG_PC)==stop
 return mu.reg_read(UC_ARM64_REG_X0)
call(0x1250,output,0)
calculate,fill=struct.unpack('<QQ',mu.mem_read(output+16,16));assert (calculate,fill)==(0x1018,0x1170)
assert call(fill,0,input_address)==call(fill,output,0)==0
assert call(calculate,0,input_address)==call(calculate,output,0)==0
f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
gain_rng=random.Random(455)
gain_inputs=[.5,1,1.0625,1.9,2,2.01,3.99,4,4.1,7.99,8,8.01,15.49,15.5,16]+[gain_rng.uniform(1,16) for _ in range(120)]
gain_vectors=[]
for value in gain_inputs:
 gain=f32(value);mu.mem_write(output,bytes(512));mu.mem_write(input_address,struct.pack('<fI',gain,987)+bytes(120))
 assert call(calculate,output,input_address)==1
 encoded=mu.mem_read(output,68)
 scale=16 if gain<=2 else 8 if gain<=4 else 4 if gain<=8 else 2
 quantized=max(1.,min(15.5,int(gain*scale)/scale));register=int(quantized*16)
 analog,reg,digital,digreg=struct.unpack_from('<fIfI',encoded)
 residual,lines=struct.unpack_from('<fI',encoded,48)
 assert (analog,reg,digital,digreg,lines)==(register/16,register,1.,256,987),(gain,analog,reg,digital,digreg,lines,register)
 assert residual==f32(gain/analog)
 gain_vectors.append(dict(real_gain=gain,register=reg,analog=analog,isp=residual))
(P/'native-gain-vectors-private.json').write_text(json.dumps(gain_vectors,indent=2)+'\n')
cases=[]
for frame in [1224,1225,1738,4096,32768,65535]:
 for exposure in [1,2,255,256,min(1024,frame),frame-3,frame]:
  for gain in [16,31,32,63,64,127,128,247,248]:cases.append((exposure,frame,gain))
rng=random.Random(454)
for _ in range(120):
 frame=rng.randint(1224,65535);cases.append((rng.randint(1,frame),frame,rng.randint(16,248)))
bad=[(0,1738,16),(65536,1738,16),(1,1223,16),(1,65536,16),(1,1738,15),(1,1738,249)]
compiler=['cc','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(HERE),str(HERE/'control-contract.c'),'-o',str(P/'control-contract')]
built=subprocess.run(compiler,capture_output=True);(P/'control-c-build-private.log').write_bytes(built.stdout+built.stderr);assert not built.returncode
input_text=''.join('%d %d %d\n'%row for row in cases+bad)
run=subprocess.run([str(P/'control-contract')],input=input_text.encode(),capture_output=True);(P/'control-c-run-private.log').write_bytes(run.stderr);assert not run.returncode
lines=run.stdout.decode().splitlines();assert len(lines)==len(cases)+len(bad)
actual=[]
for values,line in zip(cases,lines):
 exposure,frame,gain=values
 mu.mem_write(output,bytes(0x3000));mu.mem_write(input_address,bytes(128))
 mu.mem_write(input_address+8,struct.pack('<4I',gain,256,exposure,frame))
 assert call(fill,output,input_address)==1
 data=mu.mem_read(output,8+7*40);assert struct.unpack_from('<I',data)[0]==7
 regs=[]
 for i in range(7):
  address,at,dt,op,delay=struct.unpack_from('<5I',data,8+i*40);value=struct.unpack_from('<I',data,8+i*40+24)[0]
  assert at==dt==1 and op==delay==0 and address<=255 and value<=255
  regs.extend([address,value])
 result,encoded=line.split();assert int(result)==0 and bytes.fromhex(encoded)==bytes(regs),(values,encoded,regs)
 actual.append(dict(input=values,registers=regs))
for line in lines[len(cases):]:
 result,encoded=line.split();assert int(result)==-1 and bytes.fromhex(encoded)==bytes([0xa5])*14
(P/'native-control-vectors-private.json').write_text(json.dumps(actual,indent=2)+'\n')
report=dict(stage=454,actual_aarch64_callbacks_executed=True,sensor_library_sha256=hashlib.sha256(raw).hexdigest(),calculate_callback=hex(calculate),fill_callback=hex(fill),null_pointer_rejections=4,native_gain_quantization_vectors=len(gain_vectors),native_fill_and_actual_c_vectors_equal=len(cases),candidate_invalid_range_rejections=len(bad)+1,asan_ubsan=True,hardware_or_pm_or_driver_tested=False,frame_base_in_register_units=1224,mode_specific_exposure_margin_not_yet_selected=True,code_sha256=hashlib.sha256((HERE/'ov02a1b_control.h').read_bytes()).hexdigest(),no_phone_sdk=True,passed=True)
(HERE/'control-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
