"""Author-only local binding of a genuinely frozen worker; no runtime identity."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-delivery-sha256', required=True)
    args = parser.parse_args()
    assert re.fullmatch('[0-9a-f]{64}', args.worker_delivery_sha256)
    worker = REF / 'charging-ui-audit-20261023/usb-irq-protection-stage-candidate'
    delivery_raw = (worker / 'delivery.json').read_bytes()
    assert sha(delivery_raw) == args.worker_delivery_sha256
    delivery = json.loads(delivery_raw)
    assert delivery['passed'] is True and delivery['frozen'] is True
    assert delivery['files']['stage-worker.py']['sha256'] == sha((worker / 'stage-worker.py').read_bytes())
    private = Path('E:/edk2-samurai-out/charging-management-20261023') if os.name == 'nt' else Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
    cohort = REF / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
    paths = dict(adoption=REF / 'charging-oem-audit-20261023/image502-adoption-candidate/adopt.py',
        key_transport=REF / 'kernel184/host.py', cohort_delivery=cohort / 'delivery.json',
        cohort_payload_result=cohort / 'payload-result.json', cohort_protocol=cohort / 'cohort-manifest.json',
        cohort_payload=private / 'usb-irq-protection-cohort-private-01/usb-irq-protection-payload.tar.gz',
        worker=worker / 'stage-worker.py', worker_delivery=worker / 'delivery.json', worker_contract=worker / 'contract.json',
        host=HERE / 'host.py', remote=HERE / 'remote.py', supervisor=HERE / 'supervisor.py')
    pins = {}
    for name, path in paths.items():
        raw = path.read_bytes()
        display = str(path).replace('\\', '/')
        if display.startswith('/mnt/e/'):
            display = 'E:/' + display[len('/mnt/e/'):]
        pins[name] = dict(path=display, sha256=sha(raw), bytes=len(raw))
    target = HERE / 'source-pins.json'
    with target.open('xb') as output:
        output.write((json.dumps(pins, indent=2) + '\n').encode())
        output.flush(); os.fsync(output.fileno())
    print(json.dumps(dict(source_pins_sha256=sha(target.read_bytes()), actual_runtime_identity_bound=False,
                          device_accessed=False)))


if __name__ == '__main__':
    main()
