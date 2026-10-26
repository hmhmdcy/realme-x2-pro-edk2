"""Start the OEM A5 image once, test HFI, stop it, and remove owned resources."""
from pathlib import Path
import errno,hashlib,json,os,re,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'state.json'
core='qcom_camss_icp_a5_core';test='camss_icp_a5_boot_test';owned_core=False;attempted_test=False;owned_firmware=False
dt=Path('/sys/firmware/devicetree/base');node=dt/'soc@0/samurai-icp356-boot@ac10000'
reserved=[dt/'reserved-memory'/('samurai-icp356-'+n+'-iova') for n in ['fw','shared','heap','trace','images']]
firmware=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf')
extra_firmware=[]
owned_helper=False;owned_adapter=False;client=None
collector=None;collector_log=None;cleanup_attempted=False
observation=dict(pid=os.getpid(),terminal=False,passed=False,firmware_handshake_passed=False,diagnostic_completed=False,snapshot_saved=False,events=[])
def save(phase,**values):
 observation.update(phase=phase,**values);tmp=ROOT/'state.tmp'
 with tmp.open('w') as stream:stream.write(json.dumps(observation,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
 tmp.replace(STATE)
 descriptor=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(descriptor)
 finally:os.close(descriptor)
def run(args):
 q=subprocess.run(args,capture_output=True,timeout=30)
 observation['events'].append(dict(command=args,exit_code=q.returncode,stderr=q.stderr.decode(errors='replace')))
 if q.returncode:raise RuntimeError('Command failed: '+args[0])
def read_m2m():return json.loads(Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/m2m_status').read_text())

def wait_exports():
 deadline=time.monotonic()+5
 while True:
  current=read_m2m()
  if not current['owner_refs']:return current
  if time.monotonic()>deadline:raise RuntimeError('Export owner still pinned; retain platform and DMA domain')
  time.sleep(.02)

def read_result():return json.loads(Path('/sys/module',test,'parameters/result').read_text())
def releasable(result):return not result.get('imported_buffers') and not result.get('imported_bytes') and result.get('terminal') and not result.get('backing_owned') and not result.get('cpu_enabled') and not result.get('power_held') and not result.get('mapped_bytes') and not result.get('remaining_groups') and not result.get('remaining_domains') and not result.get('ipe_dma_pending') and not result.get('request_fw_mapped')
def clocks():
 out={}
 for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
  f=line.split()
  if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):out[f[0]]=int(f[1])
 return out
def camss_status():return Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()
save('preflight');start_uptime=float(Path('/proc/uptime').read_text().split()[0]);taint_before=int(Path('/proc/sys/kernel/tainted').read_text())
try:
 assert taint_before==0,'Unexpected taint before A5 bootstrap'
 meta=json.loads((ROOT/'manifest.json').read_text())
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(meta['boot_guard']).read_bytes()
 assert Path('/proc/sys/kernel/osrelease').read_text().strip()==meta['kernel_release']
 for name,digest in meta['payload_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
 assert hashlib.sha256((ROOT/'firmware.elf').read_bytes()).hexdigest()==meta['firmware_sha256']
 for name in ['camss@acb3000','clock-controller@ad00000','iommu@15000000']:
  assert int.from_bytes((dt/'soc@0'/name/'phandle').read_bytes(),'big')==meta[name]
 assert int.from_bytes((dt/'interrupt-parent').read_bytes(),'big')==meta['interrupt_parent']
 camera=dt/meta['firmware_region_path'].lstrip('/')
 assert (camera/'no-map').exists()
 assert (camera/'phandle').read_bytes()==meta['existing_firmware_phandle'].to_bytes(4,'big')
 assert (dt/'soc@0/icp@ac10000/memory-region').read_bytes()==(camera/'phandle').read_bytes()
 assert (camera/'reg').read_bytes()==meta['firmware_physical'].to_bytes(8,'big')+meta['firmware_bytes'].to_bytes(8,'big')
 assert not Path('/sys/module',core).exists() and not Path('/sys/module',test).exists() and not node.exists() and not any(p.exists() for p in reserved)
 observation['clocks_before']=clocks();observation['camss_before']=camss_status()
 assert len(observation['clocks_before'])==17 and not any(observation['clocks_before'].values()),'ICP/BPS/IPE busy or clock inventory incomplete'
 assert observation['camss_before']=='suspended','CAMSS has an active consumer'
 assert Path('/sys/class/devcoredump').is_dir()
 disabled=Path('/sys/class/devcoredump/disabled')
 assert not disabled.exists() or disabled.read_text().strip()=='0','Standard devcoredump is disabled'
 assert not any((p/'failing_device').exists() and (p/'failing_device').resolve().name=='ac10000.samurai-icp356-boot' for p in Path('/sys/class/devcoredump').glob('devcd*'))
 firmware.parent.mkdir(parents=True,exist_ok=True)
 with firmware.open('xb') as stream:
  owned_firmware=True;stream.write((ROOT/'firmware.elf').read_bytes());stream.flush();os.fsync(stream.fileno())
 save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True
 save('load-helper');run(['insmod',str(ROOT/'helper.ko')]);owned_helper=True
 save('load-adapter');run(['insmod',str(ROOT/'adapter.ko')]);owned_adapter=True
 save('arm-collector')
 collector_log=(ROOT/'collector.log').open('xb')
 collector=subprocess.Popen([sys.executable,str(ROOT/'snapshot-collector.py'),str(ROOT),'--seconds','120'],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 deadline=time.monotonic()+3
 while not (ROOT/'collector-ready.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.01)
 assert collector.poll() is None and (ROOT/'collector-ready.json').exists(),'Collector not live and armed; no A5 start allowed'
 ready=json.loads((ROOT/'collector-ready.json').read_text());assert ready['pid']==collector.pid and ready['ready']
 observation.update(collector_pid=collector.pid,collector_armed_before_boot_module=True)
 save('load-boot-test');attempted_test=True;run(['insmod',str(ROOT/'test.ko'),'hold_start_failure=1','snapshot_offsets='+','.join(str(w['offset']) for w in meta['snapshot_profile']['windows']),'snapshot_words='+','.join(str(w['words']) for w in meta['snapshot_profile']['windows']),'enable_m2m=1'])

 ready_result=read_result();observation['probe_snapshot_before_refresh']=ready_result
 deadline=time.monotonic()+3
 while True:
  refreshed=read_m2m();ready_result=read_result()
  observation['ready_result']=ready_result;observation['ready_m2m_status']=refreshed
  observation['ready_pm_status']=Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/power/runtime_status').read_text().strip()
  save('post-bind-result',device_result=ready_result)
  assert not ready_result.get('cpu_release_attempted') and not refreshed['jobs'],'Unexpected pre-client firmware activity'
  if releasable(ready_result) and observation['ready_pm_status']=='suspended':break
  if time.monotonic()>deadline:raise RuntimeError('Post-bind runtime PM did not reach idle')
  time.sleep(.02)

 assert ready_result.get('terminal') and ready_result.get('phase')=='ready' and not ready_result.get('error') and not ready_result.get('cpu_release_attempted') and not ready_result.get('irq_enabled') and releasable(ready_result),'Probe did not return a resource-only ready state'
 assert ready_result.get('engine_dma_capable'),'Combined ICP SID ownership is required before frame dispatch'
 assert Path('/sys/module',test,'parameters/bound_seen').read_text().strip()=='Y','Platform binding notification not complete'
 assert collector.poll() is None,'Collector ended before explicit firmware run'

 save('binding-ready',device_result=ready_result,binding_returned_before_cpu_release=True)
 before=read_m2m();assert before['registered'] and not before['users'] and not before['running'] and not before['pinned'] and not before['jobs']
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5']
 assert len(nodes)==1 and (nodes[0]/'device').resolve().name=='ac10000.samurai-icp356-boot'
 media=[p for p in Path('/sys/bus/media/devices').glob('media*') if any(parent.name=='ac10000.samurai-icp356-boot' for parent in p.resolve().parents)]
 observation['media_discovery']=[dict(name=p.name,path=str(p.resolve())) for p in Path('/sys/bus/media/devices').glob('media*')]
 assert len(media)==1,'M2M media device must be discoverable'

 (ROOT/'export-lifetime-client').chmod(0o700)
 with (ROOT/'export-client.log').open('xb') as output:
  client=subprocess.Popen([str(ROOT/'export-lifetime-client'),'/dev/'+nodes[0].name,str(ROOT)],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
  save('export-client-running',export_client_pid=client.pid)
  def held(marker):
   deadline=time.monotonic()+5
   while not (ROOT/marker).exists():
    assert client.poll() is None,'Export client exited before '+marker
    assert time.monotonic()<deadline,'Export client marker timeout: '+marker
    time.sleep(.01)
   current=read_m2m()
   assert not any(current[k] for k in ['users','running','jobs','pinned','orphans'])
   assert current['owner_refs']>0,'Export no longer pins real platform owner'
   assert int(Path('/sys/module',test,'refcnt').read_text())>=current['owner_refs']
   observation[marker.replace('-','_')]=current
   save(marker)
  held('export-held')
  (ROOT/'close-export-fd').touch()
  held('mmap-only-held')
  (ROOT/'release-export-mmap').touch()
  observation['export_client_exit']=client.wait(timeout=8)
 assert observation['export_client_exit']==0
 assert (ROOT/'export-released').exists()
 observation['export_after_release']=wait_exports()
 observation['export_fd_and_vma_lifetime_passed']=True
 save('export-lifetime-complete')
 (ROOT/'m2m-client').chmod(0o700)
 with (ROOT/'client-private.json').open('xb') as output,(ROOT/'client-private.log').open('xb') as errors:
  client=subprocess.Popen([str(ROOT/'m2m-client'),'/dev/'+nodes[0].name,str(ROOT)],stdin=subprocess.DEVNULL,stdout=output,stderr=errors)
  save('client-running',client_pid=client.pid,video_node=nodes[0].name,media_node=media[0].name)
  exit_code=client.wait(timeout=45)
 observation['client_exit']=exit_code
 assert exit_code==0,'V4L2 client failed; preserve private output/log and inspect cleanup'
 client_report=json.loads((ROOT/'client-private.json').read_text());assert client_report['passed'] and len(client_report['cases'])==4
 after=wait_exports()
 assert after['registered'] and not any(after[k] for k in ['users','running','fatal','pinned','orphans','failed'])
 assert after['jobs']==after['completed']==18 and after['starts']==3
 assert after['direct_completed']==18 and after['cancelled']==0
 observation.update(m2m_before=before,m2m_after_client=after,client_report=client_report)
 save('m2m-client-complete')
 save('cleanup-dma-pm',cleanup_attempted=True);cleanup_attempted=True
 Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
 final=wait_exports();result=read_result()
 assert not any(final[k] for k in ['users','running','fatal','pinned','orphans'])
 assert releasable(result) and result['error']==result['cleanup_error']==result['pc_error']==0
 assert result['init_response']==1 and result['init_done'] and result['pc_done']
 assert result['session_creates']==result['session_destroys']==result['session_peak']==2
 assert result['frames_completed']==result['image_frames']==8
 assert result['direct_frames']==8 and result['copy_frames']==0 and result['imported_buffers']==result['imported_bytes']==0
 assert collector.poll() is None,'Collector must cover the complete native client'
 (ROOT/'collector-stop').touch()
 deadline=time.monotonic()+13
 while not (ROOT/'collector-result.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.005)
 assert (ROOT/'collector-result.json').exists()
 collected=json.loads((ROOT/'collector-result.json').read_text());observation['collector_result']=collected
 assert not collected.get('captured') or collected.get('owned_snapshot_acknowledged')
 observation.update(m2m_final=final,device_result=result,firmware_handshake_passed=True,
  m2m_control_and_pixel_client_passed=True,passed=True)

except BaseException as error:
 observation['error']=str(error);(ROOT/'failure.log').write_text(traceback.format_exc())
finally:
 try:
  child_live=client is not None and client.poll() is None
  observation['client_live']=child_live
  if collector is not None:
   if collector.poll() is None:
    (ROOT/'collector-stop').touch();collector.wait(timeout=3)
   observation['collector_exit']=collector.returncode
   if (ROOT/'collector-result.json').exists():observation['collector_result']=json.loads((ROOT/'collector-result.json').read_text())
   if collector_log is not None:collector_log.close()
  if attempted_test and Path('/sys/module',test).exists():
   if child_live:
    observation['requires_cleanup_attention']=True
   else:
    status=wait_exports();observation['m2m_before_removal']=status
    if not status['users'] and not cleanup_attempted:
     save('cleanup-after-client-error',cleanup_attempted=True);cleanup_attempted=True
     Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
     status=read_m2m();observation['m2m_cleanup_retry_result']=status
    result=read_result();observation['device_result']=result
    (ROOT/'sfr-private.txt').write_text(Path('/sys/module',test,'parameters/sfr').read_text())
    collected=observation.get('collector_result',{})
    snapshots_safe=not collected.get('captured') or collected.get('owned_snapshot_acknowledged',False)
    live_owned=[p for p in Path('/sys/class/devcoredump').glob('devcd*') if (p/'failing_device').exists() and (p/'failing_device').resolve().name=='ac10000.samurai-icp356-boot']
    if not any(status[k] for k in ['users','running','pinned','orphans','owner_refs']) and releasable(result) and snapshots_safe and not live_owned:
     save('unload-platform-owner');run(['rmmod',test])
    else:observation['requires_cleanup_attention']=True
  if owned_adapter and not Path('/sys/module',test).exists():
   save('unload-adapter');run(['rmmod','camss_icp_a5_m2m']);owned_adapter=False
  if owned_helper and not Path('/sys/module/camss_icp_a5_m2m').exists() and not Path('/sys/module',test).exists():
   save('unload-helper');run(['rmmod','v4l2_mem2mem']);owned_helper=False
  if owned_core and not Path('/sys/module',test).exists() and not Path('/sys/module/camss_icp_a5_m2m').exists():
   save('unload-core');run(['rmmod',core]);owned_core=False
  if owned_firmware and not Path('/sys/module',test).exists():
   firmware.unlink();owned_firmware=False
 except BaseException as error:
  observation['cleanup_error']=str(error);observation['passed']=False
 deadline=time.monotonic()+5
 while camss_status()!='suspended' and time.monotonic()<deadline:time.sleep(.1)
 observation['clocks_after']=clocks();observation['camss_after']=camss_status()
 observation['adapter_absent']=not Path('/sys/module/camss_icp_a5_m2m').exists();observation['helper_absent']=not Path('/sys/module/v4l2_mem2mem').exists()
 observation['m2m_video_absent']=not any((p/'name').read_text().strip()=='qcom-ipe-a5' for p in Path('/sys/class/video4linux').glob('video*'))
 observation['passed']=bool(observation['passed'] and observation['adapter_absent'] and observation['helper_absent'] and observation['m2m_video_absent'] and not observation['client_live'])
 observation['core_absent']=not Path('/sys/module',core).exists();observation['test_absent']=not Path('/sys/module',test).exists()
 observation['temporary_dt_nodes_absent']=not node.exists() and not any(p.exists() for p in reserved)
 observation['temporary_firmware_removed']=not owned_firmware and not firmware.exists() and not extra_firmware and not any((firmware.parent/name).exists() for name in ['samurai-ipe382-stripe.bin'])
 observation['taint_before']=taint_before;observation['taint_after']=int(Path('/proc/sys/kernel/tainted').read_text())
 logs=subprocess.run(['dmesg'],capture_output=True,text=True).stdout;new=[]
 for line in logs.splitlines():
  match=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if match and float(match.group(1))>=start_uptime:new.append(line)
 (ROOT/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|OF: ERROR|watchdog received|crash detected in modem'
 observation['new_relevant_faults']=[line for line in new if re.search(pattern,line)]
 observation['passed']=bool(observation['passed'] and observation['core_absent'] and observation['test_absent'] and observation['temporary_dt_nodes_absent'] and observation['temporary_firmware_removed'] and observation['camss_after']=='suspended' and observation['clocks_after']==observation['clocks_before'] and observation['taint_after']==taint_before and not observation['new_relevant_faults'])
 observation['diagnostic_completed']=bool(observation.get('diagnostic_completed') and observation['core_absent'] and observation['test_absent'] and observation['temporary_dt_nodes_absent'] and observation['temporary_firmware_removed'] and observation['camss_after']=='suspended' and observation['clocks_after']==observation['clocks_before'] and observation['taint_after']==taint_before and not observation['new_relevant_faults'])
 save('finished',terminal=True)
