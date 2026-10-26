from pathlib import Path
import hashlib,json,re,shlex,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2')
private=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(private/'wifi-baseline-private.tar.gz') as tf:
 data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 sha,name=line.split(None,1)
 assert hashlib.sha256(data[name.strip().removeprefix('./')]).hexdigest()==sha
profile=data['profile-private.txt'].decode()
fields={}
for line in profile.splitlines():
 if ':' in line:
  name,value=line.split(':',1);fields[name.strip()]=value.strip()
ssid=fields['802-11-wireless.ssid']
def unescape_fields(line):
 result=[];current='';escaped=False
 for char in line:
  if escaped:current+=char;escaped=False
  elif char=='\\':escaped=True
  elif char==':':result.append(current);current=''
  else:current+=char
 result.append(current);assert not escaped
 return result
aps=[unescape_fields(line) for line in data['scan-private.txt'].decode().splitlines()]
assert all(len(ap)==6 for ap in aps)
old=(private.parent/'kernel109/wpa-5g-private.conf').read_text()
def wpa_field(name):
 values=re.findall(r'^\s*'+name+r'\s*=\s*(.+?)\s*$',old,re.M)
 assert len(values)==1
 return bytes.fromhex(values[0]).decode() if name=='ssid' and not values[0].startswith('"') else shlex.split(values[0])[0]
old_ssid=wpa_field('ssid');psk=wpa_field('psk')
current_match=[ap for ap in aps if ap[0]==ssid]
old_match=[ap for ap in aps if ap[0]==old_ssid]
report=dict(current_kernel=126,current_boot_verified=True,nm_version=data['nm-version.txt'].decode().strip(),
 baseline_frequency_mhz=float(re.search(r'freq: ([\d.]+)',data['link-before-private.txt'].decode())[1]),
 persistent_profile_band=fields['802-11-wireless.band'],scan_rescan_exit=int(data.get('rescan-exit.txt',b'0')),
 scanned_ap_count=len(aps),scanned_5ghz_ap_count=sum(float(a[2].split()[0])>=5000 for a in aps),
 current_ssid_matches=[dict(freq_mhz=float(a[2].split()[0]),channel=int(a[3]),signal=int(a[4]),security=a[5]) for a in current_match],
 previous_5ghz_ssid_same_as_current=ssid==old_ssid,
 previous_5ghz_ssid_matches=[dict(freq_mhz=float(a[2].split()[0]),channel=int(a[3]),signal=int(a[4]),security=a[5]) for a in old_match],
 previous_psk_matches_current=psk==fields['802-11-wireless-security.psk'],
 nv_sources_unchanged=True,source_hashes_unchanged=True,physical_5ghz_not_yet_tested=True)
for key in ['nv-check.txt','source-check.txt','vendor-check.txt']:assert all(l.endswith(': OK') for l in data[key].decode().splitlines())
(root/'reference/kernel128/wifi-baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
