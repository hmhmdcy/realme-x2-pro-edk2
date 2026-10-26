"""Remove the temporary copy opt-in after verifying the installed common path."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent
for mode in range(6000080,6000085):
 d=json.loads((R/('system-'+str(mode)+'-validation.json')).read_text());assert d['diagnostic_completed'] and d['production_service_identities_and_system_maps_verified']
old=json.loads((R.parent/'kernel262/launcher-install-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,stat,subprocess,sys
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k264-launcher-transaction';assert not out.exists();out.mkdir();old=json.loads(sys.argv[1]);user=pwd.getpwuid(10000)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
expected={i['file']:i['after_sha256'] for i in old['launcher_files']};items=[]
for relative in ['.local/share/applications/org.gnome.Snapshot.desktop','.local/share/dbus-1/services/org.gnome.Snapshot.service']:
 p=Path(user.pw_dir)/relative;data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==expected[p.name]
 s=data.decode();assert s.count('SAMURAI_CAMERA_COPY=1 ')==1 and 'GSK_RENDERER=cairo' in s and 'GDK_DISABLE=gl,vulkan,offload' in s
 new=s.replace('SAMURAI_CAMERA_COPY=1 ','').encode();assert b'SAMURAI_CAMERA_COPY' not in new
 info=p.stat();(out/(p.name+'-before-private')).write_bytes(data);temp=p.with_name(p.name+'.k264-tmp');assert not temp.exists();temp.write_bytes(new);temp.chmod(stat.S_IMODE(info.st_mode));os.chown(temp,info.st_uid,info.st_gid);temp.replace(p)
 (out/(p.name+'-after-private')).write_bytes(new);items.append(dict(file=p.name,before_sha256=hashlib.sha256(data).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest()))
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh');raw={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]};env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS']};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
q=subprocess.run(['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method','org.freedesktop.DBus.ReloadConfig'],env=env,preexec_fn=demote,capture_output=True,timeout=5);(out/'reload-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
report=dict(stage=264,copy_opt_in_removed=True,launcher_files=items,existing_cpu_renderer_configuration_retained=True,session_dbus_reload_passed=True,app_binary_not_modified=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps(old)),input=code.encode(),timeout=25,check=False);(host.PRIVATE/'launcher-update-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'Inspect saved file transaction before retrying'
d=json.loads(r.stdout);(R/'launcher-update-validation.json').write_text(json.dumps(d,indent=2)+'\n')
for name in ['org.gnome.Snapshot.desktop','org.gnome.Snapshot.service']:
 q=host.ssh('cat '+shlex.quote('/var/lib/samurai/k264-launcher-transaction/'+name+'-after-private'))
 (R.parents[1]/'linux-port/camera/snapshot-launcher'/name).write_bytes(q.stdout)
print(json.dumps(d,indent=2))
