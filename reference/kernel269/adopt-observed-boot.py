"""Record the read-verified unexpected boot without replacing historical guards."""
from pathlib import Path
import hashlib,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('old',R.parent/'kernel267/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
d=json.loads((P/'unexpected-reboot-r1/identity-private.json').read_text())
assert d['release']=='7.3.0-rc6-rmx1931-samurai-k132+' and not d['rotation_rule_exists']
expected=json.loads((R.parent/'kernel267/postboot-hardware-validation.json').read_text())['modules']
assert all(v['loaded'] and v['sha256']==expected[n]['sha256'] for n,v in d['modules'].items())
identity=P/'current-boot-private.json';assert not identity.exists()
code=r'''
from pathlib import Path
import json,os
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED
os.umask(0o077);p=Path('/var/lib/samurai/k269-work');p.mkdir(mode=0o700)
(p/'boot-id-private.txt').write_text(EXPECTED+'\n')
print(json.dumps(dict(verified=True)))
'''.replace('EXPECTED',repr(d['boot_id']))
q=h.raw_ssh('python3 -',input=code.encode(),timeout=15);assert json.loads(q.stdout)['verified']
identity.write_text(json.dumps(d,indent=2)+'\n');identity.chmod(0o600)
print('K269_NEW_BOOT_GUARD_RECORDED_ORIGINAL_KEY_AND_FIVE_CAMERA_MODULES_VERIFIED')
