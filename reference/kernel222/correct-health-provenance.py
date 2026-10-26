from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
path=here/'final-health.py';text=path.read_text();assert 'no_camera_capture_or_engine_start_or_reboot=True' in text
text=text.replace('no_camera_capture_or_engine_start_or_reboot=True','camera_metadata_captures_performed=True,no_gnss_engine_start_or_flash_or_reboot=True').replace('uim_slot_status_lines=slot_lines','uim_slot_status_lines_historical_stage221=slot_lines');compile(text,'health222-corrected-provenance','exec');path.write_text(text)
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k222-baseline/boot-id-private.txt').read_bytes()
out=root/'k222-final-health';p=out/'summary.json';backup=out/'summary-before-provenance-correction.json';assert not backup.exists();backup.write_bytes(p.read_bytes())
r=json.loads(p.read_text());assert r.pop('no_camera_capture_or_engine_start_or_reboot') is True
r['uim_slot_status_lines_historical_stage221']=r.pop('uim_slot_status_lines');r.update(camera_metadata_captures_performed=True,no_gnss_engine_start_or_flash_or_reboot=True,initial_copied221_capture_provenance_flag_corrected=True)
assert json.loads((root/'k222-capture-request-gap-r7/summary.json').read_text())['program_exit']==0
p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'health-provenance-correction-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
