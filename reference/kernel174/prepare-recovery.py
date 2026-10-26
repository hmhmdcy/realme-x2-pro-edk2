from pathlib import Path
import json, os, tarfile

os.umask(0o077)
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel174/recovery')
out.mkdir(mode=0o700)
baseline = json.loads((ref.parent/'kernel172/build-package-validation.json').read_text())
names = ['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh',
         'enter-bootloader.ps1','enable-transition-eud.ps1']
for name in names:
    s = (ref.parent/'kernel172'/name).read_text()
    s = s.replace('kernel172','kernel174/recovery').replace('k172','k174-recovery').replace('K172','K174_RECOVERY')
    s = s.replace("startswith('#168 ')","startswith('#172 ')").replace("'^#168 '","'^#172 '")
    s = s.replace('current_kernel=168','current_kernel=172').replace('target_kernel=172','target_kernel=172')
    s = s.replace("strip()=='0'", "strip()=='128'").replace('taint=0','taint=128')
    s = s.replace('tainted)\" = 0','tainted)\" = 128')
    if name == 'collect-preflash.py':
        s = s.replace('612a012426200d4997b33ee98edd18ea6e15a61d23901aa82cb61acd68c392f2',baseline['boot_sha256'])
        s = s.replace('d711ab4122eba4b0f2cc9d9792c89eb05c49957fb637b19aa595e878909921f6',baseline['logdump_sha256'])
        s = s.replace("assert prior.count('WARNING:')==0", "assert prior.count('WARNING:')==0\nassert prior.count('Oops:') == 1 and 'regmap_name_read_file+0x54' in prior\nassert prior.count('Internal error:') == 1")
        s = s.replace("'/tmp/k174-recovery-source-boot-id-private.txt'", "'/var/lib/samurai/k174-debugfs-oops/boot-id-private.txt'")
    if name == 'check-quiesce.py':
        s = s.replace("assert current.count('WARNING:')==prior.count('WARNING:')==0", "assert current.count('WARNING:')==prior.count('WARNING:')==0\nassert current.count('Oops:') == prior.count('Oops:') == 1\nassert 'regmap_name_read_file+0x54' in prior\nassert current.count('Internal error:') == prior.count('Internal error:') == 1")
    if name.endswith('.ps1'):
        s = s.replace('headset-first','recovery-first')
        s = s.replace('E:\\edk2-samurai-out\\kernel174/recovery','E:\\edk2-samurai-out\\kernel174\\recovery')
    if name == 'enter-bootloader.ps1': s = s.replace("$Prefix='headset'","$Prefix='recovery-first'")
    (ref/('recovery-'+name)).write_text(s)
with tarfile.open(out/'tools-private.tar','w') as archive:
    for name in names:
        if not name.endswith('.ps1'):
            archive.add(ref/('recovery-'+name),arcname=name)
            if name in ['check-quiesce.py','freeze-for-bootloader.sh']:
                archive.add(ref/('recovery-'+name),arcname='k174-recovery-'+name)
print('K174_RECOVERY_TOOLS_PREPARED',flush=True)
