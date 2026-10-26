from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
paths=list((root/'k190-mm-build').rglob('mm-iface-modem-location.c'));assert len(paths)==1
s=paths[0].read_text();lines=s.splitlines();blocks=[]
for i,l in enumerate(lines):
 if 'refresh_rate' in l.lower() and ('get_' in l or '==' in l or '<' in l or 'MAX' in l):blocks.append('\n'.join(lines[max(0,i-5):i+10]))
out=root/'k201-geoclue-install';(out/'mm-iface-modem-location-private.c').write_text(s)
print(json.dumps(dict(path=str(paths[0]),refresh_blocks=blocks[:12])))
