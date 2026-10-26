dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};stopped=False;changed=False;child=None;failure=None;verified=False
start_uptime=float(Path('/proc/uptime').read_text().split()[0]);proof=json.loads((root/'proof.json').read_text())
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
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 state['taint_before']=int(Path('/proc/sys/kernel/tainted').read_text());assert state['taint_before']==512
 state['before_notes']=notes();state['before_status']=status();state['before_core']=core()
 expected_jobs=793
 if root.name!='k427-ds4-r1':
  prior=json.loads(Path('/var/lib/samurai/k427-ds4-r1/state.json').read_text())
  assert prior['terminal'] and prior['formal_modules_restored'] and prior['services_restored'] and not prior['new_faults'] and prior['taint_after']==512
  assert notes()==prior['before_notes'];expected_jobs=0
 assert status()['jobs']==status()['completed']==status()['direct_completed']==expected_jobs and not any(status()[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n');stopped=True;stop_services(items);idle()
 save('unloading-formal');changed=True
 for n in names:run(['rmmod',n],'remove-'+n)
 assert not (dev/'driver').exists()
 for n in reversed(names):run(['insmod',str(root/proof['modules'][n]['file'])],'load-'+n)
 idle();assert notes()=={n:r['note_sha256'] for n,r in proof['modules'].items()}
 assert status()['registered'] and status()['jobs']==0 and not core()['cpu_release_attempted'];save('candidate-ready',candidate_notes=notes())
 state['captures']={}
 for model,kind,pattern in [('s5kgw1','full-only',2)]+[(m,k,p) for m in ['s5kgw1','s5k3m5','imx471','imx319'] for k,p in [('pattern',2),('scene',0)]]:
  label=model+'-'+kind
  case=root/label;case.mkdir();shutil.copyfile(root/('params-'+model+'-private.bin'),case/'params-private.bin')
  with (case/'capture.log').open('xb') as log:
   env=os.environ.copy();env['DS4_SENSOR_MODEL']=model
   if kind=='full-only':env['DS4_CAPTURE_FULL_ONLY']='1'
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'ds4-capture'),str(case),str(pattern)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('capture-'+label,client_pid=child.pid);code=child.wait(timeout=38)
  text=(case/'capture.log').read_text(errors='replace');state['captures'][label]={'exit_code':code,'full_frames':text.count('FRAME kind=full '),'ds4_frames':text.count('FRAME kind=ds4 '),'restored':'FIXTURE_RESTORATION result=0' in text}
  assert code==0 and 'DS4_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-2400:]
  if kind!='full-only':assert all(x in text for x in ['DS4_STARVE_BEGIN','DS4_RESUMED','DS4_STOP_FULL_CONTINUES'])
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
   run(['modprobe','qcom_camss'],'restore-formal');idle()
   assert notes()==state['before_notes'];state['formal_modules_restored']=True
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
