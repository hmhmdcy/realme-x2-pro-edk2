"""Adapt the already validated 367 normal-restart sequence for this incident.

No generated action is executed here. Only the known taint-W incident may be
accepted; ordinary baseline services are quiesced before the same EUD restart.
"""
from pathlib import Path
import hashlib
import json

ref = Path(__file__).resolve().parent
reused = ref.parent / 'kernel367'
old_guard = "Path('/var/lib/samurai/k366-recovered/boot-id-private.txt').read_bytes()"
new_guard = "(json.loads(Path('/root/charging-management-20261023/original-private.json').read_text())['boot_id'] + '\\n').encode()"
receipt = {}
for original, output in [('native-quiesce.py','recovery-quiesce.py'),
                         ('restart-bootloader.py','recovery-restart.py')]:
    text = (reused / original).read_text()
    assert old_guard in text
    text = text.replace(old_guard, new_guard)
    text = text.replace('k367-quiesce', 'charging-20261023-recovery')
    text = text.replace('k367-reboot-phase-private', 'charging-20261023-reboot-phase-private')
    text = text.replace("Path('/proc/sys/kernel/tainted').read_text().strip()=='0'",
                        "Path('/proc/sys/kernel/tainted').read_text().strip()=='512'")
    text = text.replace("proof['taint']==0", "proof['taint']==512")
    text = text.replace('taint=0,', 'taint=512,')
    # The original bulk module deployment receipt predates current camera
    # modules. The separate current baseline inspection verifies those notes.
    line = " assert json.loads((r/'k363-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']\n"
    text = text.replace(line, '')
    text = text.replace(line.lstrip(), '')
    text = '# Recovery only; source sequence: reference/kernel367/' + original + '\n' + text
    compile(text, output, 'exec')
    (ref / output).write_text(text)
    receipt[output] = {'reused_source': str(reused / original),
        'source_sha256': hashlib.sha256((reused / original).read_bytes()).hexdigest(),
        'generated_sha256': hashlib.sha256(text.encode()).hexdigest()}
text = (ref/'recovery-quiesce.py').read_text()
start = text.index('state=dict(')
end = text.index('save();before=')
definitions = text[start:end]
resume = '''from pathlib import Path
import ctypes,dbus,json,os,signal,subprocess,time,traceback
o=Path('/var/lib/samurai/charging-20261023-recovery')
previous=json.loads((o/'state-private.json').read_text())
assert previous['terminal'] and previous['exit_code']==1
failure=(o/'failure-private.txt').read_text()
assert "num_users" in failure and "512" in failure
assert not (o/'initial-failure-private.txt').exists()
(o/'failure-private.txt').rename(o/'initial-failure-private.txt')
r=Path('/var/lib/samurai');os.umask(0o077)
'''+definitions+'''save();before=subprocess.check_output(['dmesg'])
try:
'''+text[text.index(" for p in Path('/sys/class/regulator')"):]
compile(resume,'recovery-quiesce-resume.py','exec')
(ref/'recovery-quiesce-resume.py').write_text(resume)
(ref / 'recovery-source.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'recovery_scripts_prepared': True, 'executed': False}))
