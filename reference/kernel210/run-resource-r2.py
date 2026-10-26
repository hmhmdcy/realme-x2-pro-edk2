from pathlib import Path
import json,host
here=Path(__file__).resolve().parent
original=(here/'inspect-camera-resources.py').read_text()
(host.PRIVATE/'resource-inspection-first-attempt-source-private.py').write_text(original)
source=original.replace("root/'k210-camera-before'","root/'k210-camera-before-r2'")
source=source.replace("all('MUX UNCLAIMED' in l and 'GPIO UNCLAIMED' in l for l in selected)","all(l.endswith(': UNCLAIMED') for l in selected)")
assert source!=original
p=host.ssh('python3 -',input=source.encode(),timeout=60)
(host.PRIVATE/'resource-inspection-r2-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);report['first_inventory_pinmux_format_assertion_failed']=True
report['actual_kernel_unclaimed_format_checked']=True
(here/'camera-resources-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
