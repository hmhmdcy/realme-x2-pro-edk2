dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;collector_log=None;stopped=False;unloaded=False;restored=False;verified=False;failure=None
meta=json.loads((root/'manifest.json').read_text());start_uptime=float(Path('/proc/uptime').read_text().split()[0])
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
 s=m2m();assert not s['jobs'] and not core()['cpu_release_attempted'];p=Path('/sys/module/camss_icp_a5_m2m/parameters/test_gamma_mode')
 if kind=='candidate':assert p.read_text().strip()=='0'
 else:assert not p.exists()
 assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists();state['probe_'+kind]=s
def launch(args,label,env=None,timeout=60):
 global client
 with (root/(label+'.out')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);save(label,client_pid=client.pid);ret=client.wait(timeout=timeout)
 assert ret==0,label+' failed; inspect this client and its saved output'
 return (root/(label+'.out')).read_text()+(root/(label+'.log')).read_text()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and disk_unchanged();notes('normal')
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 items=services()
 with (root/'services-private.json').open('x') as f:f.write(json.dumps(items));f.flush();os.fsync(f.fileno())
 stopped=True;stop_services(items);state['before']=idle();owner_zero();save('loading-private-candidate');unloaded=True;unload();load('candidate')
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True);save('arming-collector',collector_pid=collector.pid)
 end=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<end;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5'];assert len(nodes)==1
 launch([str(root/'colour-client'),'/dev/'+nodes[0].name,str(root)],'colour-pixels',timeout=75)
 rows=[json.loads(l) for l in (root/'colour-pixels.out').read_text().splitlines()];assert len(rows)==21 and [(r['format'],r['mode']) for r in rows[:20]]==[(f,m) for f in range(2) for m in range(10)] and rows[-1]['passed']
 state['native_cases']=rows;state['after_native']=idle();owner_zero();s=state['after_native'];assert s['jobs']==s['completed']==s['direct_completed']==20 and s['starts']==s['stops']==20 and not any(s[k] for k in ['failed','cancelled','first_error'])
 state['native_core_after']=core();assert not state['native_core_after']['watchdogs'] and not state['native_core_after']['protocol_errors'];save('native-colour-completed-before-restore')
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
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[l for l in logs.splitlines() if (m:=re.search(r'\[\s*(\d+\.\d+)\]',l)) and float(m[1])>=start_uptime]
 with (root/'kernel-log-private.txt').open('x') as f:f.write('\n'.join(new)+'\n');f.flush();os.fsync(f.fileno())
 faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',l)]
 state.update(failure=failure,normal395_restored=restored,normal_files_and_profiles_unchanged=disk_unchanged(),new_unexpected_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']},candidate_permanently_installed=False)
 save('finished',terminal=True,passed=bool(verified and failure is None and restored and disk_unchanged() and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
