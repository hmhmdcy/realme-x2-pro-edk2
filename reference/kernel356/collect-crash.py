from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai/k356-boot-r1');state=json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else dict(state_file_missing=True)
proc=Path('/proc')/str(state.get('pid',6799))
state['worker_process_observed']=proc.exists() and str(root/'worker.py').encode() in (proc/'cmdline').read_bytes()
pstore={p.name:p.read_text(errors='replace') for p in Path('/sys/fs/pstore').glob('*') if p.is_file()}
report=dict(boot_matches=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
 kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
 model=Path('/sys/firmware/devicetree/base/model').read_bytes().rstrip(b'\0').decode(),worker_state=state,pstore=pstore,
 worker_log=(root/'worker.log').read_text(errors='replace') if (root/'worker.log').exists() else '',root_files=[p.name for p in root.iterdir()] if root.exists() else [],core_present=Path('/sys/module/qcom_camss_icp_a5_core').exists(),test_present=Path('/sys/module/camss_icp_a5_boot_test').exists(),
 temporary_firmware_exists=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists())
report['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
print(json.dumps(report))
'''
r=host.raw_ssh('python3 -',input=code.encode(),timeout=25);d=json.loads(r.stdout);(host.PRIVATE/'crash-r1-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k not in ['pstore','worker_log','boot_id']},indent=2))
print('pstore_files',list(d['pstore']))
for name,s in d['pstore'].items():
 lines=s.splitlines();hits=set()
 for i,l in enumerate(lines):
  if any(t in l for t in ['panic','SError','Internal error','Call trace:','Asynchronous','abort','fault','camss_a5','icp','Trace:']):hits.update(range(max(0,i-2),min(len(lines),i+18)))
 print(name)
 for i in sorted(hits):print(lines[i])
