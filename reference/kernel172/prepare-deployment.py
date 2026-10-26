from pathlib import Path
import json, tarfile

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
build = json.loads((ref / 'build-package-validation.json').read_text())
old_build = json.loads((ref.parent / 'kernel171/build-package-validation.json').read_text())
assert build['kernel_build'] == 172 and build['firmware_only_dtb_changed'] and build['modules132_runtime_compatible']
names = ['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh',
         'enter-bootloader.ps1','enable-transition-eud.ps1','flash-speaker-sd1.ps1','collect-runtime.py']
for name in names:
    s = (ref.parent / 'kernel171' / name).read_text()
    for a,b in [('kernel171','kernel172'),('k171','k172'),('K171','K172'),('stage=171','stage=172'),('speaker-sd1','headset')]:
        s = s.replace(a,b)
    if name == 'collect-preflash.py':
        s = s.replace('d96c8b6cb7cf4cef7349360ea87793692ec3b3df8200934f4264dc3cc361f37c', old_build['boot_sha256'])
        s = s.replace('3ecb785f64bb533b4b649baa179bf66e8166f74ee85a41a07b9ce6cc26fb60b9', old_build['logdump_sha256'])
    if name == 'check-quiesce.py': s = s.replace('target_kernel=168','target_kernel=172')
    if name == 'flash-speaker-sd1.ps1':
        s = s.replace('!$build.image_unchanged', '!$build.firmware_only_dtb_changed')
        s = s.replace('$build.kernel_build_kept -ne 168', '$build.kernel_build -ne 172')
        s = s.replace('kernel_build=168','kernel_build=172')
    if name == 'collect-runtime.py':
        s = s.replace("startswith('#168 ')", "startswith('#172 ')").replace('kernel_build=168','kernel_build=172')
        s = s.replace(old_build['boot_sha256'],build['boot_sha256']).replace(old_build['logdump_sha256'],build['logdump_sha256'])
        insertion = '''mbhc_started = log.count('samurai MBHC started: micbias=2700 mV')
jack_bound = log.count('WCD934x headset detection connected')
assert mbhc_started == jack_bound == 1
jack_status = {}
for name in ['Headphone Jack', 'Mic Jack']:
    value = capture('jack-' + name.replace(' ', '-'), ['amixer','-c','0','cget',"iface=CARD,name='" + name + "'"])
    jack_status[name] = re.search(r': values=(.*)',value)[1].strip()
'''
        s = s.replace('report = dict(stage=172,', insertion + '\nreport = dict(stage=172, mbhc_started_count=mbhc_started, jack_bound_count=jack_bound, jack_status=jack_status,')
    dest = ref / (name.replace('speaker-sd1','headset'))
    assert not dest.exists(), dest
    dest.write_text(s)
with tarfile.open(out / 'deployment-tools-private.tar', 'w') as archive:
    for name in names:
        if not name.endswith('.ps1'):
            archive.add(ref / name, arcname=name)
            if name in ['check-quiesce.py','freeze-for-bootloader.sh']:
                archive.add(ref / name, arcname='k172-' + name)
print('K172_DEPLOYMENT_TOOLS_PREPARED', flush=True)
