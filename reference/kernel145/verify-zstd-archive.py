from pathlib import Path
import hashlib
import json
import subprocess
import sys

archive = Path(sys.argv[1])
expected = sys.argv[2]
size = int(sys.argv[3])
assert archive.resolve().is_relative_to(Path('/mnt/e/edk2-samurai-out/cleanup145/volumes'))
digest = hashlib.sha256()
total = 0
with subprocess.Popen(['zstd', '-q', '-d', '-c', str(archive)], stdout=subprocess.PIPE) as child:
    while block := child.stdout.read(4 * 1024 * 1024):
        digest.update(block)
        total += len(block)
    assert child.wait() == 0
assert total == size and digest.hexdigest() == expected
print(json.dumps(dict(decompressed_bytes=total, sha256=digest.hexdigest(), verified=True)))
