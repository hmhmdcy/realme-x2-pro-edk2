"""Record the first review, then refine only candidate style/barrier comments."""
import importlib.util
import json
from pathlib import Path

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare227', ref / 'prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
source = p.BUILD / 'candidate/fastrpc.c'
assert p.digest(source.read_bytes()) == 'a1d61124ea538ef2d1d63b899e287e044fd5d37a62b20462cc7d0ee202027d3b'
assert p.snapshot() == json.loads((p.PRIVATE / 'kernel-before-private.json').read_text())
(p.PRIVATE / 'fastrpc-review-r1-private.c').write_bytes(source.read_bytes())
(p.PRIVATE / 'fastrpc-review-r1-private.patch').write_bytes((ref / 'fastrpc-publication-lifetime.patch').read_bytes())
base = (p.PRIVATE / 'fastrpc-before-private.c').read_text()
new = p.candidate(base)
source.write_text(new)
patch = p.make_patch(base, new)
(ref / 'fastrpc-publication-lifetime.patch').write_text(patch)
report = json.loads((ref / 'fastrpc-source-validation.json').read_text())
report.update(candidate_source_sha256=p.digest(new.encode()), patch_sha256=p.digest(patch.encode()),
              first_checkpatch_failed_and_retained=True, refinement='style and explicit barrier comments')
(ref / 'fastrpc-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
