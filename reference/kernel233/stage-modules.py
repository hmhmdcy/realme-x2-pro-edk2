from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
lock=json.loads((P/'deployment-lock-private.json').read_text())
for key in ['mfd_module','provider_module']:
 info=lock['files'][key];assert hashlib.sha256(Path(info['path']).read_bytes()).hexdigest()==info['sha256']
code="""from pathlib import Path
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-baseline/boot-id-private.txt').read_bytes()
out=root/'k233-tools';assert not out.exists();out.mkdir(mode=0o700)
print('TOOLS_CREATED')
"""
result=host.ssh('python3 -',input=code.encode(),timeout=15);(P/'tools-create-private.log').write_bytes(result.stdout+result.stderr)
for key,name in [('mfd_module','qcom-pm8008.ko'),('provider_module','reset-realme-rmx1931-pm8008.ko')]:host.upload(Path(lock['files'][key]['path']),'/var/lib/samurai/k233-tools/'+name)
host.upload(P/'deployment-lock-private.json','/var/lib/samurai/k233-tools/deployment-lock-private.json')
result=host.ssh('python3 -',input=(R/'install-modules.py').read_bytes(),timeout=110)
(P/'module-stage-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout);(R/'module-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n')
state=json.loads((P/'current-work-private.json').read_text());state.update(state='two modules and preload options/softdep staged; old195 MFD remains live; provider unloaded',next='Prepare exact233 quiesce/transition tools, retaining old Q+regulator until reboot; guard233-baseline; then controlled boot-only flash232 with219 rollback',module_staged=True,transition_pending=False);(P/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(report))
