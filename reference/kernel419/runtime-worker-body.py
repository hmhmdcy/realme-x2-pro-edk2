dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;collector_log=None;stopped=False;unloaded=False;restored=False;verified=False;failure=None
meta=json.loads((root/'manifest.json').read_text());start_uptime=float(Path('/proc/uptime').read_text().split()[0]);kernel_anchor=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines()[-1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released(c):return not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def idle():
 wait_idle();s=m2m();assert not any(s[k] for k in ['users','running','fatal','pinned','orphans']) and released(core());return s
def owner_zero():
 end=time.monotonic()+5
 while m2m()['owner_refs']:assert time.monotonic()<end;time.sleep(.02)
def disk_unchanged():return all(sha(n)==h for n,h in meta['normal_files'].items()) and all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
def notes(kind):
 assert sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta[kind+'_core_note_sha256']
 assert sha('/sys/module/camss_icp_a5_m2m/notes/.note.gnu.build-id')==meta[kind+'_adapter_note_sha256']
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==meta['camss_note_sha256']
def unload():
 if Path('/sys/module/qcom_camss').exists():idle();owner_zero();run(['rmmod','qcom_camss'],'unload-platform',timeout=20)
 for name in ['camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
  if Path('/sys/module',name).exists():run(['rmmod',name],'unload-'+name,timeout=15)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()
def load(kind):
 if kind=='candidate':
  run(['insmod',str(root/'candidate-core.ko')],'load-candidate-core',timeout=20);run(['insmod',str(root/'test-adapter.ko')],'load-test-adapter',timeout=20)
 run(['modprobe','qcom_camss'],'load-'+kind+'-platform',timeout=25);assert (dev/'driver').resolve().name=='qcom-sm8150-icp';notes(kind);idle();owner_zero()
 s=m2m();assert not s['jobs'] and not core()['cpu_release_attempted']
 assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_ltm_mode').exists()
 param=Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack')
 if kind=='candidate':assert param.exists() and param.read_text().strip()=='0'
 else:assert not param.exists()
 state['probe_'+kind]=s
def launch(args,label,env=None,timeout=60):
 global client
 with (root/(label+'.out')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);save(label,client_pid=client.pid);ret=client.wait(timeout=timeout)
 assert ret==0,label+' failed; inspect this client and its saved output'
 return (root/(label+'.out')).read_text()+(root/(label+'.log')).read_text()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 assert int(Path('/proc/sys/kernel/tainted').read_text())==512 and disk_unchanged();notes('normal')
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 items=services()
 with (root/'services-private.json').open('x') as f:f.write(json.dumps(items));f.flush();os.fsync(f.fileno())
 stopped=True;stop_services(items);state['before']=idle();owner_zero();save('loading-private-candidate');unloaded=True;unload();load('candidate')
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True);save('arming-collector',collector_pid=collector.pid)
 end=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<end;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5'];assert len(nodes)==1
 import fcntl
 media=[]
 for p in Path('/dev').glob('media[0-9]*'):
  fd=os.open(p,os.O_RDWR|os.O_CLOEXEC)
  try:
   info=bytearray(256);fcntl.ioctl(fd,0xc1007c00,info)
   if bytes(info[16:48]).split(b'\0')[0]==b'SM8150 IPE':media.append(str(p))
  finally:os.close(fd)
 assert len(media)==1
 library=root/'lib';library.mkdir();(library/'libcamera.so.0.7.2').write_bytes((root/'libcamera.so.0.7.2').read_bytes());(library/'libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
 env=os.environ.copy()
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 env.update(LD_LIBRARY_PATH=str(library),LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera',LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 state['fault_start_uptime']=float(Path('/proc/uptime').read_text().split()[0]);save('typed-request-fault-client')
 launch([str(root/'ack-loss-client'),'/dev/'+nodes[0].name,media[0],str(root)],'typed-ack-loss',env=env,timeout=90)
 case=json.loads((root/'typed-ack-loss.out').read_text());assert case['passed'] and case['dropped_ack_count']==1 and case['actual_libcamera418']
 assert case['warm_core']['session_peak']==2 and case['combined_ltm_gamma_timeout'] and case['idle_consumer_preserves_fatal_gate'] and case['blocked_callback_seconds']<1
 state['case']=case;state['fault_end_uptime']=float(Path('/proc/uptime').read_text().split()[0]);state['after_fault_test']=idle();owner_zero()
 s=state['after_fault_test'];assert s['completed']==s['direct_completed']==3 and s['first_error']==-110 and s['failed']>=2
 assert s['jobs']==s['completed']+s['failed']+s['cancelled'] and not any(s[k] for k in ['users','running','fatal','pinned','orphans'])
 state['test_core_after']=core();assert not state['test_core_after']['watchdogs'] and not state['test_core_after']['protocol_errors']
 save('typed-ack-loss-reset-recovery-complete')
 unload();load('normal');restored=True;save('normal395-restored')
 env=os.environ.copy()
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 captures={}
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists());identity='/base'+str((device/'of_node').resolve()).split('/base',1)[1];before=m2m()
  text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],'gst-'+model,env=env,timeout=45)
  match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text);assert match and int(match[1])>0 and int(match[4])==int(match[5])==0 and 'IPE enabled ' in text and 'FIXTURE_RESTORATION result=0' in text
  s=idle();owner_zero();c=core();delta={k:s[k]-before[k] for k in ['jobs','completed','direct_completed']};assert delta['jobs']==delta['completed']==delta['direct_completed']>=int(match[1]) and not any(s[k] for k in ['failed','cancelled','first_error'])
  assert c['frames_completed']==delta['completed'] and c['session_creates']==c['session_destroys']==1 and not c['watchdogs'] and not c['protocol_errors']
  captures[model]=dict(frames=int(match[1]),ipe_completed=delta['completed'],extra_completed=delta['completed']-int(match[1]),passed=True);state['captures']=captures.copy();save('verified-gst-'+model)
 state.update(after_normal=m2m(),normal_core_after=core());verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Inspect the same live client before changing its owner'
  if (dev/'driver').exists():idle();owner_zero()
  if unloaded and not restored:save('restoring-normal395');unload();load('normal');restored=True
  if collector is not None:
   (root/'collector-stop').touch();collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text());assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and (not state['collector_result']['captured'] or state['collector_result']['acknowledged'])
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');lines=logs.splitlines();assert lines.count(kernel_anchor)==1;new=lines[lines.index(kernel_anchor)+1:]
 with (root/'kernel-log-private.txt').open('x') as f:f.write('\n'.join(new)+'\n');f.flush();os.fsync(f.fileno())
 expected=[];faults=[];begin=end=-1
 if state.get('case',{}).get('passed'):
  dropped=[i for i,l in enumerate(new) if 'FAULT_TEST dropped validated frame ACK once' in l];assert len(dropped)==1;begin=dropped[0]
  end=next(i for i in range(begin+1,len(new)) if 'A5 SYS_INIT acknowledged' in new[i])
 for i,line in enumerate(new):
  in_case=begin<=i<end
  if in_case and re.search(r'(?:A5 IPE frame failed|IPE m2m job failed) ret=-(?:110|5)(?:\s|$)',line):expected.append(line);continue
  if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',line):faults.append(line)
 state['expected_frame_error_log_count']=len(expected)
 state.update(failure=failure,normal395_restored=restored,normal_files_and_profiles_unchanged=disk_unchanged(),new_unexpected_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']},candidate_permanently_installed=False,baseline_taint=512,known_warning_from417_failed_runtime_r2=True)
 save('finished',terminal=True,passed=bool(verified and failure is None and restored and disk_unchanged() and not faults and state['taint']==512 and all(len(v)==1 for v in state['services'].values())))
