dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;collector_log=None;stopped=False;unloaded=False;restored=False;verified=False;failure=None
meta=json.loads((root/'manifest.json').read_text());start_uptime=float(Path('/proc/uptime').read_text().split()[0])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def idle():
 wait_idle();s=m2m();assert not any(s[k] for k in ['users','running','fatal','pinned','orphans']) and released(core());return s
def owner_zero():
 deadline=time.monotonic()+5
 while m2m()['owner_refs']:assert time.monotonic()<deadline,'Camera provider still owned';time.sleep(.02)
def notes(kind):
 assert sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta[kind+'_core_note_sha256']
 for n,h in meta['unchanged_notes'].items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h
def unload():
 if Path('/sys/module/qcom_camss').exists():idle();owner_zero();run(['rmmod','qcom_camss'],'unload-camss',timeout=20)
 for n in ['camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
  if Path('/sys/module',n).exists():run(['rmmod',n],'unload-'+n,timeout=15)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()
def load(kind):
 if kind=='test':run(['insmod',str(root/'test-core.ko')],'load-test-core',timeout=20)
 run(['modprobe','qcom_camss'],'load-'+kind+'-platform',timeout=25)
 assert (dev/'driver').resolve().name=='qcom-sm8150-icp';notes(kind);idle();owner_zero();s=m2m();assert not s['jobs'] and not core()['cpu_release_attempted']
 param=Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack')
 assert (param.exists() and param.read_text().strip()=='0') if kind=='test' else not param.exists()
 state['probe_'+kind]=s
def launch(args,label,env=None,timeout=60):
 global client
 with (root/(label+'.out')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);save(label,client_pid=client.pid);code=client.wait(timeout=timeout)
 assert code==0,label+' failed; inspect owned child'
 return (root/(label+'.out')).read_text()+(root/(label+'.log')).read_text()
def unchanged():
 return all(sha(n)==h for n,h in meta['normal_files'].items()) and all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and unchanged();notes('normal')
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);state['normal_before_unload']=idle();owner_zero()
 save('loading-private-test-core');unloaded=True;unload();load('test')
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5'];assert len(nodes)==1
 launch([str(root/'ack-loss-client'),'/dev/'+nodes[0].name],'ack-loss-concurrency',timeout=90)
 case=json.loads((root/'ack-loss-concurrency.out').read_text());assert case['passed'] and case['dropped_ack_count']==1 and case['warm_core']['session_peak']==2
 state['case']=case;state['test_after']=idle();owner_zero();assert state['test_after']['jobs']==6 and state['test_after']['completed']==3 and state['test_after']['failed']==3 and state['test_after']['first_error']==-110
 state['test_core_after']=core();assert not state['test_core_after']['watchdogs'] and not state['test_core_after']['protocol_errors']
 save('restoring-normal393-core');unload();load('normal');restored=True;state['normal_after_restore']=m2m()
 camera=next(p for p in Path('/sys/bus/i2c/drivers/imx319').iterdir() if (p/'of_node').exists());identity='/base'+str((camera/'of_node').resolve()).split('/base',1)[1]
 env=os.environ.copy()
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],'normal-default-gst',env=env,timeout=45)
 m=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text);assert m and int(m[1])>0 and int(m[4])==int(m[5])==0 and 'IPE enabled ' in text and 'FIXTURE_RESTORATION result=0' in text
 s=idle();owner_zero();assert s['jobs']==s['completed']==s['direct_completed']==int(m[1]) and not any(s[n] for n in ['failed','cancelled','first_error'])
 state.update(normal_after=s,normal_core_after=core(),default_gst_frames=int(m[1]));assert unchanged();verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Same client still live: no unload/restart before inspecting it'
  if (dev/'driver').exists():idle();owner_zero()
  if unloaded and not restored:
   save('cleanup-restore-normal393-core');unload();load('normal');restored=True
  if collector is not None:
   (root/'collector-stop').touch();collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text());assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and (not state['collector_result']['captured'] or state['collector_result']['acknowledged'])
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[l for l in logs.splitlines() if (m:=re.search(r'\[\s*(\d+\.\d+)\]',l)) and float(m[1])>=start_uptime]
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n');faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:',l)]
 state.update(failure=failure,normal393_restored=restored,normal_disk_files_and_profiles_unchanged=unchanged(),new_unexpected_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and restored and failure is None and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
