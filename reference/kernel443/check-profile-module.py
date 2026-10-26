"""Check the actual unchanged IPA5's mode capability and typed DS4 upload."""
from pathlib import Path
import hashlib,json,shutil,struct,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'profile-export-validation.json').read_text())['passed']
source=(HERE.parent/'kernel424/ipa-contract.cpp').read_text().split(' constexpr unsigned capacity=262144;')[0]
source=source.replace('info.outputSize=Size(4608,3456);','info.outputSize=Size(4608,std::stoul(argv[3]));')
source+='''
 constexpr unsigned capacity=262144;
 SharedFD fd(memfd_create("parameters",MFD_CLOEXEC));assert(!ftruncate(fd.get(),capacity));
 std::vector<FrameBuffer::Plane> planes{{fd,0,capacity}};
 assert(!ipa->mapBuffers({IPABuffer(1,planes)},{}));
 ControlList start(controls::controls),converted(sensor);start.set(controls::AwbEnable,false);
 assert(!ipa->start(1,start,&converted));
 uint32_t bytes=0;assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes>0);
 auto *memory=static_cast<const char*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,fd.get(),0));assert(memory!=MAP_FAILED);
 std::ofstream output(argv[4],std::ios::binary);output.write(memory,bytes);output.close();assert(output.good());
 munmap(const_cast<char*>(memory),capacity);ipa->stop();ipa->unmapBuffers({1});
 std::cout<<"DS4_CAPABILITY height="<<argv[3]<<" pd10="<<configuration.pd10<<std::endl;
 ipa.reset();dlclose(handle);
}
'''
(HERE/'profile-module.cpp').write_text(source)
W='/private/camss443-profile';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True);(work/'contract.cpp').write_text(source)
for name,path in [('baseline',P.parent/'kernel440/factory-s5kgw1-private.yaml'),('candidate',P/'factory-s5kgw1-private.yaml')]:shutil.copyfile(path,work/(name+'.yaml'))
T='/work/libcamera/src/libcamera-v0.7.2';rows=[];packets={}
with storage.sdk_candidate():
 module=storage.candidate()/'src/libcamera-v0.7.2/output/src/ipa/camss-vfe/ipa_camss_vfe.so'
 assert hashlib.sha256(module.read_bytes()).hexdigest()=='3f83969b6e23311fed22f3f03dba6af514c4e16a293994fbf9903a50f6782e7a'
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include',W+'/contract.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o',W+'/contract'],capture_output=True)
 (P/'profile-contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2000:]
 for name in ['baseline','candidate']:
  for height in [3456,2592]:
   label=name+'-'+str(height);destination=W+'/'+label+'.bin'
   q=subprocess.run(['chroot',str(storage.SDK),*env,W+'/contract',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/'+name+'.yaml',str(height),destination],capture_output=True,timeout=25)
   (P/(label+'-profile-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(label,q.stderr.decode()[-2000:])
   expected=not(name=='baseline' and height==2592)
   assert ('pd10='+str(int(expected))).encode() in q.stdout
   raw=(work/(label+'.bin')).read_bytes();version,length=struct.unpack_from('<2I',raw);assert version==1 and len(raw)==length+8
   at=8;blocks={}
   while at<len(raw):
    kind,flags,n=struct.unpack_from('<HHI',raw,at);assert n>=8 and n%8==0 and at+n<=len(raw) and kind not in blocks
    blocks[kind]=raw[at:at+n];at+=n
   assert (8 in blocks)==expected;packets[label]=(raw,blocks)
   if name=='candidate' and height==2592:assert blocks[8]==(P/'expected-mode4-ds4-private.bin').read_bytes()
   shutil.copyfile(work/(label+'.bin'),P/(label+'-ife-parameters-private.bin'))
   rows.append(dict(profile=name,height=height,pd10=expected,typed_ds4_blocks=int(8 in blocks),passed=True))
assert packets['baseline-3456'][0]==packets['candidate-3456'][0]
before=packets['baseline-2592'][1];after=packets['candidate-2592'][1].copy();del after[8];assert before==after
r=dict(stage=443,actual_unchanged_arm64_ipa5=True,werror_build=True,mode3456_packet_byte_identical=True,
 mode2592_only_new_ds4_block=True,typed_ds4_equals_original_mode4_pass_full=True,rows=rows,
 synthetic_configuration_not_hardware=True,phone_accessed=False,passed=True)
(HERE/'profile-module-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
