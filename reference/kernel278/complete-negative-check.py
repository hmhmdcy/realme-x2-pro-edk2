"""Complete the existing negative check from retained output, correcting APK CLI interpretation."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k278-negative-support').replace('root.mkdir(mode=0o700);','')
code+=r'''
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
assert json.loads((root/'support-stdout-private.json').read_text())==dict(af_mode=False,af_trigger=False,af_state=False)
versions={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields={l[:1]:l[2:] for l in block.splitlines() if len(l)>1 and l[1]==':'}
 if fields.get('P') in ['libcamera','libcamera-ipa','samurai-camera-config']:versions[fields['P']]=fields['V']
assert versions=={'libcamera':'99990.7.2-r23','libcamera-ipa':'99990.7.2-r23','samurai-camera-config':'0.1.0-r18'}
after=health();assert after['passed']
(root/'initial-host-check-failure-private.txt').write_text('First support probe exited0 and showed AF absent. Final host assertion misused apk info -v, which prints repository descriptions on this APK version. No second probe or package operation was started.')
state.update(state='terminal',terminal=True,exit_code=0,existing_probe_output_reused=True);save()
print(json.dumps(dict(stage=278,old_r23_af_controls_absent=True,old_system_packages_unchanged=True,current_boot276_guard_verified=True,health=after,
 installed_db_versions_verified=True,initial_apk_cli_assertion_corrected=True,no_second_probe_started=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'negative-check-completion-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'negative-support-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k!='health'}))
