from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'independent-sensor-pm-validation.json').read_text())['independent_resume_and_suspend_verified']
p=host.ssh('python3 -',input=(here/'capture-user-libcamera.py').read_bytes(),timeout=100);(host.PRIVATE/'user-capture-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'user-libcamera-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
