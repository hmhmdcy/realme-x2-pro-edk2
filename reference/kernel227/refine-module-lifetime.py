"""Add the live-FD module pin and reverse module-exit dependency ordering."""
import importlib.util
import json
from pathlib import Path

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare227', ref / 'prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
source = p.BUILD / 'candidate/fastrpc.c'
assert p.digest(source.read_bytes()) == '1ce32e364f66608f84459e12e617e450246d9f75caa2a51757350f166163ee3e'
(p.PRIVATE / 'fastrpc-review-r2-private.c').write_bytes(source.read_bytes())
for name in ['fastrpc-source-validation.json', 'fastrpc-build-validation.json', 'fastrpc-host-validation.json',
             'fastrpc-publication-lifetime.patch']:
    (p.PRIVATE / ('pre-owner-' + name)).write_bytes((ref / name).read_bytes())
base = (p.PRIVATE / 'fastrpc-before-private.c').read_text()
new = p.candidate(base)
source.write_text(new)
patch = p.make_patch(base, new)
(ref / 'fastrpc-publication-lifetime.patch').write_text(patch)
report = json.loads((ref / 'fastrpc-source-validation.json').read_text())
report.update(candidate_source_sha256=p.digest(new.encode()), patch_sha256=p.digest(patch.encode()),
              revision='r3-module-owner', module_open_pins_driver=True,
              module_exit_reverse_init_order=True,
              live_device_before=dict(fastrpc_open_fds=1, module_refcount=0))
(ref / 'fastrpc-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
