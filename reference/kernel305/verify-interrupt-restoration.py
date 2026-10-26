"""Disambiguate expected interrupted exit from restoration failure, then re-open."""
from pathlib import Path
import hashlib,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'four-camera-regression-validation.json').read_text())['passed']
source=(HERE.parent/'kernel300/pipeline-fixture.c').read_text()
old=' if(saved&&restore(media))result=1;'
assert source.count(old)==1
source=source.replace(old,' int restored=saved?restore(media):-1;\n if(restored)result=1;\n printf("FIXTURE_RESTORATION result=%d\\n",restored);')
(HERE/'pipeline-fixture.c').write_text(source)
binary=host.PRIVATE/'pipeline-fixture305-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
 '-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'pipeline-fixture.c'),'-o',str(binary)],capture_output=True,timeout=30)
(host.PRIVATE/'fixture305-compile-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,q.stderr.decode()
digest=hashlib.sha256(binary.read_bytes()).hexdigest()
code=r'''
from pathlib import Path
import hashlib,sys
p=Path('/run/samurai305-tools/pipeline-fixture305');assert not p.exists()
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==SHA
p.write_bytes(data);p.chmod(0o755);print('DIAGNOSTIC_FIXTURE_STAGED')
'''.replace('SHA',repr(digest))
q=host.ssh('python3 -c '+shlex.quote(code),input=binary.read_bytes(),timeout=20);print(q.stdout.decode())
code=r'''
from pathlib import Path
import json,os,pwd,re,signal,subprocess,time
root=Path('/var/lib/samurai/k305-interrupt-restoration-r1');assert not root.exists();root.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name)
before=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'])
(root/'graph-before-private.txt').write_bytes(before)
rows=[]
for index in range(2):
 p=subprocess.Popen(['/run/samurai305-tools/pipeline-fixture305','/dev/media0','/usr/sbin/cam','-c',
  '/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','--capture='+('10000' if index==0 else '12')],
  env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 interrupted=False
 try:stdout,stderr=p.communicate(timeout=3 if index==0 else 20)
 except subprocess.TimeoutExpired:
  assert index==0
  interrupted=True;p.send_signal(signal.SIGINT);stdout,stderr=p.communicate(timeout=10)
 (root/(str(index)+'-stdout-private.log')).write_bytes(stdout);(root/(str(index)+'-stderr-private.log')).write_bytes(stderr)
 seq=[int(n) for n in re.findall(rb'seq:\s*(\d+)',stdout)]
 after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'])
 row=dict(interrupted=interrupted,frames=len(seq),fixture_exit=p.returncode,
  child_exit_normal=b'FIXTURE_CHILD status=0 exited=1 exit=0 signalled=0' in stdout,
  graph_restored=before==after,all_saved_formats_selections_controls_videos_restored=b'FIXTURE_RESTORATION result=0' in stdout,
  monotonic_sequence=bool(seq) and all(b>a for a,b in zip(seq,seq[1:])))
 row['passed']=row['child_exit_normal'] and row['graph_restored'] and row['all_saved_formats_selections_controls_videos_restored'] and row['monotonic_sequence'] and (interrupted and len(seq)>=12 and p.returncode==1 if index==0 else not interrupted and len(seq)==12 and p.returncode==0)
 rows.append(row);assert row['passed']
report=dict(stage=305,rows=rows,passed=all(r['passed'] for r in rows),original_fixture_interrupted_exit_ambiguous=True,explicit_restoration_result_added=True)
(root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=45)
(host.PRIVATE/'interrupt-restoration-response-private.log').write_bytes(q.stdout+q.stderr)
report=json.loads(q.stdout)
report.update(fixture_source_sha256=hashlib.sha256(source.encode()).hexdigest(),fixture_binary_sha256=digest,werror_compile=True)
(HERE/'interrupt-restoration-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['passed']
