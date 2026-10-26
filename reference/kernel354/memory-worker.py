"""Run the memory-only diagnostic once and remove only resources we loaded."""
from pathlib import Path
import json,os,re,subprocess,time,traceback
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'state.json';pid=os.getpid()
core='qcom_camss_icp_a5_core';test='camss_icp_a5_memory_test';owned_core=False;owned_test=False
observation=dict(pid=pid,terminal=False,passed=False,firmware_started=False,events=[])
def save(phase,**values):
 observation.update(phase=phase,**values);tmp=ROOT/'state.tmp';tmp.write_text(json.dumps(observation,indent=2)+'\n');tmp.replace(STATE)
def run(args):
 q=subprocess.run(args,capture_output=True,timeout=30)
 observation['events'].append(dict(command=args,exit_code=q.returncode,stderr=q.stderr.decode(errors='replace')))
 if q.returncode:raise RuntimeError('Command failed: '+args[0])
def read_result():return json.loads(Path('/sys/module',test,'parameters/result').read_text())
save('preflight')
start_uptime=float(Path('/proc/uptime').read_text().split()[0]);taint_before=int(Path('/proc/sys/kernel/tainted').read_text())
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
 meta=json.loads((ROOT/'manifest.json').read_text());assert Path('/proc/sys/kernel/osrelease').read_text().strip()==meta['kernel_release']
 dt=Path('/sys/firmware/devicetree/base');assert int.from_bytes((dt/'soc@0/iommu@15000000/phandle').read_bytes(),'big')==meta['phandle']
 assert not Path('/sys/module',core).exists() and not Path('/sys/module',test).exists()
 assert not (dt/'soc@0/samurai-icp354-memory').exists() and not (dt/'reserved-memory/samurai-icp354-fw-iova').exists()
 clocks={}
 for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
  fields=line.split()
  if fields and fields[0] in ['cam_cc_icp_clk','cam_cc_icp_ahb_clk']:clocks[fields[0]]=int(fields[1])
 observation['icp_leaf_clock_enable_counts']=clocks
 assert len(clocks)==2 and all(count==0 for count in clocks.values()),'ICP clocks are not quiescent'
 save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True
 save('load-memory-test');run(['insmod',str(ROOT/'test.ko')]);owned_test=True
 deadline=time.monotonic()+30
 while True:
  result=read_result();save('memory-test',device_result=result)
  if result['terminal']:break
  if time.monotonic()>deadline:raise RuntimeError('Diagnostic has not reached a terminal result')
  time.sleep(.2)
 assert not result['firmware_started']
 if result['backing_owned']:
  driver=Path('/sys/bus/platform/drivers/samurai-a5-icp-memory-test')
  cleanup=next(p/'cleanup' for p in driver.iterdir() if p.is_symlink() and (p/'cleanup').is_file())
  cleanup.write_text('1\n');result=read_result();save('cleanup-retry',device_result=result)
 assert not result['backing_owned'] and result['mapped_bytes']==0,'Backing remains owned; do not force unload'
 assert result['error']==0 and result['verified_pages']==1280 and result['removed_pages']==1280 and result['group_devices']==1
 observation['passed']=True
except BaseException as error:
 observation['error']=str(error);(ROOT/'failure.log').write_text(traceback.format_exc())
finally:
 try:
  if Path('/sys/module',test).exists():
   result=read_result();observation['device_result']=result
   if result.get('terminal') and not result.get('backing_owned') and result.get('mapped_bytes')==0:
    save('unload-memory-test');run(['rmmod',test]);owned_test=False
   else:observation['requires_cleanup_attention']=True
  if owned_core and not Path('/sys/module',test).exists():
   save('unload-core');run(['rmmod',core]);owned_core=False
 except BaseException as error:
  observation['cleanup_error']=str(error);observation['passed']=False
 dt=Path('/sys/firmware/devicetree/base')
 observation['core_absent']=not Path('/sys/module',core).exists();observation['test_absent']=not Path('/sys/module',test).exists()
 observation['temporary_dt_nodes_absent']=not (dt/'soc@0/samurai-icp354-memory').exists() and not (dt/'reserved-memory/samurai-icp354-fw-iova').exists()
 observation['taint_before']=taint_before;observation['taint_after']=int(Path('/proc/sys/kernel/tainted').read_text())
 logs=subprocess.run(['dmesg'],capture_output=True,text=True).stdout;new=[]
 for line in logs.splitlines():
  match=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if match and float(match.group(1))>=start_uptime:new.append(line)
 (ROOT/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault'
 observation['new_relevant_faults']=[line for line in new if re.search(pattern,line)]
 observation['passed']=bool(observation['passed'] and observation['core_absent'] and observation['test_absent'] and observation['temporary_dt_nodes_absent'] and observation['taint_after']==taint_before and not observation['new_relevant_faults'])
 save('finished',terminal=True)
