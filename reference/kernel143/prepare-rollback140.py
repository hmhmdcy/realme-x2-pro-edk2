from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
old=out.parent/'kernel140'
runtime=json.loads(ref.joinpath('first-runtime-validation.json').read_text())
assert runtime['new_boot_verified'] and runtime['counts']['dsi_errors']>0
assert not runtime['clean_runtime_accepted']
assert not ref.joinpath('rollback140-build-validation.json').exists()
runtime.update(candidate_rejected=True,display_fifo_underflow_observed=True,rollback_target=140)
ref.joinpath('first-runtime-validation.json').write_text(json.dumps(runtime,indent=2)+'\n')
out.joinpath('rejected-boot-id-private.txt').write_bytes(out.joinpath('embedded-boot-id-private.txt').read_bytes())
def sha(path):
    d=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):d.update(chunk)
    return d.hexdigest()
bundle=json.loads(ref.joinpath('threaded-console-build-package-validation.json').read_text())
image=old/'Image-k140-dma-diagnostic-private'
target=old/'logdump-k140-dma-diagnostic.img'
assert sha(image)=='2b244772eb7e15ce587722cd3fed37f775a05d4562a4ac2e6b80701aeb04dc45'
assert sha(target)=='0ac9d6678ba4218a049fca47090c4fdd290d03d6a1fd72a6d9f04f046b21d925'
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==out.parent.joinpath('kernel132/DTB-k132-private').read_bytes()
for row in bundle['artifacts']:
    path=target if row['role']=='logdump' else Path(row['artifact_path'])
    if row['role']=='logdump':row.update(artifact_path=str(target),sha256=sha(target),bytes=target.stat().st_size)
    else:assert sha(path)==row['sha256']
bundle.update(kernel_build=140,image_sha256=sha(image),eud_nbcon_threaded_normal_output=False,
    rollback_target=140,rollback140_bundle_verified=True,old140_image_fat_readback_exact=True,
    preserves_slimbus_unwind139_and_diagnostics140=True,deployed=False,actual_runtime_verified=False)
for folder in [ref,out]:folder.joinpath('rollback140-build-validation.json').write_text(json.dumps(bundle,indent=2)+'\n')
def write(name,text):
    assert not ref.joinpath(name).exists()
    if name.endswith('.py'):ast.parse(text)
    ref.joinpath(name).write_text(text)

text=ref.joinpath('quiesce-current140.sh').read_text()
text=text.replace('k143-preflash','k143-first-runtime').replace('k143-quiesce','k143-rollback-quiesce').replace("'^#140 '","'^#143 '")
text=text.replace('"$before/old132-module-tree.sha256"','/var/lib/samurai/k132-preflash/new-module-tree.sha256')
start=text.index('cat /proc/asound/card0/pcm0p')
end=text.index('test "$(cat /proc/sys/kernel/tainted)" = 0',start)
write('quiesce-rejected143-desktop.sh',text[:start]+'dmesg > "$dest/dmesg-at-blank.txt"\necho K143_REJECTED143_DESKTOP_QUIESCED\n')
tail='#!/bin/sh\nset -eu\numask 077\nbefore=/var/lib/samurai/k143-first-runtime\ndest=/var/lib/samurai/k143-rollback-quiesce\n'
tail+='uname -v | grep -q \'^#143 \'\ntest "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"\n'
tail+='test ! -e /tmp/k143-rollback-quiesce-private.tar\ntest ! -e "$dest/SHA256SUMS"\n'
tail+=text[start:end]
tail+='python3 /tmp/k143-check-rollback-warning.py --record\ncat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"\nsync\n'
tail+='(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum \'{}\' \';\') > "$dest/SHA256SUMS"\n'
tail+='tar -C "$dest" -cf /tmp/k143-rollback-quiesce-private.tar .\necho K143_REJECTED143_PERIPHERALS_QUIESCED_AND_SEALED\n'
write('quiesce-rejected143-peripherals.sh',tail)

