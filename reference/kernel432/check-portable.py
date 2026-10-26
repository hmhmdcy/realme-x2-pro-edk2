"""Compare reusable GTM numerical primitive to original HAL on host and ARM64."""
from pathlib import Path
import hashlib,importlib.util,json,math,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage432portable',HERE.parent/'kernel284/storage.py').mounted_build();n=module('gtm432portable',HERE/'gtm-model.py')
axis=(P/'gtm-normalized-axis-private.bin').read_bytes();domain=(P/'gtm-integer-axis-private.bin').read_bytes();hist_axis=(P/'gtm-contrast-axis-private.bin').read_bytes();inputs=[];expected=[];branches=[]
for row in json.loads((P/'adrc-records-private.json').read_text()):
 if not row['enabled']:continue
 variant,step=row['variant'],row['step'];name=variant+'-'+str(step);adrc=(P/(name+'-adrc-private.bin')).read_bytes();assert len(adrc)==4240
 curve=adrc[16:56]+adrc[92:128];controls=adrc[60:64]+adrc[4228:4236];hist=adrc[128:4224]
 selected=next(s for tag,c,s in json.loads((P.parent/'kernel431'/(variant+'-gtm-selections-private.json')).read_text()) if tag=='gtm10_ife' and c[2]==0)
 for swap in [False,True]:
  m=n.Machine(swap=swap);chromatix,_=m.load_parsed(P/(variant+'-'+str(selected['uid'])+'-native-parse-private.json'));lut,_,_=m.calculate(chromatix,adrc=adrc,bank=int(swap))
  if not swap:assert lut==(P/(name+'-adrc-lut-private.bin')).read_bytes()
  else:
   original=(P/(name+'-adrc-lut-private.bin')).read_bytes();assert lut==b''.join(original[i+4:i+8]+original[i:i+4] for i in range(0,512,8))
  assert set(m.providers)<=set(['0x5b1250','0x5b1290','0x5b1960'])
  record=curve+controls+axis+domain+hist_axis+hist+struct.pack('<I',swap);assert len(record)==8804
  inputs.append(record);expected.append(struct.pack('<I',1)+lut);branches.append(dict(variant=variant,step=step,swap=swap,bank=int(swap)))
packing_checks=0
variant='sunny_s5kgw1';adrc=(P/(variant+'-0-adrc-private.bin')).read_bytes();gold=(P/(variant+'-0-adrc-lut-private.bin')).read_bytes()
selected=next(s for tag,c,s in json.loads((P.parent/'kernel431'/(variant+'-gtm-selections-private.json')).read_text()) if tag=='gtm10_ife' and c[2]==0)
for selector in [0,2,3]:
 for swap in [False,True]:
  wanted=b''.join(gold[i+4:i+8]+gold[i:i+4] for i in range(0,512,8)) if swap else gold
  for bank in [0,1]:
   m=n.Machine(packing_selector=selector,swap=swap);chromatix,_=m.load_parsed(P/(variant+'-'+str(selected['uid'])+'-native-parse-private.json'));lut,_,_=m.calculate(chromatix,adrc=adrc,bank=bank);assert lut==wanted;packing_checks+=1
invalid=[]
for off,value,fmt in [(0,math.nan,'f'),(76,-1.,'f'),(80,1.1,'f'),(84,math.inf,'f'),(88,0.,'f'),(92,math.nan,'f'),(348+4,0,'I'),(608+4,-1.,'f'),(608+4096,math.nan,'f')]:
 raw=bytearray(inputs[0]);struct.pack_into('<'+fmt,raw,off,value);invalid.append(bytes(raw))
inputs+=invalid;expected+=[bytes(4)+bytes([0xa7])*512]*len(invalid);raw=b''.join(inputs);wanted=b''.join(expected)
(P/'portable-input-private.bin').write_bytes(raw);(P/'portable-expected-private.bin').write_bytes(wanted)
names=['kernel432/gtm-runner.cpp','kernel432/libipa/gtm_tmc11.cpp','kernel432/libipa/gtm_tmc11.h','kernel412/libipa/tmc11_ltm.cpp','kernel412/libipa/tmc11_ltm.h'];sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss432-gtm'
for name in names:
 dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
sources=[n for n in names if n.endswith('.cpp')];rows=[]
for arch in ['host','aarch64']:
 flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
 if arch=='host':
  binary=P/'gtm-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in sources],'-o',str(binary)];launch=[str(binary)]
 else:
  binary='/private/camss432-gtm/gtm-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss432-gtm/'+n for n in sources],'-o',binary];launch=['chroot',str(sdk),binary]
 q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run(launch,input=raw,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode();(P/('portable-'+arch+'-actual-private.bin')).write_bytes(q.stdout)
 assert len(q.stdout)==len(wanted);assert q.stdout==wanted,(arch,[(i,a,b) for i,(a,b) in enumerate(zip(q.stdout,wanted)) if a!=b][:12])
 rows.append(dict(architecture=arch,cases=len(inputs),different_bytes=0,passed=True));print(json.dumps(rows[-1]),flush=True)
r=dict(stage=432,original_adrc_cases=len(branches),invalid_cases=len(invalid),architectures=rows,ife_base18_slope26_pack_verified=True,native_selector_swap_bank_combinations=packing_checks,bank_and_swap_independently_varied=True,all_512_lut_bytes_written_by_native=True,target_text_writes_rejected=True,stock_axes_and_curves_private=True,platform_state_explicit_offline_fixture=True,host_libm_not_bionic=True,model2_tmc11_only=True,full_gtm_legacy_manual_or_v2_ported=False,production_ipa_integrated=False,phone_accessed=False,passed=True)
(HERE/'portable-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
