from pathlib import Path
import hashlib, json, tarfile

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel173')
project = ref.parent.parent
assert json.loads((ref / 'host-tests-validation.json').read_text())['all_passed']
items = {'samurai-audio-route.py':project / 'linux-port/scripts/samurai-audio-route.py',
         'Realme_X2_Pro.conf':project / 'linux-port/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf',
         'HiFi.conf':project / 'linux-port/ucm2/conf.d/Realme_X2_Pro/HiFi.conf'}
manifest = dict(stage=173,sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in items.items()})
(out / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(out / 'candidate-files-private.tar','w') as archive:
    for n,p in items.items(): archive.add(p,arcname=n)
    archive.add(out / 'manifest.json',arcname='manifest.json')
(ref / 'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('K173_CANDIDATE_ARCHIVE_PREPARED',flush=True)
