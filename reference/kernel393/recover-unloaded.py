"""Restore the unchanged old pair after r1's incorrect static-device check."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0]
prefix=prefix.replace("root=Path(sys.argv[1]);state={'stage':342,'pid':os.getpid(),'terminal':False,'phase':'preflight'}","root=Path('/var/lib/samurai/k393-deployment-r1');state={}")
prefix=prefix.replace("marker=root/'state.json'","marker=root/'recovery-state.json'")
body=r'''
meta=json.loads((root/'manifest.json').read_text());assert json.loads((root/'state.json').read_text())['terminal']
assert not (root/'recovery-state.json').exists() and not any(processes(n) for n in ['pipewire','wireplumber'])
for n in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']:assert not Path('/sys/module',n).exists()
for r in meta['modules']:assert hashlib.sha256(Path(r['target']).read_bytes()).hexdigest()==r['old_sha256']
run(['modprobe','qcom_camss'],'recover-old-platform',timeout=25)
dev=Path('/sys/bus/platform/devices/ac10000.icp');assert (dev/'driver').resolve().name=='qcom-sm8150-icp'
for r in meta['modules']:assert hashlib.sha256(Path('/sys/module',r['module'],'notes/.note.gnu.build-id').read_bytes()).hexdigest()==r['old_note_sha256']
assert not json.loads((dev/'state').read_text())['cpu_release_attempted']
items=json.loads((root/'services-private.json').read_text());started={};restart(items,'recovered',started);wait_idle()
report=dict(stage=393,old_pair_restored_without_file_changes=True,static_device_remained_unbound_after_unload=True,probe_did_not_start_firmware=True,m2m=json.loads((dev/'m2m_status').read_text()),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']},passed=True)
assert all(len(v)==1 for v in report['services'].values())
(root/'recovery-state.json').write_text(json.dumps(report)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -c '+shlex.quote(prefix+'\n'+body),timeout=40);(HERE/'r1-recovery-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
