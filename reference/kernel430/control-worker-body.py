dev=Path('/sys/bus/platform/devices/ac10000.icp');child=None;items={};started={};stopped=False;failure=None;verified=False
meta=json.loads((root/'manifest.json').read_text());before_log=subprocess.check_output(['dmesg'])
def status():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def notes():return {n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in meta['normal_notes']}
def idle():
 wait_idle();deadline=time.monotonic()+6
 while status()['owner_refs']:assert time.monotonic()<deadline;time.sleep(.02)
 assert not any(status()[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
 assert not any(core()[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k429-recovered/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and notes()==meta['normal_notes']
 for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);idle();state['before_status']=status()
 import fcntl
 video=[str(Path('/dev')/p.parent.name) for p in Path('/sys/class/video4linux').glob('video*/name') if p.read_text().strip()=='qcom-ipe-a5'];assert len(video)==1
 media=[]
 for path in Path('/dev').glob('media[0-9]*'):
  with path.open('rb',buffering=0) as f:
   data=bytearray(256);fcntl.ioctl(f.fileno(),0xc1007c00,data,True)
  if bytes(data[16:48]).split(b'\0')[0]==b'SM8150 IPE':media.append(str(path))
 assert len(media)==1
 with (root/'client.log').open('xb') as log:
  child=subprocess.Popen([str(root/'control-ipe'),video[0],media[0],str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('control-replay',client_pid=child.pid);code=child.wait(timeout=55)
 text=(root/'client.log').read_text();assert code==0 and 'CONTROL_RESULT result=0 frames=4' in text,text[-3000:]
 idle();state['after_jobs']=status();assert all(state['after_jobs'][k]-state['before_status'][k]==4 for k in ['jobs','completed','direct_completed'])
 verified=True
except BaseException:failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
  idle()
  if stopped:restart(items,'restore',started);state['services_restored']=True
  wait_idle();assert all(len(processes(n))==1 for n in ['pipewire','wireplumber'])
  assert notes()==meta['normal_notes'];state.update(normal_modules_unchanged=True,after_core=core(),after_status=status())
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 logs=subprocess.check_output(['dmesg']);(root/'kernel-log-private.txt').write_bytes(logs)
 faults={w.decode():logs.count(w)-before_log.count(w) for w in [b'WARNING:',b'Oops:',b'Unhandled',b'IOMMU fault',b'arm-smmu',b'SError',b'BUG:',b'CCI error',b'Stream stop failed:',b'Missing SOF tag']}
 state.update(failure=failure,new_faults=faults,taint_after=int(Path('/proc/sys/kernel/tainted').read_text()))
 save('finished',terminal=True,passed=bool(verified and failure is None and not any(faults.values()) and state['taint_after']==0 and state.get('services_restored')))
