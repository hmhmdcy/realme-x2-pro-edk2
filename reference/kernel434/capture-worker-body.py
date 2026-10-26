dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};stopped=False;changed=False;child=None;failure=None;verified=False
start_uptime=float(Path('/proc/uptime').read_text().split()[0]);proof=json.loads((root/'proof.json').read_text());baseline=json.loads((root/'baseline-private.json').read_text())
names=['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']
def status():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def idle():
 wait_idle();deadline=time.monotonic()+6
 while status()['owner_refs']:
  assert time.monotonic()<deadline,'CAMSS still owned';time.sleep(.02)
 assert released(core())
def notes():return {n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in names}
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
 state['taint_before']=int(Path('/proc/sys/kernel/tainted').read_text());assert state['taint_before']==0
 state['before_notes']=notes();state['before_status']=status();state['before_core']=core()
 assert notes()==baseline['notes']
 assert all(status()[k]==baseline['status'][k] for k in ['jobs','completed','direct_completed','failed','cancelled','first_error'])
 assert not any(status()[k] for k in ['users','running','fatal','pinned','orphans'])
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n');stopped=True;stop_services(items);idle()
 save('unloading-formal');changed=True
 for n in names:run(['rmmod',n],'remove-'+n)
 assert not (dev/'driver').exists()
 for n in reversed(names):run(['insmod',str(root/proof['modules'][n]['file'])],'load-'+n)
 idle();assert notes()=={n:r['note_sha256'] for n,r in proof['modules'].items()}
 assert status()['registered'] and status()['jobs']==0 and not core()['cpu_release_attempted'];save('candidate-ready',candidate_notes=notes())
 state['captures']={}
 for label,pattern in [('pattern',2),('scene',0)]:
  case=root/label;case.mkdir()
  for name in ['params-private.bin','gtm-packets-private.bin']:shutil.copyfile(root/name,case/name)
  with (case/'capture.log').open('xb') as log:
   env=os.environ.copy();env['DS4_SENSOR_MODEL']='s5kgw1'
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'gtm-capture'),str(case),str(pattern)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('capture-'+label,client_pid=child.pid);code=child.wait(timeout=38)
  text=(case/'capture.log').read_text(errors='replace');state['captures'][label]=dict(exit_code=code,full_frames=text.count('GTM_FRAME kind=full '),pd10_frames=text.count('GTM_FRAME kind=ds4 '),stats_frames=text.count('GTM_STATS '),phases=text.count('GTM_PHASE_DONE '),restored='FIXTURE_RESTORATION result=0' in text)
  assert code==0 and 'GTM_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3200:]
  assert state['captures'][label]['phases']==(9 if pattern else 3)
  idle();assert status()['jobs']==0 and released(core());save(label+'-finished')
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
except BaseException:failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=8)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
  if changed:
   idle()
   for n in names:
    if Path('/sys/module',n).exists():run(['rmmod',n],'cleanup-'+n)
   run(['modprobe','qcom_camss'],'restore-formal');idle();assert notes()==state['before_notes'];state['formal_modules_restored']=True
  if stopped:restart(items,'restore',started);state['services_restored']=True
  wait_idle();assert all(len(processes(n))==1 for n in ['pipewire','wireplumber'])
  state['after_status']=status();state['after_core']=core();assert released(core())
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[]
 for line in logs.splitlines():
  m=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if m and float(m[1])>=start_uptime:new.append(line)
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|Missing SOF tag'
 state.update(new_faults=[l for l in new if re.search(pattern,l)],taint_after=int(Path('/proc/sys/kernel/tainted').read_text()),failure=failure)
 save('finished',terminal=True,passed=bool(verified and failure is None and state.get('formal_modules_restored') and state.get('services_restored') and state['taint_after']==state['taint_before'] and not state['new_faults']))
