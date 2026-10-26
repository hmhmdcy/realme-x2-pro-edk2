from pathlib import Path
import hashlib,host,json,shlex

here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k219-reboot-tools'
assert not (host.PRIVATE/'reboot-request-private.json').exists()
host.ssh('test ! -e /var/lib/samurai/k219-before-reboot && test ! -e /var/lib/samurai/k219-quiesce && mkdir -m700 '+dest,timeout=30)
for name in ['quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py']:
    data=(here/name).read_bytes();assert len(data)<65536
    code="from pathlib import Path;import hashlib,sys;d=sys.stdin.buffer.read();assert hashlib.sha256(d).hexdigest()=="+repr(hashlib.sha256(data).hexdigest())+";p=Path("+repr(dest+'/'+name)+");assert not p.exists();p.write_bytes(d);p.chmod(0o600);Path("+repr('/tmp/k219-'+name)+").write_bytes(d)"
    host.ssh('python3 -c '+shlex.quote(code),input=data,timeout=30)
p=host.ssh('python3 -',input=(here/'collect-pre-reboot.py').read_bytes(),timeout=100)
(host.PRIVATE/'pre-reboot-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'pre-reboot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
p=host.ssh('sh '+dest+'/quiesce-current183.sh',timeout=200)
(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('cat /var/lib/samurai/k219-quiesce/quiesce-validation.json',timeout=30)
proof=json.loads(p.stdout);assert proof['quiesce_audit_pass'] and proof['taint']==0
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
(here/'quiesce-validation.json').write_text(json.dumps({k:v for k,v in proof.items() if k!='boot_id'},indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k!='boot_id'}))
