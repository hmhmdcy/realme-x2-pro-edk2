dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};stopped=False;unload_sent=False;load_sent=False;collector=None;collector_log=None;verified=False;child=None;failure=None
start_uptime=float(Path('/proc/uptime').read_text().split()[0])
def read_status():return json.loads((dev/'m2m_status').read_text())
def core_state():return json.loads((dev/'state').read_text())
def wait_owner_zero():
 deadline=time.monotonic()+5
 while read_status()['owner_refs']:
  assert time.monotonic()<deadline,'CAMSS still held';time.sleep(.02)
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def capture(model,label,candidate):
 global child
 devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()];assert len(devices)==1
 camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1];env=os.environ.copy()
 for key in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 env['LIBCAMERA_LOG_LEVELS']='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG'
 if candidate:env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera')
 with (root/(label+'.log')).open('xb') as log:
  child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',camera_id,'640','480'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save(label,client_pid=child.pid);code=child.wait(timeout=45)
 text=(root/(label+'.log')).read_text(errors='replace');match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
 assert code==0 and match and int(match[1])>0 and int(match[4])==int(match[5])==0 and 'FIXTURE_RESTORATION result=0' in text
 assert ('IPE enabled ' in text)==candidate
 wait_idle();wait_owner_zero();return dict(frames=int(match[1]),ipe_enabled=candidate,passed=True)
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n');stopped=True;stop_services(items);wait_idle();wait_owner_zero()
 before=read_status();assert before['completed']==before['direct_completed']==before['jobs']==99 and released(core_state())
 state['before_removal']=before
 assert not Path('/sys/bus/platform/drivers/qcom-camss/unbind').exists() and not Path('/sys/bus/platform/drivers/qcom-sm8150-icp/unbind').exists()
 save('unloading-camss-and-icp');unload_sent=True;run(['rmmod','qcom_camss'],'unload-camss')
 assert not Path('/sys/module/qcom_camss').exists() and not (dev/'driver').exists()
 assert not any((p/'name').read_text().strip()=='qcom-ipe-a5' for p in Path('/sys/class/video4linux').glob('video*'))
 save('camss-and-icp-unregistered',unload_passed=True)
 load_sent=True;run(['modprobe','qcom_camss'],'reload-camss');wait_idle();wait_owner_zero()
 assert (dev/'driver').resolve().name=='qcom-sm8150-icp' and read_status()['registered'] and read_status()['jobs']==0 and released(core_state()) and not core_state()['cpu_release_attempted']
 state['reloaded_ready']=read_status();state['reloaded_core_state']=core_state();save('normal-drivers-reloaded')
 lib=root/'lib';lib.mkdir();(lib/'libcamera.so.0.7.2').symlink_to('/var/lib/samurai/k387-pipeline-r5/libcamera.so.0.7.2');(lib/'libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 state['post_reload_ipe']=capture('imx319','candidate-ipe',True);ipe=read_status();assert ipe['completed']==ipe['direct_completed']==state['post_reload_ipe']['frames'] and ipe['failed']==ipe['first_error']==ipe['cancelled']==0
 state['post_reload_ipe_status']=ipe
 state['installed_ife_captures']={n:capture(n,'installed-'+n,False) for n in ['imx471','imx319','s5k3m5','s5kgw1']}
 assert read_status()['jobs']==ipe['jobs'],'Installed original path unexpectedly dispatched IPE'
 assert released(core_state());state['final_status']=read_status();state['final_core_state']=core_state();verified=True
except BaseException:failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=12)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
  if collector is not None:
   (root/'collector-stop').touch();state['collector_exit']=collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text())
   assert not state['collector_result'].get('error') and not state['collector_result']['captured']
  assert Path('/sys/module/qcom_camss').exists() and (dev/'driver').exists() and released(core_state())
  wait_owner_zero()
  if stopped:restart(items,'restore',started);wait_idle();state['services_restored']=True
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[]
 for line in logs.splitlines():
  m=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if m and float(m[1])>=start_uptime:new.append(line)
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n');pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|crash detected in modem|CCI error|Stream stop failed:'
 state.update(new_faults=[l for l in new if re.search(pattern,l)],taint_after=int(Path('/proc/sys/kernel/tainted').read_text()),failure=failure)
 save('finished',terminal=True,passed=bool(verified and failure is None and state.get('services_restored') and not state['taint_after'] and not state['new_faults']))
