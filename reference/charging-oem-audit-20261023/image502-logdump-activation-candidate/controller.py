"""One Image502 logdump-only activation host journal. Default check-local never uses transport."""
from pathlib import Path,PurePosixPath
import argparse,ast,base64,hashlib,importlib.util,json,os,re,secrets,subprocess,sys,time
if sys.flags.optimize:raise RuntimeError("optimized interpreter is unsupported")
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MATERIALIZED=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-materialized-001')
WORKERS=MATERIALIZED
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-activation')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
MUTATING={'prepare','quiesce','restart'}
WORKER_HASHES={}

def create(path,raw):
 with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def save(path,data):create(path,json.dumps(data,indent=2).encode())
def load_json(path):return json.loads(Path(path).read_bytes())
def fact(path):return {'path':Path(path).name,'sha256':sha(Path(path).read_bytes())}

def profile(raw):
 adopted=json.loads(raw['adoption']);endpoint=json.loads(raw['endpoint']);post=json.loads(raw['postboot_501'])
 assert adopted['passed'] and adopted['guard_created'] and adopted['pointer']['Image501_verified']
 a=adopted['pointer'];before,after=post['raw']['identity_before'],post['raw']['identity_after']
 assert post['result']['passed'] and post['result']['read_only'] and post['result']['hardware_writes']==0 and before==after
 assert before['boot_id']==endpoint['observed_new_boot'] and before['uname']['version'].startswith('#501 ')
 assert endpoint['postboot_Image501_passed'] and endpoint['original_key_verified'] and a['original_key_verified']
 assert a['guard_path']==endpoint['guard_path']=='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
 assert a['postboot_raw_sha256']==sha(raw['postboot_501'])
 assert a['candidate_boot_sha256']==post['raw']['boot_partition']['sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
 assert a['candidate_logdump_sha256']==post['raw']['logdump_partition']['sha256']=='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
 assert a['charging_manifest_sha256']==post['raw']['manifest']['sha256']=='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
 for name in ['old501_flash_terminal','old501_reboot_terminal']:
  terminal=json.loads(raw[name]);assert terminal['passed'] and terminal['terminal'] and terminal['commands_terminal']
  assert terminal['transaction_id']=='image501-gauge-live-001' and terminal['old_boot_id']!=before['boot_id']
  assert terminal['context_sha256']==post['context_sha256']
 flash=json.loads(raw['old501_flash_terminal'])
 assert flash['partitions_written']==['logdump','boot'] and flash['pair_complete'] and flash['flashed_pair_sha256']=={'boot':a['candidate_boot_sha256'],'logdump':a['candidate_logdump_sha256']}
 assert endpoint['kind']=='usb-ipv6' and endpoint['peer']=='fe80::62:bcff:fe28:a101%29' and endpoint['interface_index']==29 and endpoint['host_key_alias']=='169.254.42.1'
 return {'identity':before,'board':{'serial_sha256':before['serial_sha256'],'compatible_sha256':sha(base64.b64decode(before['compatible_b64'],validate=True))}}

def local_inputs(require_tests=True):
 spec=importlib.util.spec_from_file_location('image502_materialization',HERE/'materialize.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 bundle=m.validate_bundle(MATERIALIZED)
 pins=load_json(HERE/'baseline-input-pins.json');raw={}
 for name,p in pins.items():
  value=Path(p['path']).read_bytes();assert sha(value)==p['sha256'];raw[name]=value
 profile(raw)
 global WORKER_HASHES
 WORKER_HASHES=dict(bundle['worker_hashes'])
 for name,digest in WORKER_HASHES.items():assert sha((WORKERS/name).read_bytes())==digest
 return pins,raw

def ssh_argv(pins):
 # Exact argument construction from pinned eud-postboot-transport.raw_ssh. Do not call
 # its subprocess.run, which would kill an unknown mutator on host timeout.
 spec=importlib.util.spec_from_file_location('eud_pinned_transport',pins['transport']['path'])
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 e=load_json(pins['endpoint']['path'])
 assert e['kind']=='usb-ipv6' and e['original_key_verified'] is True and e['postboot_Image501_passed'] is True
 assert e['host_key_alias']=='169.254.42.1' and e['interface_index']==29 and e['peer']=='fe80::62:bcff:fe28:a101%29'
 return [m.base.SSH,'-6','-T',*m.base.OPTIONS,'-o','HostKeyAlias=169.254.42.1','root@'+e['peer'],'python3 -']

def process_identity(pid):
 p=Path('/proc',str(pid));fields=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'startticks':int(fields[19]),'argv':[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]}

def process_status(receipt):
 try:
  now=process_identity(receipt['pid'])
  if now['startticks']!=receipt['startticks']:return 'pid_reused'
  fields=Path('/proc',str(receipt['pid']),'stat').read_text().rsplit(')',1)[1].split()
  return 'zombie' if fields[0]=='Z' else 'alive' if now['argv']==receipt['argv'] else 'unknown'
 except FileNotFoundError:return 'absent'
 except (OSError,KeyError,ValueError):return 'unknown'

def ssh_worker(job):
 # Sole owner of the real SSH Popen handle. It keeps waiting across the
 # controller's bounded wait and records its true exit; no timeout kill/retry.
 j=load_json(job);directory=Path(job).parent
 assert directory.is_relative_to(PRIVATE) and j['controller_sha256']==sha(Path(__file__).read_bytes())
 assert sha(Path(j['program']).read_bytes())==j['program_sha256']
 with (directory/'stdout-private.json').open('xb') as out,(directory/'stderr-private.txt').open('xb') as err:
  child=subprocess.Popen(j['ssh_argv'],stdin=subprocess.PIPE,stdout=out,stderr=err,close_fds=True)
  identity=None;receipt_error=None
  try:
   identity=process_identity(child.pid)
   save(directory/'ssh-process-private.json',{**identity,'requested_argv':j['ssh_argv']})
  except Exception as e:receipt_error=str(e)
  try:child.communicate(input=Path(j['program']).read_bytes())
  finally:
   # Even a receipt failure or a closed stdin still joins this exact child.
   # Missing identity must never be filled from a later reused PID.
   child.wait()
  out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
 save(directory/'ssh-terminal-private.json',{**(identity or {'pid':child.pid}),'terminal':True,'returncode':child.returncode,'receipt_error':receipt_error})

def start_job(directory,action,data,pins,wait_seconds=35):
 target=directory/(action+'-job-'+str(time.time_ns()));target.mkdir(mode=0o700)
 program=('CONFIG='+repr(data)+'\n'+(HERE/'remote.py').read_text()).encode()
 create(target/'program-private.py',program)
 j={'program':str(target/'program-private.py'),'program_sha256':sha(program),'ssh_argv':ssh_argv(pins),
  'controller_sha256':sha(Path(__file__).read_bytes()),'action':action}
 save(target/'job-private.json',j)
 with (target/'supervisor.log').open('xb') as log:
  child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'_ssh-worker','--job',str(target/'job-private.json')],
   stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 try:save(target/'supervisor-process-private.json',process_identity(child.pid))
 except Exception as e:save(target/'supervisor-receipt-error-private.json',{'pid':child.pid,'error':str(e),'do_not_replay':True})
 try:child.wait(timeout=wait_seconds)
 except subprocess.TimeoutExpired:return {'pending':True,'job':str(target),'fetch_only':action in MUTATING}
 return {'pending':False,'job':str(target),'supervisor_returncode':child.returncode}

