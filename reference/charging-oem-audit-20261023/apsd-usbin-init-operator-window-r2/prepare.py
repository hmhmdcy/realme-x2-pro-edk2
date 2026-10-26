"""R2 changes only UI_WAIT_MS; frozen R1 source/delivery remain untouched."""
from pathlib import Path
import difflib,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-usbin-init-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
delivery=json.loads((OLD/'delivery.json').read_text())
for n in ['samurai-usbin-init.c','usbin-init-core.h','prepare-tests.py','test-init.c','tested-functions.inc','tested-struct.inc','function-manifest.json','protocol.json','build-private.py']:
 assert sha(OLD/n)==delivery['files'][n],n
for n in ['samurai-usbin-init.c','prepare-tests.py','tested-functions.inc','tested-struct.inc','function-manifest.json']:
 shutil.copy2(OLD/n,HERE/n)
old=(OLD/'usbin-init-core.h').read_text();assert old.count('#define UI_WAIT_MS 60000ULL')==1
new=old.replace('#define UI_WAIT_MS 60000ULL','#define UI_WAIT_MS 300000ULL')
(HERE/'usbin-init-core.h').write_bytes((OLD/'usbin-init-core.h').read_bytes().replace(b'#define UI_WAIT_MS 60000ULL',b'#define UI_WAIT_MS 300000ULL'))
(HERE/'operator-window.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/usbin-init-core.h',tofile='b/usbin-init-core.h')))
protocol=json.loads((OLD/'protocol.json').read_text());assert protocol['times']['window_ms']==60000
protocol['times']['window_ms']=300000
(HERE/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
assert sha(HERE/'samurai-usbin-init.c')==delivery['files']['samurai-usbin-init.c']
prefix=(OLD/'test-init.c').read_text().split('static void stable(void)')[0]
(HERE/'test-boundary-prefix.inc').write_text(prefix)
build=(OLD/'build-private.py').read_text()
build=build.replace("REF/'kernel461/storage.py'","REF/'kernel284/storage.py'")
build=build.replace("shared=storage.mount.mounted_build();original=(shared/'source').resolve()","shared=storage.mounted_build();original=shared.parent/'source354'")
build=build.replace("/apsd-usbin-init-candidate')","/apsd-usbin-init-operator-window-r2')")
assert "private=Path('/home/cy122/charging-management-20261023/apsd-usbin-init-operator-window-r2')" in build
(HERE/'build-private.py').write_text(build)
r=dict(passed=True,old_delivery_sha256=sha(OLD/'delivery.json'),old_test_receipt_sha256=sha(OLD/'test-result.json'),
 old_source_sha256=delivery['files']['samurai-usbin-init.c'],new_source_sha256=sha(HERE/'samurai-usbin-init.c'),
 old_core_sha256=delivery['files']['usbin-init-core.h'],new_core_sha256=sha(HERE/'usbin-init-core.h'),
 old_protocol_sha256=delivery['files']['protocol.json'],new_protocol_sha256=sha(HERE/'protocol.json'),
 only_production_change='UI_WAIT_MS 60000ULL -> 300000ULL',old_12_groups_reused_not_rerun=True,
 physical_test=False,phone_accessed=False,sdk_invoked=False,Git_invoked=False)
(HERE/'source-result.json').write_text(json.dumps(r,indent=2)+'\n');print('R2 exact one-constant candidate prepared')
