from pathlib import Path
import ast
import json
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel181')
old = json.loads((ref.parent/'kernel180/build-package-validation.json').read_text())
names = ['collect-preflash.py','quiesce-current176.sh','check-quiesce.py','freeze-for-bootloader.sh',
         'disable-crtc.py','flash-pdr-irq.ps1','linux-restart2-bootloader.py','collect-runtime.py','test-adsp-restart.py']
written=[]
for name in names:
    s=(ref.parent/'kernel180'/name).read_text()
    s=s.replace('kernel180','kernel181').replace('k180','k181').replace('K180','K181').replace('stage=180','stage=181')
    if name=='collect-runtime.py' or name=='test-adsp-restart.py':
        s=s.replace("startswith('#180 ')","startswith('#181 ')").replace('kernel_build=180','kernel_build=181')
        s=s.replace(old['logdump_sha256'],json.loads((ref/'build-package-validation.json').read_text())['logdump_sha256'])
    else:
        s=s.replace("startswith('#176 ')","startswith('#180 ')").replace("'^#176 '","'^#180 '")
        s=s.replace('current_kernel=176','current_kernel=180').replace('target_kernel=180','target_kernel=181')
    if name=='collect-preflash.py':
        s=s.replace('6e3ebbe791455ae2c06a2374106f57c1d7ea0aac358191c44d8322b8d50f16cb',old['logdump_sha256'])
    if name=='flash-pdr-irq.ps1':
        s=s.replace('$build.kernel_build -ne 180','$build.kernel_build -ne 181').replace('kernel_build=180','kernel_build=181')
        s=s.replace('logdump-k181-pdr-irq.img','logdump-k181-offline-irq.img')
        s=s.replace('if (!$build.pdr_transaction_peer_and_lifetime_fix_included', 'if (!$build.offline_main_irq_cache_cleanup_included -or !$build.pdr_transaction_peer_and_lifetime_fix_included')
    if name=='linux-restart2-bootloader.py':
        s=s.replace("phase_path.write_text(json.dumps(report, indent=2) + '\\n')\n        Path('/sys/bus/platform/drivers/qcom_eud_com/unbind')",
                    "phase_path.write_text(json.dumps(report, indent=2) + '\\n')\n        print(json.dumps(report), flush=True)\n        time.sleep(0.5)\n        Path('/sys/bus/platform/drivers/qcom_eud_com/unbind')",1)
    dest=name.replace('quiesce-current176','quiesce-current180').replace('flash-pdr-irq','flash-offline-irq')
    if dest.endswith('.py'):ast.parse(s)
    (ref/dest).write_text(s);written.append(dest)
with tarfile.open(out/'deployment-tools-private.tar','w') as archive:
    for name in written:
        if not name.endswith('.ps1'):archive.add(ref/name,arcname='k181-'+name)
print('K181_FRESH180_DEPLOYMENT_TOOLS_PREPARED')
