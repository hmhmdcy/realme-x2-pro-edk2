from pathlib import Path
import hashlib
import json
import tarfile
import host

pid = int((host.PRIVATE/'kmsg-worker-pid-private.txt').read_text())
worker = int((host.PRIVATE/'original-cycles-worker-pid-private.txt').read_text())
code = '''from pathlib import Path
import json,os,signal,time
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt').read_bytes()
target=Path('/proc/%d/cmdline')
assert not target.exists() or b'run-original-cycles.py' not in target.read_bytes(), 'Inspect a still-live original cycle worker'
pid=%d
p=Path('/proc')/str(pid)
live=p.exists() and b'kmsg-collector.py' in (p/'cmdline').read_bytes()
if live:os.kill(pid,signal.SIGTERM)
deadline=time.monotonic()+5
summary=Path('/var/lib/samurai/k186-candidate-kmsg/summary.json')
while not summary.exists() and time.monotonic()<deadline:time.sleep(.1)
assert summary.exists()
print(json.dumps(dict(cycle_worker_terminal=True,kmsg_handle_was_live=live,kmsg_summary=json.loads(summary.read_text()))))
''' % (worker,pid)
p=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'failed-trial-workers-final-private.json').write_bytes(p.stdout)
print(p.stdout.decode().strip())
names=['k186-reboot-runtime','k186-load-fastrpc','k186-load-fastrpc-r2',
    'k186-original-cycle1','k186-original-cycles','k186-candidate-kmsg','k186-candidate-failure']
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k186-candidate-failure-private.tar.gz '+' '.join(names)+' && sha256sum /tmp/k186-candidate-failure-private.tar.gz',timeout=55)
digest=p.stdout.decode().split()[0]
path=host.PRIVATE/'k186-candidate-failure-private.tar.gz'
host.download('/tmp/k186-candidate-failure-private.tar.gz',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
folder=host.PRIVATE/'candidate-failure-evidence-private'
with tarfile.open(path) as tar:tar.extractall(folder,filter='data')
ref=Path(__file__).resolve().parent
for name,source in [('candidate-runtime-failure-validation.json','k186-candidate-failure/summary.json'),
    ('reboot-runtime-validation.json','k186-reboot-runtime/summary.json'),
    ('candidate-kmsg-validation.json','k186-candidate-kmsg/summary.json')]:
    data=json.loads((folder/source).read_text());data['evidence_archive_sha256']=digest
    (ref/name).write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'failed_trial_archive_sha_verified':True,'native_failure_kept':True,'reports_exported':3}))
