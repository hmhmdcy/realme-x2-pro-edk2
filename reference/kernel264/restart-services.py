"""Restart the two verified orphaned desktop daemons with their standard environments."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'package-install-validation.json').read_text());assert proof['installed']
baseline=json.loads((R/'baseline-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,resource,select,signal,subprocess,sys,time
os.umask(0o077);proof,baseline=json.loads(sys.argv[1]);root=Path('/var/lib/samurai');out=root/'k264-services';assert not out.exists();out.mkdir()
state=dict(stage=264,phase='preflight',terminal=False);processes=[];logs=[]
def save(phase):state['phase']=phase;(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def identity(pid):return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
def env_for(pid):
 raw={k.decode():v.decode() for x in Path('/proc',str(pid),'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
 names=['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_CONFIG_HOME','XDG_CONFIG_DIRS','XDG_DATA_DIRS','XDG_STATE_HOME']
 env={k:v for k,v in raw.items() if k in names or k.startswith(('PIPEWIRE_','WIREPLUMBER_','SPA_','LIBCAMERA_'))}
 assert not any(k in raw for k in ['LD_PRELOAD','LD_LIBRARY_PATH'])
 assert not any(k in env for k in ['PIPEWIRE_CONFIG_DIR','PIPEWIRE_CONFIG_NAME','PIPEWIRE_RUNTIME_DIR','PIPEWIRE_REMOTE','SPA_PLUGIN_DIR'])
 env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin';return env
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
devices=list(baseline['runtime']);assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
for path,digest in proof['payload_sha256'].items():assert hashlib.sha256((Path('/')/path).read_bytes()).hexdigest()==digest
user=pwd.getpwuid(10000);expected={x['name']:x for x in baseline['processes']};assert set(expected)=={'phosh','pipewire','wireplumber'}
for item in expected.values():assert identity(item['pid'])==item['start_ticks']
envs={}
for name in ['pipewire','wireplumber']:
 pid=expected[name]['pid'];p=Path('/proc',str(pid))
 assert (p/'comm').read_text().strip()==name and os.readlink(p/'exe')=='/usr/bin/'+name
 assert (p/'cmdline').read_bytes().split(b'\0')[:-1]==[('/usr/bin/'+name).encode()]
 assert int((p/'status').read_text().split('Uid:',1)[1].split()[0])==user.pw_uid
 envs[name]=env_for(pid)
def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
for name in ['pipewire','wireplumber']:
 q=subprocess.run(['rc-service','--user',name,'status'],env=envs[name],preexec_fn=demote,capture_output=True,timeout=5)
 assert q.returncode==3 and b'stopped' in q.stdout,'Service-manager state changed; inspect before restart'
(out/'environments-before-private.json').write_text(json.dumps(envs,indent=2)+'\n')
save('stopping-verified-old-daemons')
for name in ['wireplumber','pipewire']:
 pid=expected[name]['pid'];fd=os.pidfd_open(pid);assert identity(pid)==expected[name]['start_ticks']
 signal.pidfd_send_signal(fd,signal.SIGTERM);assert select.select([fd],[],[],8)[0],name+' failed to exit cleanly';os.close(fd)
save('starting-standard-daemons')
for name in ['pipewire','wireplumber']:
 log=(out/(name+'-private.log')).open('xb');logs.append(log)
 env=envs[name].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
 if name=='pipewire':
  readfd,writefd=os.pipe();env['PIPEWIRE_NOTIFICATION_FD']=str(writefd)
  p=subprocess.Popen(['/usr/bin/'+name],env=env,preexec_fn=demote,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(writefd,));os.close(writefd)
  assert select.select([readfd],[],[],10)[0] and os.read(readfd,64),'PipeWire readiness missing';os.close(readfd)
 else:p=subprocess.Popen(['/usr/bin/'+name],env=env,preexec_fn=demote,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
 processes.append((name,p))
 assert p.poll() is None
 if name=='wireplumber':
  deadline=time.monotonic()+8
  while time.monotonic()<deadline:
   assert p.poll() is None,'WirePlumber exited'
   if '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in Path('/proc',str(p.pid),'maps').read_text():break
   time.sleep(.1)
  else:raise AssertionError('System libcamera SPA was not loaded')
new=[]
for name,p in processes:
 maps=Path('/proc',str(p.pid),'maps').read_text().splitlines()
 assert any(l.split()[-1]=='/usr/lib/libpipewire-0.3.so.0.1609.0' for l in maps)
 assert not any('/var/lib/samurai/k264-' in l and '.so' in l for l in maps)
 new.append(dict(name=name,pid=p.pid,start_ticks=identity(p.pid)))
assert identity(expected['phosh']['pid'])==expected['phosh']['start_ticks']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for log in logs:log.flush();log.close()
report=dict(stage=264,old_daemons_terminated_with_sigterm=True,no_forced_kill=True,new_processes=new,standard_system_core_and_spa_loaded=True,private_candidate_paths_absent=True,phosh_identity_unchanged=True,camera_devices_suspended=True,openrc_user_services_remain_unmanaged=True,reboot_performed=False,taint=0)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state['terminal']=True;save('verified');print(json.dumps(report))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps([proof,baseline])),input=code.encode(),timeout=65,check=False);(host.PRIVATE/'services-restart-private.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0,'Inspect saved service state and logs; do not replay the restart'
d=json.loads(r.stdout);(R/'services-restart-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
