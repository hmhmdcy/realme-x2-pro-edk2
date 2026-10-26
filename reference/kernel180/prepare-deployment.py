from pathlib import Path
import ast
import json
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel180')
old = json.loads((ref.parent / 'kernel176/build-package-validation.json').read_text())
names = ['collect-preflash.py', 'quiesce-current175.sh', 'check-quiesce.py', 'freeze-for-bootloader.sh',
         'disable-crtc.py', 'enter-bootloader.ps1', 'enable-transition-eud.ps1', 'flash-reset.ps1']
written = []
for name in names:
    s = (ref.parent / 'kernel176' / name).read_text()
    s = s.replace('kernel176', 'kernel180').replace('k176', 'k180').replace('K176', 'K180').replace('stage=176', 'stage=180')
    s = s.replace("startswith('#175 ')", "startswith('#176 ')").replace("'^#175 '", "'^#176 '")
    s = s.replace('CURRENT175', 'CURRENT176').replace('current_kernel=175', 'current_kernel=176').replace('target_kernel=176', 'target_kernel=180')
    if name == 'collect-preflash.py':
        s = s.replace("assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==Path('/var/lib/samurai/k175-final/boot-id-private.txt').read_text().strip()",
                      '# Capture a fresh current boot; all subsequent operations compare this exact identity.')
        s = s.replace("assert prior.count('Failed to bring up WCD934X: err = -110')==1", '# Known audio failures are recorded, not reset or treated as a new healthy boot.')
        s = s.replace('cbeedef03586aae616f8c7ec9423f5667904682fa128c184b5c0b7620392acb2', old['logdump_sha256'])
        s = s.replace("capture(['dmesg'],'dmesg-private.txt')", "(out / 'start-uptime-private.txt').write_text(Path('/proc/uptime').read_text())\ncapture(['dmesg'],'dmesg-private.txt')")
    if name == 'check-quiesce.py':
        s = s.replace("assert current.count('Failed to bring up WCD934X: err = -110')==prior.count('Failed to bring up WCD934X: err = -110')==1",
                      '# Preserve old kernel176 audio faults; quiesce proof uses actual offline/resource state.')
        s = s.replace('import os\n', 'import os\nimport re\n')
        marker = 'report=dict(stage=180,boot_id=boot,quiesce_audit_pass=True,'
        audit = '''cutoff=float((before/'start-uptime-private.txt').read_text().split()[0])
patterns={'irq_read':'Failed to read IRQ status', 'irq_config':'Failed to write config',
          'irq_mask':'Failed to sync masks', 'pdr_timeout':'register listener txn wait failed', 'asoc':'ASoC error'}
window='\n'.join(line for line in current.splitlines() if (m:=re.match(r'^\\[\\s*(\\d+\\.\\d+)\\]',line)) and float(m[1])>=cutoff)
(out/'quiesce-audio-faults-private.json').write_text(json.dumps({'cutoff':cutoff,'faults':{key:window.count(value) for key,value in patterns.items()}},indent=2)+'\n')
'''
        # This is source text: keep escaped newlines inside its string literals.
        audit = audit.replace("window='\n'.join", "window='\\n'.join").replace("indent=2)+'\n')", "indent=2)+'\\n')")
        assert marker in s
        s = s.replace(marker, audit + marker)
    if name == 'flash-reset.ps1':
        s = s.replace('$build.reset_address_refresh_and_managed_probe_cleanup_included', '$build.pdr_transaction_peer_and_lifetime_fix_included')
        s = s.replace('$build.kernel_build -ne 176', '$build.kernel_build -ne 180').replace('kernel_build=176', 'kernel_build=180')
        s = s.replace('logdump-k180-reset.img', 'logdump-k180-pdr-irq.img')
    dest = name.replace('quiesce-current175', 'quiesce-current176').replace('flash-reset', 'flash-pdr-irq')
    if dest.endswith('.py'):
        ast.parse(s)
    (ref / dest).write_text(s)
    written.append(dest)
with tarfile.open(out / 'deployment-tools-private.tar', 'w') as archive:
    for name in written:
        if name.endswith('.ps1'):
            continue
        archive.add(ref / name, arcname='k180-' + name)
print('K180_DEPLOYMENT_TOOLS_PREPARED')
