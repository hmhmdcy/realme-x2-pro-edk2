"""Hash the reviewed leaf only; no tests, compiler, devices or source mutation."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_bytes())
b=json.loads((HERE/'build-result.json').read_bytes())
s=json.loads((HERE/'review-result.json').read_bytes())
r=json.loads((HERE/'test-artifact-relocation.json').read_bytes())
assert t['passed'] and b['passed'] and r['public_generated_ELF_absent']
assert t['source_sha256']==b['source_sha256']==s['source_sha256']==sha(HERE/'samurai-usb-input.c')
assert not (HERE/'test-events').exists()
names=['README.md','prepare.py','samurai-usb-input.c','samurai-usb-input-decode.h',
       'baseline-samurai-usb-input.c','board-irq.fragment.dts','usb-events.patch','irq-events.inc',
       'source-result.json','test-events.c','actual-events-and-stop.inc','run-tests.py',
       'run-tests-before-private-output.py','test-result.json','test-artifact-relocation.json',
       'relocate-test-artifact.py','build-private-object.py','build-result.json',
       'build-private-object-before-source-path.py','build-pre-source-path-result.json',
       'review-static.py','review-result.json','seal.py']
files={n:{'sha256':sha(HERE/n),'bytes':(HERE/n).stat().st_size} for n in names}
files.update({'source-reference/'+p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in (HERE/'source-reference').glob('*.c')})
delivery={'schema':'samurai-usb-input-IRQ-candidate-v1','frozen':True,'files':files,
          'actual_cases':16,'object_sha256':b['object_sha256'],'source_sha256':b['source_sha256'],
          'not_deployed':True,'DT_not_applied':True,'latency_not_accepted':True}
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps({'delivery_sha256':sha(HERE/'delivery.json'),'source_sha256':b['source_sha256'],
                  'test_receipt_sha256':sha(HERE/'test-result.json'),'build_receipt_sha256':sha(HERE/'build-result.json')}))
