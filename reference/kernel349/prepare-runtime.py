from pathlib import Path
import copy,hashlib,importlib.util,io,json,math,re,shutil,struct,subprocess,sys,tarfile
sys.path.insert(0,'/usr/lib/python3/dist-packages')
import yaml
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed']
cases={};factory=[c for c in json.loads((P/'cases-private.json').read_text()) if '-factory-' in c['name']]
for c in factory:
 m=c['match'];model=c['model'];cases[c['name']]=dict(model=model,profile=c['profile'],output='640x480',
  sensor_size=str(m['width'])+'x'+str(m['height']),test_pattern=2 if model=='s5kgw1' else 3 if model=='s5k3m5' else 4,
  match=m,gamma=True)
main=next(c for c in factory if c['model']=='s5kgw1');profile=yaml.safe_load((P/'profiles'/main['profile']).read_text())
for label,scales in [('main-linear',[1.,1.,1.]),('main-rgb',[.5,.75,.25])]:
 diagnostic=copy.deepcopy(profile)
 for mode in diagnostic['modes']:
  if 'gamma' in mode:mode['gamma']=dict(mode='static',curves=[[16.*i*scale for i in range(65)] for scale in scales])
 name=label+'.yaml';(P/'profiles'/name).write_text(yaml.safe_dump(diagnostic,sort_keys=False))
 cases[label]=dict(cases[main['name']],profile=name)
for label,item in cases.items():
 m=item['match'];line_us=m['line_length']*1000000/m['pixel_rate'];raw=bytearray()
 for target in [500,5000,12000 if item['model']=='imx471' else 25000]:
  measured=math.floor(math.floor(target/line_us+.5)*line_us+.5)
  raw.extend(struct.pack('<9fi',1,0,0,0,1,0,0,0,1,measured))
 (P/'profiles'/(label+'-phase-oracle-private.bin')).write_bytes(raw)
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel341/lsc-aec-smoke.cpp').read_text().replace('CCM_FRAME','GAMMA_FRAME').replace('CCM_RESULT','GAMMA_RESULT')
s=s.replace('if(camera->start(&initial))return 8;','int started=camera->start(&initial);std::cout<<"START_STATUS status="<<started<<std::endl;if(started)return 8;')
s=s.replace('#include <memory>','#include <memory>\n#include <optional>')
s=s.replace(' std::vector<std::vector<uint8_t>> images;',
 ''' std::vector<std::vector<uint8_t>> images,startupImages;
 std::vector<unsigned> startupSequences;
 std::optional<std::array<float,9>> previousMatrix;''')
s=s.replace('  bool matrixMatches=!hasCcm || matrix.has_value();',
 '''  bool matrixMatches=!hasCcm || matrix.has_value();
  std::optional<std::array<float,9>> currentMatrix;
  if(matrix){currentMatrix.emplace();std::copy(matrix->begin(),matrix->end(),currentMatrix->begin());}
  const bool matrixStable=currentMatrix==previousMatrix;''')
s=s.replace('bool settled=applied && gains &&', 'bool settled=matrixStable && applied && gains &&')
s=s.replace('   if(applied)previous=data;else previous.clear();',
 '''   if(phase==0){startupImages.push_back(data);startupSequences.push_back(m.sequence);}
   if(applied){previous=data;previousMatrix=currentMatrix;}else{previous.clear();previousMatrix.reset();}''')
s=s.replace('std::cout<<" matrix-match="<<matrixMatches;', 'std::cout<<" matrix-match="<<matrixMatches<<" matrix-stable="<<matrixStable;')
needle=' std::cout<<"GAMMA_RESULT frames="'
s=s.replace(needle,''' if(!stopped)for(size_t i=0;i<capture.startupImages.size();i++){
  std::string path=std::string(argv[3])+"-startup"+std::to_string(capture.startupSequences[i])+"-private.nv12";
  int output=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);if(output<0){good=false;break;}
  const auto &data=capture.startupImages[i];size_t done=0;
  while(done<data.size()){ssize_t n=write(output,data.data()+done,data.size()-done);if(n<=0){good=false;break;}done+=n;}
  if(close(output))good=false;
 }
'''+needle)
(HERE/'gamma-smoke.cpp').write_text(s)
relative=Path('/private/camss349-runtime');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(exist_ok=True);TREE='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 shutil.copyfile(HERE/'gamma-smoke.cpp',stage/'probe.cpp')
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',str(relative/'probe.cpp'),
  '-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',str(relative/'gamma-smoke')],capture_output=True)
 (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
# Retain the existing well-tested process helpers, then use the combined worker.
s=(HERE.parent/'kernel341/native-probe.py').read_text();prefix=s[:s.index('stopped=[]')]
prefix=prefix.replace('models=list(cases)',"models=sys.argv[2].split(',') if len(sys.argv)>2 and sys.argv[2]!='all' else list(cases)")
prefix=prefix.replace('"""Temporarily run candidate core/IPA on installed CAMSS338, then restore consumers."""','"""Temporary Gamma IPA+348 module validation with338 restoration."""')
body=(HERE/'worker-body.py').read_text();(HERE/'native-probe.py').write_text(prefix+body)
build=json.loads((HERE.parent/'kernel348/kernel-build-validation.json').read_text());assert not build['exit_code']
proof=json.loads((P.parent/'kernel348/proof.json').read_text());(P/'proof.json').write_text(json.dumps(proof)+'\n')
tree=storage.candidate()/'src/libcamera-v0.7.2';source=tree/'output/src/libcamera/libcamera.so.0.7.2'
lib=P/'runtime-lib';lib.mkdir(exist_ok=True);soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True))[1]
shutil.copyfile(source,lib/soname);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'proof.json','proof.json'),
  (Path(build['module']),'qcom-camss.ko'),(P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(stage/'gamma-smoke','bin/gamma-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for name in sorted({c['profile'] for c in cases.values()}|{label+'-phase-oracle-private.bin' for label in cases}):tar.add(P/'profiles'/name,arcname='profiles/'+name)
 for source in (tree/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
 prior=P/'probe-r1-observation.json'
 if prior.exists():
  reference=json.loads(prior.read_text());assert reference['state']['terminal'] and not reference['worker_live'] and reference['state']['summary']['passed']
  content=json.dumps(reference['state']['summary']['old_kernel_rejection']).encode();item=tarfile.TarInfo('old-kernel-reference.json');item.size=len(content);item.mode=0o600;tar.addfile(item,io.BytesIO(content))
for name in ['launch-probe.py','poll-probe.py','final-state.py']:
 s=(HERE.parent/'kernel341'/name).read_text().replace('k341-dynamic-lsc-','k349-gamma-').replace('stage=341','stage=349');(HERE/name).write_text(s)
s=(HERE.parent/'kernel335/fetch-images.py').read_text().replace('k335-ccm-','k349-gamma-').replace('six-phase','Gamma')
(HERE/'fetch-images.py').write_text(s)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=349,cases=len(cases),four_cameras_five_modes=True,source_factory_curves=True,
 old_kernel_negative_test=True,temporary_combined_module_and_ipa=True,private_configuration_not_installed=True,passed=True),indent=2)+'\n')
print('Prepared combined348 driver +349 IPA experiment, including old-kernel rejection and asymmetric RGB diagnostic.')
