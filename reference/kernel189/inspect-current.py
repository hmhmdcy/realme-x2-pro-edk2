from pathlib import Path
import json
import host

code='''from pathlib import Path
import os,json,subprocess
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k188-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k189-baseline');assert not out.exists();out.mkdir(mode=0o700)
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
report=dict(stage=189,current_kernel=183,same_boot_as188=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 remoteproc={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
 power=Path('/sys/devices/platform/sensor-power/state').read_text().strip(),
 automatic_service_absent=not Path('/etc/runlevels/default/samurai-ssc').is_symlink(),
 full_boot_fatal_count=log.count('fatal error received'),full_boot_scm_errors=log.count('Assign memory protection call failed'),
 phosh_running=bool(subprocess.run(['pidof','phosh'],capture_output=True).stdout.strip()),
 uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
assert report['taint']==0 and report['remoteproc']=={'adsp':'running','slpi':'offline','modem':'running'}
assert report['power']=='vdd=0 vddio=0' and report['automatic_service_absent']
assert report['full_boot_fatal_count']==1 and report['full_boot_scm_errors']==0
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'baseline-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
(Path(__file__).resolve().parent/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
