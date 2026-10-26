from pathlib import Path
import ast
import json
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel183')
baseline = json.loads((ref.parent / 'kernel181/build-package-validation.json').read_text())
candidate = json.loads((ref / 'build-package-validation.json').read_text())
assert candidate['kernel_build'] == 183 and candidate['offline_stream_abort_and_transport_snapshot_included']
names = ['collect-preflash.py', 'quiesce-current180.sh', 'check-quiesce.py', 'freeze-for-bootloader.sh',
         'disable-crtc.py', 'flash-offline-irq.ps1', 'linux-restart2-bootloader.py', 'collect-runtime.py']
written = []
for name in names:
    s = (ref.parent / 'kernel181' / name).read_text()
    s = s.replace('kernel181', 'kernel183').replace('k181', 'k183').replace('K181', 'K183')
    s = s.replace('stage=181', 'stage=183').replace("'stage': 181", "'stage': 183").replace('stage=181;', 'stage=183;')
    s = s.replace('CURRENT176', 'CURRENT181').replace('old kernel176 audio faults', 'old kernel181 audio faults')
    if name == 'collect-runtime.py':
        s = s.replace("startswith('#181 ')", "startswith('#183 ')").replace('kernel_build=181', 'kernel_build=183')
        s = s.replace(baseline['logdump_sha256'], candidate['logdump_sha256'])
    elif name == 'flash-offline-irq.ps1':
        s = s.replace('$build.kernel_build -ne 181', '$build.kernel_build -ne 183').replace('kernel_build=181', 'kernel_build=183')
        s = s.replace('logdump-k183-offline-irq.img', 'logdump-k183-offline-stream.img')
        s = s.replace('if (!$build.offline_main_irq_cache_cleanup_included',
                      'if (!$build.offline_stream_abort_and_transport_snapshot_included -or !$build.offline_main_irq_cache_cleanup_included')
    else:
        s = s.replace("startswith('#180 ')", "startswith('#181 ')").replace("'^#180 '", "'^#181 '")
        s = s.replace('current_kernel=180', 'current_kernel=181').replace('target_kernel=181', 'target_kernel=183')
    if name == 'collect-preflash.py':
        old = json.loads((ref.parent / 'kernel180/build-package-validation.json').read_text())
        s = s.replace(old['logdump_sha256'], baseline['logdump_sha256'])
    dest = name.replace('quiesce-current180', 'quiesce-current181').replace('flash-offline-irq', 'flash-offline-stream')
    if dest.endswith('.py'):
        ast.parse(s)
    assert not (ref / dest).exists(), dest
    (ref / dest).write_text(s)
    written.append(dest)
with tarfile.open(out / 'deployment-tools-private.tar', 'w') as t:
    for name in written:
        if not name.endswith('.ps1'):
            t.add(ref / name, arcname='k183-' + name)
print('K183_FRESH181_DEPLOYMENT_TOOLS_PREPARED')
