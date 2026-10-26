from pathlib import Path
import ast,hashlib,json,host
ref=Path(__file__).resolve().parent;source=ref/'samurai-gnss-assist.py';ast.parse(source.read_text());digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.ssh('python3 -',input=b'''from pathlib import Path
import hashlib
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
p=Path('/usr/sbin/samurai-gnss-assist');assert hashlib.sha256(p.read_bytes()).hexdigest()=='71748403c9ef5019b2e47ce1ff5973f13034334de1f927ab8c59ecdd3154ffd2'
assert not Path('/etc/init.d/samurai-gnss-assist').exists()
(root/'k201-assist-tool/worker-before-watch-private.py').write_bytes(p.read_bytes())
''')
host.upload(source,'/usr/sbin/samurai-gnss-assist');host.upload(ref/'samurai-gnss-assist.initd','/etc/init.d/samurai-gnss-assist')
p=host.ssh('chmod 755 /usr/sbin/samurai-gnss-assist /etc/init.d/samurai-gnss-assist && rc-update add samurai-gnss-assist default && rc-service samurai-gnss-assist start',timeout=30)
(host.PRIVATE/'assist-watch-deploy-private.log').write_bytes(p.stdout+p.stderr)
report=dict(stage=201,source_sha256=digest,initd_sha256=hashlib.sha256((ref/'samurai-gnss-assist.initd').read_bytes()).hexdigest(),installed_path='/usr/sbin/samurai-gnss-assist',openrc_default_enabled=True,active_gps_only=True,no_modem_power_or_gps_setup_calls=True)
(ref/'assist-deployment-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
