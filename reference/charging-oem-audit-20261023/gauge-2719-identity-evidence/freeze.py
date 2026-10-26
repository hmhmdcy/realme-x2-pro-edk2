"""Freeze named identity evidence sources and actual local receipts only."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
report=json.loads((HERE/'test-result.json').read_bytes());assert report['passed']
assert report['parser_sha256']==sha((HERE/'identity-fingerprint.py').read_bytes())
assert report['test_sha256']==sha((HERE/'test-fingerprint.py').read_bytes())
evidence=json.loads((HERE/'result.json').read_bytes());assert evidence['passed']
for name,item in evidence['inputs'].items():assert sha(Path(item['path']).read_bytes())==item['sha256'],name
argv=[sys.executable,'-B',str(HERE/'identity-fingerprint.py')]
child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stdout,stderr=child.communicate();rc=child.wait();assert rc==0 and not stderr
assert json.loads(stdout)==dict(source_only=True,device_accessed=False,new_mac_query_authorized=False)
local=dict(passed=True,argv=argv,pid=child.pid,terminal=True,returncode=rc,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),device_accessed=False)
(HERE/'local-checks.json').write_text(json.dumps(local,indent=2)+'\n',encoding='utf-8',newline='\n')
names=['identity-fingerprint.py','test-fingerprint.py','test-result.json','audit.py','result.json','README.md','local-checks.json','freeze.py']
delivery=dict(schema='samurai-gauge-2719-identity-evidence-delivery-v1',passed=True,
    files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in names},
    runtime_or_new_MAC_query_or_build=False,production_patch_created=False,
    result='cached full fingerprint recovered; exact model and new bit compatibility remain unverified; no repeated0002 needed',
    archive_explicit_whitelist=names)
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),parser_sha256=report['parser_sha256'])))
