from pathlib import Path
import json,host
ref=Path(__file__).resolve().parent;build=json.loads((ref/'front-helper-build-validation.json').read_text());test=json.loads((ref/'front-sequence-host-validation.json').read_text());assert test['source_sha256']==build['helper_source_sha256'] and test['asan_ubsan_passed']
for path in [host.PRIVATE/'samurai-front-identify-k193-private.ko',ref/'front-helper-build-validation.json',ref/'samurai-front-identify.c']:
 host.upload(path,'/var/lib/samurai/k193-tools/'+path.name)
print('Atomic front ID helper staged privately; not loaded')