def terminal_job(path):
 p=Path(path);term=load_json(p/'ssh-terminal-private.json');assert term['terminal'] is True and type(term['returncode']) is int
 assert not term.get('receipt_error'),'original SSH identity receipt failed; no qualified context'
 original=load_json(p/'ssh-process-private.json')
 assert all(term[k]==original[k] for k in ['pid','startticks','argv'])
 return term,(p/'stdout-private.json').read_bytes()

def require_known(directory,name):
 data=load_json(directory/(name+'-known-private.json'));term,raw=terminal_job(data['job'])
 assert term['returncode']==0;return json.loads(raw)

def reconcile(directory):
 """Read only the original job's real terminal; never dispatch/replay anything."""
 c=load_json(directory/'request-private.json');result={}
 for action in ['prepare','quiesce','restart']:
  selected=directory/(action+'-job-private.json');known=directory/(action+'-known-private.json')
  if not selected.exists() or known.exists():continue
  job=Path(load_json(selected)['job']);j=load_json(job/'job-private.json')
  assert j['action']==action
  program=Path(j['program']).read_bytes();assert sha(program)==j['program_sha256']
  first=ast.parse(program).body[0];assert isinstance(first,ast.Assign) and first.targets[0].id=='CONFIG'
  original=ast.literal_eval(first.value)
  assert original['action']==action and all(original[k]==c[k] for k in ['transaction_id','token','expected_boot'])
  assert original['worker_hashes']==WORKER_HASHES
  if action!='prepare':assert original['guard_sha256']==sha((directory/'guard-private.json').read_bytes())
  try:term,raw=terminal_job(job)
  except FileNotFoundError:result[action]='original_job_pending';continue
  if action=='restart':
   save(known,{'job':str(job),'received_at':time.time(),'remote_outcome_unproved':True,'original_ssh_returncode':term['returncode']})
   result[action]='terminal_remote_outcome_unproved';continue
  if term['returncode']!=0:result[action]='original_ssh_failed_no_promotion';continue
  value=json.loads(raw)
  if action=='prepare':
   assert value['prepared'] is True and value['transaction_id']==c['transaction_id'] and value['token']==c['token'] and value['boot_id']==c['expected_boot']
   guard=base64.b64decode(value['guard_base64'],validate=True);assert sha(guard)==value['guard_sha256']
   meta=json.loads(guard)
   assert all(meta[k]==v for k,v in c['fixed'].items())
   assert all(meta[k]==c[k] for k in ['transaction_id','token']) and meta['boot_id']==c['expected_boot']
   assert meta['soc_serial_sha256']==c['expected_board']['serial_sha256'] and meta['compatible_sha256']==c['expected_board']['compatible_sha256']
   assert meta['kernel_version']==c['expected_version'] and meta['rootfs_release_sha256']==c['expected_rootfs_sha256']
   target=directory/'guard-private.json'
   if target.exists():assert target.read_bytes()==guard
   else:create(target,guard)
  else:
   assert (directory/'prepare-known-private.json').exists() and value['launched'] is True
   p=value['process'];base='/root/charging-management-20261023/'+c['transaction_id']
   assert all(p[k]==c[k] for k in ['transaction_id','token']) and p['boot_id']==c['expected_boot']
   assert type(p['pid']) is int and p['pid']>0 and type(p['startticks']) is int and p['startticks']>0
   assert p['worker_sha256']==WORKER_HASHES['eud-quiesce.py']
   assert p['argv']==['python3','-B',base+'/eud-quiesce.py','--guard',base+'/guard-private.json','--commit-quiesce']
  save(known,{'job':str(job),'received_at':time.time(),'qualified_from_original_terminal':True})
  result[action]='original_terminal_rc0_and_bound_reply'
 return result

