dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};collector=None;child=None;stopped=False;verified=False;failure=None
def status():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def idle():
 wait_idle();s=status();c=core()
 assert not any(s[k] for k in ['users','running','fatal','pinned','orphans'])
 assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
 return s
start_uptime=float(Path('/proc/uptime').read_text().split()[0])
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 meta=json.loads((root/'manifest.json').read_text())
 for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);state['before']=idle();assert not state['before']['owner_refs']
 with (root/'collector.log').open('xb') as log:
  collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 camera=next(p for p in Path('/sys/bus/i2c/drivers/imx319').iterdir() if (p/'of_node').exists());identity='/base'+str((camera/'of_node').resolve()).split('/base',1)[1]
 env=os.environ.copy()
 for key in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 args=[str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480']
 with (root/'default-gst.log').open('xb') as log:
  child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);save('default-gstreamer-recovery',client_pid=child.pid);state['client_exit']=child.wait(timeout=45)
 assert state['client_exit']==0
 text=(root/'default-gst.log').read_text();m=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
 assert m and int(m[1])>0 and int(m[4])==int(m[5])==0 and 'IPE enabled ' in text and 'FIXTURE_RESTORATION result=0' in text
 state['after']=idle();before=state['before'];after=state['after']
 assert not after['owner_refs'] and after['failed']==before['failed']==2 and after['cancelled']==before['cancelled']==4 and after['first_error']==before['first_error']==-22
 assert after['completed']-before['completed']==int(m[1]) and after['direct_completed']==after['completed']
 state['frames']=int(m[1]);state['historical_expected_error_counter_not_active_fault']=True;verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert child is None or child.poll() is not None,'Inspect the same live child before restarting consumers'
  idle()
  if collector is not None:
   (root/'collector-stop').touch();collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text());assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and not state['collector_result']['captured']
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[l for l in logs.splitlines() if (m:=re.search(r'\[\s*(\d+\.\d+)\]',l)) and float(m[1])>=start_uptime]
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n');faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:',l)]
 state.update(failure=failure,new_faults=faults,core_after=core(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