text=ref.joinpath('check-known-quiesce-warning.py').read_text()
text=text.replace('k143-quiesce','k143-rollback-quiesce').replace("startswith('#140 ')","startswith('#143 ')").replace('k143-preflash','k143-first-runtime')
text=text.replace("assert int(Path('/proc/sys/kernel/tainted').read_text()) == 512","taint=int(Path('/proc/sys/kernel/tainted').read_text())\nassert taint in [0,512]")
start=text.index("assert before.count('WARNING:')")
end=text.index("patterns =",start)
text=text[:start]+'''assert before.count('WARNING:') == 0
assert after.count('WARNING:') == (1 if taint == 512 else 0)
if taint == 512:
    assert delta.count('ida_free called for id=1 which is not allocated.') == 1
    assert re.search(r'WARNING: lib/idr.c:594 at ida_free\\+', delta)
    assert all(name + '+' in delta for name in ['ida_free','slim_unregister_controller','slim_pd_status','pdr_notifier_work'])
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|unable to prepare channel', delta)
blank=base.joinpath('dmesg-at-blank.txt').read_text()
assert after.startswith(blank)
assert not re.search(r'frame done timeout|dsi_err_worker',after[len(blank):])
'''+text[end:]
text=text.replace("patterns = ['gpu fault:', 'frame done timeout', 'dsi_err_worker', 'unable to prepare channel']","patterns = ['gpu fault:', 'unable to prepare channel']")
text=text.replace('current_kernel=140, target_kernel=143, taint=512','current_kernel=143, target_kernel=140, taint=taint').replace('warning_count=1','warning_count=after.count(\'WARNING:\')')
text=text.replace("K143_EXACT_OLD_SLIM_WARNING_RETAINED_TRANSITION_ONLY","K143_ROLLBACK_QUIESCED_FAULT_SCOPE_CHECKED")
write('check-rollback-warning.py',text)

