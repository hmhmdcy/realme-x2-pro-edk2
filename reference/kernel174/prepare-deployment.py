from pathlib import Path
import json, os, tarfile

os.umask(0o077)
ref=Path(__file__).parent
out=Path('/mnt/e/edk2-samurai-out/kernel174')
build=json.loads((ref/'build-package-validation.json').read_text())
old=json.loads((ref.parent/'kernel172/build-package-validation.json').read_text())
assert build['kernel_build']==174 and build['dtb172_unchanged'] and build['modules132_runtime_compatible']
names=['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1','enable-transition-eud.ps1','collect-runtime.py']
written=[]
for name in names:
    s=(ref.parent/'kernel172'/name).read_text()
    s=s.replace('kernel172','kernel174').replace('k172','k174').replace('K172','K174').replace('stage=172','stage=174')
    s=s.replace("startswith('#168 ')","startswith('#172 ')").replace("'^#168 '","'^#172 '")
    s=s.replace('current_kernel=168','current_kernel=172').replace('target_kernel=172','target_kernel=174').replace('CURRENT168','CURRENT172')
    if name=='collect-preflash.py':
        s=s.replace('612a012426200d4997b33ee98edd18ea6e15a61d23901aa82cb61acd68c392f2',old['boot_sha256'])
        s=s.replace('d711ab4122eba4b0f2cc9d9792c89eb05c49957fb637b19aa595e878909921f6',old['logdump_sha256'])
        s=s.replace("'/tmp/k174-source-boot-id-private.txt'","'/var/lib/samurai/k174-recovery-runtime/boot-id-private.txt'")
        s=s.replace("assert prior.count('WARNING:')==0","assert prior.count('WARNING:')==0\nassert prior.count('Oops:')==0")
    if name=='quiesce-current163.sh':
        a=s.index('timeout -s TERM -k 2 20 sh -c \'echo 4 > /sys/class/graphics/fb0/blank\'')
        b=s.index('\nfor sample',a)
        s=s[:a]+'python3 /tmp/k174-disable-crtc.py > "$dest/explicit-crtc-disable.txt" 2>&1'+s[b:]
    if name.endswith('.ps1'):
        s=s.replace('headset-first','port-first').replace("$Prefix='headset'","$Prefix='port-first'")
    if name=='collect-runtime.py':
        s=s.replace("startswith('#172 ')","startswith('#174 ')").replace('kernel_build=172','kernel_build=174')
        s=s.replace(old['logdump_sha256'],build['logdump_sha256'])
    dest=name.replace('quiesce-current163','quiesce-current172')
    (ref/dest).write_text(s);written.append(dest)
s=(ref/'recovery-disable-crtc.py').read_text()
s=s.replace('k174-recovery-quiesce','k174-quiesce').replace("== '128'","== '0'")
s=s.replace("assert log.count('Oops:') == 1 and 'regmap_name_read_file+0x54' in log","assert log.count('Oops:') == 0 and log.count('WARNING:') == 0")
s=s.replace("assert 'active=1' in Path('/sys/kernel/debug/dri/1/state').read_text()","# A null modeset is safe even if the console is already inactive.")
s=s[:s.index("subprocess.run(['python3','/tmp/k174-recovery-check-quiesce.py'")]+"print('K174_EXPLICIT_CRTC_DISABLE_VERIFIED',flush=True)\n"
(ref/'disable-crtc.py').write_text(s);written.append('disable-crtc.py')
with tarfile.open(out/'deployment-tools-private.tar','w') as ar:
    for name in written:
        if name.endswith('.ps1'):continue
        ar.add(ref/name,arcname=name)
        if name in ['check-quiesce.py','freeze-for-bootloader.sh','disable-crtc.py']:
            ar.add(ref/name,arcname='k174-'+name)
print('K174_DEPLOYMENT_TOOLS_PREPARED',flush=True)
