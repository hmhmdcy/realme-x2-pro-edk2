"""Check the saved patch against preserved 302 sources and compare every changed byte."""
from pathlib import Path
import json, subprocess, tarfile, tempfile
import host
HERE = Path(__file__).resolve().parent
build = json.loads((HERE/'build-validation.json').read_text())
tree = Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
with tempfile.TemporaryDirectory(prefix='camss303-replay-') as temporary:
    root = Path(temporary)
    with tarfile.open(host.PRIVATE/'tested302-source-private.tar.gz','r:gz') as tar:
        for item in tar.getmembers():
            assert not item.name.startswith('/') and '..' not in Path(item.name).parts
        tar.extractall(root,filter='data')
    q = subprocess.run(['git','-C',str(root),'apply','--check',str(HERE/'libcamera-hardware-ae.patch')],capture_output=True)
    assert q.returncode == 0, q.stderr.decode()
    subprocess.run(['git','-C',str(root),'apply',str(HERE/'libcamera-hardware-ae.patch')],check=True)
    for name in build['source_sha256']:
        assert (root/name).read_bytes() == (tree/name).read_bytes(), name
report = dict(stage=303, passed=True, preserved302_baseline_replay=True, changed_source_files_compared=len(build['source_sha256']),
              hardware_verified=False)
(HERE/'patch-replay-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
