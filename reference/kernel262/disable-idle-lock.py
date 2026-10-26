"""Honor the user's request with normal GSettings and ScreenSaver APIs."""
from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,subprocess,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
out=root/'k262-lock-policy';assert not out.exists();out.mkdir(mode=0o700)
desktops=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()=='phosh':desktops.append(p)
 except OSError:pass
assert len(desktops)==1
env={k.decode():v.decode() for x in (desktops[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
def run(args):
 q=subprocess.run(args,env=env,preexec_fn=demote,capture_output=True,text=True,timeout=8)
 return dict(exit=q.returncode,stdout=q.stdout.strip(),stderr=q.stderr.strip())
policies=[('org.gnome.desktop.screensaver','lock-enabled','false'),('org.gnome.desktop.session','idle-delay','uint32 0')]
before={s+':'+k:run(['gsettings','get',s,k]) for s,k,v in policies}
state=run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'])
(out/'before-private.json').write_text(json.dumps(dict(settings=before,lock=state),indent=2)+'\n')
changed=[]
for schema,key,value in policies:
 assert before[schema+':'+key]['exit']==0
 if before[schema+':'+key]['stdout']!=value:
  assert run(['gsettings','set',schema,key,value])['exit']==0;changed.append(schema+':'+key)
unlock=run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.SetActive','false'])
time.sleep(1)
after=run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'])
report=dict(stage=262,automatic_lock_already_disabled=not changed,settings_changed=changed,lock_before=state,normal_set_active_false=unlock,lock_after=after,unlocked=after['exit']==0 and after['stdout']=='(false,)',no_password_or_pam_changes=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'lock-policy-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(Path(__file__).parent/'lock-policy-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
