"""Validate the already downloaded archive after the local stats parser correction."""
from pathlib import Path
import hashlib,json
import host

host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
ref=Path(__file__).resolve().parent;folder=host.PRIVATE/'final-evidence-private'
archive=host.PRIVATE/'final-evidence-private.tar.gz'
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
p=host.ssh('sha256sum /tmp/k189-final-evidence-private.tar.gz')
assert p.stdout.decode().split()[0]==digest
report=json.loads((ref/'final-validation.json').read_text())
data=(ref/'final-and-export.py').read_text();tail=data[data.index('three=[]'):]
exec(compile(tail,str(ref/'final-and-export.py'),'exec'))
