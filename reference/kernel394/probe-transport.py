from pathlib import Path
import json,shlex
import host
code=r'''from pathlib import Path
import json
assert b'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
guard=Path('/var/lib/samurai/k390-active/boot-id-private.txt');same=guard.exists() and guard.read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
state=Path('/var/lib/samurai/k394-ack-loss-r1/state.json');root=state.parent
print(json.dumps(dict(model_verified=True,same390_boot=same,release=Path('/proc/sys/kernel/osrelease').read_text().strip(),uptime=float(Path('/proc/uptime').read_text().split()[0]),normal_icp_driver=Path('/sys/bus/platform/devices/ac10000.icp/driver').resolve().name,test_parameter_present=Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists(),worker_state=json.loads(state.read_text()) if state.exists() else None,experiment_root_exists=root.exists(),experiment_files=[p.name for p in root.iterdir()] if root.exists() else [],prior393_root_exists=Path('/var/lib/samurai/k393-deployment-r4').exists(),pstore_files=[p.name for p in Path('/sys/fs/pstore').iterdir()])))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25);(host.PRIVATE/'transport-probe-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps({k:v for k,v in d.items() if k!='worker_state'},indent=2));s=d['worker_state'] or {};print(json.dumps(dict(worker_phase=s.get('phase'),worker_terminal=s.get('terminal'),worker_pid=s.get('pid'))))