text=ref.joinpath('verify-quiesce.py').read_text()
text=text.replace('quiesce-private.tar','rollback-quiesce-private.tar').replace('source-boot-id-private.txt','rejected-boot-id-private.txt')
start=text.index("assert data['state.txt']")
end=text.index("for name,count",start)
text=text[:start]+'''taint=int(data['state.txt'].splitlines()[-1]);assert taint in [0,512]
warning=json.loads(data['known-warning-transition.json'])
assert warning['current_kernel']==143 and warning['target_kernel']==140 and warning['taint']==taint
before=data['dmesg-before.txt'].decode();after=data['dmesg-after.txt'].decode();blank=data['dmesg-at-blank.txt'].decode()
assert after.startswith(before) and after.startswith(blank)
assert before.count('WARNING:')==0 and after.count('WARNING:')==(1 if taint==512 else 0)
delta=after[len(before):]
if taint==512:
    assert delta.count('ida_free called for id=1 which is not allocated.')==1
    assert all(name+'+' in delta for name in ['ida_free','slim_unregister_controller','slim_pd_status','pdr_notifier_work'])
import re
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|unable to prepare channel',delta)
assert not re.search(r'frame done timeout|dsi_err_worker',after[len(blank):])
'''+text[end:]
text=text.replace('current_kernel=140,target_kernel=143','current_kernel=143,target_kernel=140').replace('taint=512,','taint=taint,')
text=text.replace('quiesce-validation.json','rollback-quiesce-validation.json').replace('CURRENT140_FULL','REJECTED143_ROLLBACK_FULL')
write('verify-rollback-quiesce.py',text)
text=ref.joinpath('freeze-for-bootloader.sh').read_text().replace('k143-preflash','k143-first-runtime').replace('k143-quiesce','k143-rollback-quiesce').replace("'^#140 '","'^#143 '")
text=text.replace('k143-check-known-quiesce-warning.py','k143-check-rollback-warning.py').replace('"$before/old132-module-tree.sha256"','/var/lib/samurai/k132-preflash/new-module-tree.sha256')
write('freeze-for-rollback.sh',text)
text=ref.joinpath('enable-transition-eud.ps1').read_text().replace('eud-thread-first','rollback140-first')
write('enable-rollback-eud.ps1',text)
text=ref.joinpath('enter-bootloader.ps1').read_text().replace('eud-thread-first','rollback140-first').replace('source-boot-id-private.txt','rejected-boot-id-private.txt').replace('quiesce-validation.json','rollback-quiesce-validation.json').replace('k143-freeze-for-bootloader.sh','k143-freeze-for-rollback.sh')
write('enter-rollback-bootloader.ps1',text)
text=ref.joinpath('flash-threaded-console-logdump.ps1').read_text().replace('eud-thread-first','rollback140-first').replace('threaded-console-build-package-validation.json','rollback140-build-validation.json').replace('source-boot-id-private.txt','rejected-boot-id-private.txt').replace('quiesce-validation.json','rollback-quiesce-validation.json')
text=text.replace('!$build.eud_nbcon_threaded_normal_output','!$build.rollback140_bundle_verified')
text=text.replace('$q.taint -ne 512','($q.taint -ne 0 -and $q.taint -ne 512)').replace('$q.current_kernel -ne 140 -or $q.target_kernel -ne 143','$q.current_kernel -ne 143 -or $q.target_kernel -ne 140')
start=text.index('$recorder=');end=text.index('$image=',start);text=text[:start]+text[end:]
text=text.replace('$image="$out/logdump-k143-threaded-console.img"','$image="E:/edk2-samurai-out/kernel140/logdump-k140-dma-diagnostic.img"')
text=text.replace('kernel_build=143','kernel_build=140').replace('flash-validation.json','rollback-flash-validation.json').replace('THREADED_CONSOLE_LOGDUMP','RESTORED140_LOGDUMP')
write('flash-rollback140-logdump.ps1',text)
text=ref.joinpath('poll-new-boot.ps1').read_text().replace('startup-ssh-','rollback-ssh-').replace('check-new-boot.py','check-rollback-boot.py').replace('NEW143_BOOT','RESTORED140_BOOT').replace('NEW143_SSH','RESTORED140_SSH')
write('poll-rollback-boot.ps1',text)
write('check-rollback-boot.py',"from pathlib import Path\nimport os\nassert os.uname().version.startswith('#140 ')\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k143-first-runtime/boot-id-private.txt').read_bytes()\nprint('K143_RESTORED140_BOOT_CONFIRMED')\n")
text=ref.joinpath('collect-runtime.sh').read_text().replace('k143-first-runtime','k143-rollback140-runtime').replace("'^#143 '","'^#140 '").replace('/var/lib/samurai/k143-preflash/boot-id-private.txt','/var/lib/samurai/k143-first-runtime/boot-id-private.txt').replace('K143_DMA_DIAGNOSTIC132_FIRST_RUNTIME','K143_RESTORED140_RUNTIME')
write('collect-rollback-runtime.sh',text)
text=ref.joinpath('verify-runtime.py').read_text().replace("out / 'first-runtime-private.tar.gz'","out / 'rollback140-runtime-private.tar.gz'").replace("out / 'preflash-private.tar.gz'","out / 'first-runtime-private.tar.gz'").replace("b'#143 SMP'","b'#140 SMP'").replace('threaded-console-build-package-validation.json','rollback140-build-validation.json')
text=text.replace('kernel_build=143','kernel_build=140').replace('boot132_and_logdump143_readback_exact','boot132_and_logdump140_readback_exact').replace('eud_nbcon_threaded_normal_output=True','eud_nbcon_threaded_normal_output=False').replace('first-runtime-validation.json','rollback-runtime-validation.json')
write('verify-rollback-runtime.py',text)
for p in ref.glob('*.sh'):subprocess.run(['bash','-n',str(p)],check=True)
print('K143_EXACT_VERIFIED140_ROLLBACK_TOOLS_READY_NO_TRANSITION_STARTED')
