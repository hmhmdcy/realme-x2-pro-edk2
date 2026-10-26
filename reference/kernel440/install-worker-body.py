"""Coherent r32/r27, three production modules and four private factory profiles."""
import stat
proof=json.loads((root/'proof.json').read_text());dev=Path('/sys/bus/platform/devices/ac10000.icp')
consumers={};new_services={};stopped=False;driver_changed=False;profiles_changed=False;packages_sent=False;verified=False;rollback=False;failure=None;client=None;user_probe=None
before=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines();kernel_anchor=before[-1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def versions():
 result={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if f.get('P') in proof['packages']:result[f['P']]=f['V']
 return result
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def idle():
 wait_idle();deadline=time.monotonic()+5
 while not released(core()) or m2m()['users'] or m2m()['running']:
  assert time.monotonic()<deadline,'IPE still owns active work';time.sleep(.02)
def owner_zero():
 deadline=time.monotonic()+5
 while m2m()['owner_refs']:
  assert time.monotonic()<deadline,'External camera consumer remains';time.sleep(.02)
def regular(record,kind='old'):
 p=Path(record['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 assert sha(p)==record[kind+'_sha256'],str(p)
 assert stat.S_IMODE(s.st_mode)==record['mode'] and s.st_uid==record['uid'] and s.st_gid==record['gid']
def profile_check(kind):
 assert {p.name for p in Path('/etc/libcamera/ipa/camss-vfe').glob('*.yaml')}=={Path(x['path']).name for x in proof['profiles']}
 for row in proof['profiles']:regular(row,kind)
def driver_check(kind):
 for row in proof['modules']:
  regular(row,kind);assert sha('/sys/module/'+row['module']+'/notes/.note.gnu.build-id')==row[kind+'_note_sha256']
 assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
 for name in ['test_cc_mode','test_gamma_mode','test_ltm_mode','test_chain_mode']:assert not Path('/sys/module/camss_icp_a5_m2m/parameters',name).exists()
def atomic_write(target,content,mode,uid,gid):
 target=Path(target);temporary=target.with_name(target.name+'.k440-tmp');assert not temporary.exists()
 assert target.is_file() and not target.is_symlink() and str(target.resolve())==proof['resolved_targets'][str(target)]
 with temporary.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
 os.chmod(temporary,mode);os.chown(temporary,uid,gid);os.replace(temporary,target)
 fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def replace_records(rows,kind):
 for row in rows:
  p=root/row['payload'] if kind=='new' else root/'backup'/row['backup']
  assert sha(p)==row[kind+'_sha256'];atomic_write(row['path'],p.read_bytes(),row['mode'],row['uid'],row['gid'])
def unload():
 if (dev/'m2m_status').exists():idle();owner_zero()
 for name in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
  if Path('/sys/module',name).exists():run(['rmmod',name],'unload-'+name,timeout=20)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()
def load(kind):
 run(['depmod','-a',os.uname().release],'depmod-'+kind,timeout=30)
 run(['modprobe','qcom_camss'],'load-'+kind,timeout=30)
 assert (dev/'driver').resolve().name=='qcom-sm8150-icp';driver_check(kind);idle();owner_zero()
def new_faults():
 lines=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines();assert lines.count(kernel_anchor)==1,'Kernel log anchor unavailable'
 new=lines[lines.index(kernel_anchor)+1:];(root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|crash detected in modem|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed'
 return [line for line in new if re.search(pattern,line)]
try:
 save('preflight')
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==proof['boot_id'] and os.uname().release==proof['uname']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and versions()==proof['old_packages']
 driver_check('old');profile_check('old');idle()
 for record in proof['configuration']:regular(record)
 consumers=services()
 # The desktop must also load the installed paths without inherited experiment overrides.
 for service in consumers.values():
  assert not any(k=='LD_LIBRARY_PATH' or k.startswith('LIBCAMERA_') and k!='LIBCAMERA_LOG_LEVELS' for k in service['env'])
 backup=root/'backup';backup.mkdir(mode=0o700)
 for row in proof['modules']+proof['profiles']+proof['configuration']:
  p=backup/row['backup'];p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(Path(row['path']).read_bytes());f.flush();os.fsync(f.fileno())
  assert sha(p)==row['old_sha256']
 (root/'services-private.json').write_text(json.dumps(consumers,indent=2)+'\n')
 for kind in ['forward','rollback']:(root/(kind+'.list')).write_text('ndx file://'+str(root/'repository'/kind/'packages.adb')+'\n')
 run(['apk','--no-network','--repositories-file',str(root/'forward.list'),'add','--simulate',*[n+'='+v for n,v in proof['packages'].items()]],'simulate',timeout=40)
 save('stopping-camera-consumers');stopped=True;stop_services(consumers);idle();owner_zero()
 save('installing-three-production-modules');driver_changed=True;unload();replace_records(proof['modules'],'new');load('new');state['ipe_before']=m2m()
 save('installing-r32-r27');packages_sent=True
 run(['apk','--no-network','--repositories-file',str(root/'forward.list'),'add',*[n+'='+v for n,v in proof['packages'].items()]],'packages',timeout=90)
 assert versions()==proof['packages']
 save('installing-four-factory-profiles');profiles_changed=True;replace_records(proof['profiles'],'new');profile_check('new')
 for name,digest in proof['installed_files'].items():assert sha('/'+name)==digest,name
 driver_check('new')
 q=run(['cam','-l'],'enumeration');assert (q.stdout+q.stderr).decode(errors='replace').count('for pipeline handler camss-vfe')==4
 with (root/'suite.json').open('xb') as output,(root/'suite.log').open('xb') as errors:
  client=subprocess.Popen([sys.executable,str(root/'camera-client.py'),str(root)],stdin=subprocess.DEVNULL,stdout=output,stderr=errors,start_new_session=True)
  save('installed-default-camera-suite',client_pid=client.pid)
  try:code=client.wait(timeout=360)
  except subprocess.TimeoutExpired:
   camera=json.loads((root/'camera-state.json').read_text());pid=camera.get('child_pid');owned=Path('/proc',str(pid),'cmdline')
   if owned.exists() and str(root).encode() in owned.read_bytes():os.killpg(pid,signal.SIGTERM)
   client.terminate();client.wait(timeout=15);raise
 assert code==0,'Default installed camera suite failed'
 suite=json.loads((root/'suite.json').read_text());assert suite['passed'] and len(suite['captures'])==8
 idle();owner_zero();state['camera_suite']=suite;state['ipe_after_suite']=m2m()
 assert state['ipe_after_suite']['completed']-state['ipe_before']['completed']==sum(x['ipe_completed'] for x in suite['captures'].values() if 'reused_from' not in x)
 assert not new_faults() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 save('restarting-desktop-consumers');restart(consumers,'new',new_services);idle()
 item=new_services['pipewire'];env=item['env'].copy();user_probe=Path(env['XDG_RUNTIME_DIR'])/(root.name+'-pw-probe')
 with user_probe.open('xb') as f:f.write((root/'pw-hardware-probe').read_bytes())
 user_probe.chmod(0o755);u=pwd.getpwuid(item['uid']);os.chown(user_probe,u.pw_uid,u.pw_gid)
 nodes=[];deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  q=run([str(user_probe),'--list'],'pw-enumeration',env=env,preexec_fn=demote(item));nodes=re.findall(rb'PW_NODE id=(\d+) name=(\S+) serial=(\S+) path=(\S+)',q.stdout)
  if len(nodes)==4:break
  time.sleep(.2)
 assert len(nodes)==4
 maps=Path('/proc',str(new_services['wireplumber']['pid']),'maps').read_text();(root/'wireplumber-maps-private.txt').write_text(maps)
 assert any('/usr/lib/libcamera.so.0.7.2' in line and '(deleted)' not in line for line in maps.splitlines())
 device=next(p for p in Path('/sys/bus/i2c/drivers/imx319').iterdir() if (p/'of_node').exists());camera_id='/base'+str((device/'of_node').resolve()).split('/base',1)[1]
 node_name='libcamera_input.'+re.sub(r'[^A-Za-z0-9_.-]','_',camera_id);selected=next(n for n in nodes if n[3].decode()==camera_id or n[1].decode()==node_name)
 prior=m2m();q=run([str(user_probe),selected[2].decode()],'installed-pipewire',env=env,preexec_fn=demote(item),timeout=35);idle();after=m2m()
 match=re.search(rb'PW_RESULT frames=(\d+) format-accepted=(\d+) errors=(\d+) result=(\d+)',q.stdout)
 assert match and int(match[1])>0 and int(match[2]) and int(match[3])==int(match[4])==0
 assert after['completed']-prior['completed']>=int(match[1]) and not after['failed'] and after['direct_completed']==after['completed']
 state['pipewire']=dict(nodes=4,frames=int(match[1]),ipe_completed=after['completed']-prior['completed'],ipe_cancelled=after['cancelled']-prior['cancelled'],installed_core_mapping_verified=True,core_mapping_process='wireplumber',passed=True)
 assert released(core());profile_check('new');driver_check('new');assert versions()==proof['packages']
 assert not new_faults() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 repo=next(x for x in proof['configuration'] if x['path'].endswith('/60-samurai-camera.list'))
 atomic_write(repo['path'],('ndx file://'+str(root/'repository/forward/packages.adb')+'\n').encode(),repo['mode'],repo['uid'],repo['gid'])
 state.update(ipe_after=after,core_after=core());verified=True;save('installed-default-paths-verified')
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Camera client still live; inspect owned child before recovery'
  if not verified and stopped:
   save('rollback')
   if new_services:stop_services(new_services)
   if (dev/'m2m_status').exists():idle();owner_zero()
   if driver_changed:unload();replace_records(proof['modules'],'old');load('old')
   if packages_sent:run(['apk','--no-network','--repositories-file',str(root/'rollback.list'),'add',*[n+'='+v for n,v in proof['old_packages'].items()]],'rollback-packages',timeout=90)
   if profiles_changed:replace_records(proof['profiles'],'old')
   for row in proof['configuration']:
    p=root/'backup'/row['backup'];atomic_write(row['path'],p.read_bytes(),row['mode'],row['uid'],row['gid'])
   assert versions()==proof['old_packages'];profile_check('old');driver_check('old')
   new_services={};restart(consumers,'rollback',new_services);idle();rollback=True
  elif (dev/'m2m_status').exists():idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if user_probe and user_probe.exists():user_probe.unlink()
 try:faults=new_faults()
 except BaseException:faults=['Kernel log verification failed: '+traceback.format_exc()]
 taint=int(Path('/proc/sys/kernel/tainted').read_text())
 state.update(installed=verified,rollback=rollback,failure=failure,packages=versions(),new_faults=faults,taint_after=taint,services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 passed=verified and failure is None and not faults and not taint and all(len(p)==1 for p in state['services'].values()) and released(core())
 save('finished',terminal=True,passed=bool(passed))
