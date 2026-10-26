"""Pin only actual offline sources. Does not create a runtime transaction."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
files={
 'binder':HERE.parent/'usb-irq-protection-rollback-host-candidate/bind.py',
 'binder_delivery':HERE.parent/'usb-irq-protection-rollback-host-candidate/delivery.json',
 'worker':HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py',
 'worker_delivery':HERE.parent/'usb-irq-protection-rollback-candidate/delivery.json',
 'stage_delivery':HERE.parent/'usb-irq-protection-stage-host-candidate-r2/delivery.json',
 'key_transport':HERE.parents[1]/'kernel184/host.py',
 **{name:HERE/(name+'.py') for name in ('host','remote','supervisor')},
}
pins={name:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size) for name,path in files.items()}
(HERE/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,source_only=True,runtime_request_generated=False)))