def fetch_reconcile(directory):
 try:return reconcile(directory)
 except (AssertionError,KeyError,ValueError) as e:return {'qualification_error':type(e).__name__+': '+str(e),'no_mutator_replayed':True}

def retain_fetch(directory,data):
 target=directory/('fetch-'+str(time.time_ns()));target.mkdir(mode=0o700)
 for name,row in data['files'].items():
  p=PurePosixPath(name);assert p.name==name and name not in ('.','..') and '\\' not in name and ':' not in name
  raw=base64.b64decode(row['base64'],validate=True);assert sha(raw)==row['sha256'];create(target/name,raw)
 save(target/'fetch-private.json',data);return target

def copy_exact(source,target):
 raw=Path(source).read_bytes()
 if Path(target).exists():assert Path(target).read_bytes()==raw
 else:create(target,raw)

def export_context(directory):
 c=load_json(directory/'request-private.json');g=load_json(directory/'guard-private.json')
 guard_sha=sha((directory/'guard-private.json').read_bytes())
 q=load_json(directory/'quiesce-process-private.json');s=load_json(directory/'quiesce-state-private.json');summary=load_json(directory/'quiesce-summary-private.json')
 assert q['status'] in ['absent','zombie'] and q['pid']==s['pid']
 base='/root/charging-management-20261023/'+g['transaction_id']
 assert q['argv']==['python3','-B',base+'/eud-quiesce.py','--guard',base+'/guard-private.json','--commit-quiesce']
 assert type(q['startticks']) is int and q['startticks']>0
 assert s['terminal'] and s['exit_code']==0 and summary['taint']==0
 assert all(v[k]==g[k] for v in (q,s,summary) for k in ['transaction_id','token','boot_id'])
 assert (directory/'quiesce-boot-id-private.txt').read_text().strip()==g['boot_id']
 claim=load_json(directory/'restart-claim-private.json');claim_sha=sha((directory/'restart-claim-private.json').read_bytes())
 assert all(claim[k]==g[k] for k in ['transaction_id','token','boot_id']) and claim['guard_sha256']==guard_sha
 known=load_json(directory/'restart-job-private.json');term,raw=terminal_job(known['job'])
 dispatch={'schema':'samurai-eud-restart-dispatch-v1','transaction_id':g['transaction_id'],'token':g['token'],'boot_id':g['boot_id'],
  'guard_sha256':guard_sha,'request_count':1,'state':'dispatched_once','worker_sha256':WORKER_HASHES['eud-restart.py'],
  'argv':claim['argv'],'host_process':term,'host_claim_sha256':claim_sha,
  'restart_claim_intent':'claimed_by_pinned_worker','restart_claim_observed':False,'syscall_success_proven':False}
 phase=directory/'restart-phase-private.json'
 if phase.exists():dispatch['captured_phase']=load_json(phase);dispatch['restart_claim_observed']=True
 save(directory/'restart-dispatch-private.json',dispatch)
 files={key:fact(directory/name) for key,name in {
  'guard':'guard-private.json','quiesce_state':'quiesce-state-private.json','quiesce_summary':'quiesce-summary-private.json',
  'quiesce_boot_id':'quiesce-boot-id-private.txt','quiesce_process':'quiesce-process-private.json',
  'restart_dispatch':'restart-dispatch-private.json','restart_claim':'restart-claim-private.json'}.items()}
 context={'schema':'samurai-image502-notify-fastboot-context-v1','transaction_id':g['transaction_id'],'token':g['token'],
  'old_boot_id':g['boot_id'],'guard_sha256':guard_sha,'files':files}
 save(directory/'host-context-private.json',context);return context

