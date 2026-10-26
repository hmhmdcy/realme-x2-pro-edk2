from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel96');files={}
with tarfile.open(out/'scan-policy.tar') as t:
    for m in t:
        if not m.isfile():continue
        name=Path(m.name).name;assert name not in files
        files[name]=t.extractfile(m).read()
names=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert name in files and name not in names
    assert hashlib.sha256(files[name]).hexdigest()==digest;names.add(name)
assert names==files.keys()-{'SHA256SUMS'}
def info(name):
    line=next(x for x in files[name].decode().splitlines() if x.startswith('command=0x0004 status=0x00 payload='))
    p=bytes.fromhex(line.split('payload=')[1]);assert len(p)>=17
    return p[:6],int.from_bytes(p[13:17],'little')
original,settings_before=info('bt-info-before.txt')
address,settings_policy=info('bt-info-policy.txt')
address_final,settings_final=info('bt-info-final.txt')
assert address==original==address_final
assert settings_policy&1 and not(settings_policy&((1<<1)|(1<<4)))
assert not(settings_final&((1<<0)|(1<<1)|(1<<4)))
for op in ('0009','0007'):assert f'command=0x{op} status=0x00' in files['policy.txt'].decode()
text=files['bt-scan.txt'].decode();assert 'command=0x0023 status=0x00' in text and 'discovering=0' in text
records=re.findall(r'address=([0-9A-F:]+) type=(\d+)',text);assert records
vals=[]
for name in ('display-before.txt','display-after.txt'):
    text=files[name].decode();assert re.search(r'underrun:\s*0\b',text)
    vals.append(int(re.search(r'vsync:\s*(\d+)',text)[1]))
assert vals[1]>vals[0]
assert b'wpa_state=COMPLETED\n' in files['wpa.txt'] and b'freq=5180\n' in files['wpa.txt']
assert len(files['nv-check.txt'].decode().splitlines())==6 and all(x.endswith(': OK') for x in files['nv-check.txt'].decode().splitlines())
assert files['persist-check.txt']==b'/dev/sda2: OK\n'
digest=hashlib.sha256((out/'bt-mgmt-probe-scan-only').read_bytes()).hexdigest()
assert digest in files['helper-sha.txt'].decode()
assert files['result.txt']==b'SCAN_ONLY_POLICY_PASS\n'
report=json.loads((out/'checkpoint-validation.json').read_text())
report.update(scan_policy_verified=True,incoming_connectable=False,bondable=False,final_bt_powered=False,
    scan_policy_private_files_verified=len(names),scan_policy_archive_sha256=hashlib.sha256((out/'scan-policy.tar').read_bytes()).hexdigest(),
    scan_policy_address_type_records=len(set(records)),scan_policy_display_vsync=vals)
(out/'checkpoint-validation-with-scan-policy.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k.startswith('scan_policy') or k in ('final_bt_powered','incoming_connectable','bondable')},indent=2))
