"""Execute maintained IO encoding and the stock topology-selection fragment."""
from pathlib import Path
import ast,hashlib,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
kernel=module('storage430',HERE.parent/'kernel284/storage.py').mounted_build().parent/'source354';d=kernel/'drivers/media/platform/qcom/camss'
boot=(d/'camss-icp-a5-boot.c').read_text();ipe=(d/'camss-icp-a5-ipe.c').read_text();state=json.loads((HERE/'source-state.json').read_text())
old=subprocess.check_output(['git','-C',str(kernel),'show',state['parent_commit']+':drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'],text=True)
def function(t,n):
 m=re.search(r'(?:static )?(?:int|bool|void)\s+'+n+r'\([^;]+?\n\{.*?^\}\n',t,re.S|re.M);assert m,n;return m[0]
tree=ast.parse((HERE.parent/'kernel425/check-io.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
body=(HERE.parent/'kernel425/io-cases.c').read_text().replace('old_encode_ipe_io(legacy, 1216, &io)','old_encode_ipe_io(legacy, 1216, &io, NULL)')
code=prefix+function(ipe,'camss_a5_ipe_pd10_quarter')+function(boot,'nv12_layout_valid')+function(boot,'encode_nv12_image')+function(boot,'camss_a5_ipe_encode_io')+function(old,'camss_a5_ipe_encode_io').replace('camss_a5_ipe_encode_io','old_encode_ipe_io')+body
(P/'io-model.c').write_text(code);cases=[(640,480,8,0,0),(640,480,8,0,8),(640,480,9,1,0),(1920,1080,8,0,0)];outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('io-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'io-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=b''.join(struct.pack('<5I',*c) for c in cases),capture_output=True);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1]
for i,c in enumerate(cases):
 b=outputs[0][i*2452:(i+1)*2452];assert len(b)==2452
 coarse=b[20:1236];legacy=b[1236:];assert struct.unpack_from('<I',coarse,1200)[0]==3 and struct.unpack_from('<I',legacy,1200)[0]==0
 if i==0:(P/'actual-c-config-private.bin').write_bytes(coarse)
n=module('native425',HERE.parent/'kernel425/native-model.py');m=n.Native();u=m.u;D=n.h.DATA
from unicorn.arm64_const import UC_ARM64_REG_X28,UC_ARM64_REG_SP,UC_ARM64_REG_PC
topology_rows=[]
for passes in [0,1,2,4]:
 for profile in [0,1,2,3]:
  obj=D+0x10000;prop=D+0x20000;config=D+0x30000;sp=n.h.STACK+0xe0000
  u.mem_write(obj+1624,struct.pack('<I',profile));u.mem_write(prop+116,struct.pack('<I',passes));u.mem_write(sp+136,struct.pack('<Q',prop));u.mem_write(sp+128,struct.pack('<Q',config));u.mem_write(config+1200,struct.pack('<I',0))
  u.reg_write(UC_ARM64_REG_X28,obj);u.reg_write(UC_ARM64_REG_SP,sp);u.emu_start(0x2cd8b0,0x2cd8d8,count=40);assert u.reg_read(UC_ARM64_REG_PC)==0x2cd8d8
  actual=m.read32(config+1200);assert actual==(3 if passes>=2 and profile==2 else 0);topology_rows.append(dict(passes=passes,profile=profile,topology=actual))
r=dict(stage=430,actual_maintained_io_functions=True,host_asan_ubsan=True,aarch64_static_qemu=True,cases=len(cases),legacy_null_coarse_unchanged=True,invalid_inputs_preserve_output=True,
 native_target_topology_selection_fragment_executed=True,native_cases=topology_rows,coarse_topology3_from_stock_pps_profile2_and_multipass=True,passed=True)
(HERE/'io-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='native_cases'},indent=2))
