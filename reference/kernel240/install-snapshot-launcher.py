"""Persist only Snapshot's proven CPU-rendering environment; preserve APK files."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
for name in ['k240-snapshot-mmap','k240-snapshot-mmap-r2']:
 p=r/name;assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
 v=json.loads((p/'summary.json').read_text());assert v['diagnostic_completed'] and v['camera_devices_suspended'] and not any(v['fault_delta'].values())
flow=json.loads((r/'k240-snapshot-mmap/frame-flow-analysis.json').read_text())
assert flow['gtk_cpu_mmap_download_count']>=20 and flow['pipewire_new_buffer_count']>=20
for p in Path('/proc').glob('[0-9]*'):
 try:assert (p/'comm').read_text().strip()!='snapshot','Existing camera app; do not duplicate or kill'
 except FileNotFoundError:pass
out=r/'k240-snapshot-launcher-transaction';assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=240,state='applying',installed_overrides=[])
(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
u=pwd.getpwuid(10000);base=Path(u.pw_dir)/'.local/share'
original=json.loads((r/'k240-snapshot-launcher-audit/original-launch-files-private.json').read_text())
sources={}
for rel,text in original.items():
 p=Path('/usr/share')/rel;assert p.read_text()==text;sources[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 env='GSK_RENDERER=cairo GDK_DISABLE=gl,vulkan,offload'
 if rel.endswith('.desktop'):
  assert text.count('Exec=snapshot\n')==1 and text.count('DBusActivatable=true\n')==1
  text=text.replace('Exec=snapshot\n','Exec=/usr/bin/env '+env+' /usr/bin/snapshot\n').replace('DBusActivatable=true\n','DBusActivatable=false\n')
  text=re.sub(r'^Name=Camera$', 'Name=Camera (Snapshot)',text,flags=re.M)
  text=re.sub(r'^Name\[zh_CN\]=.*$', 'Name[zh_CN]=相机（Snapshot）',text,flags=re.M)
  text=re.sub(r'^Name\[zh_TW\]=.*$', 'Name[zh_TW]=相機（Snapshot）',text,flags=re.M)
 else:
  assert text.count('Exec=/usr/bin/snapshot --gapplication-service\n')==1
  text=text.replace('Exec=/usr/bin/snapshot --gapplication-service\n','Exec=/usr/bin/env '+env+' /usr/bin/snapshot --gapplication-service\n')
 p=base/rel;assert not p.exists(),str(p)
 for directory in reversed([q for q in p.parents if q!=Path(u.pw_dir) and Path(u.pw_dir) in q.parents]):
  if not directory.exists():directory.mkdir();os.chown(directory,u.pw_uid,u.pw_gid);directory.chmod(0o755)
  assert directory.is_dir() and not directory.is_symlink() and directory.stat().st_uid==u.pw_uid
 (out/(p.name+'-before-private.json')).write_text(json.dumps(dict(existed=False,system_sha256=sources[rel]))+'\n')
 temp=p.with_name(p.name+'.k240-new');assert not temp.exists()
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
 with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
 os.chown(temp,u.pw_uid,u.pw_gid);os.chmod(temp,0o644);os.replace(temp,p)
 state['installed_overrides'].append(rel);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
 (out/p.name).write_text(text)
 assert p.read_text()==text and p.stat().st_uid==u.pw_uid
 assert hashlib.sha256((Path('/usr/share')/rel).read_bytes()).hexdigest()==sources[rel]
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/10000/bus')
inner="from gi.repository import Gio;import json;d=Gio.DesktopAppInfo.new('org.gnome.Snapshot.desktop');assert d is not None;print(json.dumps(dict(filename=d.get_filename(),commandline=d.get_commandline(),name=d.get_name(),dbus_activatable=d.get_boolean('DBusActivatable'))))"
p=subprocess.run(['/usr/bin/python3','-c',inner],env=env,preexec_fn=demote,capture_output=True,timeout=8)
(out/'gio-resolution-private.json').write_bytes(p.stdout);(out/'gio-stderr-private.txt').write_bytes(p.stderr);assert p.returncode==0
info=json.loads(p.stdout);assert info['filename']==str(base/'applications/org.gnome.Snapshot.desktop') and not info['dbus_activatable']
assert 'GSK_RENDERER=cairo' in info['commandline'] and 'GDK_DISABLE=gl,vulkan,offload' in info['commandline']
manifest={rel:dict(sha256=hashlib.sha256((base/rel).read_bytes()).hexdigest(),uid=(base/rel).stat().st_uid,mode=(base/rel).stat().st_mode&0o777) for rel in original}
(out/'override-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
report=dict(stage=240,only_snapshot_per_user_launcher_and_dbus_environment_changed=True,override_count=2,
 desktop_and_dbus_service_both_set_cpu_renderer=True,desktop_direct_exec_selected=True,native_Gio_resolves_user_override=True,
 original_signed_package_files_unchanged=True,no_global_desktop_or_gpu_settings_changed=True,no_kernel_changes=True,
 display_name='相机（Snapshot）',rollback='Remove the two exact per-user overrides after checking saved manifest hashes',
 source_buffer_pool_default_preserved=True,preview_frame_backpressure_and_photography_still_open=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
state['state']='verified';(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'snapshot-launcher-install-host-private.log').write_bytes(p.stdout+p.stderr)
data=json.loads(p.stdout);(R/'snapshot-launcher-install-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
