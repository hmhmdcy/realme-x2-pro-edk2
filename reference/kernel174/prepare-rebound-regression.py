from pathlib import Path
import ast, tarfile

ref=Path(__file__).parent
out=Path('/mnt/e/edk2-samurai-out/kernel174')
s=(ref/'collect-runtime.py').read_text().replace('k174-runtime','k174-runtime-v2')
s=s.replace('assert mbhc_started == jack_bound == 1','assert mbhc_started == jack_bound == 2')
s=s.replace('report = dict(stage=174,','report = dict(stage=174, initial_boot_card_registration_failed=True, machine_rebind_used_for_this_regression=True, permanent_card_rebind_fix_pending=True,')
(ref/'collect-rebound-runtime.py').write_text(s)
for name in ['test-capture-stop.py','capture-acoustic.py','test-desktop-duplex.py']:
    s=(ref/name).read_text().replace('k174-runtime/boot-id-private.txt','k174-runtime-v2/boot-id-private.txt')
    if name=='test-capture-stop.py':s=s.replace('k174-stop','k174-stop-v2')
    ast.parse(s);(ref/name).write_text(s)
with tarfile.open(out/'regression-rebound-tools-private.tar','w') as ar:
    for name in ['collect-rebound-runtime.py','capture-acoustic.py','test-desktop-duplex.py','test-capture-stop.py']:
        ar.add(ref/name,arcname='k174-'+name)
print('K174_REBOUND_REGRESSION_PREPARED',flush=True)
