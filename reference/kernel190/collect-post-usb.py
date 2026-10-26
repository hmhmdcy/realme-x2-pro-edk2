from pathlib import Path
import hashlib,json,subprocess
import host
ref=Path(__file__).resolve().parent
try:p=host.ssh('python3 -',input=(ref/'post-usb-state.py').read_bytes(),timeout=60)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/'post-usb-failure-private.log').write_bytes(e.stdout+e.stderr);raise SystemExit('Post USB collection failed')
report=json.loads(p.stdout);path=host.PRIVATE/'usb-supplement-private.tar.gz'
host.download('/var/lib/samurai/k190-post-usb/usb-supplement-private.tar.gz',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==report['supplement_sha256']
report['supplement_host_hash_verified']=True
(ref/'post-usb-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
