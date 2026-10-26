from pathlib import Path
import hashlib,json,re,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(out/'wifi-5ghz-once-private.tar.gz') as tf:
 data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 sha,name=line.split(None,1);assert hashlib.sha256(data[name.strip().removeprefix('./')]).hexdigest()==sha
with tarfile.open(out/'wifi-baseline-private.tar.gz') as tf:
 base={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
assert data['boot-id-private.txt']==base['boot-id-private.txt']
def freq(name):
 match=re.search(r'freq: ([\d.]+)',data.get(name,b'').decode());return float(match[1]) if match else None
def result(name):
 vals=data.get(name,b'').decode().split()
 return dict(http_status=int(vals[0]),bytes=int(vals[1]),seconds=float(vals[2])) if len(vals)==4 else None
def errors(blob):
 text=blob.decode()
 return {name:len(re.findall(pattern,text)) for name,pattern in {
  'modem_fatal':r'(?:modem.*fatal|Fatal error.*modem)',
  'gpu_fault':r'\*\*\* gpu fault',
  'dpu_timeout':r'frame done timeout',
  'key_install_timeout':r'failed to install key',
  'ath10k_crash':r'(?:ath10k.*firmware crashed|ath10k.*firmware crash)',
  'reason7_deauth':r'deauthenticated.*Reason: 7',
  'call_trace':r'Call trace:'}.items()}
before=errors(data['dmesg-before-private.txt']);after=errors(data['dmesg-after-private.txt'])
assert all(after[k]>=before[k] for k in before)
samples=[float(l.split()[0]) for l in data.get('samples.txt',b'').decode().splitlines()]
report=dict(current_kernel=126,test_exit=int(data['test-exit.txt']),
 archive_sha256=hashlib.sha256((out/'wifi-5ghz-once-private.tar.gz').read_bytes()).hexdigest(),
 same_boot=True,test_network_pass=data.get('network-result.txt',b'').strip()==b'PASS',
 verified_5ghz_frequency_mhz=freq('link-5ghz-private.txt'),
 gateway_packets_received=int(re.search(r'(\d+) packets received',data.get('gateway-private.txt',b'').decode())[1]) if re.search(r'(\d+) packets received',data.get('gateway-private.txt',b'').decode()) else None,
 https=result('https-result-private.txt'),apkindex_https=result('index-result-private.txt'),
 index_package_count=int(data.get('index-package-count.txt',b'0')),
 stability_samples=len(samples),stability_seconds=round(samples[-1]-samples[0],2) if samples else 0,
 all_samples_5ghz=bool(samples) and all(freq(f'link-sample-{n}-private.txt')==5180 for n in range(len(samples))),
 restored_original_uuid=data['restored-uuid-private.txt']==base['active-uuid-private.txt'],
 restored_original_frequency_mhz=freq('link-restored-private.txt'),
 restore_exit=int(data['restore-exit.txt']),clone_removed=int(data.get('remove-exit.txt',b'1'))==0,
 logging_restored=int(data['logging-restore-exit.txt'])==0,
 mac_unchanged=data['mac-before-private.sha256']==data['mac-after-private.sha256'],
 new_faults={k:after[k]-before[k] for k in before},taint=int(data['taint-after.txt']),
 modem_running=data['modem-after.txt'].strip()==b'running',
 desktop_processes_present=bool(data['phosh-after.txt'].strip()) and bool(data['phoc-after.txt'].strip()),
 permanent_profiles_unchanged=True,nv_sensor_vendor_sources_unchanged=True,
 coldboot_suspend_longrun_not_accepted=True,goal_complete=False)
for key in ['profile-files-check.txt','nv-check.txt','source-check.txt','vendor-check.txt']:
 assert all(l.endswith(': OK') for l in data[key].decode().splitlines())
(r/'reference/kernel128/5ghz-once-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
