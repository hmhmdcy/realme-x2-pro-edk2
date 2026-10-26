# Appended after the proven service save/stop/restart helpers.
proof=json.loads((root/'proof.json').read_text());baseline=proof['baseline'];child=None
items={};started={};services_stopped=False;swap_started=False;new_sg_loaded=False
verified=False;failure=None;restored=False;child_reports={}
start_uptime=float(Path('/proc/uptime').read_text().split()[0])
before=subprocess.check_output(['dmesg'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loaded(name):return Path('/sys/module',name).exists()
def note(name):return sha('/sys/module/'+name+'/notes/.note.gnu.build-id')
def absent_candidates():
 return not any(loaded(n) for n in ['camss_icp_a5_boot_test','camss_icp_a5_m2m','qcom_camss_icp_a5_core','v4l2_mem2mem']) and not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists()
def module_snapshot():
 return {n:dict(note_sha256=note(n),refcount=int(Path('/sys/module',n,'refcnt').read_text()),holders=sorted(p.name for p in Path('/sys/module',n,'holders').iterdir())) for n in baseline if loaded(n)}
def unload_camss(label):
 wait_idle()
 assert int(Path('/sys/module/qcom_camss/refcnt').read_text())==0,'CAMSS still has a real consumer'
 assert sorted(p.name for p in Path('/sys/module/videobuf2_dma_sg/holders').iterdir())==['qcom_camss']
 run(['rmmod','qcom_camss'],label+'-camss')
 assert not list(Path('/sys/module/videobuf2_dma_sg/holders').iterdir())
 assert int(Path('/sys/module/videobuf2_dma_sg/refcnt').read_text())==0
def stop_current():
 global services_stopped
 current=services();save('stopping-consumers');services_stopped=True;stop_services(current);wait_idle()
def start_saved(label):
 global started,services_stopped
 started={};restart(items,label,started);services_stopped=False;wait_idle()
def suite(name):
 global child
 suite_root=root/name
 with (suite_root/'worker.log').open('xb') as log:
  child=subprocess.Popen([sys.executable,str(suite_root/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 save(name+'-running',child_pid=child.pid,child_root=str(suite_root))
 code=child.wait(timeout=390)
 report=json.loads((suite_root/'state.json').read_text());child_reports[name]=report
 assert code==0 and report['terminal'] and report['passed'],name+' suite failed; retain evidence'
 assert absent_candidates(),name+' still owns hardware resources'
 save(name+'-passed',child_exit=code,child_reports=child_reports)
def installed_capture(model):
 devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()];assert len(devices)==1
 camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
 env=os.environ.copy()
 for key in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 with (root/('restored-'+model+'.log')).open('xb') as log:
  proc=subprocess.Popen([str(root/'pipeline/pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',camera_id,'640','480'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:code=proc.wait(timeout=45)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=12)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
   raise
 text=(root/('restored-'+model+'.log')).read_text(errors='replace')
 match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
 assert code==0 and 'FIXTURE_RESTORATION result=0' in text and match and int(match[1])>0 and int(match[4])==int(match[5])==0
 return dict(frames=int(match[1]),passed=True)
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert absent_candidates()
 for n,row in baseline.items():
  assert note(n)==row['note_sha256'] and sha(row['path'])==row['file_sha256']
 assert sha(root/'sg.ko')==proof['sg_sha256']
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n');wait_idle()
 save('baseline-verified',modules_before=module_snapshot())
 stop_current();save('swap-standard-sg');swap_started=True
 unload_camss('forward');run(['rmmod','videobuf2_dma_sg'],'forward-remove-sg')
 run(['insmod',str(root/'sg.ko')],'forward-load-sg');new_sg_loaded=True
 assert note('videobuf2_dma_sg')==proof['sg_note_sha256']
 run(['modprobe','qcom_camss'],'forward-reload-camss');wait_idle()
 assert note('qcom_camss')==baseline['qcom_camss']['note_sha256']
 save('temporary-framework-ready',temporary_modules=module_snapshot())
 suite('native')
 assert child_reports['native']['export_fd_and_vma_lifetime_passed']
 start_saved('between-suites')
 suite('pipeline')
 verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  live=child is not None and child.poll() is None
  assert not live and absent_candidates(),'Worker or hardware ownership still live; shared framework retained'
  if swap_started:
   if not services_stopped:stop_current()
   save('restore-original-framework')
   if loaded('qcom_camss'):unload_camss('restore')
   if loaded('videobuf2_dma_sg'):
    assert not list(Path('/sys/module/videobuf2_dma_sg/holders').iterdir()) and int(Path('/sys/module/videobuf2_dma_sg/refcnt').read_text())==0
    run(['rmmod','videobuf2_dma_sg'],'restore-remove-sg')
   run(['modprobe','videobuf2_dma_sg'],'restore-original-sg');new_sg_loaded=False
   run(['modprobe','qcom_camss'],'restore-original-camss');wait_idle()
  for n,row in baseline.items():assert note(n)==row['note_sha256'] and sha(row['path'])==row['file_sha256']
  restored=True
  save('original-framework-restored',modules_restored=module_snapshot())
  if verified:
   run(['cam','-l'],'restored-enumeration')
   assert (root/'restored-enumeration.log').read_text().count('for pipeline handler camss-vfe')==4
   captures={model:installed_capture(model) for model in ['imx471','imx319','s5k3m5','s5kgw1']}
   save('installed-four-camera-regression-passed',installed_captures=captures)
 except BaseException:
  (root/'restore-failure.txt').write_text(traceback.format_exc());state['restore_error']=traceback.format_exc();verified=False
 finally:
  if items and services_stopped and restored:
   try:start_saved('final')
   except BaseException:state['service_restore_error']=traceback.format_exc();verified=False
  after=subprocess.check_output(['dmesg']);(root/'kernel-log-private.txt').write_bytes(after)
  pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|OF: ERROR|watchdog received|crash detected in modem|CCI error|Stream stop failed:'
  relevant=[]
  for line in after.decode(errors='replace').splitlines():
   match=re.search(r'\[\s*(\d+\.\d+)\]',line)
   if match and float(match[1])>=start_uptime and re.search(pattern,line):relevant.append(line)
  state.update(child_reports=child_reports,original_framework_restored=restored,new_sg_loaded=new_sg_loaded,failure=failure is not None,new_relevant_faults=relevant,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
   services={name:[int(p.name) for p in processes(name)] for name in ['pipewire','wireplumber']},
   camera_pm={name:Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip() if Path('/sys/bus/platform/devices',name).exists() else 'absent' for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']})
  passed=verified and restored and failure is None and not state['taint'] and not relevant and all(len(p)==1 for p in state['services'].values()) and all(v=='suspended' for v in state['camera_pm'].values())
  save('finished',terminal=True,passed=passed)
