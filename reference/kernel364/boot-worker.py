"""Start the OEM A5 image once, test HFI, stop it, and remove owned resources."""
from pathlib import Path
import json,os,re,subprocess,time,traceback
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'state.json'
core='qcom_camss_icp_a5_core';test='camss_icp_a5_boot_test';owned_core=False;attempted_test=False;owned_firmware=False
dt=Path('/sys/firmware/devicetree/base');node=dt/'soc@0/samurai-icp356-boot@ac10000'
reserved=[dt/'reserved-memory'/('samurai-icp356-'+n+'-iova') for n in ['fw','shared','heap','trace']]
firmware=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf')
observation=dict(pid=os.getpid(),terminal=False,passed=False,events=[])
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
def releasable(result):return result.get('terminal') and not result.get('backing_owned') and not result.get('cpu_enabled') and not result.get('power_held') and not result.get('mapped_bytes')
def clocks():
 out={}
 for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
  f=line.split()
  if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):out[f[0]]=int(f[1])
 return out
def camss_status():return Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()
save('preflight');start_uptime=float(Path('/proc/uptime').read_text().split()[0]);taint_before=int(Path('/proc/sys/kernel/tainted').read_text())
try:
 meta=json.loads((ROOT/'manifest.json').read_text())
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(meta['boot_guard']).read_bytes()
 assert Path('/proc/sys/kernel/osrelease').read_text().strip()==meta['kernel_release']
 for name in ['camss@acb3000','clock-controller@ad00000','iommu@15000000']:
  assert int.from_bytes((dt/'soc@0'/name/'phandle').read_bytes(),'big')==meta[name]
 assert int.from_bytes((dt/'interrupt-parent').read_bytes(),'big')==meta['interrupt_parent']
 camera=dt/meta['firmware_region_path'].lstrip('/')
 assert (camera/'no-map').exists()
 assert (camera/'reg').read_bytes()==meta['firmware_physical'].to_bytes(8,'big')+meta['firmware_bytes'].to_bytes(8,'big')
 assert not Path('/sys/module',core).exists() and not Path('/sys/module',test).exists() and not node.exists() and not any(p.exists() for p in reserved)
 observation['clocks_before']=clocks();observation['camss_before']=camss_status()
 assert len(observation['clocks_before'])==17 and not any(observation['clocks_before'].values()),'ICP/BPS/IPE busy or clock inventory incomplete'
 assert observation['camss_before']=='suspended','CAMSS has an active consumer'
 firmware.parent.mkdir(parents=True,exist_ok=True)
 with firmware.open('xb') as stream:
  owned_firmware=True;stream.write((ROOT/'firmware.elf').read_bytes());stream.flush();os.fsync(stream.fileno())
 save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True
 save('load-boot-test');attempted_test=True;run(['insmod',str(ROOT/'test.ko')])
 deadline=time.monotonic()+20
 while True:
  result=read_result();save('boot-test',device_result=result)
  if result['terminal']:break
  if time.monotonic()>deadline:raise RuntimeError('Bootstrap has not reached a terminal result')
  time.sleep(.2)
 if not releasable(result):
  path=Path('/sys/bus/platform/drivers/samurai-a5-icp-boot-test')
  cleanup=next(p/'cleanup' for p in path.iterdir() if p.is_symlink() and (p/'cleanup').is_file())
  cleanup.write_text('1\n');result=read_result();save('cleanup-retry',device_result=result)
 assert releasable(result),'A5 or mapped backing remains owned; do not force unload'
 assert result['error']==0 and result['cleanup_error']==0 and result['pc_error']==0,result
 assert result['init_response']==1 and result['init_done'] and result['ping_done'] and result['pc_done']
 assert result['fw_version'] and result['interrupts']>=3 and result['messages']>=3
 assert result['reset_asserted'] and not result['watchdogs'] and not result['protocol_errors']
 assert result['remaining_groups']==0 and result['remaining_domains']==0
 observation['passed']=True
except BaseException as error:
 observation['error']=str(error);(ROOT/'failure.log').write_text(traceback.format_exc())
finally:
 try:
  if attempted_test and Path('/sys/module',test).exists():
   result=read_result();observation['device_result']=result
   (ROOT/'sfr-private.txt').write_text(Path('/sys/module',test,'parameters/sfr').read_text())
   if releasable(result):
    save('unload-boot-test');run(['rmmod',test])
   else:observation['requires_cleanup_attention']=True
  if owned_core and not Path('/sys/module',test).exists():
   save('unload-core');run(['rmmod',core]);owned_core=False
  if owned_firmware and not Path('/sys/module',test).exists():firmware.unlink();owned_firmware=False
 except BaseException as error:observation['cleanup_error']=str(error);observation['passed']=False
 deadline=time.monotonic()+5
 while camss_status()!='suspended' and time.monotonic()<deadline:time.sleep(.1)
 observation['clocks_after']=clocks();observation['camss_after']=camss_status()
 observation['core_absent']=not Path('/sys/module',core).exists();observation['test_absent']=not Path('/sys/module',test).exists()
 observation['temporary_dt_nodes_absent']=not node.exists() and not any(p.exists() for p in reserved)
 observation['temporary_firmware_removed']=not owned_firmware and not firmware.exists()
 observation['taint_before']=taint_before;observation['taint_after']=int(Path('/proc/sys/kernel/tainted').read_text())
 logs=subprocess.run(['dmesg'],capture_output=True,text=True).stdout;new=[]
 for line in logs.splitlines():
  match=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if match and float(match.group(1))>=start_uptime:new.append(line)
 (ROOT/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|OF: ERROR'
 observation['new_relevant_faults']=[line for line in new if re.search(pattern,line)]
 observation['passed']=bool(observation['passed'] and observation['core_absent'] and observation['test_absent'] and observation['temporary_dt_nodes_absent'] and observation['temporary_firmware_removed'] and observation['camss_after']=='suspended' and observation['clocks_after']==observation['clocks_before'] and observation['taint_after']==taint_before and not observation['new_relevant_faults'])
 save('finished',terminal=True)
