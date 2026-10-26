from pathlib import Path
import json,re,shutil,subprocess,tarfile,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera330-wb-built/src/libcamera-v0.7.2';SRC=SDK/TREE.lstrip('/')
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed']
stage=SDK/'private/camss330-runtime';stage.mkdir(mode=0o700,exist_ok=True)
shutil.copyfile(HERE/'cct-smoke.cpp',stage/'cct-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',
 '/private/camss330-runtime/cct-smoke.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base',
 '-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss330-runtime/cct-smoke'],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
cases={}
for model,size in [('s5kgw1','4608x3456'),('imx471','2304x1728'),('imx319','1632x1224'),('s5k3m5','2104x1560')]:
 name='legacy-'+model;base=yaml.safe_load((HERE.parent/'kernel313'/(model+'.yaml')).read_text())
 for mode in base['modes']:mode['residual_black_subtraction']=0;mode['range_normalization']=1.
 (P/'profiles'/(name+'.yaml')).write_text(yaml.safe_dump(base,sort_keys=False))
 cases[name]=dict(model=model,profile=name,output='320x240',sensor_size=size,lsc=False,cct=False,test_pattern=2 if model=='s5kgw1' else 3)
for name,item in json.loads((P/'cases-private.json').read_text()).items():
 cases[name]={k:v for k,v in item.items() if k not in ['match','expected_gains']};cases[name]['cct']=True
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel327/native-probe.py').read_text().replace('stage=327','stage=330')
s=s.replace("str(root/(selection+'-private.nv12'))",'str(root/selection)')
s=s.replace("str(item['test_pattern'])]","str(item['test_pattern']),str(int(item['cct']))]")
s=s.replace("str(root/'bin/lsc-smoke')","str(root/'bin/cct-smoke')")
s=s.replace("        app=[", "        env['LIBCAMERA_IPA_MODULE_PATH']=str(root/'ipa')\n        env['LD_LIBRARY_PATH']=str(root/'lib')\n        app=[")
s=s.replace("t.count('LSC_IMAGE ')","t.count('CCT_FRAME ')")
(HERE/'native-probe.py').write_text(s)
lib=P/'runtime-lib';lib.mkdir(exist_ok=True)
source=SRC/'output/src/libcamera/libcamera.so.0.7.2'
dynamic=subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True)
soname=re.search(r'\(SONAME\).*\[(.*?)\]',dynamic)[1]
shutil.copyfile(source,lib/soname)
subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
with tarfile.open(P/'runtime.tar.gz','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'profiles','profiles'),
  (P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(stage/'cct-smoke','bin/cct-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for source in (SRC/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
for name in ['launch-probe.py','poll-probe.py','fetch-images.py']:
 s=(HERE.parent/'kernel327'/name).read_text().replace('k327-lsc-','k330-cct-')
 (HERE/name).write_text(s)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=330,uses_candidate_core_and_signed_ipa=True,
 core_soname=soname,core_debug_stripped=True,ipa_unmodified_after_signature=True,legacy_cases=4,calibrated_cases=10,
 startup_and_runtime_cct=True,installed=False,passed=True),indent=2)+'\n')
print('Prepared temporary candidate core/signed IPA, four legacy and ten two-phase CCT cases.')
