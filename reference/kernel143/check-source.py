from pathlib import Path
import hashlib
import json
import re
import subprocess

root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
meta=json.loads(ref.joinpath('source-preparation-validation.json').read_text())
assert meta['actual_functions_tested']
source=root.joinpath('drivers/tty/serial/eud.c').read_text()
assert hashlib.sha256(source.encode()).hexdigest()==meta['candidate_source_sha256']
before=out.joinpath('eud-before-private.c').read_text()
names=['eud_put','eud_send_frame','eud_console_rx_locked','eud_rx_collect_locked','eud_rx_irq','eud_rx_work',
    'eud_remove','tx_journal_read','eud_rx_run_bootloader']
unchanged=[]
def function(text,name):
    match=re.search(r'^static[^;{}]*\b'+name+r'\([^;{}]*\)\n\{',text,re.M)
    if not match:return None
    depth=1;end=match.end()
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]
for name in names:
    old=function(before,name)
    if old is not None:
        assert old==function(source,name),name
        unchanged.append(name)
check=subprocess.run(['perl',str(root/'scripts/checkpatch.pl'),'--no-signoff','--ignore','COMMIT_MESSAGE',str(ref/'eud-threaded-console.patch')],capture_output=True,text=True)
out.joinpath('checkpatch-private.txt').write_text(check.stdout+check.stderr)
print(check.stdout+check.stderr)
assert check.returncode==0
assert root.joinpath('.config').read_bytes()==out.joinpath('config-before-private').read_bytes()
diagnostic=json.loads(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel140/dma-diagnostic-source-validation.json').read_text())
assert all(hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest()==digest for name,digest in diagnostic['files'].items())
report=dict(stage=143,candidate_source_sha256=meta['candidate_source_sha256'],
    only_stage143_file_changed='drivers/tty/serial/eud.c',unchanged_critical_functions=unchanged,
    dma_diagnostics140_and_slimbus_unwind139_preserved=True,kernel_config_unchanged=True,
    checkpatch_code_errors=0,checkpatch_code_warnings=0,
    callback_api_checked_against_local_kernel=True,goal_complete=False)
ref.joinpath('source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
