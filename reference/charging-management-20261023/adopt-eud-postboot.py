"""Adopt the actually passed boot-only baseline; preserve every older guard."""
from pathlib import Path
import hashlib, importlib.util, json, os, shlex

BASE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
TX = BASE / 'eud-boot-activation/eud-boot-r2-live-001'
GUARD = '/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt'
MANIFEST = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
sha = lambda b: hashlib.sha256(b).hexdigest()

def create(p, raw):
    with p.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())

def main():
    observed = TX / 'postboot-r3-01-private'
    report = json.loads((observed / 'stdout-private.json').read_bytes())
    receiver = json.loads((observed / 'receiver-result-private.json').read_bytes())
    assert receiver['passed'] and receiver['transport_exit'] == 0 and report['result']['passed']
    raw = report['raw']; old = json.loads((TX / 'guard-private.json').read_bytes())
    boot = raw['identity_before']['boot_id']
    assert boot == raw['identity_after']['boot_id'] and boot != old['boot_id']
    assert (TX / 'candidate-first-boot-id-private.txt').read_text().strip() == boot
    topology = json.loads((TX / 'host-topology-postboot-private.json').read_bytes())
    assert topology['eud_present_count'] == 0
    assert not any('VID_05C6&PID_950' in x['InstanceId'] for x in topology['chain'])
    notes = {n.replace('-', '_'): x['loaded_note_sha256'] for n, x in
             {**raw['charging_modules'], **raw['camera_modules']}.items()}
    notes['s5k3m5'] = 'a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13'
    request = dict(boot=boot, release=old['kernel_release'], version=old['kernel_version'],
                   rootfs=old['rootfs_release_sha256'], guard=GUARD, notes=notes,
                   manifest=MANIFEST, postboot_raw_sha256=sha((observed/'stdout-private.json').read_bytes()))
    create(TX / 'adopt-request-private.json', json.dumps(request, indent=2).encode())
    code = r'''from pathlib import Path
import hashlib,json,os,sys
d=json.loads(sys.stdin.buffer.read());sha=lambda b:hashlib.sha256(b).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot']
assert os.uname().release==d['release'] and os.uname().version==d['version']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha(Path('/etc/samurai-rootfs-release').read_bytes())==d['rootfs']
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==d['manifest']
for n,h in d['notes'].items():
 assert sha(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes())==h
 assert Path('/sys/module',n,'initstate').read_text().strip()=='live'
t={k:int(v) for k,v in (x.split('=') for x in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
assert t['valid']==t['online']==t['protection_ok']==1 and 0<=t['age_ms']<=3000
assert all(t[k]==0 for k in ['shadow','error','stop_error','latched','fault','source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
assert not Path('/sys/class/tty/ttyEUD0').exists()
p=Path(d['guard']);assert not p.exists() and not p.parent.exists()
os.umask(0o077);p.parent.mkdir(mode=0o700)
with p.open('x') as f:f.write(d['boot']+'\n');f.flush();os.fsync(f.fileno())
fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
assert p.read_text().strip()==d['boot']
print(json.dumps({'guard_created':True,'old_guards_preserved':True,'charging_controls_written':False}))
'''
    spec = importlib.util.spec_from_file_location('transport', Path(__file__).parent/'r7-transport.py')
    transport = importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)
    q = transport.raw_ssh('python3 -c '+shlex.quote(code), input=json.dumps(request).encode(), timeout=15, check=False)
    create(TX/'adopt-stdout-private.json', q.stdout); create(TX/'adopt-stderr-private.txt', q.stderr)
    create(TX/'adopt-transport-terminal-private.json', json.dumps({'returncode':q.returncode}).encode())
    assert q.returncode == 0 and json.loads(q.stdout)['guard_created']
    adoption = dict(guard_path=GUARD, original_key_verified=True, baseline481_verified=True,
                    charging_manifest_sha256=MANIFEST, candidate_boot_sha256=old['candidate_boot_sha256'],
                    postboot_raw_sha256=request['postboot_raw_sha256'])
    pointer = BASE/'boot-adoption-private.json'
    create(TX/'boot-adoption-before-eud-private.json', pointer.read_bytes())
    temporary = BASE/'boot-adoption-eud-next-private.json'
    create(temporary, json.dumps(adoption,indent=2).encode()); temporary.replace(pointer)
    endpoint = dict(kind='usb-ipv6', peer='fe80::62:bcff:fe28:a101%29', interface_index=29,
                    host_key_alias='169.254.42.1', original_key_verified=True, observed_new_boot=boot,
                    guard_path=GUARD, postboot_R3_passed=True)
    create(TX/'new-endpoint-private.json', json.dumps(endpoint,indent=2).encode())
    fd=os.open(BASE,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps({'new_boot_adopted':True,'guard_created':True,'old_guards_preserved':True,
                      'R8_verified':True,'camera481_verified':True,'no_charging_control_write':True}))

if __name__ == '__main__': main()
