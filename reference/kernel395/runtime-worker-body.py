dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;collector_log=None;stopped=False;unloaded=False;core_updated=False;verified=False;restored_old=False;failure=None
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
def sync_directory(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def persist(p,data,mode):
 with Path(p).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 Path(p).chmod(mode);sync_directory(Path(p).parent)
def write_core(data):
 target=Path(meta['core_target']);tmp=target.with_name(target.name+'.k395-new');assert not tmp.exists();persist(tmp,data,state['core_mode']);os.replace(tmp,target);sync_directory(target.parent)
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
 run(['modprobe','qcom_camss'],'load-'+kind+'-platform',timeout=25);assert (dev/'driver').resolve().name=='qcom-sm8150-icp';notes(kind);idle();owner_zero()
 s=m2m();assert s['jobs']==0 and not core()['cpu_release_attempted']
 param=Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack');assert (param.exists() and param.read_text().strip()=='0') if kind=='test' else not param.exists()
 state['probe_'+kind]=s;state['loaded_kind']=kind
def launch(args,label,env=None,timeout=60):
 global client
 with (root/(label+'.out')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);save(label,client_pid=client.pid);code=client.wait(timeout=timeout)
 assert code==0,label+' failed; inspect owned client'
 return (root/(label+'.out')).read_text()+(root/(label+'.log')).read_text()
def unchanged_other():return all(sha(n)==h for n,h in meta['other_files'].items()) and all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and unchanged_other() and sha(meta['core_target'])==meta['old_core_sha256'];notes('old')
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 state['core_mode']=Path(meta['core_target']).stat().st_mode&0o777;backup=root/'backup';backup.mkdir(mode=0o700);persist(backup/'normal393-core.ko',Path(meta['core_target']).read_bytes(),state['core_mode']);assert sha(backup/'normal393-core.ko')==meta['old_core_sha256']
 items=services();persist(root/'services-private.json',json.dumps(items).encode(),0o600);stopped=True;stop_services(items);state['before_old_epoch']=idle();owner_zero()
 save('loading-candidate-test-core');unloaded=True;unload();load('test')
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5'];assert len(nodes)==1
 launch([str(root/'ack-loss-client'),'/dev/'+nodes[0].name],'ack-loss-concurrency',timeout=90)
 case=json.loads((root/'ack-loss-concurrency.out').read_text());assert case['passed'] and case['dropped_ack_count']==1 and case['warm_core']['session_peak']==2
 state['case']=case;state['after_fault_test']=idle();owner_zero();s=state['after_fault_test'];assert s['jobs']==6 and s['completed']==3 and s['failed']==3 and s['first_error']==-110 and s['cancelled']==0
 state['test_core_after']=core();assert not state['test_core_after']['watchdogs'] and not state['test_core_after']['protocol_errors']
 save('fault-recovery-verified-before-install')
 unload();save('installing-normal395-core');core_updated=True;write_core((root/'normal-core.ko').read_bytes());assert sha(meta['core_target'])==meta['new_core_sha256']
 run(['depmod',meta['release']],'depmod-new',timeout=35);load('new');state['normal395_installed']=True;save('normal395-loaded-no-test-knobs')
 env=os.environ.copy()
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 captures={}
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists());identity='/base'+str((device/'of_node').resolve()).split('/base',1)[1];prior=m2m()
  text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],'gst-'+model,env=env,timeout=45)
  m=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text);assert m and int(m[1])>0 and int(m[4])==int(m[5])==0 and 'IPE enabled ' in text and 'FIXTURE_RESTORATION result=0' in text
  s=idle();owner_zero();assert s['completed']-prior['completed']==int(m[1]) and s['direct_completed']==s['completed'] and not any(s[k] for k in ['failed','cancelled','first_error'])
  captures[model]=dict(frames=int(m[1]),ipe_completed=s['completed']-prior['completed'],passed=True)
 state.update(captures=captures,after_normal=m2m(),normal_core_after=core());assert unchanged_other() and sha(meta['core_target'])==meta['new_core_sha256'];verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Same client remains live; inspect it before module changes'
  if (dev/'driver').exists():idle();owner_zero()
  if not verified and unloaded:
   save('restoring-old393-core');unload()
   if core_updated:write_core((root/'backup/normal393-core.ko').read_bytes());assert sha(meta['core_target'])==meta['old_core_sha256'];run(['depmod',meta['release']],'depmod-old',timeout=35)
   load('old');restored_old=True
  if collector is not None:
   (root/'collector-stop').touch();collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text());assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and (not state['collector_result']['captured'] or state['collector_result']['acknowledged'])
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[l for l in logs.splitlines() if (m:=re.search(r'\[\s*(\d+\.\d+)\]',l)) and float(m[1])>=start_uptime]
 persist(root/'kernel-log-private.txt',('\n'.join(new)+'\n').encode(),0o600);faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:',l)]
 state.update(failure=failure,installed=verified,restored_old=restored_old,other_files_and_profiles_unchanged=unchanged_other(),new_unexpected_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
