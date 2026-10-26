"""Pin only existing frozen stage materials. No future activation/runtime pins."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
PINS = {
 'stage_host_delivery': ('charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/delivery.json', 'ee53341c31c75970df3fdbe3a417fe5042aabd3096ec8717547a87de9751c956'),
 'stage_host': ('charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/host.py', '84c53252d1993fc3ffce803e5c91d7cfe98f5a75c5f08e4e6c436d6615670660'),
 'stage_remote': ('charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/remote.py', '1dfeeb4fc8d6236750563c144e8d67603387c19b57bb1da5bbd1de594cfe8855'),
 'stage_supervisor': ('charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/supervisor.py', 'b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'),
 'stage_worker_delivery': ('charging-ui-audit-20261023/usb-irq-protection-stage-candidate/delivery.json', '7fe11dd984756ef9d5f6a16f5488adf138d381fdbed26d408965cd28aec9bbb5'),
 'stage_worker': ('charging-ui-audit-20261023/usb-irq-protection-stage-candidate/stage-worker.py', '47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a'),
 'cohort_delivery': ('charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/delivery.json', '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b'),
}


def main():
    pins = {}
    for name, (relative, expected) in PINS.items():
        path = REF / relative
        raw = path.read_bytes()
        assert sha(raw) == expected
        display = str(path).replace('\\', '/')
        if display.startswith('/mnt/e/'):
            display = 'E:/' + display[len('/mnt/e/'):]
        pins[name] = dict(path=display, sha256=expected, bytes=len(raw))
    target = HERE / 'stage-source-pins.json'
    with target.open('xb') as output:
        output.write((json.dumps(pins, indent=2) + '\n').encode())
    print(json.dumps(dict(source_pins_sha256=sha(target.read_bytes()), future_activation_or_request_created=False)))


if __name__ == '__main__': main()
