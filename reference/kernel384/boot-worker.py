"""Start the OEM A5 image once, test HFI, stop it, and remove owned resources."""
from pathlib import Path
import errno,hashlib,json,os,re,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'state.json'
core='qcom_camss_icp_a5_core';test='camss_icp_a5_boot_test';owned_core=False;attempted_test=False;owned_firmware=False
dt=Path('/sys/firmware/devicetree/base');node=dt/'soc@0/samurai-icp356-boot@ac10000'
reserved=[dt/'reserved-memory'/('samurai-icp356-'+n+'-iova') for n in ['fw','shared','heap','trace','images']]
firmware=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf')
extra_firmware=[]
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
def read_result():return json.loads(Path('/sys/module',test,'parameters/result').read_text())
def releasable(result):return result.get('terminal') and not result.get('backing_owned') and not result.get('cpu_enabled') and not result.get('power_held') and not result.get('mapped_bytes') and not result.get('remaining_groups') and not result.get('remaining_domains') and not result.get('ipe_dma_pending') and not result.get('request_fw_mapped')
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
 save('arm-collector')
 collector_log=(ROOT/'collector.log').open('xb')
 collector=subprocess.Popen([sys.executable,str(ROOT/'snapshot-collector.py'),str(ROOT)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 deadline=time.monotonic()+3
 while not (ROOT/'collector-ready.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.01)
 assert collector.poll() is None and (ROOT/'collector-ready.json').exists(),'Collector not live and armed; no A5 start allowed'
 ready=json.loads((ROOT/'collector-ready.json').read_text());assert ready['pid']==collector.pid and ready['ready']
 observation.update(collector_pid=collector.pid,collector_armed_before_boot_module=True)
 save('load-boot-test');attempted_test=True;run(['insmod',str(ROOT/'test.ko'),'hold_start_failure=1','snapshot_offsets='+','.join(str(w['offset']) for w in meta['snapshot_profile']['windows']),'snapshot_words='+','.join(str(w['words']) for w in meta['snapshot_profile']['windows']),'enable_frame=1'])
 ready_result=read_result()
 assert ready_result.get('terminal') and ready_result.get('phase')=='ready' and not ready_result.get('error') and not ready_result.get('cpu_release_attempted') and not ready_result.get('irq_enabled') and releasable(ready_result),'Probe did not return a resource-only ready state'
 assert ready_result.get('engine_dma_capable'),'Combined ICP SID ownership is required before frame dispatch'
 assert Path('/sys/module',test,'parameters/bound_seen').read_text().strip()=='Y','Platform binding notification not complete'
 assert collector.poll() is None,'Collector ended before explicit firmware run'
 save('binding-ready',device_result=ready_result,binding_returned_before_cpu_release=True)
 save('explicit-post-bind-run')
 Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/run').write_text('1')
 deadline=time.monotonic()+20
 while True:
  result=read_result();save('boot-test',device_result=result)
  if result['terminal']:break
  if time.monotonic()>deadline:raise RuntimeError('Bootstrap has not reached a terminal result')
  time.sleep(.2)
 held=bool(result.get('phase')=='failed-held' and result.get('terminal') and result.get('error') and result.get('cpu_release_attempted') and not result.get('cleanup_error') and not result.get('cpu_enabled') and not result.get('irq_enabled') and result.get('reset_asserted') and result.get('power_held') and result.get('backing_owned'))
 observation['held_window_returned']=held
 assert held or releasable(result),'Start has no confirmed held or fully released terminal state; inspect ownership'
 if not held and releasable(result):(ROOT/'collector-stop').touch()
 save('wait-snapshot',device_result=result)
 deadline=time.monotonic()+13
 while not (ROOT/'collector-result.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.005)
 assert (ROOT/'collector-result.json').exists(),'Collector incomplete; preserve standard dump and inspect owner'
 collected=json.loads((ROOT/'collector-result.json').read_text());observation['collector_result']=collected
 observation['snapshot_saved']=bool(collected.get('snapshot_saved'))
 observation['code_page_match']=bool(collected.get('snapshot',{}).get('code_page_match'))
 save('snapshot-collected')
 if held:
  save('cleanup-dma-pm',cleanup_attempted=True);cleanup_attempted=True
  Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
  result=read_result();save('cleanup-returned',device_result=result)
 assert releasable(result),'DMA/PM cleanup did not release all resources'
 assert not collected.get('captured') or collected.get('owned_snapshot_acknowledged'),'Standard snapshot still owns device reference'
 handshake=bool(result['error']==0 and result['cleanup_error']==0 and result['pc_error']==0 and result['init_response']==1 and result['init_done'] and result['ping_done'] and result['pc_done'] and result['fw_version'] and result['interrupts']>=3 and result['messages']>=3 and not result['watchdogs'] and not result['protocol_errors'])
 sessions=bool(result.get('session_creates')==2 and result.get('session_destroys')==2 and result.get('session_peak')==2 and not result.get('image_sessions') and not result.get('session_uncertain'))
 observation['ipe_session_lifecycle_passed']=sessions
 observation['firmware_handshake_passed']=handshake
 observation['firmware_failure_observed']=bool(result.get('init_response')==3)
 observation['diagnostic_completed']=bool(held and observation['snapshot_saved'] and not collected.get('error') and collected.get('owned_snapshot_acknowledged'))
 io=bool(result.get('io_configs')==2 and result.get('config_maps')==2 and result.get('config_unmaps')==2 and not result.get('config_fw_mapped') and len(result.get('scratch_bytes',[]))==2)
 observation['ipe_io_config_passed']=io
 frame=bool(result.get('image_frames')==1 and result.get('frames_completed')==1 and result.get('transfer_maps')==1 and result.get('transfer_unmaps')==1 and result.get('ipe_reset_acks')==[3,3] and result.get('engine_dma_capable') and not result.get('ipe_dma_pending') and not result.get('request_fw_mapped') and result.get('image_bytes')==460800)
 observation['image_control_completion_passed']=frame
 observation['passed']=handshake and sessions and io and frame

except BaseException as error:
 observation['error']=str(error);(ROOT/'failure.log').write_text(traceback.format_exc())
finally:
 try:
  if collector is not None:
   if collector.poll() is None:
    (ROOT/'collector-stop').touch();collector.wait(timeout=3)
   observation['collector_exit']=collector.returncode
   if (ROOT/'collector-result.json').exists():observation['collector_result']=json.loads((ROOT/'collector-result.json').read_text())
   if collector_log is not None:collector_log.close()
  if attempted_test and Path('/sys/module',test).exists():
   result=read_result();observation['device_result']=result
   if result.get('phase')=='failed-held' and not cleanup_attempted:
    save('cleanup-after-collector-error',cleanup_attempted=True);cleanup_attempted=True
    Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
    result=read_result();observation['device_result']=result
   if result.get('frames_completed')==1 and result.get('image_bytes')==460800 and not result.get('error'):
    image=Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/image').read_bytes();assert len(image)==460800
    with (ROOT/'ipe-output-private.nv12').open('xb') as stream:stream.write(image);stream.flush();os.fsync(stream.fileno())
   (ROOT/'sfr-private.txt').write_text(Path('/sys/module',test,'parameters/sfr').read_text())
   collected=observation.get('collector_result',{})
   snapshot_safe=not collected.get('captured') or collected.get('owned_snapshot_acknowledged',False)
   live_owned=[p for p in Path('/sys/class/devcoredump').glob('devcd*') if (p/'failing_device').exists() and (p/'failing_device').resolve().name=='ac10000.samurai-icp356-boot']
   if releasable(result) and snapshot_safe and not live_owned:
    save('unload-boot-test');run(['rmmod',test])
   else:observation['requires_cleanup_attention']=True
  if owned_core and not Path('/sys/module',test).exists():
   save('unload-core');run(['rmmod',core]);owned_core=False
  if owned_firmware and not Path('/sys/module',test).exists():firmware.unlink();owned_firmware=False
  if not Path('/sys/module',test).exists():
   for path in extra_firmware:path.unlink()
   extra_firmware=[]
 except BaseException as error:observation['cleanup_error']=str(error);observation['passed']=False
 deadline=time.monotonic()+5
 while camss_status()!='suspended' and time.monotonic()<deadline:time.sleep(.1)
 observation['clocks_after']=clocks();observation['camss_after']=camss_status()
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
