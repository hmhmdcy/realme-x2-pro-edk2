"""Offline source derivation only; never creates a runtime identity/request."""
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'usb-irq-protection-stage-host-candidate-r2'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def derived_remote(raw):
    text = raw.decode()
    changes = [
        ("r'usb-irq-protection-stage-[a-z0-9-]{8,48}'", "r'protection-capture-[a-z0-9-]{8,48}'"),
        ("'samurai-usb-irq-protection-stage-request-v1'", "'samurai-protection-capture-request-v1'"),
        ("r'image502-[a-z0-9-]{8,64}'", "r'usb-irq-protection-activate-[a-z0-9-]{8,48}'"),
        ("        need(sha(base64.b64decode(request['payload_base64'], validate=True)) == request['payload_sha256'], 'payload differs')\n", '')]
    for before, after in changes:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    return text.encode()

def main():
    original = (OLD / 'remote.py').read_bytes()
    assert sha(original) == '1dfeeb4fc8d6236750563c144e8d67603387c19b57bb1da5bbd1de594cfe8855'
    result = derived_remote(original)
    (HERE / 'remote.py').write_bytes(result)
    supervisor = (OLD / 'supervisor.py').read_bytes()
    assert sha(supervisor) == 'b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'
    (HERE / 'supervisor.py').write_bytes(supervisor)
    print(json.dumps({'offline_source_only': True, 'remote_sha256': sha(result), 'supervisor_byte_exact': True}))

if __name__ == '__main__': main()
