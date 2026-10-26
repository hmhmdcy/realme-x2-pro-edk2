import json,shlex
import host
code=r'''from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai/k393-deployment-r1');meta=json.loads((root/'manifest.json').read_text());dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(modules={n:Path('/sys/module',n).exists() for n in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']},static_device_exists=dev.exists(),driver_bound=(dev/'driver').exists(),old_files_match=all(hashlib.sha256(Path(r['target']).read_bytes()).hexdigest()==r['old_sha256'] for r in meta['modules']),worker_terminal=json.loads((root/'state.json').read_text())['terminal'],services={n:[int(p.name) for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()==n] for n in ['pipewire','wireplumber']})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(host.PRIVATE/'transition-inspection-private.json').write_bytes(q.stdout);print(q.stdout.decode())
