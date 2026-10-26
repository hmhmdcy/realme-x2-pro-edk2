from pathlib import Path
import hashlib
import host

ref = Path(__file__).resolve().parent
source = (ref / 'test-bluez-scan.py').read_text()
old = "save('objects-before-private.json',objects); assert all(not v.get('org.bluez.Device1',{}).get('Connected',False) and not v.get('org.bluez.Device1',{}).get('Paired',False) and not v.get('org.bluez.Device1',{}).get('Bonded',False) for v in objects.values())"
new = """save('objects-before-private.json',objects)
    existing={str(path):{key:bool(value['org.bluez.Device1'].get(key,False)) for key in ('Paired','Bonded')} for path,value in objects.items() if 'org.bluez.Device1' in value}
    assert all(not v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values())"""
assert source.count(old) == 1
source = source.replace(old, new)
old = "assert all(not d.get('Connected',False) and not d.get('Paired',False) and not d.get('Bonded',False) for d in devices.values())"
new = """assert all(not d.get('Connected',False) for d in devices.values())
        for device,flags in existing.items():
            assert device in devices and all(bool(devices[device].get(key,False))==value for key,value in flags.items())
        assert all(not d.get('Paired',False) and not d.get('Bonded',False) for path,d in devices.items() if path not in existing)"""
assert source.count(old) == 1
source = source.replace(old, new)
source = source.replace('paired_connected_bonded=False', 'no_new_pairing_or_connection=True,preexisting_pairs_preserved=True')
source = source.replace('dict(kernel=183,rounds=rounds,', 'dict(kernel=183,rounds=rounds,preexisting_pair_count=sum(v["Paired"] for v in existing.values()),')
# Avoid an unbound summary variable if failure precedes GetManagedObjects.
source = source.replace('signals=[]; health=[];', 'existing={}; signals=[]; health=[];')
path = ref / 'test-bluez-scan-preserve-pairs.py'
path.write_text(source)
host.upload(path, '/var/lib/samurai/k185-tools/' + path.name)
host.upload(ref / 'setup-scan-policy.py', '/var/lib/samurai/k185-tools/setup-scan-policy.py')
host.ssh('python3 /var/lib/samurai/k185-tools/setup-scan-policy.py', timeout=40)
result = host.ssh('nohup python3 /var/lib/samurai/k185-tools/test-bluez-scan-preserve-pairs.py /var/lib/samurai/k185-scan-before-v2 > /var/lib/samurai/k185-scan-before-v2-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'scan-before-v2-worker-pid-private.txt').write_bytes(result.stdout)
print('Temporary reconnect policy applied; baseline scans started with existing pairing preserved.')
