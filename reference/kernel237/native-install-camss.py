"""One idle CAMSS replacement, preserving both bound sensor/PMIC drivers."""
from pathlib import Path
import hashlib,json,os,stat,struct,subprocess,tempfile,time,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
out=root/'k237-camss-install';assert not out.exists();out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
state=dict(stage=237,state='running',phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
def save(phase=None):
 if phase:state['phase']=phase
 p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');os.replace(p,out/'state-private.json')
def checked(args,label):
 p=subprocess.run(args,capture_output=True);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label
 return p
sha=lambda data:hashlib.sha256(data).hexdigest()
def note(data):
 off=struct.unpack_from('<Q',data,40)[0];size,count,idx=struct.unpack_from('<HHH',data,58);secs=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)];strings=data[secs[idx][4]:secs[idx][4]+secs[idx][5]]
 found=[data[s[4]:s[4]+s[5]] for s in secs if strings[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id'];assert len(found)==1;return found[0]
def rails():
 result={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-front-','cam-rear-')) or Path('/sys/bus/i2c/devices/1-0004').resolve() in p.resolve().parents:
   result[name]={k:(p/k).read_text().strip() for k in ['state','num_users','microvolts']}
 return result
save();error=None;report=None
try:
 tree=Path('/usr/lib/modules')/os.uname().release;relative='kernel/drivers/media/platform/qcom/camss/qcom-camss.ko';target=tree/relative
 lock=json.loads((root/'k237-tools/install-lock-private.json').read_text());candidate=root/'k237-tools/qcom-camss-unwind237.ko'
 assert sha(candidate.read_bytes())==lock['candidate_sha256'] and sha(target.read_bytes())==lock['original_sha256']
 assert Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()==note(target.read_bytes())
 assert Path('/sys/module/qcom_camss/refcnt').read_text().strip()=='0'
 inventory={str(p.relative_to(tree)):sha(p.read_bytes()) for p in tree.rglob('*') if p.is_file()}
 assert inventory==json.loads((root/'k236-lab-fix/module-inventory-after-private.json').read_text())
 for proc in Path('/proc').glob('[0-9]*'):
  for fd in (proc/'fd').glob('*'):
   try:path=os.readlink(fd)
   except OSError:continue
   assert not path.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')), 'camera client appeared'
 devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
 assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 saved_rails=rails();(out/'rails-before-private.json').write_text(json.dumps(saved_rails,indent=2)+'\n')
 notes={name:Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes() for name in ['qcom_pm8008','qcom_pm8008_imx319_lab','reset_realme_rmx1931_pm8008','imx319','imx471']}
 before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
 backup=out/'before';backup.mkdir(mode=0o700)
 originals=[target]+[p for p in tree.iterdir() if p.is_file()]
 metadata={}
 for p in originals:
  rel=str(p.relative_to(tree));dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());st=p.stat();metadata[rel]=dict(mode=stat.S_IMODE(st.st_mode),uid=st.st_uid,gid=st.st_gid,sha256=sha(p.read_bytes()))
 (out/'backup-metadata-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
 save('unloading-idle-old-camss-once');checked(['rmmod','qcom_camss'],'unload');assert not Path('/sys/module/qcom_camss').exists()
 save('atomic-file-replacement')
 st=target.stat();fd,name=tempfile.mkstemp(prefix='.k237-',dir=target.parent);temp=Path(name)
 with os.fdopen(fd,'wb') as f:f.write(candidate.read_bytes());f.flush();os.fchmod(f.fileno(),stat.S_IMODE(st.st_mode));os.fchown(f.fileno(),st.st_uid,st.st_gid);os.fsync(f.fileno())
 assert sha(temp.read_bytes())==lock['candidate_sha256'];os.replace(temp,target)
 checked(['depmod','-a'],'depmod');save('loading-new-camss-once');checked(['modprobe','qcom_camss'],'load')
 assert Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()==note(candidate.read_bytes())
 checked(['cam','-l'],'cam-list')
 graph=checked(['media-ctl','-d','/dev/media0','-p'],'media').stdout.decode();assert 'imx319 7-0010' in graph and 'imx471 9-0010' in graph
 time.sleep(2)
 assert rails()==saved_rails
 assert all(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==data for name,data in notes.items())
 assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
 after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
 faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()}
 assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 actual={str(p.relative_to(tree)):sha(p.read_bytes()) for p in tree.rglob('*') if p.is_file()}
 changed={n for n in actual if actual[n]!=inventory.get(n)};assert set(actual)==set(inventory)
 assert changed<={relative}|{str(p.relative_to(tree)) for p in tree.iterdir() if p.is_file()}
 assert actual[relative]==lock['candidate_sha256']
 (out/'module-inventory-after-private.json').write_text(json.dumps(actual,indent=2)+'\n')
 report=dict(stage=237,camss_sha256=actual[relative],default_and_loaded_note_match=True,old_idle_camss_replaced_once=True,both_sensors_pmic_provider_kept=True,rails_unchanged=True,both_camera_graphs_present=True,all_camera_pm_suspended=True,taint=0,fault_delta=faults,no_frames_requested=True,module_related_files=len(actual),changed_files=len(changed))
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(exit_code=0)
except BaseException:
 error=traceback.format_exc();(out/'failure-private.txt').write_text(error);state.update(exit_code=1)
finally:
 state.update(state='terminal');save('terminal')
if report:print(json.dumps(report),flush=True)
if error:raise SystemExit(1)
