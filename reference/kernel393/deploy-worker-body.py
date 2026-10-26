dev=Path('/sys/bus/platform/devices/ac10000.icp');items={};started={};client=None;collector=None;collector_log=None;stopped=False;changed=False;unloaded=False;verified=False;rollback=False;failure=None
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
def notes(which):
 for row in meta['modules']:assert sha('/sys/module/'+row['module']+'/notes/.note.gnu.build-id')==row[which+'_note_sha256']
def unload():
 if Path('/sys/module/qcom_camss').exists():
  idle();owner_zero();run(['rmmod','qcom_camss'],'unload-camss',timeout=20)
 for name in ['camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
  if Path('/sys/module',name).exists():run(['rmmod',name],'unload-'+name,timeout=15)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()
def write_module(target,data,mode):
 target=Path(target);tmp=target.with_name(target.name+'.k393-new');assert not tmp.exists()
 with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 tmp.chmod(mode);os.replace(tmp,target);fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def start_platform(which):
 run(['depmod',meta['release']],'depmod-'+which,timeout=35);run(['modprobe','qcom_camss'],'load-'+which,timeout=25)
 assert (dev/'driver').resolve().name=='qcom-sm8150-icp';notes(which)
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==meta['camss_note_sha256']
 s=idle();state['probe_'+which+'_initial_status']=s
 # Device discovery may briefly open a newly registered video node. Join
 # those references with the same bounded wait used before normal unload.
 owner_zero();s=m2m();assert s['jobs']==0 and not s['owner_refs']
 assert not core()['cpu_release_attempted'],'Probe must not start firmware'
def launch(args,label,env=None,timeout=60):
 global client
 with (root/(label+'.out')).open('xb') as out,(root/(label+'.log')).open('xb') as err:
  client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  save(label,client_pid=client.pid);result=client.wait(timeout=timeout)
 assert result==0,label+' failed; inspect owned client'
 return (root/(label+'.out')).read_text()+(root/(label+'.log')).read_text()
def profiles_match():return all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and profiles_match()
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 notes('old');assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==meta['camss_note_sha256']
 backup=root/'backup';backup.mkdir(mode=0o700)
 for row in meta['modules']:
  target=Path(row['target']);assert sha(target)==row['old_sha256'];shutil.copyfile(target,backup/target.name);assert sha(backup/target.name)==row['old_sha256'];row['mode']=target.stat().st_mode&0o777
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);state['before_old_epoch']=idle();owner_zero()
 save('unloading-old-platform');unloaded=True;unload()
 save('installing-core-adapter-pair');changed=True
 for row in meta['modules']:write_module(row['target'],(root/row['file']).read_bytes(),row['mode']);assert sha(row['target'])==row['new_sha256']
 start_platform('new');state['after_load_new_epoch']=m2m();save('normal-new-platform-bound')
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5'];assert len(nodes)==1
 text=launch([str(root/'local-error-client'),'/dev/'+nodes[0].name],'local-error-and-cancel',timeout=90)
 cases=[json.loads(l) for l in (root/'local-error-and-cancel.out').read_text().splitlines()];state['cases']=cases
 assert len(cases)==2 and all(c['passed'] for c in cases) and cases[0]['same_fd_repaired_while_peer_session_live']
 s=idle();owner_zero();assert s['jobs']==7 and s['completed']==s['direct_completed']==5 and s['cancelled']==1 and s['failed']==1 and s['first_error']==-22
 state['after_native']=s;captures={};env=os.environ.copy()
 for key in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists());identity='/base'+str((device/'of_node').resolve()).split('/base',1)[1];prior=m2m()
  text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],'gst-'+model,env=env,timeout=45)
  m=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
  assert m and int(m[1])>0 and int(m[4])==int(m[5])==0 and 'IPE enabled ' in text and 'FIXTURE_RESTORATION result=0' in text
  s=idle();owner_zero();assert s['completed']-prior['completed']==int(m[1]) and s['failed']==1 and s['cancelled']==1
  captures[model]=dict(frames=int(m[1]),ipe_completed=s['completed']-prior['completed'],passed=True)
 state.update(captures=captures,after=m2m(),core_after=core());assert profiles_match();verified=True
 save('new-pair-default-four-camera-verified')
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None,'Owned client remains live; inspect it before rollback/restart'
  if (dev/'driver').exists():idle();owner_zero()
  if collector is not None:
   (root/'collector-stop').touch();collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text());assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and not state['collector_result']['captured']
  if not verified and unloaded:
   save('rolling-back-pair');unload()
   if changed:
    for row in meta['modules']:write_module(row['target'],(root/'backup'/Path(row['target']).name).read_bytes(),row['mode']);assert sha(row['target'])==row['old_sha256']
   start_platform('old');rollback=True
  if stopped:restart(items,'restored',started);wait_idle()
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[l for l in logs.splitlines() if (m:=re.search(r'\[\s*(\d+\.\d+)\]',l)) and float(m[1])>=start_uptime]
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n');faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:',l)]
 state.update(failure=failure,installed=verified,rollback=rollback,new_faults=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),private_profiles_unchanged=profiles_match(),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and not state['taint'] and all(len(v)==1 for v in state['services'].values())))
