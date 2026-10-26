from pathlib import Path
import json
out = Path('/mnt/e/edk2-samurai-out/kernel92')
def parse(path):
    return dict(s.split('=',1) for s in path.read_text().splitlines() if s.startswith('CONFIG_') and '=' in s)
before = parse(out/'config-before')
after = parse(Path('/home/cy122/x2pro-linux/linux/.config'))
changes = {key:{'before':before.get(key),'after':after.get(key)} for key in before.keys()|after.keys() if before.get(key)!=after.get(key)}
requested = parse(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel92/connectivity-builtins.config'))
assert all(after.get(k)==v for k,v in requested.items())
crypto = {'CONFIG_CRYPTO_KPP2','CONFIG_CRYPTO_KPP','CONFIG_CRYPTO_ECDH','CONFIG_CRYPTO_ECC'}
assert all(k.startswith('CONFIG_BT') or k.startswith('CONFIG_NFC') or k in crypto for k in changes)
assert all(v['after']=='y' for v in changes.values())
(out/'config-validation.json').write_text(json.dumps(changes,indent=2)+'\n')
print('PASS: only Bluetooth/NFC built-ins and selected dependencies changed', len(changes))
