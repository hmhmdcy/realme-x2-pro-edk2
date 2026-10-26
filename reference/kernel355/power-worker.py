"""Run the resource lifecycle probe and release the temporary test device."""
from pathlib import Path
import json,os,re,subprocess,time,traceback
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'state.json'
core='qcom_camss_icp_a5_core';test='camss_icp_a5_power_test';owned_core=False;owned_test=False
dt=Path('/sys/firmware/devicetree/base');node=dt/'soc@0/samurai-icp355-power@ac10000'
observation=dict(pid=os.getpid(),terminal=False,passed=False,firmware_started=False,events=[])
def save(phase,**values):
 observation.update(phase=phase,**values);tmp=ROOT/'state.tmp';tmp.write_text(json.dumps(observation,indent=2)+'\n');tmp.replace(STATE)
def run(args):
 q=subprocess.run(args,capture_output=True,timeout=30)
 observation['events'].append(dict(command=args,exit_code=q.returncode,stderr=q.stderr.decode(errors='replace')))
 if q.returncode:raise RuntimeError('Command failed: '+args[0])
def read_result():return json.loads(Path('/sys/module',test,'parameters/result').read_text())
def clocks():
 names=['icp','bps','ipe_0','ipe_1'];out={}
 for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
  f=line.split()
  if f and any(f[0].startswith('cam_cc_'+n+'_') for n in names):out[f[0]]=int(f[1])
 return out
def camss_status():return Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()
save('preflight');start_uptime=float(Path('/proc/uptime').read_text().split()[0]);taint_before=int(Path('/proc/sys/kernel/tainted').read_text())
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
 meta=json.loads((ROOT/'manifest.json').read_text());assert Path('/proc/sys/kernel/osrelease').read_text().strip()==meta['kernel_release']
 for name in ['camss@acb3000','clock-controller@ad00000']:
  assert int.from_bytes((dt/'soc@0'/name/'phandle').read_bytes(),'big')==meta[name]
 assert not Path('/sys/module',core).exists() and not Path('/sys/module',test).exists() and not node.exists()
 observation['clocks_before']=clocks();observation['camss_before']=camss_status()
 assert len(observation['clocks_before'])==17 and not any(observation['clocks_before'].values()),'ICP/BPS/IPE resources busy or clock inventory incomplete'
 assert observation['camss_before']=='suspended','CAMSS has an active consumer'
 save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True
 save('load-power-test');run(['insmod',str(ROOT/'test.ko')]);owned_test=True
 deadline=time.monotonic()+20
 while True:
  result=read_result();save('power-test',device_result=result)
  if result['terminal']:break
  if time.monotonic()>deadline:raise RuntimeError('Probe did not finish')
  time.sleep(.2)
 assert result['error']==0 and result['suspend_error']==0,result
 assert result['powered_groups']==15 and result['powered_domains']==7
 assert result['remaining_groups']==0 and result['remaining_domains']==0 and result['runtime_suspended']
 assert not result['firmware_started']
 observation['passed']=True
except BaseException as error:
 observation['error']=str(error);(ROOT/'failure.log').write_text(traceback.format_exc())
finally:
 try:
  if owned_test:
   observation['device_result']=read_result();save('unload-power-test');run(['rmmod',test]);owned_test=False
  if owned_core and not Path('/sys/module',test).exists():
   save('unload-core');run(['rmmod',core]);owned_core=False
 except BaseException as error:observation['cleanup_error']=str(error);observation['passed']=False
 deadline=time.monotonic()+5
 while camss_status()!='suspended' and time.monotonic()<deadline:time.sleep(.1)
 observation['clocks_after']=clocks();observation['camss_after']=camss_status()
 observation['core_absent']=not Path('/sys/module',core).exists();observation['test_absent']=not Path('/sys/module',test).exists();observation['temporary_dt_node_absent']=not node.exists()
 observation['taint_before']=taint_before;observation['taint_after']=int(Path('/proc/sys/kernel/tainted').read_text())
 logs=subprocess.run(['dmesg'],capture_output=True,text=True).stdout;new=[]
 for line in logs.splitlines():
  match=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if match and float(match.group(1))>=start_uptime:new.append(line)
 (ROOT/'kernel-log-private.txt').write_text('\n'.join(new)+'\n')
 pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault'
 observation['new_relevant_faults']=[line for line in new if re.search(pattern,line)]
 observation['passed']=bool(observation['passed'] and observation['core_absent'] and observation['test_absent'] and observation['temporary_dt_node_absent'] and observation['camss_after']=='suspended' and observation['clocks_after']==observation['clocks_before'] and observation['taint_after']==taint_before and not observation['new_relevant_faults'])
 save('finished',terminal=True)