def host_jobs(directory):
 result={}
 for p in sorted(directory.glob('*-job-*')):
  if not p.is_dir():continue
  row={}
  for key,name in [('supervisor','supervisor-process-private.json'),('ssh','ssh-process-private.json')]:
   f=p/name
   if f.exists():
    original=load_json(f);row[key]={'original':original,'status':process_status(original)}
  if (p/'ssh-terminal-private.json').exists():row['ssh_terminal']=load_json(p/'ssh-terminal-private.json')
  result[p.name]=row
 return result

def run(action,tx,execute=False,window_confirmed=False,*,private=PRIVATE,start=start_job,require_tests=True):
 assert action in ['prepare','quiesce','fetch','inspect-restart','restart']
 assert execute and window_confirmed,'explicit execution and current exclusive window required'
 assert re.fullmatch(r'image502-notify-live-001',tx)
 pins,raw=local_inputs(require_tests);directory=private/tx
 if action=='prepare':
  directory.parent.mkdir(mode=0o700,parents=True,exist_ok=True);directory.mkdir(mode=0o700)
  current=profile(raw);identity=current['identity'];board=current['board']
  fixed=json.loads((WORKERS/'prepare-contract.json').read_bytes())['fixed_guard_fields']
  c={'transaction_id':tx,'token':secrets.token_hex(24),'expected_boot':identity['boot_id'],'expected_board':board,
   'expected_release':identity['uname']['release'],'expected_version':identity['uname']['version'],'expected_rootfs_sha256':identity['rootfs']['sha256'],
   'fixed':fixed,'worker_hashes':WORKER_HASHES,
   'files':{name:{'sha256':sha(value),'base64':base64.b64encode(value).decode()} for name,value in {
    **{n:(WORKERS/n).read_bytes() for n in WORKER_HASHES},'camera481-expected-private.json':raw['camera_wrapper']}.items()},
   'guard_fragment_sha256':sha((WORKERS/'guard-fragment.py').read_bytes()),
   'guard_fragment_base64':base64.b64encode((WORKERS/'guard-fragment.py').read_bytes()).decode()}
  save(private/'active-owner-private.json',{'transaction_id':tx,'token':c['token'],'expected_boot':c['expected_boot'],
   'scope':'this activation only; no automatic release or new-transaction bypass'})
  save(directory/'request-private.json',c)
 else:
  c=load_json(directory/'request-private.json');assert c['transaction_id']==tx
  owner=load_json(private/'active-owner-private.json');assert all(owner[k]==c[k] for k in ['transaction_id','token','expected_boot'])
  if action!='fetch':
   require_known(directory,'prepare')
   c['guard_sha256']=sha((directory/'guard-private.json').read_bytes())
   for name in MUTATING:
    if name!=action and (directory/(name+'-intent-private.json')).exists() and not (directory/(name+'-known-private.json')).exists():
     raise ValueError('prior mutation pending/unknown; only fetch')
 if action in ['inspect-restart','restart']:
  require_known(directory,'quiesce')
  q=load_json(directory/'quiesce-process-private.json');assert q['status'] in ['absent','zombie']
 if action=='restart':
  selected=sorted(directory.glob('inspect-restart-known-*-private.json'));assert selected,'read-only inspect required'
  inspected=load_json(selected[-1]);term,value=terminal_job(inspected['job'])
  assert term['returncode']==0 and json.loads(value)['inspect_only'] is True
  assert 0<=time.time()-inspected['received_at']<=30,'repeat read-only inspect when stale'
  g=load_json(directory/'guard-private.json');base='/root/charging-management-20261023/'+tx
  argv=['python3','-B',base+'/eud-restart.py','--guard',base+'/guard-private.json','--commit-restart2-bootloader']
  save(directory/'restart-claim-private.json',{'schema':'samurai-eud-restart-host-claim-v1','transaction_id':tx,'token':c['token'],
   'boot_id':c['expected_boot'],'guard_sha256':c['guard_sha256'],'request_count':1,'worker_sha256':WORKER_HASHES['eud-restart.py'],'argv':argv})
 if action in MUTATING:save(directory/(action+'-intent-private.json'),{'transaction_id':tx,'token':c['token'],'request_count':1,'action':action})
 data={**c,'action':action,'execute':True,'window_confirmed':True}
 if action=='fetch':fetch_reconcile(directory)
 job=start(directory,action,data,pins)
 save(directory/(action+'-job-private.json') if action in MUTATING else directory/(action+'-job-'+str(time.time_ns())+'-private.json'),job)
 if job['pending']:return job
 term,stdout=terminal_job(job['job'])
 if action in MUTATING:
  reconciled=reconcile(directory)
  assert (directory/(action+'-known-private.json')).exists(),'original action not qualified; preserve and fetch only'
  if action=='restart':
   if not (directory/'host-context-private.json').exists():export_context(directory)
   return {'ssh_returncode':term['returncode'],'restart_outcome_unproved':True,'reconciled':reconciled}
  return {'action':action,'known':True,'value':json.loads(stdout),'reconciled':reconciled}
 if action=='fetch' and term['returncode']!=0:
  if (directory/'restart-known-private.json').exists() and not (directory/'host-context-private.json').exists():
   try:export_context(directory)
   except FileNotFoundError:pass
  return {'remote_fetch_failed':True,'ssh_returncode':term['returncode'],'host_jobs':host_jobs(directory),'no_cleanup_performed':True}
 assert term['returncode']==0,'SSH action failed; preserve originals, fetch only for mutators'
 value=json.loads(stdout)
 if action=='fetch':
  target=retain_fetch(directory,value)
  if value['same_old_boot'] and 'quiesce' in value['processes']:
   q=value['processes']['quiesce'];assert q['transaction_id']==tx and q['token']==c['token']
   if (directory/'quiesce-known-private.json').exists():
    original=require_known(directory,'quiesce')['process']
    assert all(q[k]==original[k] for k in ['pid','startticks','argv','transaction_id','token','boot_id','worker_sha256'])
   if q['status'] in ['absent','zombie']:
    state=target/'quiesce-state-private.json';summary=target/'quiesce-summary.json'
    if state.exists() and summary.exists() and load_json(state).get('terminal') is True and load_json(state).get('exit_code')==0:
     for src,dst in [('quiesce-state-private.json','quiesce-state-private.json'),('quiesce-summary.json','quiesce-summary-private.json'),('quiesce-boot-id-private.txt','quiesce-boot-id-private.txt')]:copy_exact(target/src,directory/dst)
     if not (directory/'quiesce-process-private.json').exists():save(directory/'quiesce-process-private.json',q)
  if 'run-phase-private.json' in value['files'] and not (directory/'restart-phase-private.json').exists():copy_exact(target/'run-phase-private.json',directory/'restart-phase-private.json')
  reconciled=fetch_reconcile(directory)
  if (directory/'restart-known-private.json').exists() and not (directory/'host-context-private.json').exists():
   try:export_context(directory)
   except FileNotFoundError:pass
  return {'retained':str(target),'processes':value['processes'],'same_old_boot':value['same_old_boot'],'host_jobs':host_jobs(directory),'reconciled':reconciled,'no_cleanup_performed':True}
 name=action+'-known-'+str(time.time_ns())+'-private.json' if action=='inspect-restart' else action+'-known-private.json'
 save(directory/name,dict(job,received_at=time.time()))
 return {'action':action,'known':True,'value':value}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',nargs='?',default='check-local',choices=['check-local','prepare','quiesce','fetch','inspect-restart','restart','_ssh-worker'])
 p.add_argument('--transaction');p.add_argument('--job');p.add_argument('--execute',action='store_true');p.add_argument('--window-confirmed',action='store_true');a=p.parse_args()
 if a.action=='_ssh-worker':ssh_worker(a.job);return 0
 if a.action=='check-local':local_inputs();print(json.dumps({'checked':True,'device_access':False,'files_written':False}));return 0
 print(json.dumps(run(a.action,a.transaction,a.execute,a.window_confirmed),indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
