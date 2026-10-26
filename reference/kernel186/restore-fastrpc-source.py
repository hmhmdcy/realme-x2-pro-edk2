"""Keep the failed prototype separately and restore the maintained source baseline."""
from pathlib import Path
import hashlib
import json
import shutil

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
private=Path('/mnt/e/edk2-samurai-out/kernel186')
path=k/'drivers/misc/fastrpc.c'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='ba187458dcaa5bb7011a3b5286ac6c0bef690be731e8d175c160c8ffb5836840'
before=(private/'fastrpc-before-private.c').read_bytes()
assert hashlib.sha256(before).hexdigest()=='a15e99ea6c420fd5d42ac91d3990fca1cba9762d1a51eacd80ad05383bed7a41'
(private/'fastrpc-failed-prototype-private.c').write_bytes(path.read_bytes())
path.write_bytes(before)
shutil.copyfile(private/'fastrpc-before-build-private.ko',k/'drivers/misc/fastrpc.ko')
report=dict(stage=186,maintained_fastrpc_source_restored=True,
    failed_patch_source_and_module_kept=True,maintained_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    default_phone_module_file_restored_separately=True,failed_prototype_accepted=False)
(Path(__file__).resolve().parent/'source-restore-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
