from pathlib import Path
import hashlib,json
import host

here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k204-bt-tools';host.ssh('test -d '+dest+' && test -e /var/lib/samurai/k204-bt-scan-pm/summary.json && test ! -e /var/lib/samurai/k204-bt-scan-pm-r2')
for name in ['test-powered-suspend.py','test-bt-scan-pm.py']:host.upload(here/name,dest+'/'+name)
policy=(here/'setup-scan-policy.py').read_text().replace('k204-bt-policy','k204-bt-policy-r2')
p=host.ssh('python3 -',input=policy.encode(),timeout=80);(host.PRIVATE/'bt-policy-r2-private.log').write_bytes(p.stdout+p.stderr)
command='nohup python3 '+dest+'/test-bt-scan-pm.py > /var/lib/samurai/k204-bt-test-worker-private.log 2>&1 < /dev/null & echo $!'
p=host.ssh(command);prior=host.PRIVATE/'bt-test-worker-pid-private.txt';saved=host.PRIVATE/'bt-test-r1-worker-pid-private.txt';assert not saved.exists();prior.rename(saved);prior.write_bytes(p.stdout);print('Started corrected Not-Powered preflight test; previous failure retained. Poll this worker, do not resubmit.')
