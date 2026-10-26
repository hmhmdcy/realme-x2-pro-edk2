"""Preserve frozen R1 bytes before the authorized stdin binding delta."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    original=(HERE/'delivery.json').read_bytes()
    assert sha(original)=='18fc4976d54ec199a141162aecaa801e51ac78402741e27982997be9bf04eaa5'
    delivery=json.loads(original)
    for name,item in delivery['files'].items():assert sha((HERE/name).read_bytes())==item['sha256']
    history=HERE/'history/revision-1';history.mkdir(parents=True,exist_ok=False)
    for source,dest in [('delivery.json','delivery.json'),('host.py','host.py'),('README.md','README-original.md.inc')]:
        with (history/dest).open('xb') as file:file.write((HERE/source).read_bytes())
    print(json.dumps(dict(passed=True,R1_delivery_sha256=sha(original),original_bytes_preserved=True)))


if __name__=='__main__':main()
