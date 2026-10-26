from pathlib import Path
import json,hashlib,tarfile,re,configparser
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129')
with tarfile.open(out/'reboot-auto-network-private.tar.gz') as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in d['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(d[n.removeprefix('./')]).hexdigest()==h
assert d['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
assert d['exit.txt']==b'0\n' and d['result.txt']==b'PASS\n' and d['taint.txt']==b'0\n'
assert d['profile-private.nmconnection']==(out.parent/'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes() and d['profile-owner.txt']==b'0:0:600\n'
c=configparser.ConfigParser(interpolation=None);c.read_string(d['profile-private.nmconnection'].decode());assert c['connection']['uuid']==d['active-uuid-private.txt'].decode().strip()==d['uuid-after-private.txt'].decode().strip()
assert 'band' not in c['wifi']
for name in ['link-before-private.txt','link-after-private.txt',*[f'link-{i}-private.txt' for i in range(6)]]:assert re.search(rb'freq: 5180(?:[.]0)?\s',d[name])
assert re.search(rb'3 packets transmitted, 3 (?:packets )?received, 0% packet loss',d['gateway-private.txt'])
https=d['https-result.txt'].decode().split();index=d['index-result.txt'].decode().split();packages=int(d['index-packages.txt'])
assert https[0]=='200' and int(https[1])==len(d['https-body.txt']) and int(https[1])>0
assert index[0]=='200' and int(index[1])==len(d['APKINDEX.tar.gz']) and packages>5000
assert b'APKINDEX\n' in d['index-members.txt']
samples=d['samples.txt'].decode().splitlines();duration=float(samples[-1].split()[0])-float(samples[0].split()[0]);assert len(samples)==6 and duration>=50
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
before=d['dmesg-before-private.txt'];after=d['dmesg-after-private.txt'];assert after.startswith(before);new=after[len(before):].decode()
faults=['frame done timeout','*** gpu fault','Unhandled context fault','WARNING:','BUG:','Oops:','failed to install key','failed to remove peer key','timed out waiting peer','firmware crashed']
counts={f:new.count(f) for f in faults};assert all(x==0 for x in counts.values())
assert b'unable to open an initial console' not in after
report=dict(current_kernel=129,actual_new_boot_auto_connected_without_explicit_activation=True,current_frequency_mhz=5180,original128_profile_credentials_uuid_mac_policy_byte_exact=True,profile_root0600=True,gateway_ping3_pass=True,https_status=200,https_bytes=int(https[1]),index_https_status=200,index_bytes=int(index[1]),index_packages=packages,index_gzip_tar_structure_pass=True,samples=6,duration_seconds=duration,all11_sources_preserved=True,new_fault_counts=counts,console_warning_count=0,physical_coldboot_suspend_and_long_run_not_claimed=True,goal_complete=False)
for folder in [ref,out]:(folder/'reboot-autoconnect-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
