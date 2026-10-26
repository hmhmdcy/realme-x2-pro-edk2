"""One incremental read-only handback after the completed physical replug."""
from pathlib import Path
import importlib.util
import json

REF=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'r7-handoff';OUT.mkdir(mode=0o700,exist_ok=True)
baseline=json.loads((PRIVATE/'r7-postboot/latest-observation-private.json').read_text())['raw']
expected={'camera_pm':baseline['pm'],'m2m':baseline['m2m'],'core':baseline['core'],
          'services':sorted([{'comm':name,**row} for name,rows in baseline['services'].items() for row in rows],key=lambda r:r['comm']),
          'anchor':baseline['dmesg']['stdout'].splitlines()[-64:]}
code='EXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import hashlib,json,runpy,subprocess
worker=Path('/root/charging-management-20261023/charging-update-r6-runner.py')
assert hashlib.sha256(worker.read_bytes()).hexdigest()=='b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98'
u=runpy.run_path(str(worker));io=u['Device']();m=io.manager(u['HASHES'][u['SERVICE']]);meta=io.verify(m)
assert hashlib.sha256(Path(u['MANIFEST']).read_bytes()).hexdigest()=='5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
io.notes_match(m,meta);data=io.observe(m);state=u['healthy'](data,True)
assert data['state']['taint']=='0' and data['openrc_started'] is True
assert data['state']['camera_pm']==EXPECTED['camera_pm'] and data['state']['m2m']==EXPECTED['m2m']
assert Path('/sys/bus/platform/devices/ac10000.icp/state').read_text().strip()==EXPECTED['core']
assert sorted(data['state']['services'],key=lambda r:r['comm'])==EXPECTED['services']
source=Path('/sys/class/power_supply/samurai-usb-input')
data['source_type']=(source/'usb_type').read_text().strip();data['source_budget_ua']=int((source/'current_max').read_text())
assert data['source_budget_ua']==data['sample']['budget_ua']==100000
assert '[SDP]' in data['source_type']
logs=subprocess.check_output(['dmesg'],text=True);lines=logs.splitlines();anchor=EXPECTED['anchor']
matches=[i for i in range(len(lines)-len(anchor)+1) if lines[i:i+len(anchor)]==anchor]
assert len(matches)==1,'new log coverage cannot be proved'
new='\n'.join(lines[matches[0]+len(anchor):])
faults={n:new.count(n) for n in ['WARNING:','BUG:','Oops:','Call Trace:','refcount_t: underflow','gpu fault:','NGD resume failed']}
assert not any(faults.values()),faults
data['dmesg']=logs
data['result']={'passed':True,'manifest_sha256':'5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68',
 'modules_exact':True,'state':state,'sample':data['sample'],'limits':data['limits'],'source_type':data['source_type'],
 'effective_source_budget_ua':data['source_budget_ua'],'camera_resources_and_services_preserved':True,
 'taint':0,'log_coverage':'unique continuous 64-line postboot tail','new_log_lines':len(lines)-matches[0]-len(anchor),
 'selected_new_faults':faults,'net_charging_proven':data['sample']['gauge_current_ua']>0,
 'physical_icon_latency_accepted':False,'pm_resume_failure_resolved':False}
print(json.dumps(data),flush=True)
'''
spec=importlib.util.spec_from_file_location('window',REF/'device-window.py')
window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
q=window.host.ssh('python3 -',input=code.encode(),timeout=30,check=False)
(OUT/'snapshot-private.json').write_bytes(q.stdout)
(OUT/'stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
data=json.loads(q.stdout);result=data['result']
(REF/'r7-handoff-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
