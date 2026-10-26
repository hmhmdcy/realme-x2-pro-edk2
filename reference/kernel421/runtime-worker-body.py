meta=json.loads((root/'manifest.json').read_text());dev=Path('/sys/bus/platform/devices/ac10000.icp')
items={};started={};client=None;collector=None;collector_log=None;stopped=False;verified=False;failure=None
kernel_anchor=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines()[-1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released():return not any(core()[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
def idle():
 wait_idle();assert released() and not any(m2m()[k] for k in ['users','running','fatal','pinned','orphans']);return m2m()
def owner_zero():
 end=time.monotonic()+5
 while m2m()['owner_refs']:assert time.monotonic()<end;time.sleep(.02)
def unchanged():
 assert all(sha(n)==h for n,h in meta['normal_files'].items())
 assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
 for n,h in meta['notes'].items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h
def launch(args,label,env=None,timeout=90):
 global client
 with (root/(label+'.out')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);save(label,client_pid=client.pid)
  code=client.wait(timeout=timeout)
 assert not code,label+' failed; inspect its terminal child and logs'
 return (root/(label+'.out')).read_text()+(root/(label+'.log')).read_text()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 assert int(Path('/proc/sys/kernel/tainted').read_text())==512;unchanged()
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);state['before']=idle();owner_zero()
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);end=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<end;time.sleep(.01)
 launch([sys.executable,str(root/'camera-client.py'),str(root)],'candidate-suite',timeout=400)
 suite=json.loads((root/'candidate-suite.out').read_text());assert suite['passed'] and len(suite['captures'])==meta.get('expected_captures',7)
 state['candidate_suite']=suite;state['after_candidate']=idle();owner_zero();unchanged();save('candidate-frame-history-complete')
 env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 device=next(p for p in Path('/sys/bus/i2c/drivers/imx471').iterdir() if (p/'of_node').exists());identity='/base'+str((device/'of_node').resolve()).split('/base',1)[1]
 prior=m2m();text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],'formal-front',env=env,timeout=45)
 match=re.search(r'GST_RESULT frames=(\d+).*bus-errors=(\d+) result=(\d+)',text);assert match and int(match[1])>0 and match[2]==match[3]=='0' and 'FIXTURE_RESTORATION result=0' in text
 after=idle();owner_zero();assert after['completed']-prior['completed']>=int(match[1]) and not after['failed']
 state['formal_front']=dict(frames=int(match[1]),ipe_completed=after['completed']-prior['completed'],passed=True)
 unchanged();verified=True;save('formal-stack-rechecked')
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Client still live: retain transaction and inspect its handle'
  idle();unchanged()
  if stopped:restart(items,'restored',started);wait_idle()
  if collector is not None:
   (root/'collector-stop').touch();state['collector_exit']=collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text())
   assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and not state['collector_result']['captured']
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 lines=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines();assert lines.count(kernel_anchor)==1
 logs=lines[lines.index(kernel_anchor)+1:];(root/'kernel-log-private.txt').write_text('\n'.join(logs)+'\n')
 faults=[l for l in logs if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',l)]
 state.update(failure=failure,formal420_unchanged=verified,new_fault_count=len(faults),taint=int(Path('/proc/sys/kernel/tainted').read_text()),after=m2m(),core_after=core(),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and state['taint']==512 and released() and all(len(v)==1 for v in state['services'].values())))
