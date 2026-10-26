from pathlib import Path
import ast
import json
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
failure = json.loads((ref / 'failed-runtime-validation.json').read_text())
assert failure['candidate_rejected'] and failure['taint'] == 512
def save(name, t):
    assert not (ref / name).exists()
    if name.endswith('.py'):
        ast.parse(t)
    (ref / name).write_text(t)
t = (ref / 'quiesce-current134.sh').read_text()
t = t.replace('before=/var/lib/samurai/k135-preflash', 'before=/var/lib/samurai/k135-first-runtime').replace('k135-quiesce', 'k135-rollback-quiesce')
t = t.replace('/dev/dri/card0', '/dev/dri/card1').replace('/dri/0/', '/dri/1/').replace(')" = 0\n', ')" = 0\n')
t = t.replace('test "$(cat /proc/sys/kernel/tainted)" = 0', 'test "$(cat /proc/sys/kernel/tainted)" = 512')
t = t.replace('$before/old134-module-tree.sha256', '/var/lib/samurai/k134-preflash/new-module-tree.sha256')
t = t.replace('K135_CURRENT134_PREFLASH_QUIESCE_COMPLETE', 'K135_FAILED_VARIANT_QUIESCE_FOR_STABLE132_COMPLETE')
save('quiesce-failed-variant.sh', t)
t = (ref / 'verify-quiesce.py').read_text()
t = t.replace("out/'quiesce-private.tar'", "out/'rollback-quiesce-private.tar'").replace("out/'source-boot-id-private.txt'", "out/'failed-boot-id-private.txt'")
t = t.replace("data['state.txt'].splitlines()[-1]==b'0'", "data['state.txt'].splitlines()[-1]==b'512'")
t = t.replace('current_kernel=134,target_kernel=134,dt_variant=135', 'current_kernel=134,target_kernel=132,failed_dt_variant=135').replace('drm_minor=0', 'drm_minor=1').replace('taint=0,', 'taint=512,')
t = t.replace('quiesce-validation.json', 'rollback-quiesce-validation.json').replace('K135_CURRENT134_FULL_QUIESCE_ARCHIVE_GUARD_PASS', 'K135_FAILED_VARIANT_QUIESCE_FOR_ROLLBACK_PASS')
save('verify-rollback-quiesce.py', t)
t = (ref / 'freeze-for-bootloader.sh').read_text().replace('before=/var/lib/samurai/k135-preflash', 'before=/var/lib/samurai/k135-first-runtime').replace('k135-quiesce', 'k135-rollback-quiesce')
t = t.replace('test "$(cat /proc/sys/kernel/tainted)" = 0', 'test "$(cat /proc/sys/kernel/tainted)" = 512').replace('/dev/dri/card0', '/dev/dri/card1').replace('/dri/0/', '/dri/1/').replace('$before/old134-module-tree.sha256', '/var/lib/samurai/k134-preflash/new-module-tree.sha256')
save('freeze-for-rollback.sh', t)
t = (ref / 'enter-bootloader.ps1').read_text().replace("$Prefix='mdss-reset-first'", "$Prefix='rollback132-first'").replace('source-boot-id-private.txt', 'failed-boot-id-private.txt').replace('quiesce-validation.json', 'rollback-quiesce-validation.json').replace('/tmp/k135-freeze-for-bootloader.sh', '/tmp/k135-freeze-for-rollback.sh')
save('enter-rollback-bootloader.ps1', t)
t = (ref / 'collect-runtime.sh').read_text().replace('dest=/var/lib/samurai/k135-first-runtime', 'dest=/var/lib/samurai/k135-rollback132-runtime')
t = t.replace("'^#134 '", "'^#132 '").replace('/var/lib/samurai/k135-preflash/boot-id-private.txt', '/var/lib/samurai/k135-first-runtime/boot-id-private.txt').replace('-k134+', '-k132+').replace('/var/lib/samurai/k134-preflash/new-module-tree.sha256', '/var/lib/samurai/k132-preflash/new-module-tree.sha256')
t = t.replace('/tmp/k135-first-runtime-private.tar.gz', '/tmp/k135-rollback132-runtime-private.tar.gz').replace('K135_FIRST_AUTOMATIC_NATIVE_RUNTIME_CAPTURED', 'K135_STABLE132_ROLLBACK_NATIVE_RUNTIME_CAPTURED')
save('collect-rollback-runtime.sh', t)
t = (ref / 'poll-new-boot.ps1').read_text().replace('postflash-ssh-', 'rollback-ssh-').replace("'^#134 '", "'^#132 '").replace('kernel_build=134', 'kernel_build=132').replace('ssh-recovery-validation.json', 'rollback-ssh-recovery-validation.json')
save('poll-rollback-boot.ps1', t)
print('K135_FAILED_VARIANT_IDENTITY_AND_TAINT512_GUARDED_ROLLBACK_TOOLS_READY', flush=True)
