"""Exercise the real IPA4 module, typed DS4 upload, and final-receipt history."""
from pathlib import Path
import hashlib,json,shutil,struct,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss431-contract'
assert json.loads((HERE/'build-validation.json').read_text())['passed']
storage.candidate();work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
source=(HERE.parent/'kernel424/ipa-contract.cpp').read_text()
source=source.replace('assert(!configured);','assert(!configured);assert(configuration.pd10==(std::string(argv[3])=="factory"));')
needle='ipa->parametersApplied(1,0,0);';assert source.count(needle)==1
source=source.replace(needle,'''{
  auto *p=static_cast<const char*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,pfd.get(),0));assert(p!=MAP_FAILED);
  std::ofstream f(std::string(argv[4])+".ife",std::ios::binary);f.write(p,bytes);assert(f.good());munmap(const_cast<char*>(p),capacity);
 }ipa->parametersApplied(1,0,0);''')
(HERE/'ipa-contract.cpp').write_text(source);(work/'contract.cpp').write_text(source)
for mode in ['factory','bypass']:shutil.copyfile(P/'factory-s5kgw1-private.yaml' if mode=='factory' else P.parent/'kernel423/bypass-s5kgw1-private.yaml',work/(mode+'.yaml'))
with storage.sdk_candidate():
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 q=subprocess.run(['chroot',str(storage.SDK),*env,T+'/output/src/apps/ipa-verify/ipa_verify',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True);(P/'signature-check.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include',W+'/contract.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o',W+'/contract'],capture_output=True)
 (P/'ipa-contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2200:]
 rows=[]
 for mode in ['bypass','factory']:
  q=subprocess.run(['chroot',str(storage.SDK),*env,W+'/contract',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/'+mode+'.yaml',mode,W+'/'+mode+'.bin'],capture_output=True,timeout=40)
  (P/(mode+'-ipa-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(mode,q.stderr.decode()[-2500:])
  raw=(work/(mode+'.bin.ife')).read_bytes();version,size=struct.unpack_from('<2I',raw);assert version==1 and len(raw)==size+8
  at=8;blocks=[]
  while at<len(raw):
   kind,flags,n=struct.unpack_from('<HHI',raw,at);assert n>=8 and n%8==0 and at+n<=len(raw)
   if kind==8:blocks.append(raw[at:at+n])
   at+=n
  assert len(blocks)==(1 if mode=='factory' else 0)
  if blocks:assert blocks[0]==(P.parent/'kernel428/params-s5kgw1-private.bin').read_bytes()[-16:]
  shutil.copyfile(work/(mode+'.bin.ife'),P/(mode+'-ife-parameters-private.bin'))
  if mode=='factory':shutil.copyfile(work/(mode+'.bin'),P/'factory-ipa-packet-private.bin')
  rows.append(dict(mode=mode,actual_ipa=True,ds4_blocks=len(blocks),packet_bytes=len(raw),passed=True))
r=dict(stage=431,private_ipa_version=4,signature_verified=True,aarch64_contract_werror=True,real_ipa_module_methods=True,
 stock_ds4_payload_identical_to_validated428=True,typed_coarse_capability_matches_profile=True,
 missing_lux_hold_busy_failure_stale_receipt_stop_and_restart_history_checks_passed=True,
 numerical_history_only_advances_on_successful_final_receipt=True,synthetic_statistics_not_hardware=True,modes=rows,passed=True)
(HERE/'ipa-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
