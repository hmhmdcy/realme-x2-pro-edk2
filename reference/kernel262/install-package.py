"""Install the one tested APK with exact payload and rollback receipts."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent
proof=json.loads((R/'package-build-validation.json').read_text())
flow=json.loads((R/'flow-3000001-validation.json').read_text())
assert flow['buffer_not_recycled']==0 and flow['summary']['diagnostic_completed']
assert flow['summary']['probe_result']['shared_bufferpool'] is False
capture=json.loads((R/'probe-3000002-validation.json').read_text())
assert capture['diagnostic_completed'] and capture['probe_result']['image_done_message']
for name,expected in [('gst-plugin-pipewire-1.6.9-r1.apk',proof['apk_sha256']),('source/gst-plugin-pipewire-1.6.9-r0.apk',proof['base_apk_sha256'])]:
 source=host.PRIVATE/name;assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
 remote=Path('/var/lib/samurai/k262-package-inputs')/source.name
 code="from pathlib import Path;import sys,os;os.umask(0o077);p=Path('/var/lib/samurai/k262-package-inputs');p.mkdir(exist_ok=True);f=p/"+repr(remote.name)+";data=sys.stdin.buffer.read();assert not f.exists() or f.read_bytes()==data;f.write_bytes(data)"
 host.ssh('python3 -c '+shlex.quote(code),input=source.read_bytes())
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
os.umask(0o077)
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
proof=json.loads(sys.argv[1]);out=root/'k262-package-transaction-r2';assert not out.exists();out.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,label):
 p=subprocess.run(args,capture_output=True,timeout=30)
 (out/(label+'-private.log')).write_bytes(p.stdout+p.stderr)
 assert p.returncode==0,label
 return p
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
for p in Path('/proc').glob('[0-9]*'):
 try:assert (p/'comm').read_text().strip() not in ['snapshot','megapixels'],'Camera app still open'
 except FileNotFoundError:pass
target=Path('/usr/lib/gstreamer-1.0/libgstpipewire.so');assert sha(target)==proof['base_plugin_sha256']
for name in ['installed','scripts.tar','triggers']:
 p=Path('/lib/apk/db')/name
 if p.exists():(out/(name+'-before-private')).write_bytes(p.read_bytes())
world=Path('/etc/apk/world').read_bytes();db=Path('/lib/apk/db/installed').read_bytes()
(out/'world-before-private').write_bytes(world);(out/'plugin-before-private.so').write_bytes(target.read_bytes())
new=root/'k262-package-inputs/gst-plugin-pipewire-1.6.9-r1.apk';old=root/'k262-package-inputs/gst-plugin-pipewire-1.6.9-r0.apk'
assert sha(new)==proof['apk_sha256'] and sha(old)==proof['base_apk_sha256']
run(['apk','verify',str(old),str(new)],'trusted-signatures')
simulation=run(['apk','add','--simulate','--no-network',str(new)],'install-simulation')
actions=[l for l in (simulation.stdout+simulation.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(actions)==1 and 'gst-plugin-pipewire' in actions[0] and 'Upgrading' in actions[0],actions
assert Path('/lib/apk/db/installed').read_bytes()==db and Path('/etc/apk/world').read_bytes()==world
run(['apk','add','--no-network',str(new)],'install')
assert sha(target)==proof['plugin_sha256']
after=Path('/lib/apk/db/installed').read_bytes()
def records(raw):
 result={}
 for block in raw.decode().split('\n\n'):
  m=re.search(r'^P:(.+)$',block,re.M)
  if m:result[m[1]]=block
 return result
before_records=records(db);after_records=records(after)
assert set(before_records)==set(after_records)
changed=[n for n in before_records if before_records[n]!=after_records[n]]
assert changed==['gst-plugin-pipewire'],changed
rollback=run(['apk','add','--simulate','--no-network',str(old)],'rollback-simulation')
lines=[l for l in (rollback.stdout+rollback.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(lines)==1 and 'Downgrading gst-plugin-pipewire' in lines[0],lines
report=dict(stage=262,installed=True,package='gst-plugin-pipewire',version='1.6.9-r1',plugin_sha256=sha(target),package_count=len(after_records),only_package_record_changed=changed,upstream_r0_apk_preserved_and_verified=True,native_downgrade_simulation_passed=True,reboot_or_service_restart=False,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps(proof)),input=code.encode(),timeout=100)
(host.PRIVATE/'package-install-private.log').write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/'package-install-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d))
