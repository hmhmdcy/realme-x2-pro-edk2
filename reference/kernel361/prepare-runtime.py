"""Build a small real-request probe; reuse exact packaged r28 and tested348."""
from pathlib import Path
import io,json,re,shutil,subprocess,sys,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2'
for name in ['package-artifact-validation.json','recovered-baseline-capture-validation.json']:assert json.loads((HERE.parent/'kernel360'/name).read_text())['passed']
source=storage.candidate();backing=source.parent/'camss361-runtime';backing.mkdir(exist_ok=True);relative=Path('/private/camss361-runtime');slot=storage.SDK/str(relative).lstrip('/');slot.mkdir(exist_ok=True)
assert not any(slot.iterdir()) and subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
subprocess.run(['mount','--bind',str(backing),str(slot)],check=True,capture_output=True)
try:
 with storage.sdk_candidate():
  if '--reuse-probe' in sys.argv:
   assert (HERE/'adaptation-smoke.cpp').read_bytes()==(slot/'probe.cpp').read_bytes() and (slot/'adaptation-smoke').is_file()
  else:
   shutil.copyfile(HERE/'adaptation-smoke.cpp',slot/'probe.cpp')
   q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',str(relative/'probe.cpp'),'-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',str(relative/'adaptation-smoke')],capture_output=True)
   (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
cases={}
for row in json.loads((P.parent/'kernel360/cases-private.json').read_text()):
 if row['name'].endswith('-rgb'):continue
 name=row['name'];m=row['match'];cases[name]=dict(model=row['model'],profile=Path(row['complete_profile']).name,match=m,
  sensor_size=str(m['width'])+'x'+str(m['height']),test_pattern=2 if row['model']=='s5kgw1' else 3 if row['model']=='s5k3m5' else 4,isolation=False)
pilot='imx319-2-preview';assert pilot in cases
cases['main-isolated']=dict(cases['s5kgw1-2-preview'],isolation=True)
cases['wide-optical']=dict(cases[pilot],test_pattern=0)
(P/'cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
proof=json.loads((P.parent/'kernel348/proof.json').read_text());build=json.loads((HERE.parent/'kernel348/kernel-build-validation.json').read_text());assert build['exit_code']==0
proof['old_kernel_reference']=json.loads((HERE.parent/'kernel349/probe-r1-validation.json').read_text())['old_kernel_rejection'];assert all(proof['old_kernel_reference'].values())
adopted=json.loads((P.parent/'kernel360/recovered-boot-adoption-private.json').read_text());proof['boot_guard']=adopted['guard_path'];proof['expected_boot']=adopted['boot_id']
prefix=source.parent/'camera360-package-prefix'
baseLibrary=source/'src/libcamera-v0.7.2/output/src/libcamera/base/libcamera-base.so.0.7.2'
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for path,target in [(HERE/'native-probe.py','worker.py'),(P/'cases-private.json','cases.json'),(Path(build['module']),'qcom-camss.ko'),(P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(backing/'adaptation-smoke','bin/adaptation-smoke'),
  (prefix/'usr/lib/libcamera.so.0.7.2','lib/libcamera.so.0.7.2'),(baseLibrary,'lib/libcamera-base.so.0.7.2'),
  (prefix/'usr/lib/libcamera/ipa/ipa_camss_vfe.so','ipa/ipa_camss_vfe.so'),(prefix/'usr/lib/libcamera/ipa/ipa_camss_vfe.so.sign','ipa/ipa_camss_vfe.so.sign'),
  (prefix/'usr/libexec/libcamera/camss_ipa_proxy','proxy/camss_ipa_proxy')]:tar.add(path,arcname=target)
 for library in [prefix/'usr/lib/libcamera.so.0.7.2',baseLibrary]:
  soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(library)],text=True))[1]
  if soname!=library.name:
   link=tarfile.TarInfo('lib/'+soname);link.type=tarfile.SYMTYPE;link.linkname=library.name;link.mode=0o777;tar.addfile(link)
 for name in {c['profile'] for c in cases.values()}:tar.add(P.parent/'kernel360/profiles'/name,arcname='profiles/'+name)
 data=json.dumps(proof).encode();entry=tarfile.TarInfo('proof.json');entry.size=len(data);entry.mode=0o600;tar.addfile(entry,io.BytesIO(data))
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=361,cases=len(cases),pilot=pilot,probe_aarch64_werror=True,
    packaged_r28_core_and_ipa_used=True,patched_common_base_library_used=True,reused_probe='--reuse-probe' in sys.argv,reused_gamma_driver_stage=348,no_isp_or_kernel_source_change=True,isolated_worker_included=True,
    existing_349_negative_and_gamma_math_evidence_reused=True,runtime_soname_links_included=True,sdk_binds_unmounted=True,passed=True),indent=2)+'\n');print('Prepared real EV/flicker/Gamma request probe with exact r28 payload and348 module.')
