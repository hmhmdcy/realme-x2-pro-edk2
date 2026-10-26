"""Read the existing bootstrap transaction; never start or stop a device job."""
from pathlib import Path
import json, re, sys, time
import host

run = sys.argv[1] if len(sys.argv)>1 else 'r5'
assert re.fullmatch(r'r\d+', run)
launch = json.loads((host.PRIVATE/('launch-'+run+'-private.json')).read_text())
code = r'''
from pathlib import Path
import json,subprocess
root=Path(ROOT);state_path=root/'state.json'
state=json.loads(state_path.read_text()) if state_path.exists() else None
pid=state['pid'] if state and 'pid' in state else PID
proc=Path('/proc')/str(pid)
cmd=(proc/'cmdline').read_bytes() if proc.exists() else b''
guard=Path('/var/lib/samurai/k356-recovered/boot-id-private.txt')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
report=dict(ssh_command_executed=True,boot_id=boot.decode().strip(),
 same_boot_as_r2_through_r5=guard.exists() and guard.read_bytes()==boot,
 kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
 state=state,worker_process_observed=cmd and str(root/'worker.py').encode() in cmd,
 worker_pid=pid,root_exists=root.exists(),
 core_present=Path('/sys/module/qcom_camss_icp_a5_core').exists(),
 test_present=Path('/sys/module/camss_icp_a5_boot_test').exists(),
 worker_log=(root/'worker.log').read_text(errors='replace') if (root/'worker.log').exists() else '',
 kernel_log=subprocess.run(['dmesg'],capture_output=True,text=True).stdout,
 pstore={p.name:p.read_text(errors='replace') for p in Path('/sys/fs/pstore').glob('*') if p.is_file()})
report['worker_process_observed']=bool(report['worker_process_observed'])
print(json.dumps(report))
'''.replace('ROOT', repr(launch['root'])).replace('PID', str(launch['pid']))
start = time.monotonic()
q = host.raw_ssh('python3 -',input=code.encode(),timeout=15,check=False)
if q.returncode:
    report = dict(run=run,ssh_command_executed=False,ssh_exit_code=q.returncode,
        observation_seconds=round(time.monotonic()-start,2),
        state_not_observed=True,worker_terminal_status_unknown=True,
        error=q.stderr.decode(errors='replace'))
else:
    report = json.loads(q.stdout)
(host.PRIVATE/('latest-'+run+'-observation-private.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['boot_id','kernel_log','pstore','worker_log','state']},indent=2))
