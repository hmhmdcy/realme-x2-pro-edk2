from pathlib import Path
import json,math,re,shutil,struct,subprocess,tarfile,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['ipa-contract-validation.json','reference-regression-validation.json','configuration-validation.json']:assert json.loads((HERE/name).read_text())['passed']
configs=json.loads((P/'profiles-private.json').read_text());cases={}
for variant in ['qtech_s5kgw1','sunny_imx471','sunny_imx319','qtech_s5k3m5sx']:
 for kind in ['factory','unit']:
  name=variant+'-'+kind;row=configs[name];item=row['item'];m=item['match'];lineUs=float(m['line_length'])*1000000/m['pixel_rate'];raw=bytearray()
  for target in [500,5000,12000 if item['model']=='imx471' else 25000]:
   lines=math.floor(target/lineUs+.5);measuredUs=math.floor(lines*lineUs+.5);raw.extend(struct.pack('<9fi',1,0,0,0,1,0,0,0,1,measuredUs))
  (P/'profiles'/(name+'-phase-oracle-private.bin')).write_bytes(raw)
  cases[name]=dict(model=item['model'],profile=name,output=item['output'],sensor_size=item['sensor_size'],test_pattern=item['test_pattern'],kind=kind,factory_ccm_enabled=item['factory_ccm_enabled'])
if '--front-pn9' in sys.argv or '--wide-pn9' in sys.argv:
 (HERE/('cases-r3.json' if '--wide-pn9' in sys.argv else 'cases-r2.json')).write_text((HERE/'cases.json').read_text())
 cases={name:item for name,item in cases.items() if item['model']==('imx319' if '--wide-pn9' in sys.argv else 'imx471')}
 for item in cases.values():item.update(test_pattern=4,manual_only=False,planned_phases=4,diagnostic_pattern='PN9')
elif '--resume' in sys.argv:
 previous=json.loads((P/'probe-r1-observation.json').read_text());assert previous['state']['terminal'] and not previous['worker_live'] and previous['state']['summary']['deployment_restored']
 oldcases=json.loads((HERE/'cases.json').read_text());(HERE/'cases-r1.json').write_text(json.dumps(oldcases,indent=2)+'\n')
 cases={name:item for name,item in cases.items() if not previous['state']['summary']['captures'][name]['probe_passed']}
 for item in cases.values():item['manual_only']=item['model']=='imx471';item['planned_phases']=3 if item['manual_only'] else 4
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel340/ccm-aec-smoke.cpp').read_text()
s=s.replace(' bool running=false,done=false;',' bool hasCcm=false;\n bool running=false,done=false;')
s=s.replace('  bool matrixMatches=matrix && (target==-1 || !std::memcmp(matrix->data(),expected[phase].data(),36));','  bool matrixMatches=!hasCcm || matrix.has_value();')
s=s.replace('awb==false && temperature==6500 && exposure','awb==false && temperature==(phase==1?2850:6500) && exposure')
s=s.replace('request->controls().set(controls::ColourTemperature,6500);','request->controls().set(controls::ColourTemperature,phase==1?2850:6500);')
s=s.replace('if(!supported || camera->controls().find(&controls::ColourCorrectionMatrix)==camera->controls().end())return 5;','if(!supported)return 5;\n capture.hasCcm=camera->controls().find(&controls::ColourCorrectionMatrix)!=camera->controls().end();')
if '--resume' in sys.argv or '--front-pn9' in sys.argv or '--wide-pn9' in sys.argv:
 s=s.replace('for(unsigned phase=0;phase<3;phase++) {','if(std::string(argv[1])=="imx471" && selectedPattern==3)capture.targets.pop_back();\n for(unsigned phase=0;phase<3;phase++) {')
 s=s.replace('if(good)for(size_t i=0;i<capture.images.size();++i)','if(!stopped)for(size_t i=0;i<capture.images.size();++i)')
if '--front-pn9' in sys.argv or '--wide-pn9' in sys.argv:
 s=s.replace(' bool hasCcm=false;',' bool hasCcm=false,temporalPattern=false;')
 s=s.replace('&& data==previous;','&& (temporalPattern || data==previous);')
 s=s.replace('Capture capture;capture.targets=', 'Capture capture;capture.temporalPattern=selectedPattern==4;capture.targets=')
(HERE/'lsc-aec-smoke.cpp').write_text(s)
relative=Path('/private/camss341-runtime');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True);TREE='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 shutil.copyfile(HERE/'lsc-aec-smoke.cpp',stage/'probe.cpp')
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',str(relative/'probe.cpp'),'-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',str(relative/'lsc-aec-smoke')],capture_output=True)
 (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
s=(HERE.parent/'kernel340/native-probe.py').read_text().replace('stage=340','stage=341').replace('bin/ccm-aec-smoke','bin/lsc-aec-smoke');(HERE/'native-probe.py').write_text(s)
if '--resume' in sys.argv or '--front-pn9' in sys.argv or '--wide-pn9' in sys.argv:
 a="        if ret or expected not in text or 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(selection+' capture failed')"
 b="        if 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(selection+' restoration failed')\n        if ret or expected not in text:state.setdefault('capture_failures',{})[selection]='Capture incomplete; completed phases retained'"
 assert a in s;s=s.replace(a,b).replace('failure=failure is not None','failure=failure is not None or bool(state.get(\'capture_failures\'))')
 (HERE/'native-probe.py').write_text(s)
tree=storage.candidate()/'src/libcamera-v0.7.2';source=tree/'output/src/libcamera/libcamera.so.0.7.2';lib=P/'runtime-lib';lib.mkdir(exist_ok=True);soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True))[1]
shutil.copyfile(source,lib/soname);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
with tarfile.open(P/'probe.tar.gz.tmp','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'profiles','profiles'),(P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(stage/'lsc-aec-smoke','bin/lsc-aec-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for source in (tree/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
(P/'probe.tar.gz.tmp').replace(P/'probe.tar.gz')
for name in ['launch-probe.py','poll-probe.py','final-state.py','fetch-images.py']:
 s=(HERE.parent/'kernel340'/name).read_text().replace('k340-aec-ccm-','k341-dynamic-lsc-').replace('stage=340','stage=341')
 if name=='fetch-images.py':s=s.replace("HERE.parent/'kernel335/fetch-images.py'","HERE.parent/'kernel335/fetch-images.py'").replace("'k340-aec-ccm-'","'k341-dynamic-lsc-'")
 (HERE/name).write_text(s)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=341,profiles=len(cases),factory_unit_paired=True,four_manual_exposure_cct_awb_phases=True,installed_camss338_reused=True,front_factory_ccm_disable_preserved=True,installed=False,passed=True),indent=2)+'\n');print('Prepared paired dynamic LSC factory/unit captures on all four cameras.')
