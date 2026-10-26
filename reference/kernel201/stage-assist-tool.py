from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;source=ref/'samurai-gnss-assist.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
code=b'''from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k201-baseline/boot-id-private.txt').read_bytes()
assert not Path('/usr/sbin/samurai-gnss-assist').exists()
assert not Path('/var/lib/samurai/gnss-assist').exists()
'''
host.ssh('python3 -',input=code)
host.upload(source,'/usr/sbin/samurai-gnss-assist');host.ssh('chmod 755 /usr/sbin/samurai-gnss-assist')
report=dict(stage=201,source_sha256=digest,installed_path='/usr/sbin/samurai-gnss-assist',worker_only=True,no_autostart_service_yet=True)
(ref/'assist-deployment-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
