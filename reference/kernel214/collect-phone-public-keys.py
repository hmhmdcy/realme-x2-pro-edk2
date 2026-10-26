from pathlib import Path
import base64,host,json
here=Path(__file__).resolve().parent;destination=host.PRIVATE/'phone-trusted-public-keys';destination.mkdir(mode=0o700)
code=r'''
from pathlib import Path
import base64,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k214-baseline/boot-id-private.txt').read_bytes()
keys={p.name:base64.b64encode(p.read_bytes()).decode() for p in Path('/etc/apk/keys').glob('*.pub') if p.is_file()}
assert keys and all('PRIVATE KEY' not in base64.b64decode(value).decode(errors='ignore') for value in keys.values())
repos={str(p):p.read_text() for p in [Path('/etc/apk/repositories'),*Path('/etc/apk/repositories.d').glob('*.list')] if p.is_file()}
print(json.dumps(dict(keys=keys,repositories=repos)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);record=json.loads(p.stdout)
for name,value in record['keys'].items():
    assert Path(name).name==name and name.endswith('.pub');(destination/name).write_bytes(base64.b64decode(value))
(host.PRIVATE/'phone-repositories-private.json').write_text(json.dumps(record['repositories'],indent=2)+'\n')
print(json.dumps(dict(stage=214,already_trusted_phone_public_keys_retrieved=len(record['keys']),private_keys_not_requested_or_copied=True,repository_configuration_saved_privately=True,no_device_mutation=True)))
