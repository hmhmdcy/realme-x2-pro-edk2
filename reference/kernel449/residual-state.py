from pathlib import Path
import json,shlex,sys
import host
HERE=Path(__file__).resolve().parent
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2','r3']
code=r'''from pathlib import Path
import json
root='/var/lib/samurai/k449-lifecycle-user-r1';residual=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
  if not args:continue
  app=Path(args[0]).name in ['lifecycle','gst-sustained','camss_ipa_proxy','pipeline-fixture'] and any('k449-user-r1-' in x or root in x for x in args)
  helper=len(args)>1 and args[1] in [root+'/worker.py',root+'/conditions-observer.py']
  if app or helper:residual.append(int(p.name))
 except OSError:pass
dirs=[str(p) for p in Path('/run/user/10000').glob('k449-user-r1-*')]
print(json.dumps(dict(processes=residual,user_directories=dirs,passed=not residual and not dirs)))
'''.replace('k449-lifecycle-user-r1','k449-lifecycle-user-'+attempt).replace('k449-user-r1-','k449-user-'+attempt+'-')
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();data=json.loads(q.stdout)
(host.PRIVATE/('residual-'+attempt+'-private.json')).write_bytes(q.stdout);assert data['passed'],data
r=dict(stage=449,attempt=attempt,worker_client_proxy_observer_exited=True,temporary_user_payloads_removed=True,passed=True)
(HERE/('residual-'+attempt+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n');(HERE/'residual-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
