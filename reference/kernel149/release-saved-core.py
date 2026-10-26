"""Release only a current coredump whose complete saved bytes match."""
from pathlib import Path
import argparse, hashlib, json
p=argparse.ArgumentParser(); p.add_argument('label'); a=p.parse_args()
assert a.label.replace('-', '').isalnum()
out=Path('/var/lib/samurai')/('k149-'+a.label)
assert (out/'boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
released=0
for dev in Path('/sys/class/devcoredump').glob('devcd*'):
    saved=out/(dev.name+'-private.data')
    assert saved.is_file() and saved.stat().st_size>1000
    assert hashlib.sha256(saved.read_bytes()).digest()==hashlib.sha256((dev/'data').read_bytes()).digest()
    (dev/'data').write_text('1')
    released+=1
print(json.dumps(dict(released_saved_cores=released,full_content_verified=True)))
