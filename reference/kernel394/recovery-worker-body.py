dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;stopped=False;failure=None;verified=False
meta=json.loads((root/'manifest.json').read_text());start_uptime=float(Path('/proc/uptime').read_text().split()[0])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def status():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def idle():
 wait_idle();s=status();c=core();assert not any(s[k] for k in ['users','running','fatal','pinned','orphans']) and not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes']);return s
def owner_zero():
 deadline=time.monotonic()+5
 while status()['owner_refs']:assert time.monotonic()<deadline;time.sleep(.02)
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 assert all(sha(n)==h for n,h in meta['normal_files'].items())
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);state['before']=idle();owner_zero();assert not state['before']['jobs']
 with (root/'collector.log').open('xb') as log:collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 env=os.environ.copy()
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 captures={}
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists());identity='/base'+str((device/'of_node').resolve()).split('/base',1)[1];prior=status()
  with (root/('gst-'+model+'.log')).open('xb') as log:
   client=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('recovery-gst-'+model,client_pid=client.pid);code=client.wait(timeout=45)
  text=(root/('gst-'+model+'.log')).read_text();m=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
  assert code==0 and m and int(m[1])>0 and int(m[4])==int(m[5])==0 and 'IPE enabled ' in text and 'FIXTURE_RESTORATION result=0' in text
  s=idle();owner_zero();assert s['completed']-prior['completed']==int(m[1]) and s['direct_completed']==s['completed'] and not any(s[k] for k in ['failed','cancelled','first_error'])
  captures[model]=dict(frames=int(m[1]),ipe_completed=s['completed']-prior['completed'],passed=True)
 state.update(captures=captures,after=status(),core_after=core());verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Inspect the same live client before restoring consumers'
  idle();owner_zero()
  if collector is not None:
   (root/'collector-stop').touch();collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text());assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and not state['collector_result']['captured']
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[l for l in logs.splitlines() if (m:=re.search(r'\[\s*(\d+\.\d+)\]',l)) and float(m[1])>=start_uptime]
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n');faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:',l)]
 state.update(failure=failure,new_unexpected_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),normal_files_unchanged=all(sha(n)==h for n,h in meta['normal_files'].items()),test_knob_absent=not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists(),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
