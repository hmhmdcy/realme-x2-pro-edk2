"""Prepare r2 staging and standard parameter tests; retain unbooted r1 modules."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel291'
s=(ROOT/'stage-device-modules.py').read_text().replace('modules-k292-private','modules-k292-r2-private').replace('k292-deployment','k292-deployment-r2')
needle="assert not Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k292+').exists()";assert needle in s;s=s.replace(needle,"assert Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k292+').is_dir()")
needle="source=stage/prefix;target=Path('/usr/lib/modules')/release;assert not target.exists()";assert needle in s
s=s.replace(needle,"""source=stage/prefix;target=Path('/usr/lib/modules')/release
assert os.uname().version.startswith('#290 ') and os.uname().release!=release
r1=Path('/var/lib/samurai/k292-deployment');old_inventory=json.loads((r1/'module-inventory-private.json').read_text())
sha_r1=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert len(old_inventory)==778 and old_inventory=={str(f.relative_to(target)):sha_r1(f) for f in target.rglob('*.ko')}
preserved=r1/'modules-r1-preserved';assert not preserved.exists() and target.stat().st_dev==preserved.parent.stat().st_dev
target.rename(preserved);assert not target.exists()
""")
p=ROOT/'stage-device-r2.py';assert not p.exists();p.write_text(s)
for name in ['prepare-transition.py','native-quiesce.py','restart-bootloader.py','bootstrap-postboot.py']:
 p=ROOT/name;s=p.read_text().replace('k292-deployment','k292-deployment-r2').replace('logdump-k292-candidate-private','logdump-k292-r2-candidate-private');p.write_text(s)
worker=(OLD/'native-pattern-pix.py').read_text().replace('k291-pattern-pix-r1','k292-wb-params-r1').replace('k291-tools/pattern-pix','k292-tools/wb-params').replace('k290-work','k292-work').replace("'#290 '","'#292 '").replace('samurai-k290+','samurai-k292+').replace('stage=291','stage=292').replace('kernel_build=290','kernel_build=292')
worker=worker.replace('child.wait(timeout=25)','child.wait(timeout=45)')
worker=worker.replace("report['actual_frames']==18","report['actual_frames']==81")
needle="(root/'summary-private.json').write_text";assert needle in worker
worker=worker.replace(needle,"report['negative_parameter_cases']=len(re.findall(r'^PARAM_REJECT ',text,re.M))\n report['parameter_completions']=len(re.findall(r'^PARAM_DQ ',text,re.M))\n report['passed']=report['passed'] and report['negative_parameter_cases']==10 and report['parameter_completions']==7 and len(images)==9\n "+needle)
p=ROOT/'native-wb-params.py';assert not p.exists();p.write_text(worker)
launcher=(OLD/'launch-pattern-pix.py').read_text()
launcher=launcher.replace("proof=json.loads((ROOT/'pattern-tool-validation.json').read_text())['tools']['pix']","proof=json.loads((ROOT/'wb-params-tool-validation.json').read_text())")
launcher=launcher.replace('pattern-pix-aarch64-private','wb-params-aarch64-private').replace('pattern-pix','wb-params').replace('k291-','k292-').replace('k290-work','k292-work').replace('stage=291','stage=292')
p=ROOT/'launch-wb-params.py';assert not p.exists();p.write_text(launcher)
poll=(OLD/'poll-pattern-pix.py').read_text().replace('pattern-pix','wb-params').replace('k291-','k292-')
p=ROOT/'poll-wb-params.py';assert not p.exists();p.write_text(poll)
print('Prepared r2 module preservation and standard metadata probe workflows.')
