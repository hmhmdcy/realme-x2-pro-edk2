from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
ready=json.loads((HERE/'framework-staging-validation.json').read_text());assert ready['passed'] and ready['run']==run
root=ready['root']
code="""from pathlib import Path
import subprocess,json,os
root=Path(ROOT);proof=json.loads((root/'proof.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
assert not any((root/n).exists() for n in ['state.json','launch.json','worker.log'])
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid,root=str(root));f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))
""".replace('ROOT',repr(root))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);(host.PRIVATE/('framework-launch-'+run+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
