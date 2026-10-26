from pathlib import Path
import ast, json, os, tarfile

os.umask(0o077)
ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel176')
build=json.loads((ref/'build-package-validation.json').read_text());old=json.loads((ref.parent/'kernel175/build-package-validation.json').read_text())
assert build['kernel_build']==176 and build['reset_address_refresh_and_managed_probe_cleanup_included'] and build['modules132_runtime_compatible']
assert json.loads((ref/'host-tests-validation.json').read_text())['all_passed']
names=['collect-preflash.py','quiesce-current174.sh','check-quiesce.py','freeze-for-bootloader.sh','disable-crtc.py',
       'enter-bootloader.ps1','enable-transition-eud.ps1','flash-lifetime.ps1','collect-runtime.py']
written=[]
for name in names:
    s=(ref.parent/'kernel175'/name).read_text()
    s=s.replace('kernel175','kernel176').replace('k175','k176').replace('K175','K176').replace('stage=175','stage=176')
    s=s.replace('current_kernel=174','current_kernel=175').replace('target_kernel=175','target_kernel=176').replace('CURRENT174','CURRENT175')
    if name!='collect-runtime.py':s=s.replace("startswith('#174 ')","startswith('#175 ')").replace("'^#174 '","'^#175 '")
    if name=='collect-preflash.py':
        s=s.replace('2bd3cd106f7e20e14fac1d78529a8df60f2fc4e94870c1d4656c4df20c8676c3',old['logdump_sha256'])
        s=s.replace('/var/lib/samurai/k174-final/boot-id-private.txt','/var/lib/samurai/k175-final/boot-id-private.txt')
        s=s.replace("assert prior.count('SLIMBUS_0_RX: ASoC error (-22)')==1","assert prior.count('SLIMBUS_0_RX: ASoC error (-22)')==0\nassert prior.count('Failed to bring up WCD934X: err = -110')==1")
    if name=='check-quiesce.py':
        s=s.replace("current.count('SLIMBUS_0_RX: ASoC error (-22)')==prior.count('SLIMBUS_0_RX: ASoC error (-22)')==1","current.count('SLIMBUS_0_RX: ASoC error (-22)')==prior.count('SLIMBUS_0_RX: ASoC error (-22)')==0")
        s=s.replace("assert current.count('Oops:')==prior.count('Oops:')==0","assert current.count('Oops:')==prior.count('Oops:')==0\nassert current.count('Failed to bring up WCD934X: err = -110')==prior.count('Failed to bring up WCD934X: err = -110')==1")
    if name=='flash-lifetime.ps1':
        s=s.replace('!$build.card_probe_failure_cleanup_included -or !$build.clock_lifetime_fix_included','!$build.reset_address_refresh_and_managed_probe_cleanup_included')
        s=s.replace('$build.kernel_build -ne 175','$build.kernel_build -ne 176').replace('kernel_build=175','kernel_build=176')
        s=s.replace('logdump-k176-lifetime-v4.img','logdump-k176-reset.img')
    if name=='collect-runtime.py':
        s=s.replace("startswith('#175 ')","startswith('#176 ')").replace('kernel_build=175','kernel_build=176')
        s=s.replace(old['logdump_sha256'],build['logdump_sha256'])
        marker='assert log.count("jack disconnect:") == 0'
        s=s.replace(marker,marker+'\nassert log.count("Error Interrupt received") == 0\nassert log.count("failed:-110") == 0\nassert log.count("Failed to bring up WCD934X:") == 0')
    dest=name.replace('quiesce-current174','quiesce-current175').replace('flash-lifetime','flash-reset')
    if dest.endswith('.py'):ast.parse(s)
    (ref/dest).write_text(s);written.append(dest)
with tarfile.open(out/'deployment-tools-private.tar','w') as ar:
    for name in written:
        if name.endswith('.ps1'):continue
        ar.add(ref/name,arcname=name)
        if name in ['check-quiesce.py','freeze-for-bootloader.sh','disable-crtc.py']:ar.add(ref/name,arcname='k176-'+name)
print('K176_DEPLOYMENT_TOOLS_PREPARED',flush=True)
