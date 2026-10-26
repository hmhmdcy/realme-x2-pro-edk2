"""Bind only already-frozen software inputs. No context, identity or runtime request."""
from pathlib import Path
import hashlib
import json
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    paths = {
        'stage_proof_frozen': HERE / 'stage-proof-frozen.json',
        'stage_proof': HERE / 'stage-proof.py',
        'device_delivery': HERE.parent / 'irq-cohort-postboot-readonly/delivery.json',
        'operator_delivery': HERE.parent / 'usb-irq-protection-fastboot-candidate/delivery.json',
        'completion_proof': HERE.parent / 'usb-irq-protection-fastboot-candidate/completion-proof.py',
        'key_transport': REF / 'kernel184/host.py'}
    expected = {'stage_proof_frozen':'6f5a5b7e6ad2dcbb8a51115864571b44f1561eaddd4848a03f0687328fc4a3d3',
        'stage_proof':'85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093',
        'device_delivery':'b2c1d2de692b2d302450b0debbfdd50221b84790523829dc57b5c96ba271689b',
        'operator_delivery':'ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41',
        'completion_proof':'d4a7b29c3f5978c1254c4b7c40376fbf12453057d4ba8cc98cbb4ef7a952be00',
        'key_transport':'7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'}
    result = {}
    for key,path in paths.items():
        raw = path.read_bytes(); assert sha(raw) == expected[key], 'frozen input differs: ' + key
        result[key] = dict(path=str(path.resolve()),sha256=sha(raw),bytes=len(raw))
    stage = json.loads(paths['stage_proof_frozen'].read_bytes())
    assert stage['passed'] is True and stage['stage_proof_sha256'] == expected['stage_proof']
    operator = json.loads(paths['operator_delivery'].read_bytes())
    assert operator['passed'] is True and operator['frozen'] is True
    with (HERE/'host-source-pins.json').open('x') as file:
        file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,software_sources_only=True,runtime_request_generated=False)))


if __name__ == '__main__': main()
