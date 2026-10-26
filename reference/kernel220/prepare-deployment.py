from pathlib import Path
import json
here=Path(__file__).resolve().parent;prior=here.parent/'kernel219'
for phase in ['candidate-threaded','candidate-isolated']:
 for w,h in [(1920,1088),(2296,1728)]:
  r=json.loads((here/f'exposure-metadata-{phase}-{w}x{h}-validation.json').read_text());assert r['program_exit']==0 and r['frame_count']==36 and r['maximum_metadata_conversion_error_us']<1
  if phase.endswith('isolated'):assert r['ipa_isolation_forced_observed']
r=json.loads((here/'exposure-metadata-candidate-threaded-4608x3456-validation.json').read_text());assert r['program_exit']==0 and r['maximum_metadata_conversion_error_us']<1
assert json.loads((here/'candidate-full-finish-validation.json').read_text())['experimental_full_raw_disabled']
def adapt(code):
 code=code.replace('k219-r6-package-candidates','k220-r7-package-candidates').replace('k214-package-candidates','k219-r6-package-candidates')
 code=code.replace('k219-r6-package-transaction','k220-r7-package-transaction')
 code=code.replace('k219-runtime/boot-id-private.txt','k220-baseline/boot-id-private.txt').replace('/var/lib/samurai/k219-runtime','/var/lib/samurai/k220-baseline')
 code=code.replace('k219-baseline/installed-before-private.txt','k220-baseline/installed-before-private.txt')
 code=code.replace('99990.7.2-r6','99990.7.2-r7').replace('0.1.0-r1','0.1.0-r2')
 code=code.replace('99990.7.2-r5','99990.7.2-r6').replace('0.1.0-r0','0.1.0-r1')
 code=code.replace('r6-native-preflight','r7-native-preflight').replace('r6-package-install','r7-package-install')
 code=code.replace('r6-preflight-host','r7-preflight-host').replace('r6-install-host','r7-install-host')
 code=code.replace('stage=219','stage=220').replace('new_r6_camera_libraries_loaded','new_r7_camera_libraries_loaded')
 code=code.replace('match_r5_rollback','match_r6_rollback').replace('seven_package_r5_downgrade','seven_package_r6_downgrade')
 code=code.replace('original_world_repositories_and_r5_payloads_retained','original_world_repositories_and_r6_payloads_retained')
 return code
text=(prior/'native-r6-preflight.py').read_text();native=text.split("code=r'''",1)[1].split("'''",1)[0];native=adapt(native)
wrapper="from pathlib import Path\nimport host,json\nhere=Path(__file__).resolve().parent\ncode="+repr(native)+'\n'
wrapper+="p=host.ssh('python3 -',input=code.encode(),timeout=70)\n(host.PRIVATE/'r7-preflight-host-private.log').write_bytes(p.stdout+p.stderr)\nr=json.loads(p.stdout);(here/'r7-native-preflight-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))\n"
compile(wrapper,'r7-preflight220','exec');(here/'native-r7-preflight.py').write_text(wrapper)
for source,target in [('install-r6-packages.py','install-r7-packages.py'),('reload-wireplumber.py','reload-wireplumber.py')]:
 code=adapt((prior/source).read_text());compile(code,target,'exec');(here/target).write_text(code)
print('Current r6 rollback and coherent seven-component r7/r2 transaction prepared')
