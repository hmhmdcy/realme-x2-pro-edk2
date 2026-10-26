"""Prepare original-source steady-target matrices and a four-phase device probe."""
from pathlib import Path
import copy,json,math,re,shutil,struct,subprocess,sys,tarfile
import yaml
import host,storage
from oracle import Oracle
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;configs=json.loads((P/'profiles-private.json').read_text());oracle=Oracle(P)
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed'] and json.loads((HERE/'reference-regression-validation.json').read_text())['passed']
sys.path.insert(0,str(HERE.parent/'kernel336'));from stock_lux import StockLux
engine=StockLux(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');manual=StockLux(P.parent/'kernel328/stats-source/com.qti.stats.aec.so')
lumaref={row['model']:row['luma'] for row in json.loads((HERE.parent/'kernel338/hardware-statistics-validation.json').read_text())['cameras']}
cases={};privateCases={}
for name in ['qtech_s5kgw1-unit','front-explicit-ccm-experiment','sunny_imx319-unit','qtech_s5k3m5sx-unit']:
 item=configs[name]['item'];m=item['match'];profile=yaml.safe_load((P/'profiles'/(name+'.yaml')).read_text());c=profile['modes'][0]['colour_correction'];lux=profile['modes'][0]['aec_lux'];a=lux['exposure_anchor']
 lineUs=float(m['line_length'])*1000000/m['pixel_rate'];phases=[];expected=bytearray()
 for wanted,gain in [(500,1.),(5000,1.),(12000 if item['model']=='imx471' else 25000,8.)]:
  lines=math.floor(wanted/lineUs+.5);ns=math.floor(lines*lineUs*1000+.5);measuredUs=math.floor(lines*lineUs+.5)
  exposure=manual.manual((a['analogue_gain'],a['exposure_time_ns'],a['index']),gain,ns)
  calc=lux['lux'];engine.configure(calc['compensate_sensitivity'],calc['reference_zero_sensitivity'],calc['table_zero_sensitivity'],calc['filter_factor']);index=engine.lux(exposure,lumaref[item['model']])
  packet,matrix=oracle.evaluate(c,6500,index);expected.extend(struct.pack('<9fi',*matrix,measuredUs));phases.append(dict(requested_us=wanted,measured_us=measuredUs,exposure_ns=ns,gain=gain,steady_lux_index=index,expected_matrix=matrix))
 (P/'profiles'/(name+'-phase-oracle-private.bin')).write_bytes(expected)
 cases[name]=dict(model=item['model'],profile=name,output=item['output'],sensor_size=item['sensor_size'],test_pattern=item['test_pattern'],factory_ccm_enabled=item['factory_ccm_enabled'],experimental_front_ccm_override=name=='front-explicit-ccm-experiment')
 privateCases[name]=dict(phases=phases)
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');(P/'runtime-cases-private.json').write_text(json.dumps(privateCases,indent=2)+'\n')
s=(HERE.parent/'kernel335/ccm-smoke.cpp').read_text()
start=s.index('  bool matrixMatches=false;');end=s.index('  for(const auto &[stream,buffer]',start)
s=s[:start]+'''  auto exposure=request->metadata().get(controls::ExposureTime);
  auto analogue=request->metadata().get(controls::AnalogueGain);
  bool matrixMatches=matrix && (target==-1 || !std::memcmp(matrix->data(),expected[phase].data(),36));
  const float wantedGain=phase==2?8.f:1.f;
  const bool applied=matrixMatches && (target==-1 ? awb==true && locked==true && temperature.has_value() :
   awb==false && temperature==6500 && exposure && std::abs(*exposure-measuredExposure[phase])<=1 && analogue && std::abs(*analogue-wantedGain)<.001f);
'''+s[end:]
s=s.replace(' std::vector<int> targets;',' std::vector<int> targets;\n std::array<int32_t,3> measuredExposure;')
start=s.index('    if(wanted>0)request->controls()');end=s.index('\n   }\n   if(camera->queueRequest',start)
s=s[:start]+'''    if(wanted>0) {
     request->controls().set(controls::ColourTemperature,6500);
     request->controls().set(controls::ExposureTime,wanted);
     request->controls().set(controls::AnalogueGain,phase==2?8.f:1.f);
    }'''+s[end:]
s=s.replace('capture.targets=std::vector<int>{6500,2850,-2,6500,-3,-1};','capture.targets=std::vector<int>{500,5000,std::string(argv[1])=="imx471"?12000:25000,-1};')
start=s.index(' for(int kelvin=1500;');end=s.index('for(auto &c:manager.cameras())',start)
s=s[:start]+''' for(unsigned phase=0;phase<3;phase++) {
  std::array<float,9> matrix;int32_t exposure;
  if(!expectedFile.read(reinterpret_cast<char*>(matrix.data()),36) || !expectedFile.read(reinterpret_cast<char*>(&exposure),4))return 2;
  capture.expected.push_back(matrix);capture.measuredExposure[phase]=exposure;
 }
'''+s[end:]
s=s.replace('initial.set(controls::ColourTemperature,6500);','initial.set(controls::ColourTemperature,6500);')
# Keep the existing capture/restore logic; change only startup exposure/gain.
s=s.replace('initial.set(controls::ExposureTime,5000);','initial.set(controls::ExposureTime,500);')
s=s.replace('"CCM_FRAME phase="','"CCM_FRAME phase="')
s=s.replace('   std::cout<<" matrix-match="<<matrixMatches;','   std::cout<<" exposure="<<exposure.value_or(0)<<" gain="<<analogue.value_or(0);\n   std::cout<<" matrix-match="<<matrixMatches;')
(HERE/'ccm-aec-smoke.cpp').write_text(s)
relative=Path('/private/camss340-runtime');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True);TREE='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 shutil.copyfile(HERE/'ccm-aec-smoke.cpp',stage/'probe.cpp')
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',str(relative/'probe.cpp'),'-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',str(relative/'ccm-aec-smoke')],capture_output=True)
 (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
s=(HERE.parent/'kernel339/native-probe.py').read_text().replace('stage=339','stage=340').replace("str(root/'bin/awb-grid-smoke')","str(root/'bin/ccm-aec-smoke')").replace("str(item['test_pattern'])]","str(item['test_pattern']),str(root/'profiles'/(item['profile']+'-phase-oracle-private.bin'))]").replace("t.count('AWB_FRAME ')","t.count('CCM_FRAME ')")
(HERE/'native-probe.py').write_text(s)
tree=storage.candidate()/'src/libcamera-v0.7.2';source=tree/'output/src/libcamera/libcamera.so.0.7.2';lib=P/'runtime-lib';lib.mkdir(exist_ok=True)
soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True))[1];shutil.copyfile(source,lib/soname);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'profiles','profiles'),(P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(stage/'ccm-aec-smoke','bin/ccm-aec-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for source in (tree/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
for name in ['launch-probe.py','poll-probe.py','final-state.py']:(HERE/name).write_text((HERE.parent/'kernel339'/name).read_text().replace('k339-lux-','k340-aec-ccm-').replace('stage=339','stage=340'))
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=340,installed_camss338_reused=True,uses_candidate_core_and_signed_ipa=True,profiles=len(cases),steady_matrix_phase_oracle='original OEM exposure/lux instructions and pinned CamX selection/interpolation/encoding',explicit_front_enable_experiment=True,installed=False,passed=True),indent=2)+'\n')
print('Prepared four cameras: three manual exposure/gain phases and automatic-WB phase.')
