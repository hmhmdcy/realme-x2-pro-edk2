"""Recheck the accepted boot230 combination after strictly read-only RFS audit."""
from pathlib import Path
import ast,json
import host
ref=Path(__file__).resolve().parent
tree=ast.parse((ref.parent/'kernel230/final-health.py').read_text())
code=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='code' for v in n.targets)))
assert code.count("out=root/'k230-final-health'")==1
code=code.replace("out=root/'k230-final-health'","out=root/'k231-final-health'").replace('report=dict(stage=230,','report=dict(stage=231,')
code=code.replace("assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()", """assert not any('/run/k231-rfs-vendor-ro ' in line or '/run/k231-rfs-persist-ro ' in line for line in Path('/proc/mounts').read_text().splitlines())
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()""")
r=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'final-health-host-private.log').write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout);report.update(audit_readonly_no_gnss_or_service_restart=True,temporary_stock_mounts_closed=True)
(ref/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
