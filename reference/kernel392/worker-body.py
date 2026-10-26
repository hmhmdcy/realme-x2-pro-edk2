dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;collector_log=None;stopped=False;failure=None;verified=False
start_uptime=float(Path('/proc/uptime').read_text().split()[0])
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def idle():
 wait_idle();s=m2m();assert not any(s[k] for k in ['users','running','fatal','pinned','orphans']) and released(core());return s
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and (dev/'driver').resolve().name=='qcom-sm8150-icp'
 meta=json.loads((root/'manifest.json').read_text())
 for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
 assert hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()==meta['camss_note_sha256']
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n');stopped=True;stop_services(items);state['before']=idle();assert not state['before']['owner_refs']
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 nodes=[]
 for p in Path('/sys/class/video4linux').glob('video*'):
  if (p/'name').read_text().strip()=='qcom-ipe-a5':nodes.append('/dev/'+p.name)
 assert len(nodes)==1
 with (root/'client.jsonl').open('xb') as out,(root/'client.log').open('xb') as err:
  client=subprocess.Popen([str(root/'cancel-client'),nodes[0],*meta.get('client_args',[])],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  save('cancel-and-rejection-running',client_pid=client.pid);result=client.wait(timeout=90)
 state['client_exit']=result
 state['cases']=[json.loads(l) for l in (root/'client.jsonl').read_text().splitlines()]
 assert result==0 and len(state['cases'])==meta.get('expected_cases',5) and all(c['passed'] for c in state['cases'])
 state['after']=idle();assert not state['after']['owner_refs']
 assert state['after']['cancelled']-state['before']['cancelled']>=meta.get('expected_cancellations',4)
 assert state['after']['failed']-state['before']['failed']==2
 assert state['after']['direct_completed']==state['after']['completed']
 assert state['after']['jobs']-state['before']['jobs']==sum(state['after'][k]-state['before'][k] for k in ['completed','cancelled','failed'])
 state['core_after']=core();verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Inspect the same live client; do not restart consumers'
  state['after']=idle();assert not state['after']['owner_refs']
  if collector is not None:
   (root/'collector-stop').touch();state['collector_exit']=collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text())
   assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and not state['collector_result']['captured']
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[]
 for line in logs.splitlines():
  m=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if m and float(m[1])>=start_uptime:new.append(line)
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|crash detected in modem|CCI error|Stream stop failed:',l)]
 state.update(failure=failure,new_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']},core_after=core(),hardware_fault_injection=False)
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
