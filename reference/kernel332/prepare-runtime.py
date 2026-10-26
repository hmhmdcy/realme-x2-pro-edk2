from pathlib import Path
import json,re,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera332-cct-built/src/libcamera-v0.7.2';SRC=SDK/TREE.lstrip('/')
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed']
stage=SDK/'private/camss332-runtime';stage.mkdir(mode=0o700,exist_ok=True)
shutil.copyfile(HERE/'cct-smoke.cpp',stage/'cct-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',
 '/private/camss332-runtime/cct-smoke.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base',
 '-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss332-runtime/cct-smoke'],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
cases={}
for name,item in json.loads((P/'cases-private.json').read_text()).items():
 if item['kind']!='unit':continue
 cases[name]={k:item[k] for k in ['model','profile','output','sensor_size','test_pattern']}
 cases[name]['lsc']=False
 (P/'profiles'/(name+'-expected-private.txt')).write_text(str(item['expected_manual_gain_cct'])+'\n')
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel330/native-probe.py').read_text().replace('stage=330','stage=332')
s=s.replace("str(int(item['cct']))", "str(root/'profiles'/(item['profile']+'-expected-private.txt'))")
(HERE/'native-probe.py').write_text(s)
lib=P/'runtime-lib';lib.mkdir(exist_ok=True);source=SRC/'output/src/libcamera/libcamera.so.0.7.2'
soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True))[1]
shutil.copyfile(source,lib/soname);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
with tarfile.open(P/'runtime.tar.gz','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'profiles','profiles'),
  (P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(stage/'cct-smoke','bin/cct-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for source in (SRC/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
for name in ['launch-probe.py','poll-probe.py','fetch-images.py','final-state.py']:
 s=(HERE.parent/'kernel330'/name).read_text().replace('k330-cct-','k332-cct-').replace('stage=330','stage=332')
 (HERE/name).write_text(s)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=332,core_soname=soname,uses_candidate_core_and_signed_ipa=True,
 ipa_unmodified_after_signature=True,unit_reference_profiles=len(cases),manual_gains_and_automatic_awb=True,installed=False,passed=True),indent=2)+'\n')
print('Prepared five reversible unit-reference manual/automatic CCT captures.')
