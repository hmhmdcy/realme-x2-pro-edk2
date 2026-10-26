from pathlib import Path
import json,subprocess,sys
import host
phase=sys.argv[1];assert phase in ['before','before-r2','after'];ref=Path(__file__).resolve().parent
try:p=host.ssh('python3 - '+phase,input=(ref/'probe-validity.py').read_bytes(),timeout=70)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/('validity-'+phase+'-failed-private.log')).write_bytes(e.stdout+e.stderr);raise SystemExit('Validity query failed; private details retained')
report=json.loads(p.stdout);(ref/('validity-'+phase+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
