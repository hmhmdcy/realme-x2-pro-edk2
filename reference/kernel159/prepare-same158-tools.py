from pathlib import Path
import ast,hashlib,json,subprocess,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel159');out=Path('/mnt/e/edk2-samurai-out/kernel159');out.mkdir(mode=0o700,exist_ok=True)
old=ref.parent/'kernel157'
for name in ['collect-preflash.py','quiesce-current156.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1','k157-startup-trace']:
    s=(old/name).read_text().replace('kernel157','kernel159').replace('k157','k159').replace('K157','K159')
    if name=='k157-startup-trace':s=s.replace('#157 ','#158 ')
    else:s=s.replace('#156 ','#158 ').replace('CURRENT156','CURRENT158').replace('current_kernel=156','current_kernel=158').replace('target_kernel=157','target_kernel=158').replace('stage=157','stage=159')
    s=s.replace("$Prefix='early-stop-first'","$Prefix='same158-second'")
    dest=ref/name.replace('quiesce-current156','quiesce-current158').replace('k157-startup','k159-startup')
    assert not dest.exists();dest.write_text(s)
    if dest.suffix=='.py':ast.parse(s)
    elif dest.suffix=='.sh' or 'startup-trace' in name:subprocess.run(['sh','-n',str(dest)],check=True)
for name in ['capture-startup.py','display-power.py','capture-display-cycles.py','verify-runtime.py','capture-boot-timing.py']:
    s=(ref.parent/'kernel158'/name).read_text().replace('kernel158','kernel159').replace('k158','k159').replace('K158','K159').replace('stage=158','stage=159')
    if name=='capture-startup.py':
        s=s.replace('/var/lib/samurai/k159-source-ram/boot-id-private.txt','/var/lib/samurai/k159-preflash/boot-id-private.txt')
        s=s.replace('live-first-active','fbcon-first').replace('live-desktop-active','desktop-first')
        s=s.replace('recorder_started_after_ssh=True,initial_frame_snapshot_not_claimed=True','recorder_started_as_boot_service=True')
    if name=='verify-runtime.py':
        s=s.replace('/var/lib/samurai/k159-source-ram/boot-id-private.txt','/var/lib/samurai/k159-preflash/boot-id-private.txt')
        s=s.replace('/var/lib/samurai/k157-preflash/','/var/lib/samurai/k159-preflash/')
        s=s.replace('preservation_reference_from_current156_before157_flash=True','preservation_reference_from_current158_before_same_image_reboot=True')
    dest=ref/name;assert not dest.exists();dest.write_text(s);ast.parse(s)
s=(ref.parent/'kernel155/reboot-same-image.ps1').read_text().replace('kernel155','kernel159').replace('K155','K159').replace('stage=155','stage=159').replace('kernel_build=154','kernel_build=158').replace('current_kernel -ne 154','current_kernel -ne 158').replace('Current154','Current158').replace('same154','same158').replace("$Prefix='host-init-first'","$Prefix='same158-second'")
(ref/'reboot-same-image.ps1').write_text(s)
s=(ref.parent/'kernel158/poll-first-boot.ps1').read_text().replace('kernel158','kernel159').replace('K158','K159')
(ref/'poll-first-boot.ps1').write_text(s)
files=['collect-preflash.py','quiesce-current158.sh','check-quiesce.py','freeze-for-bootloader.sh','capture-startup.py','k159-startup-trace',
    'display-power.py','capture-display-cycles.py','verify-runtime.py','capture-boot-timing.py']
with tarfile.open(out/'same158-tools-private.tar','w') as t:
    for n in files:t.add(ref/n,arcname=n)
    t.add(ref.parent/'kernel158/build-package-validation.json',arcname='build-package-validation.json')
report=dict(stage=159,kernel_build=158,source_kernel=158,new_flash_planned=False,
    same_image_reboot=True,first_frame_and_kms_failure_events_captured=True,
    archive_sha256=hashlib.sha256((out/'same158-tools-private.tar').read_bytes()).hexdigest())
(ref/'observation-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
