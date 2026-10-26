# Appended to the proven service save/stop/restart helpers.
dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};stopped=False;client=None;collector=None;collector_log=None;verified=False;failure=None
start_uptime=float(Path('/proc/uptime').read_text().split()[0])
def state_icp():return json.loads((dev/'state').read_text())
def status():return json.loads((dev/'m2m_status').read_text())
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def wait_exports():
 deadline=time.monotonic()+5
 while True:
  s=status()
  if not s['owner_refs']:return s
  assert time.monotonic()<deadline,'CAMSS still has open contexts or exported buffers'
  time.sleep(.02)
def clocks():
 out={}
 for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
  f=line.split()
  if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):out[f[0]]=int(f[1])
 return out
def launch(args,label,timeout):
 global client
 with (root/(label+'.json')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  save(label+'-running',client_pid=client.pid)
  code=client.wait(timeout=timeout)
 assert code==0,label+' failed; inspect private client output'
 return json.loads((root/(label+'.json')).read_text())
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and (dev/'driver').resolve().name=='qcom-sm8150-icp'
 meta=json.loads((root/'manifest.json').read_text())
 for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
 assert not Path('/sys/module/camss_icp_a5_boot_test').exists()
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n');stopped=True;stop_services(items);wait_idle()
 before=wait_exports();assert not any(before[k] for k in ['users','running','jobs','pinned','orphans']) and released(state_icp())
 state['clocks_before']=clocks();assert len(state['clocks_before'])==17 and not any(state['clocks_before'].values())
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid)
 deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():
  assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5'];assert len(nodes)==1
 video='/dev/'+nodes[0].name
 for name in ['export-lifetime-client','m2m-client','pipeline-fixture','pipeline-smoke']:(root/name).chmod(0o700)
 with (root/'export-client.log').open('xb') as log:
  client=subprocess.Popen([str(root/'export-lifetime-client'),video,str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('export-lifetime-running',export_client_pid=client.pid)
  def held(marker):
   deadline=time.monotonic()+5
   while not (root/marker).exists():
    assert client.poll() is None and time.monotonic()<deadline;time.sleep(.01)
   s=status();assert not any(s[k] for k in ['users','running','jobs','pinned','orphans']) and s['owner_refs']==1
   assert int(Path('/sys/module/qcom_camss/refcnt').read_text())==1
   state[marker.replace('-','_')]=s;save(marker)
  held('export-held');(root/'close-export-fd').touch();held('mmap-only-held');(root/'release-export-mmap').touch()
  state['export_client_exit']=client.wait(timeout=8);assert not state['export_client_exit'] and (root/'export-released').exists()
 state['export_after_release']=wait_exports();state['export_lifetime_passed']=True
 native=launch([str(root/'m2m-client'),video,str(root)],'native-client',50);assert native['passed'] and len(native['cases'])==4
 native_status=wait_exports();native_state=state_icp()
 assert native_status['completed']==native_status['direct_completed']==native_status['jobs']==18 and native_status['starts']==3 and native_status['first_error']==native_status['failed']==native_status['cancelled']==0
 assert released(native_state) and native_state['frames_completed']==native_state['direct_frames']==8 and native_state['copy_frames']==0 and not native_state['pc_error']
 state.update(native_report=native,native_status=native_status,native_core_state=native_state);save('native-passed')
 lib=root/'lib';lib.mkdir();(lib/'libcamera.so.0.7.2').symlink_to(root/'libcamera.so.0.7.2');(lib/'libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
 pipeline=launch([sys.executable,str(root/'camera-client.py'),str(root)],'pipeline-client',240);assert pipeline['passed'] and len(pipeline['captures'])==7
 final=wait_exports();core_state=state_icp()
 completed=sum(r['ipe_completed'] for r in pipeline['captures'].values())
 assert final['completed']-native_status['completed']==completed and final['direct_completed']==final['completed'] and final['jobs']==final['completed']+final['cancelled']
 assert not any(final[k] for k in ['users','running','fatal','pinned','orphans','failed','first_error'])
 assert core_state['direct_frames']==core_state['frames_completed']>0 and core_state['copy_frames']==0 and not core_state['pc_error'] and released(core_state)
 assert collector.poll() is None
 (dev/'cleanup').write_text('1');assert released(state_icp())
 state.update(pipeline_report=pipeline,final_status=status(),final_core_state=state_icp(),pipeline_completed=completed,native_completed=18);verified=True;save('all-clients-passed')
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  if client is not None and client.poll() is None:
   os.killpg(client.pid,signal.SIGTERM)
   try:client.wait(timeout=12)
   except subprocess.TimeoutExpired:os.killpg(client.pid,signal.SIGKILL);client.wait(timeout=5)
  state['client_live']=client is not None and client.poll() is None
  current=wait_exports()
  if not current['users'] and not current['running']:(dev/'cleanup').write_text('1')
  state['cleanup_status']=status();state['cleanup_core_state']=state_icp()
  assert released(state['cleanup_core_state']) and not any(state['cleanup_status'][k] for k in ['users','running','pinned','orphans','owner_refs'])
  if collector is not None:
   (root/'collector-stop').touch();state['collector_exit']=collector.wait(timeout=5)
   state['collector_result']=json.loads((root/'collector-result.json').read_text())
   assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and (not state['collector_result']['captured'] or state['collector_result']['acknowledged'])
  if stopped:restart(items,'restore',started);wait_idle();state['services_restored']=True
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 state['clocks_after']=clocks();state['taint_after']=int(Path('/proc/sys/kernel/tainted').read_text());state['failure']=failure
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[]
 for line in logs.splitlines():
  m=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if m and float(m[1])>=start_uptime:new.append(line)
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|crash detected in modem|CCI error|Stream stop failed:'
 state['new_faults']=[l for l in new if re.search(pattern,l)]
 passed=verified and failure is None and state.get('services_restored') and not state['taint_after'] and not state['new_faults'] and state['clocks_after']==state['clocks_before']
 save('finished',terminal=True,passed=bool(passed))
