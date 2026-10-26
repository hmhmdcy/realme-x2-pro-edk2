"""Only adapt the previously passed one-object builder's target inputs."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'dwc-suspend-halt-error-candidate/build-object.py'
text=OLD.read_text()
assert hashlib.sha256(OLD.read_bytes()).hexdigest()=='54f8611643c541c9d72bc7caec059ac0067512949330f428b4ecdfb622cce0cc'
changes={
 "dwc-suspend-halt-object-01":"dwc-suspend-retry-object-01",
 "tests['summary']['cases'] == 13":"tests['summary']['cases'] == 15",
 "'gadget.c':source['inputs']['gadget.c']":"'gadget.c':'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314'",
 "'storage284_dwc_halt_object'":"'storage284_dwc_retry_object'",
}
for old,new in changes.items():
 assert text.count(old)==1,old
 text=text.replace(old,new)
ast.parse(text)
assert not (HERE/'build-object.py').exists(),'Prepared builder already exists; preserve it'
(HERE/'build-object.py').write_text(text,newline='\n')
(HERE/'build-source-reuse.json').write_text(json.dumps(dict(passed=True,
 original_builder_sha256=hashlib.sha256(OLD.read_bytes()).hexdigest(),
 candidate_builder_sha256=hashlib.sha256(text.encode()).hexdigest(),
 same_single_child_wait_lifecycle=True,only_output_and_frozen_source_adaptation=True,
 no_build_started=True),indent=2)+'\n')
print(json.dumps(dict(prepared=True,builder_sha256=hashlib.sha256(text.encode()).hexdigest())))
