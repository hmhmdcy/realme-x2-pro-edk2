from pathlib import Path
import json,re,tarfile,runpy
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(out/'wifi-5ghz-once-private.tar.gz') as tf:
 data={m.name.removeprefix('./'):tf.extractfile(m).read().decode(errors='replace') for m in tf if m.isfile() and m.name.endswith('.txt')}
before=data['dmesg-before-private.txt'].splitlines();after=data['dmesg-after-private.txt'].splitlines()
assert after[:len(before)]==before
new=after[len(before):]
def redact(text):
 return re.sub(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}','[private MAC]',text)
selected=[redact(line) for line in new if any(x in line for x in ['failed to install key','wmi key ','deauthenticated','authenticated','associated'])]
report=dict(current_kernel=126,key_timeout_and_link_events=selected,needs_key_lifecycle_investigation=True,real_5ghz_data_pass_does_not_erase_timeouts=True)
(r/'reference/kernel128/key-transition-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
print('K126_SOURCE_READY_FOR_READONLY_KEY_LIFECYCLE_INSPECTION')
