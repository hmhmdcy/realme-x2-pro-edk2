from pathlib import Path
import hashlib,json,re,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(out/'keytrace-postflash-private.tar.gz') as tf:
 data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 sha,name=line.split(None,1);assert hashlib.sha256(data[name.strip().removeprefix('./')]).hexdigest()==sha
assert data['exit.txt']==b'0\n' and data['debug-mask.txt']==b'0\n'
assert set(re.findall(r'overrun:\s*(\d+)',data['trace-stats.txt'].decode()))=={'0'}
records=[]
for line in data['trace-private.txt'].decode().splitlines():
 m=re.match(r'^\s*\S+-(\d+)\s+\[\d+\]\s+\S+\s+([\d.]+): (\w+): (.*)',line)
 if m:records.append(dict(pid=int(m[1]),time=float(m[2]),event=m[3],message=m[4]))
keys=[]
for i,row in enumerate(records):
 if row['event']!='drv_set_key':continue
 assert row['message'].startswith('phy0 vif:wlan0')
 m=re.search(r'cmd: (\d+).*flags=(0x[0-9a-f]+|0), keyidx=(-?\d+)',row['message']);assert m
 key=dict(cmd=int(m[1]),flags=int(m[2],0),keyidx=int(m[3]))
 returned=next(x for x in records[i+1:] if x['event']=='drv_return_int' and x['pid']==row['pid'])
 key.update(return_code=int(returned['message'].rsplit(' - ',1)[1]),duration_ms=round(1000*(returned['time']-row['time']),3),
  security_indications=sum(x['event']=='ath10k_log_dbg' and 'sec ind ' in x['message'] for x in records[i+1:] if x['time']<=returned['time']),
  wmi_send_count=sum(x['event']=='ath10k_log_dbg' and 'wmi tlv vdev install key' in x['message'] for x in records[i+1:] if x['time']<=returned['time']))
 keys.append(key)
pairwise=[x for x in keys if x['cmd']==1 and x['flags']&8]
installs=[x for x in keys if x['cmd']==0]
assert len(pairwise)==2 and all(x['return_code']==0 and x['duration_ms']<50 and x['security_indications']==0 and x['wmi_send_count']==1 for x in pairwise)
assert len(installs)==4 and all(x['return_code']==0 and x['security_indications']==1 and x['wmi_send_count']==1 for x in installs)
report=dict(current_kernel=128,current_boot_delete_wait_resolved=True,pairwise_delete_count=2,
 pairwise_delete_wait_ms=[x['duration_ms'] for x in pairwise],pairwise_delete_confirmations=0,
 successful_install_count=len(installs),install_return_ms=[x['duration_ms'] for x in installs],
 all_installations_acknowledged=True,trace_overruns=0,raw_wmi_htt_key_dump_disabled=True,
 debug_mask=0,key_operations=keys,archive_sha256=hashlib.sha256((out/'keytrace-postflash-private.tar.gz').read_bytes()).hexdigest(),
 narrow_wcn3990_snoc_patch_real_runtime_pass=True,unforced_disconnect_reason7_not_fixed=True,goal_complete=False)
(r/'reference/kernel128/key-delete-postflash-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
