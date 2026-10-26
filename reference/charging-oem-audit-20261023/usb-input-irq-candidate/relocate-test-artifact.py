"""Move the already tested ELF into the existing private object tree; no rerun."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
PRIVATE=Path('/home/cy122/charging-management-20261023/usb-input-irq-object-r1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=HERE/'test-events';target=PRIVATE/'tests/test-events'
assert PRIVATE.is_dir() and (PRIVATE/'samurai-usb-input.o').is_file()
assert source.is_file() and not source.is_symlink() and not target.exists()
assert source.read_bytes()[:4]==b'\x7fELF'
old_size=source.stat().st_size;digest=sha(source)
receipt=HERE/'test-result.json';old=json.loads(receipt.read_bytes())
assert old['passed'] and old['actual_function_result']['actual_function_cases']==16
assert sha(HERE/'run-tests-before-private-output.py')==old['runner_sha256']
target.parent.mkdir(exist_ok=True)
shutil.move(str(source),str(target))
assert sha(target)==digest and target.stat().st_size==old_size and not source.exists()
result={'scope':'artifact/output path only; no test or build rerun',
        'original_test_receipt_sha256':sha(receipt),'old_runner_sha256':old['runner_sha256'],
        'new_runner_sha256':sha(HERE/'run-tests.py'),'runner_delta':'generated test ELF output path moved to private/tests',
        'old_ELF_path':str(source),'new_private_ELF_path':str(target),'ELF_bytes':old_size,'ELF_sha256':digest,
        'public_generated_ELF_absent':True,'original_test_receipt_unchanged':True,'cases_rerun':False,
        'source_sha256':sha(Path(__file__))}
(HERE/'test-artifact-relocation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
