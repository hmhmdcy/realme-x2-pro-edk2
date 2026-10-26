"""Seal already-tested offline files; no transport, build, or device access."""
from pathlib import Path
import json
import common

HERE=Path(__file__).resolve().parent
tested=json.loads((HERE/'test-result.json').read_text())
assert tested['passed']
for name,digest in tested['files'].items():assert common.sha((HERE/name).read_bytes())==digest,name
review=HERE.parents[1]/'charging-session-20261023/usbin-init-host-independent-review/absent-expiry-result.json'
reviewed=json.loads(review.read_text());assert reviewed['passed']
files=dict(tested['files'])
for name in ['README.md','test-result.json','prepare-inputs.py','seal-delivery.py','actual-fixtures/state-fixtures.c','actual-fixtures/stdout.jsonl','actual-fixtures/tested-functions.inc','actual-fixtures/tested-struct.inc','actual-fixtures/usbin-init-core.h']:
    files[name]=common.sha((HERE/name).read_bytes())
receipt={'passed':True,'scope':'offline controller/observer for one physical-off USBIN initialization transaction',
    'worker_sha256':tested['worker_sha256'],'controller_sha256':files['controller.py'],'helper_module_sha256':files['samurai-usbin-init.ko'],
    'test_result_sha256':files['test-result.json'],'targeted_assertions':tested['case_count'],'files':files,
    'independent_review_path':str(review),'independent_review_sha256':common.sha(review.read_bytes()),
    'phone_accessed':False,'ssh_executed':False,'sdk_invoked':False,'deployed':False,
    'not_phone_acceptance':True,'unconditional_cleanup':False,'automatic_retry':False}
common.save(HERE/'delivery.json',receipt)
print(json.dumps({'passed':True,'delivery_sha256':common.sha((HERE/'delivery.json').read_bytes()),'worker_sha256':receipt['worker_sha256'],'controller_sha256':receipt['controller_sha256']}))
