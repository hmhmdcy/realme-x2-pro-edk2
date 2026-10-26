"""Cross-check real IPA serialization against the independent Hermite model."""
from pathlib import Path
import json, math, shutil, struct, subprocess, yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');TREE='/work/libcamera321-lsc-built/src/libcamera-v0.7.2'
stage=SDK/'private/camss322-mesh';stage.mkdir(exist_ok=True)
s=(HERE.parent/'kernel321/ipa-contract.cpp').read_text()
s=s[:s.index('\n if(lsc) {')]+'''\n assert(bytes==1848);
 assert(std::fwrite(parameters+56,1,sizeof(camss_params_lsc),stdout)==sizeof(camss_params_lsc));
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);
 return 0;
}\n'''
s=s.replace('#include <array>','#include <array>\n#include <cstdio>')
s=s.replace('bytes==(lsc?1848:56)','bytes==1848').replace(' const bool lsc=argc==4 && std::string(argv[3])=="lsc";','')
s=s.replace('constexpr uint32_t legacy=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);','')
(stage/'dump.cpp').write_text(s);(HERE/'dump-ipa-mesh.cpp').write_text(s)
args=['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+TREE+'/include','-I'+TREE+'/output/include',
 '/private/camss322-mesh/dump.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-ldl','-o','/private/camss322-mesh/dump']
q=subprocess.run(args,capture_output=True);(P/'mesh-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
# Import only mathematical definitions, avoiding the older runner's side effects.
old=(HERE.parent/'kernel319/check-factory-resampling.py').read_text();ns={'math':math,'struct':struct}
exec(old[old.index('def geometry'):old.index('\ncases=')],ns)
f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
results=[]
for name in ['factory','unit']:
 shutil.copyfile(P/'profiles'/(name+'.yaml'),stage/(name+'.yaml'))
 q=subprocess.run(['chroot',str(SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base','/private/camss322-mesh/dump',TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss322-mesh/'+name+'.yaml'],capture_output=True,timeout=60)
 (P/('mesh-'+name+'.log')).write_bytes(q.stderr);assert not q.returncode,q.stderr.decode();assert len(q.stdout)==1792
 (P/(name+'-mesh-private.bin')).write_bytes(q.stdout)
 header=struct.unpack_from('<HHIHHHHB',q.stdout);assert header[:3]==(6,2,1792)
 lsc=yaml.safe_load((stage/(name+'.yaml')).read_text())['modes'][0]['lens_shading']
 channels=['r','gr','gb','b'];source=[[f32(v) for v in lsc['gains'][c]] for c in channels]
 if name=='unit':
  source=[[f32(v*f32(f32(g)/f32(u))) for v,g,u in zip(source[i],lsc['golden'][c],lsc['unit'][c])] for i,c in enumerate(channels)]
  green=[f32(f32(a*.5)+f32(b*.5)) for a,b in zip(source[1],source[2])];source[1]=source[2]=green
 grid=ns['geometry'](1632,1224);assert header[3:]==grid
 expected=[math.floor(v*1024+.5) for ch in source for v in ns['predict'](ch,grid,[1631,1223,0,0,2,2])]
 actual=struct.unpack_from('<884H',q.stdout,24)
 errors=[abs(a-b) for a,b in zip(actual,expected)]
 assert max(errors)==0
 results.append(dict(case=name,words=len(actual),maximum_q10_error=max(errors),grid=list(grid),passed=True))
report=dict(stage=322,actual_aarch64_ipa_dso=True,independent_python_hermite_model=True,cases=results,passed=True)
(HERE/'ipa-mesh-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
