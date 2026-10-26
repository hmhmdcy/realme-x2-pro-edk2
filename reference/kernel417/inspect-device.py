"""Read fresh device state before considering any temporary candidate load."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''from pathlib import Path
import hashlib,json
d=Path('/sys/bus/platform/devices/ac10000.icp')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=dict(same_boot_as394=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes(),
 driver=(d/'driver').resolve().name,m2m=json.loads((d/'m2m_status').read_text()),core=json.loads((d/'state').read_text()),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 notes={n:sha('/sys/module/'+n+'/notes/.note.gnu.build-id') for n in ['qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_m2m']},
 prior406={p.parent.name:json.loads(p.read_text()) for p in [Path('/var/lib/samurai/k406-ltm-r1/state.json'),Path('/var/lib/samurai/k406-ltm-r2/state.json')]})
print(json.dumps(r))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'initial-device-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps(dict(same_boot=d['same_boot_as394'],driver=d['driver'],taint=d['taint'],m2m=d['m2m'],core_released=not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes']),prior406={k:dict(terminal=v.get('terminal'),passed=v.get('passed'),restored=v.get('normal395_restored')) for k,v in d['prior406'].items()}),indent=2))
