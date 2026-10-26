"""Pin frozen software and an existing archive only; never bind runtime facts."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    paths={'rollback_delivery':HERE.parent/'usb-irq-protection-rollback-candidate/delivery.json',
        'worker':HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py',
        'saved_proof':HERE.parent/'usb-irq-protection-rollback-candidate/saved-proof.py',
        'auth_delivery':HERE.parent/'irq-cohort-postboot-host-candidate/delivery.json',
        'auth_host':HERE.parent/'irq-cohort-postboot-host-candidate/host.py',
        'payload':Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01/rollback-r8-payload.tar.gz')}
    pins={name:dict(path=str(path.resolve()),sha256=sha(path.read_bytes()),bytes=path.stat().st_size) for name,path in paths.items()}
    with (HERE/'source-pins.json').open('x') as file:file.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(passed=True,software_and_existing_archive_only=True,runtime_request_generated=False)))


if __name__=='__main__':main()
