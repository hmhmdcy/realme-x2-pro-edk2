from pathlib import Path
import host,json

pid=int((host.PRIVATE/'debug-worker-pid-private.txt').read_text().strip())
native=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-debug-nmea';p=Path('/proc/PID_PLACEHOLDER')
running=p.exists() and b'/var/lib/samurai/k208-loc-tools/capture-debug-nmea.py' in (p/'cmdline').read_bytes()
result=dict(running=running,summary_present=(out/'summary.json').exists())
if result['summary_present']:result['result']=json.loads((out/'summary.json').read_text())
elif (out/'progress.json').exists():
    report=json.loads((out/'progress.json').read_text())
    result['progress']={k:report[k] for k in ['original_nmea_mask','temporary_nmea_mask','nmea_messages','nmea_types','pqwm1_reports','pqwm1_parse_errors','positive_cnr_fields','valid_gga','errors'] if k in report}
print(json.dumps(result))
'''.replace('PID_PLACEHOLDER',str(pid))
p=host.ssh('python3 -',input=native.encode(),timeout=25)
(host.PRIVATE/'debug-last-observation-private.json').write_bytes(p.stdout)
value=json.loads(p.stdout)
if not value['running'] and value['summary_present']:
    (Path(__file__).resolve().parent/'debug-nmea-validation.json').write_text(json.dumps(value['result'],indent=2)+'\n')
print(json.dumps(value))
