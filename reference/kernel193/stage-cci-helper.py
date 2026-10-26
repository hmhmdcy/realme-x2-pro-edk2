from pathlib import Path
import json,host
ref=Path(__file__).resolve().parent;out=host.PRIVATE
build=json.loads((ref/'cci-helper-build-validation.json').read_text());test=json.loads((ref/'cci-helper-host-validation.json').read_text());assert test['asan_ubsan_passed'] and test['source_sha256']==build['helper_source_sha256']
host.ssh("python3 -",input=b"from pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k193-baseline/boot-id-private.txt').read_bytes()\nPath('/var/lib/samurai/k193-tools').mkdir(mode=0o700)\n")
for path in [out/'samurai-cci-bringup-k193-private.ko',ref/'cci-helper-build-validation.json',ref/'samurai-cci-bringup.c']:
 host.upload(path,'/var/lib/samurai/k193-tools/'+path.name)
print('CCI helper staged privately; not loaded')
