"""481 body appended to the tested440 durable/service prefix and fresh owner gate."""
import importlib.util, stat
os.umask(0o077)

plan=json.loads((root/'plan-private.json').read_text());cohort=plan['cohort'];backup=root/'backup'
dev=Path('/sys/bus/platform/devices/ac10000.icp')
original={};consumers={};current_services={};mutation=False;stopped=False;success=False;failure=None
active_child=None;db_before=None;kernel_before=None
trust_before=None
repositories_before=None;repositories_directory_before=None
promotion_deadline=time.monotonic()+plan['promotion_deadline_seconds']
overall_deadline=time.monotonic()+plan['diagnostic_budget_seconds']
recovering=False
last_verified_kind='rollback';changed_since_verified=False
state.update(package_database_restore_method='native apk only; raw DB backup is forensic',
             phases=[],quiescence=[],final_baseline='original',package_transactions=[],manual_inspection_required=False)
state.update(promotion_deadline_monotonic=promotion_deadline,diagnostic_budget_monotonic=overall_deadline)

def budget():
 if recovering:
  state['diagnostic_budget_overrun']=time.monotonic()>overall_deadline
 else:assert time.monotonic()<promotion_deadline,'Promotion deadline expired; restore original'

def run(args,label,timeout=30,env=None,preexec_fn=None):
 global active_child
 assert re.fullmatch(r'[A-Za-z0-9_.-]+',label)
 budget()
 if recovering:state['cleanup_budget_exceeded']=time.monotonic()>overall_deadline
 if not recovering:timeout=min(timeout,max(1,promotion_deadline-time.monotonic()))
 log=root/(label+'-stdout-private.txt');err=root/(label+'-stderr-private.txt')
 assert not log.exists() and not err.exists(),'No replay of an existing command'
 clean={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':str(root),'LANG':'C','LC_ALL':'C','TMPDIR':str(root/'tmp')}
 with log.open('xb') as out,err.open('xb') as errors:
  active_child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=errors,env=env or clean,preexec_fn=preexec_fn)
  ticks=Path('/proc',str(active_child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
  save('owned-child',active_child=dict(pid=active_child.pid,start_ticks=ticks,argv=args,label=label))
  late=False
  try:code=active_child.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   late=True;save('awaiting-same-owned-child',unknown_state=True,manual_inspection_required=True)
   # Never kill/replay a possibly committing APK transaction. Observe this handle.
   while active_child.poll() is None:time.sleep(1)
   code=active_child.returncode
  active_child=None
 record=dict(argv=args,exit_code=code,stdout_sha256=sha(log),stderr_sha256=sha(err),finished_after_deadline=late)
 (root/(label+'-result-private.json')).write_text(json.dumps(record,indent=2)+'\n')
 save('owned-child-complete',active_child=None,unknown_state=False,last_command=record)
 if code or late:raise RuntimeError(label+' failed or exceeded its bound; child now terminal')
 return subprocess.CompletedProcess(args,code,log.read_bytes(),err.read_bytes())

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def metadata(path):
 p=Path(path);s=p.lstat();r=dict(mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
 if p.is_symlink():r.update(type='symlink',target=os.readlink(p))
 elif p.is_file():r.update(type='file',sha256=sha(p),bytes=s.st_size)
 elif p.is_dir():r['type']='directory'
 else:raise RuntimeError('Unsupported target '+str(p))
 return r

def atomic(path,data,attrs):
 budget()
 p=Path(path);temporary=p.with_name(p.name+'.k481-tmp');assert not temporary.exists()
 assert not p.is_symlink() and (not p.exists() or p.is_file())
 with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 os.chown(temporary,attrs['uid'],attrs['gid']);os.chmod(temporary,attrs['mode']);os.replace(temporary,p)
 fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def database():
 result={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  if not block.strip():continue
  lines=block.splitlines();names=[x[2:] for x in lines if x.startswith('P:')]
  assert len(names)==1 and names[0] not in result;result[names[0]]=lines
 return result

def versions():
 db=database();return {name:next(x[2:] for x in db[name] if x.startswith('V:')) for name in cohort['forward_packages']}

def unchanged_other_packages():
 now=database();names=set(cohort['forward_packages'])
 assert {k:v for k,v in now.items() if k not in names}=={k:v for k,v in db_before.items() if k not in names},'Noncohort APK database entries changed'

def trust_inventory():
 result={}
 for directory in [Path('/etc/apk/keys'),Path('/usr/share/apk/keys')]:
  assert directory.is_dir() and not directory.is_symlink(),'Unsupported trust-root layout; refuse before mutation'
  for path in [directory,*directory.rglob('*')]:result[str(path)]=metadata(path)
 return result

def inspect_files(kind):
 assert versions()==cohort[kind+'_packages'];unchanged_other_packages()
 assert trust_inventory()==trust_before,'Original APK trust set changed'
 for path,row in plan['package_files'][kind].items():
  actual=metadata(path);assert actual['uid']==actual['gid']==0
  if 'symlink' in row:assert actual['type']=='symlink' and actual['target']==row['symlink']
  else:assert actual['type']=='file' and actual['sha256']==row['sha256'] and actual['mode']==row['mode'],path
 for family in ['modules','profiles']:
  for row in cohort[family]:
   path=Path(row['path']);assert str(path.resolve())==row['resolved_path']
   actual=metadata(path);assert actual['type']=='file' and actual['sha256']==row[kind+'_sha256']
   assert actual['uid']==actual['gid']==0 and actual['mode']==0o644
   for directory in [path.parent,path.resolve().parent]:
    values=metadata(directory);assert values['type']=='directory' and values['mode']==0o755 and values['uid']==values['gid']==0
 for row in cohort['modules']:assert sha('/sys/module/'+row['name']+'/notes/.note.gnu.build-id')==row[kind+'_note_sha256']
 assert {p.name for p in Path('/sys/module').iterdir()}==set(state['initial_module_names']),'Module dependency set expanded'
 return dict(kind=kind,packages=versions(),noncohort_database_entries_unchanged=True,
  installed_database_sha256=sha('/lib/apk/db/installed'),world_sha256=sha('/etc/apk/world'),
  modules={row['name']:dict(file=metadata(row['path']),note_sha256=sha('/sys/module/'+row['name']+'/notes/.note.gnu.build-id')) for row in cohort['modules']},
  profiles={row['model']:metadata(row['path']) for row in cohort['profiles']},package_files_checked=len(plan['package_files'][kind]))

def idle():
 if not (dev/'m2m_status').exists():
  assert not Path('/sys/module/qcom_camss').exists(),'CAMSS present without owned IPE interface'
  if (dev/'state').exists():
   values=json.loads((dev/'state').read_text())
   assert not any(values[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','imported_buffers'])
  return
 deadline=time.monotonic()+8
 while True:
  status=json.loads((dev/'m2m_status').read_text());core=json.loads((dev/'state').read_text())
  released=not any(core[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
  suspended=all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci'])
  if released and suspended and not any(status[k] for k in ['users','running','fatal','pinned','orphans','first_error']):return
  assert time.monotonic()<deadline,'Camera not idle';time.sleep(.1)

def camera_fds():
 nodes={p.stat().st_rdev for pattern in ['video*','media*','v4l-subdev*'] for p in Path('/dev').glob(pattern) if stat.S_ISCHR(p.stat().st_mode)}
 found=[]
 for proc in Path('/proc').glob('[0-9]*'):
  try:
   values=(proc/'stat').read_text().rsplit(')',1)[1].split()
   if values[0]=='Z':continue
   for fd in (proc/'fd').iterdir():
    try:
     value=fd.stat()
     if stat.S_ISCHR(value.st_mode) and value.st_rdev in nodes:found.append(dict(pid=int(proc.name),fd=int(fd.name),target=os.readlink(fd),start_ticks=values[19]))
    except (FileNotFoundError,ProcessLookupError):pass
  except (FileNotFoundError,ProcessLookupError):pass
 return found

def quiesce(label):
 global stopped
 stopped=True
 if current_services:stop_services(current_services);current_services.clear()
 # Only known camera clients are signalled; unknown holders cause a safe stop.
 clients={}
 for name in ['cam','gst-launch-1.0','gst-sustained','capture','pipeline-smoke','gst-hardware-pr','pw-hardware-pro']:
  for p in processes(name):
   clients[name+'-'+p.name]=dict(pid=int(p.name),comm=name,start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19])
 for item in clients.values():
  p=Path('/proc',str(item['pid']));assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
  descriptor=os.pidfd_open(item['pid'])
  try:
   signal.pidfd_send_signal(descriptor,signal.SIGTERM)
   assert select.select([descriptor],[],[],8)[0],'Camera client failed to exit'
  finally:os.close(descriptor)
 idle();holders=camera_fds();save(label,live_camera_fds=holders,stopped_clients=clients)
 assert not holders,'Unknown live camera holder; inspect before any module operation'
 if (dev/'m2m_status').exists():assert json.loads((dev/'m2m_status').read_text())['owner_refs']==0,'Camera ownership references remain'
 state['quiescence'].append(dict(phase=label,no_live_camera_fds=True,ownership_zero_or_module_absent=True,idle_verified=True))
 save(label+'-proven')

def switch_modules(kind,label):
 for name in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core','s5k3m5']:
  if Path('/sys/module',name).exists():run(['rmmod',name],label+'-unload-'+name,timeout=15)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()
 for row in cohort['modules']:
  source=(root/kind/'modules'/(row['name']+'.ko')) if kind=='forward' else backup/row['path'].lstrip('/')
  assert sha(source)==row[kind+'_sha256'];atomic(row['resolved_path'],source.read_bytes(),original[row['path']])
 by_name={row['name']:row for row in cohort['modules']}
 for name in ['s5k3m5','qcom_camss_icp_a5_core','camss_icp_a5_m2m','qcom_camss']:
  run(['insmod',by_name[name]['resolved_path']],label+'-load-'+name,timeout=15)
  assert sha('/sys/module/'+name+'/notes/.note.gnu.build-id')==by_name[name][kind+'_note_sha256']
 idle();assert not camera_fds()

def apk_args(kind):
 return ['/sbin/apk','--no-network','--repositories-file',str(root/(kind+'.list')),'--cache-dir',str(root/'cache'),'--logfile=no','--progress=no','--interactive=no']

def package_phase(kind,label):
 global mutation
 mutation=True;save(label+'-native-apk-start',native_apk_attempted=True)
 command=apk_args(kind)+['add']+[name+'='+version for name,version in sorted(cohort[kind+'_packages'].items())]
 run(command,label+'-packages',timeout=90)
 state['package_transactions'].append(dict(phase=label,kind=kind,pins=cohort[kind+'_packages'],native_apk_exit_code=0))
 for row in cohort['profiles']:
  source=root/kind/'profiles'/(row['model']+'.yaml') if kind=='forward' else backup/row['path'].lstrip('/')
  assert sha(source)==row[kind+'_sha256'];atomic(row['resolved_path'],source.read_bytes(),original[row['path']])

def restore_config():
 budget()
 for path,attrs in original.items():
  if path=='/etc/apk/world' or path=='/etc/apk/repositories' or path.startswith('/etc/apk/repositories.d/'):
   assert attrs['type']=='file';atomic(path,(backup/path.lstrip('/')).read_bytes(),attrs)
 created=Path(plan['persistent_repository_file'])
 if created.exists():
  assert created.is_file() and not created.is_symlink();budget();created.unlink()
 persistent=Path(plan['persistent_repository_dir'])
 if persistent.exists():
  expected={p.name:sha(p) for p in (root/'forward/repository').iterdir()}
  assert persistent.is_dir() and not persistent.is_symlink()
  for item in persistent.iterdir():
   assert item.is_file() and not item.is_symlink() and item.name in expected and sha(item)==expected[item.name]
   budget();item.unlink()
  persistent.rmdir()
 assert Path('/etc/apk/world').read_bytes()==(backup/'etc/apk/world').read_bytes()
 for path,attrs in original.items():
  if path.startswith('/etc/apk/repos'):assert metadata(path)==attrs,path
 assert {p.name:metadata(p) for p in Path('/etc/apk/repositories.d').iterdir()}==repositories_before,'Repository member set changed'
 assert metadata('/etc/apk/repositories.d')==repositories_directory_before

def probe(label):
 spec=importlib.util.spec_from_file_location('default_probe482',root/'default-probe.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 expected=dict(plan['expected_forward'],deadline_monotonic=promotion_deadline);result=module.run(root,state,phase=label,expected=expected)
 assert result['passed'];idle();assert not camera_fds();save(label+'-probe-passed',default_probe=result)

def phase(kind,label,do_probe=False):
 global mutation,last_verified_kind,changed_since_verified
 budget()
 quiesce(label+'-quiescent');mutation=True;changed_since_verified=True;switch_modules(kind,label)
 package_phase(kind,label)
 if kind=='rollback':restore_config()
 evidence=inspect_files(kind);idle()
 if do_probe:probe(label);evidence=inspect_files(kind)
 (root/(label+'-installed-db-forensic.txt')).write_bytes(Path('/lib/apk/db/installed').read_bytes())
 (root/(label+'-world-forensic.txt')).write_bytes(Path('/etc/apk/world').read_bytes())
 (root/(label+'-proof-private.json')).write_text(json.dumps(evidence,indent=2)+'\n')
 state['phases'].append(dict(phase=label,kind=kind,verified=True,default_probe=do_probe))
 last_verified_kind=kind;changed_since_verified=False;save(label+'-verified')

def faults():
 text=subprocess.check_output(['dmesg'],text=True)
 assert text.splitlines().count(kernel_before[-1])==1,'Kernel anchor missing'
 new=text.splitlines()[text.splitlines().index(kernel_before[-1])+1:]
 (root/'kernel-new-private.txt').write_text('\n'.join(new)+'\n')
 return [line for line in new if re.search(r'WARNING:|Oops:|BUG:|Unhandled.*fault|IOMMU.*[Ff]ault|A5 IPE frame failed|IPE m2m job failed|Stream stop failed:',line)]

def keep_forward():
 budget()
 # Package material is public signed data; forensic/profile originals stay private.
 destination=Path(plan['persistent_repository_dir']);assert not destination.exists();destination.mkdir(mode=0o755);destination.chmod(0o755);os.chown(destination,0,0)
 for source in sorted((root/'forward/repository').iterdir()):
  target=destination/source.name;atomic(target,source.read_bytes(),dict(uid=0,gid=0,mode=0o644))
 world=(backup/'etc/apk/world').read_bytes();lines=world.splitlines(keepends=True);remaining=dict(cohort['forward_packages']);output=[]
 for line in lines:
  match=re.match(rb'([A-Za-z0-9_.+-]+)(?:@[^<>=~\s]+)?(?:[<>=~].*)?$',line.rstrip(b'\r\n'))
  name=match[1].decode() if match else None
  if name in remaining:output.append((name+'='+remaining.pop(name)+'\n').encode())
  else:output.append(line)
 data=b''.join(output)
 if data and not data.endswith(b'\n'):data+=b'\n'
 data+=b''.join((name+'='+version+'\n').encode() for name,version in sorted(remaining.items()))
 atomic('/etc/apk/world',data,original['/etc/apk/world'])
 atomic(plan['persistent_repository_file'],('ndx file://'+str(destination/'packages.adb')+'\n').encode(),dict(uid=0,gid=0,mode=0o644))
 for path,attrs in original.items():
  if path.startswith('/etc/apk/repos'):assert metadata(path)==attrs,'Other repository configuration changed'
 expected_repositories=dict(repositories_before)
 expected_repositories[Path(plan['persistent_repository_file']).name]=metadata(plan['persistent_repository_file'])
 assert {p.name:metadata(p) for p in Path('/etc/apk/repositories.d').iterdir()}==expected_repositories
 assert metadata('/etc/apk/repositories.d')==repositories_directory_before
 default_repositories=['/sbin/apk','--no-network','--cache-dir',str(root/'cache'),'--logfile=no','--progress=no','--interactive=no']
 run(default_repositories+['add','--simulate']+[name+'='+version for name,version in sorted(cohort['forward_packages'].items())],'final-default-repositories-solver',timeout=40)

try:
 assert root.name==plan['window_id'] and os.geteuid()==0 and plan['deployable'];assert not backup.exists()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert charging()==plan['handoff']['charging'],'Charging baseline changed; no mutation authorized'
 assert shutil.disk_usage('/').free>=plan['minimum_target_free_bytes']
 for name,digest in plan['payload_sha256'].items():assert sha(root/name)==digest,name
 (root/'tmp').mkdir(mode=0o700);(root/'cache').mkdir(mode=0o700)
 db_before=database();trust_before=trust_inventory();state['initial_module_names']=sorted(p.name for p in Path('/sys/module').iterdir())
 repositories_directory_before=metadata('/etc/apk/repositories.d')
 repositories_before={p.name:metadata(p) for p in Path('/etc/apk/repositories.d').iterdir()}
 assert all(row['type']=='file' for row in repositories_before.values()),'Unsupported repository member type; refuse before mutation'
 consumers=services();current_services.update(consumers)
 for item in consumers.values():
  assert item['uid']==10000 and not any(key=='LD_LIBRARY_PATH' or key.startswith('LIBCAMERA_') and key!='LIBCAMERA_LOG_LEVELS' for key in item['env'])
  values=dict(line.split(':',1) for line in Path('/proc',str(item['pid']),'status').read_text().splitlines() if ':' in line)
  assert [int(value) for value in values['Uid'].split()]==[10000]*4 and int(values['CapEff'].strip(),16)==0
 inspect_files('rollback');idle();kernel_before=subprocess.check_output(['dmesg'],text=True).splitlines();state['kernel_anchor']=kernel_before[-1]
 backup.mkdir(mode=0o700)
 paths=set(plan['package_files']['rollback'])|{row['path'] for family in ['modules','profiles'] for row in cohort[family]}|{'/etc/apk/world','/etc/apk/repositories'}
 paths.update(str(p) for p in Path('/etc/apk/repositories.d').iterdir() if p.is_file())
 for p in sorted(paths):
  original[p]=metadata(p)
  if p=='/etc/apk/world' or p.startswith('/etc/apk/repos'):assert original[p]['type']=='file','Unsupported repository/world type; refuse before mutation'
  if original[p]['type']=='file':
   target=backup/p.lstrip('/');target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(Path(p).read_bytes());assert sha(target)==original[p]['sha256']
 forensic=backup/'forensic-apk-db';forensic.mkdir(mode=0o700)
 for source in Path('/lib/apk/db').iterdir():
  if source.is_file() and not source.is_symlink():(forensic/source.name).write_bytes(source.read_bytes())
 (backup/'original-attributes-private.json').write_text(json.dumps(original,indent=2)+'\n')
 (backup/'services-private.json').write_text(json.dumps(consumers,indent=2)+'\n')
 (backup/'original-trust-private.json').write_text(json.dumps(trust_before,indent=2)+'\n')
 (backup/'original-repositories-private.json').write_text(json.dumps(dict(directory=repositories_directory_before,members=repositories_before),indent=2)+'\n')
 # The backup must be durable before any module or native-package mutation.
 for entry in backup.rglob('*'):
  if entry.is_file():
   fd=os.open(entry,os.O_RDONLY)
   try:os.fsync(fd)
   finally:os.close(fd)
 for directory in sorted([p for p in backup.rglob('*') if p.is_dir()]+[backup,root],key=lambda p:len(p.parts),reverse=True):
  fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 state['scripts_hooks_policy']='native APK defaults enabled; no claim that absent cohort scripts/hooks were exercised'
 state['commit_hooks_before']={str(p):metadata(p) for p in Path('/etc/apk/commit_hooks.d').glob('*')}
 for kind in ['forward','rollback']:
  (root/(kind+'.list')).write_text('ndx file://'+str(root/kind/'repository/packages.adb')+'\n')
  run(apk_args(kind)+['verify']+[str(p) for p in sorted((root/kind/'repository').iterdir())],'verify-'+kind,timeout=50)
 run(apk_args('forward')+['add','--simulate']+[name+'='+version for name,version in sorted(cohort['forward_packages'].items())],'fresh-forward-solver',timeout=40)
 assert not Path(plan['persistent_repository_file']).exists() and not Path(plan['persistent_repository_dir']).exists()
 save('fresh-backup-complete')
 phase('forward','forward-first',True)
 phase('rollback','rollback-exact')
 assert all(metadata(path)==attrs for path,attrs in original.items()),'Rollback file/attribute mismatch'
 save('rollback-proven',exact_rollback_verified=True,rollback_database_semantics_verified=True)
 gate(plan)  # Freshness is never extended to promote after an expired window.
 phase('forward','forward-final',True)
 assert not faults() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 keep_forward();inspect_files('forward');restart(consumers,'final',current_services);idle()
 for name,item in current_services.items():
  assert len(processes(name))==1 and processes(name)[0].name==str(item['pid'])
  values=dict(line.split(':',1) for line in Path('/proc',str(item['pid']),'status').read_text().splitlines() if ':' in line)
  assert [int(value) for value in values['Uid'].split()]==[10000]*4 and int(values['CapEff'].strip(),16)==0
 deadline=time.monotonic()+8;maps=''
 while time.monotonic()<deadline:
  maps=Path('/proc',str(current_services['wireplumber']['pid']),'maps').read_text()
  lines=[line for line in maps.splitlines() if '/usr/lib/libcamera.so.0.7.2' in line]
  if lines:break
  time.sleep(.2)
 assert lines and all('(deleted)' not in line and int(line.split()[4])==Path('/usr/lib/libcamera.so.0.7.2').stat().st_ino for line in lines)
 (root/'final-wireplumber-maps-private.txt').write_text(maps)
 assert not faults() and charging()==plan['handoff']['charging'];success=True
 state.update(final_baseline='r33-r28-candidate',persistent_repository=plan['persistent_repository_file'])
except BaseException:
 failure=traceback.format_exc();(root/'failure-private.txt').write_text(failure)
finally:
 if failure and stopped:
  try:
   recovering=True
   budget()
   assert active_child is None,'Owned child live; inspect same handle, do not replay'
   quiesce('recovery-quiescent')
   if mutation and (changed_since_verified or last_verified_kind!='rollback'):
    switch_modules('rollback','recovery');package_phase('rollback','recovery');restore_config();inspect_files('rollback')
    assert all(metadata(path)==attrs for path,attrs in original.items()),'Recovery files/attrs differ'
   elif mutation:
    inspect_files('rollback');assert all(metadata(path)==attrs for path,attrs in original.items())
   restart(consumers,'recovery',current_services);idle();state['original_recovered']=True;state['final_baseline']='original'
  except BaseException:state.update(cleanup_failure=traceback.format_exc(),manual_inspection_required=True,final_baseline='unverified')
 try:
  state.update(packages=versions(),new_faults=faults() if kernel_before else [],taint_after=int(Path('/proc/sys/kernel/tainted').read_text()))
  state['final_services']={name:{key:item[key] for key in ['pid','start_ticks','uid']} for name,item in current_services.items()}
 except BaseException:state['final_observation_failure']=traceback.format_exc();success=False
 state.update(failure=failure,installed=success,passed=bool(success and not failure),terminal=True)
 save('complete' if state['passed'] else 'failed')
