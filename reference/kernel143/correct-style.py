from pathlib import Path
import difflib
import hashlib
import json

root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
meta=json.loads(ref.joinpath('source-preparation-validation.json').read_text())
source=root/'drivers/tty/serial/eud.c'
old=source.read_text()
assert hashlib.sha256(old.encode()).hexdigest()==meta['candidate_source_sha256']
text=old.replace('        struct mutex tx_mutex;','\tstruct mutex tx_mutex;')
for line in ['mutex_lock(&up->tx_mutex);','mutex_unlock(&up->tx_mutex);','mutex_init(&up->tx_mutex);']:
    text=text.replace('        '+line,'\t'+line)
assert ''.join(old.split())==''.join(text.split()) and text!=old
source.write_text(text)
before=out.joinpath('eud-before-private.c').read_text()
ref.joinpath('eud-threaded-console.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),
    fromfile='a/drivers/tty/serial/eud.c',tofile='b/drivers/tty/serial/eud.c')))
out.joinpath('eud-candidate-private.c').write_text(text)
meta['candidate_source_sha256']=hashlib.sha256(text.encode()).hexdigest()
meta['actual_functions_tested']=False
ref.joinpath('source-preparation-validation.json').write_text(json.dumps(meta,indent=2)+'\n')
tested=ref/'actual-function-test-validation.json'
out.joinpath('pre-style-function-test-validation-private.json').write_bytes(tested.read_bytes())
tested.unlink()
print('K143_ONLY_NEW_MUTEX_LINES_INDENTATION_CORRECTED_TOKENS_IDENTICAL')
