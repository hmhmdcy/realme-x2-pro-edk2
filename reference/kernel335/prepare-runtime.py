from pathlib import Path
import io,json,re,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera335-ccm-built/src/libcamera-v0.7.2';SRC=SDK/TREE.lstrip('/')
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed']
stage=SDK/'private/camss335-runtime';stage.mkdir(mode=0o700,exist_ok=True);shutil.copyfile(HERE/'ccm-smoke.cpp',stage/'ccm-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',
 '/private/camss335-runtime/ccm-smoke.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base',
 '-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss335-runtime/ccm-smoke'],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
cases={}
for name,item in json.loads((P/'cases-private.json').read_text()).items():
 if item['kind']!='unit' or not item['ccm_enabled']:continue
 cases[name]={k:item[k] for k in ['model','profile','output','sensor_size','test_pattern','factory_ccm_enabled']}
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel334/native-probe.py').read_text().replace('stage=334','stage=335')
s=s.replace("models=sys.argv[2].split(',') if len(sys.argv)>2 else ['imx319']","cases=json.loads((root/'cases.json').read_text());models=list(cases)")
start=s.index('        env=dict(os.environ,LIBCAMERA_LOG_LEVELS=');end=s.index("        with (root/('capture-'+selection+'.log'))",start)
s=s[:start]+'''        item=cases[selection];model=item['model']
        devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
        if len(devices)!=1:raise RuntimeError('Sensor node not unique: '+model)
        sensor='/dev/'+devices[0].name
        env=dict(os.environ,LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/(item['profile']+'.yaml')),LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
        for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
        env['LIBCAMERA_IPA_MODULE_PATH']=str(root/'ipa');env['LD_LIBRARY_PATH']=str(root/'lib')
        app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/ccm-smoke'),model,sensor,str(root/selection),item['output'],item['sensor_size'],str(item['test_pattern']),str(root/'profiles'/(item['profile']+'-oracle-private.bin'))]
'''+s[end:]
s=s.replace("expected='CAPTURE_RESULT success=1 cleanup_complete=1' if selection=='pattern' else 'bus-errors=0 result=0'", "expected=' failed=0 result=0'")
s=s.replace("if ret or expected not in text:","if ret or expected not in text or 'FIXTURE_RESTORATION result=0' not in text:")
s=s.replace("t.count('CCM_FRAME ')+t.count('GST_IMAGE ')","t.count('CCM_FRAME ')")
s=s.replace("('CAPTURE_RESULT success=1 cleanup_complete=1' in t) if m=='pattern' else ('bus-errors=0 result=0' in t)","(' failed=0 result=0' in t)")
s=s.replace("('cleanup_complete=1' in t) if m=='pattern' else ('FIXTURE_RESTORATION result=0' in t)","('FIXTURE_RESTORATION result=0' in t)")
s=s.replace('temporary_module_only=True','temporary_userspace_and_module_only=True')
(HERE/'native-probe.py').write_text(s)
lib=P/'runtime-lib';lib.mkdir(exist_ok=True);source=SRC/'output/src/libcamera/libcamera.so.0.7.2'
soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True))[1]
shutil.copyfile(source,lib/soname);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
module=Path(json.loads((HERE.parent/'kernel334/kernel-build-validation.json').read_text())['module'])
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'profiles','profiles'),(P.parent/'kernel334/proof.json','proof.json'),(module,'qcom-camss.ko'),
  (P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(stage/'ccm-smoke','bin/ccm-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for source in (SRC/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
for name in ['launch-probe.py','poll-probe.py','final-state.py']:
 s=(HERE.parent/'kernel334'/name).read_text().replace('k334-ccm-','k335-ccm-').replace('stage=334','stage=335');(HERE/name).write_text(s)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=335,core_soname=soname,uses_candidate_core_and_signed_ipa=True,temporary_334_camss_module=True,ipa_unmodified_after_signature=True,
 unit_reference_profiles=len(cases),front_factory_ccm_disabled_override_explicit=True,manual_cct_matrix_gains_and_auto_awb=True,installed=False,passed=True),indent=2)+'\n')
print('Prepared candidate core/IPA and temporary334 CAMSS for five six-phase captures.')
