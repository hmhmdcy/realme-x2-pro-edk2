"""Finish the read-only verification of the already successful APK transaction."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'package-build-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,re,subprocess,sys
proof=json.loads(sys.argv[1]);out=Path('/var/lib/samurai/k262-package-transaction-r2')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k260-work/boot-id-private.txt').read_bytes()
target=Path('/usr/lib/gstreamer-1.0/libgstpipewire.so')
assert hashlib.sha256(target.read_bytes()).hexdigest()==proof['plugin_sha256']
db=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes()
def records(raw):
 result={}
 for block in raw.decode().split('\n\n'):
  m=re.search(r'^P:(.+)$',block,re.M)
  if m:result[m[1]]=block
 return result
before=records((out/'installed-before-private').read_bytes());after=records(db)
assert set(before)==set(after)
changed=[n for n in before if before[n]!=after[n]];assert changed==['gst-plugin-pipewire']
q=subprocess.run(['apk','add','--simulate','--no-network','/var/lib/samurai/k262-package-inputs/gst-plugin-pipewire-1.6.9-r0.apk'],capture_output=True,timeout=30)
(out/'rollback-simulation-r2-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'See rollback simulation log'
actions=[l for l in (q.stdout+q.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(actions)==1 and 'Downgrading gst-plugin-pipewire' in actions[0],actions
assert db==Path('/lib/apk/db/installed').read_bytes() and world==Path('/etc/apk/world').read_bytes()
oldworld=set((out/'world-before-private').read_text().splitlines());newworld=set(world.decode().splitlines())
assert all(l.startswith('gst-plugin-pipewire') for l in oldworld^newworld)
(out/'world-after-private').write_bytes(world)
report=dict(stage=262,installed=True,package='gst-plugin-pipewire',version='1.6.9-r1',plugin_sha256=proof['plugin_sha256'],package_count=len(after),only_package_record_changed=changed,world_added=sorted(newworld-oldworld),world_removed=sorted(oldworld-newworld),upstream_r0_apk_preserved_and_verified=True,native_downgrade_simulation_passed=True,rollback_round_trip_tested=False,reboot_or_service_restart=False,taint=int(Path('/proc/sys/kernel/tainted').read_text()),failed_first_install_simulation_before_mutation=True,first_post_install_rollback_option_rejected=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps(proof)),input=code.encode(),timeout=45)
(host.PRIVATE/'finish-install-private.log').write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/'package-install-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
