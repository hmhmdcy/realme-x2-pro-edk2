"""Use the separately verified package result; preserve the failed check as history."""
from pathlib import Path
import base64,hashlib,json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'packages-install-validation.json').read_text())['apk_install_not_repeated']
p=R/'restart-bootloader.py';old=p.read_bytes();new=old.replace(b'packages-state-private.json',b'packages-verified-state-private.json')
assert new!=old and old.count(b'packages-state-private.json')==1
args=dict(old_sha=hashlib.sha256(old).hexdigest(),new=base64.b64encode(new).decode())
code=r'''
from pathlib import Path
import base64,hashlib,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k270-work/boot-id-private.txt').read_bytes()
assert json.loads((r/'k273-main-transaction/packages-verified-state-private.json').read_text())['exit_code']==0
p=r/'k273-tools/restart-bootloader.py';old=p.read_bytes();assert hashlib.sha256(old).hexdigest()==args['old_sha']
backup=p.with_name('restart-before-package-verification.py');assert not backup.exists();backup.write_bytes(old)
new=base64.b64decode(args['new']);compile(new,p.name,'exec');p.write_bytes(new);os.sync()
print(json.dumps(dict(restart_guard_uses_verified_package_state=True,failed_postinstall_check_preserved=True,no_restart_sent=True)))
'''
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=20)
p.write_bytes(new)
p=R/'bootstrap-postboot.py';t=p.read_text();assert t.count('packages-state-private.json')==1;p.write_text(t.replace('packages-state-private.json','packages-verified-state-private.json'))
(host.PRIVATE/'restart-guard-correction-private.json').write_bytes(q.stdout);print(q.stdout.decode())
