from pathlib import Path
import ast, json, os, tarfile

os.umask(0o077)
ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175')
build=json.loads((ref/'build-package-validation.json').read_text())
old=json.loads((ref.parent/'kernel174/build-package-validation.json').read_text())
tests=json.loads((ref/'host-tests-validation.json').read_text())
assert build['kernel_build']==175 and build['already_up_bind_fix_included'] and build['card_probe_failure_cleanup_included'] and build['clock_lifetime_fix_included']
assert build['dtb172_unchanged'] and build['modules132_runtime_compatible'] and tests['all_passed'] and tests['clock_result']=='clock_cases=4'
names=['collect-preflash.py','quiesce-current172.sh','check-quiesce.py','freeze-for-bootloader.sh','disable-crtc.py',
       'enter-bootloader.ps1','enable-transition-eud.ps1','flash-port-lifecycle.ps1','collect-runtime.py']
written=[]
for name in names:
    s=(ref.parent/'kernel174'/name).read_text()
    s=s.replace('kernel174','kernel175').replace('k174','k175').replace('K174','K175').replace('stage=174','stage=175')
    s=s.replace("startswith('#172 ')","startswith('#174 ')").replace("'^#172 '","'^#174 '")
    s=s.replace('current_kernel=172','current_kernel=174').replace('target_kernel=174','target_kernel=175').replace('CURRENT172','CURRENT174')
    if name=='collect-preflash.py':
        s=s.replace('0562112b37e7b6b62d764d75836ca169eb006ae446e89ca9c4a20f29fd7420c2',old['logdump_sha256'])
        s=s.replace("'/var/lib/samurai/k175-recovery-runtime/boot-id-private.txt'","'/var/lib/samurai/k174-final/boot-id-private.txt'")
        s=s.replace("assert prior.count('Oops:')==0","assert prior.count('Oops:')==0\nassert prior.count('SLIMBUS_0_RX: ASoC error (-22)')==1")
    if name=='check-quiesce.py':
        s=s.replace("assert current.count('WARNING:')==prior.count('WARNING:')==0","assert current.count('WARNING:')==prior.count('WARNING:')==0\nassert current.count('SLIMBUS_0_RX: ASoC error (-22)')==prior.count('SLIMBUS_0_RX: ASoC error (-22)')==1\nassert current.count('Oops:')==prior.count('Oops:')==0")
    if name=='flash-port-lifecycle.ps1':
        s=s.replace('$build.kernel_build -ne 174','$build.kernel_build -ne 175').replace('kernel_build=174','kernel_build=175')
        s=s.replace('logdump-k175-port-lifecycle.img','logdump-k175-lifetime-v4.img')
        s=s.replace('!$build.dtb172_unchanged','!$build.card_probe_failure_cleanup_included -or !$build.clock_lifetime_fix_included -or !$build.dtb172_unchanged')
    if name=='collect-runtime.py':
        s=s.replace("startswith('#174 ')","startswith('#175 ')").replace('kernel_build=174','kernel_build=175')
        s=s.replace(old['logdump_sha256'],build['logdump_sha256'])
        s=s.replace('assert mbhc_started == jack_bound == 1','assert mbhc_started == jack_bound and mbhc_started >= 1\nassert log.count("SLIMBUS_0_RX: ASoC error") == 0\nassert log.count("jack disconnect:") == 0\nassert Path("/sys/kernel/debug/regmap/217:250:1:0/name").read_text().strip() == "wcd934x-slim"\nassert Path("/sys/kernel/debug/regmap/217:250:0:0/name").read_text().strip() == "nodev"')
        s=s.replace('report = dict(stage=175,','report = dict(stage=175, soundcard_present_without_machine_rebind=True, current_main_and_interface_regmap_names_read_without_oops=True,')
    dest=name.replace('quiesce-current172','quiesce-current174').replace('flash-port-lifecycle','flash-lifetime')
    if dest.endswith('.py'):ast.parse(s)
    (ref/dest).write_text(s);written.append(dest)
with tarfile.open(out/'deployment-tools-private.tar','w') as ar:
    for name in written:
        if name.endswith('.ps1'):continue
        ar.add(ref/name,arcname=name)
        if name in ['check-quiesce.py','freeze-for-bootloader.sh','disable-crtc.py']:ar.add(ref/name,arcname='k175-'+name)
print('K175_DEPLOYMENT_TOOLS_PREPARED',flush=True)
