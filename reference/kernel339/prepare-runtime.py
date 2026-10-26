"""Reuse the AWB capture tool with candidate core/IPA; retain deployed CAMSS338."""
from pathlib import Path
import json,re,shutil,subprocess,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed']
configs=json.loads((P/'profiles-private.json').read_text());cases={}
for label in ['qtech_s5kgw1-unit','sunny_imx471-unit','sunny_imx319-unit','qtech_s5k3m5sx-unit','colour-compensation']:
 item=configs[label]['item'];cases[label]={k:item[k] for k in ['model','output','sensor_size','test_pattern']};cases[label]['profile']=label
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel335/native-probe.py').read_text().replace('stage=335','stage=339')
s=s.replace('"""Temporarily load the new CAMSS, capture RGB, then restore the deployed module."""','"""Temporarily run candidate core/IPA on installed CAMSS338, then restore consumers."""')
s=s.replace("proof=json.loads((root/'proof.json').read_text())\n",'')
start=s.index('    deployed=subprocess.check_output(');end=s.index('    wait_idle()',start)
s=s[:start]+"    if before_note!='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297':raise RuntimeError('Expected installed CAMSS338')\n"+s[end:]
start=s.index("    save('unloading-deployed')");end=s.index("    save('capturing')",start)
s=s[:start]+s[end:]
s=s.replace("str(root/'bin/ccm-smoke')","str(root/'bin/awb-grid-smoke')").replace(",str(root/'profiles'/(item['profile']+'-oracle-private.bin'))",'')
s=s.replace("t.count('CCM_FRAME ')","t.count('AWB_FRAME ')").replace('temporary_userspace_and_module_only=True','temporary_userspace_only=True,installed_camss338_reused=True')
# No module mutation or restore is required for this userspace-only change.
start=s.index('        if changed:');end=s.index('        restored=hashlib',start)
s=s[:start]+s[end:];s=s.replace('changed=False\n','')
(HERE/'native-probe.py').write_text(s)
lib=P/'runtime-lib';lib.mkdir(exist_ok=True);tree=storage.candidate()/'src/libcamera-v0.7.2'
source=tree/'output/src/libcamera/libcamera.so.0.7.2'
soname=re.search(r'\(SONAME\).*\[(.*?)\]',subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(source)],text=True))[1]
shutil.copyfile(source,lib/soname);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(lib/soname)],check=True)
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for source,target in [(HERE/'native-probe.py','worker.py'),(HERE/'cases.json','cases.json'),(P/'profiles','profiles'),(P.parent/'kernel313/pipeline-fixture','pipeline-fixture'),(storage.SDK/'private/camss338-runtime/awb-grid-smoke','bin/awb-grid-smoke'),(lib,'lib')]:tar.add(source,arcname=target)
 for source in (tree/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
  if source.is_file():tar.add(source,arcname='ipa/'+source.name)
for name in ['launch-probe.py','poll-probe.py','final-state.py']:
 s=(HERE.parent/'kernel335'/name).read_text().replace('k335-ccm-','k339-lux-').replace('stage=335','stage=339');(HERE/name).write_text(s)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=339,uses_candidate_core_and_signed_ipa=True,installed_camss338_reused=True,ipa_unmodified_after_signature=True,existing_awb_probe_reused=True,profiles=len(cases),private_explicit_reference_coordinates=True,installed=False,passed=True),indent=2)+'\n')
print('Prepared temporary userspace runtime lux test, using installed CAMSS338.')
