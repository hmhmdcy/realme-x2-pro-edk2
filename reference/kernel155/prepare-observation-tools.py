from pathlib import Path
import ast,hashlib,json,subprocess,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel155')
base=ref.parent/'kernel154'
out=Path('/mnt/e/edk2-samurai-out/kernel155');out.mkdir(mode=0o700,exist_ok=True)
for name in ['collect-preflash.py','quiesce-current153.sh','check-quiesce.py','freeze-for-bootloader.sh',
    'enter-bootloader.ps1','capture-startup.py','k154-startup-trace','display-power.py','capture-wake-recovery.py']:
    s=(base/name).read_text().replace('kernel154','kernel155').replace('k154','k155').replace('K154','K155')
    # Stage 155 deliberately reboots the same #154 image, without a flash.
    if name in ['collect-preflash.py','quiesce-current153.sh','check-quiesce.py','freeze-for-bootloader.sh']:
        s=s.replace("'#153 '","'#154 '").replace("'^#153 '","'^#154 '")
        s=s.replace('current_kernel=153','current_kernel=154').replace('stage=154','stage=155')
        s=s.replace('CURRENT153','CURRENT154')
    if name=='capture-startup.py':
        mark="            rows.append(dict(index=i,elapsed=time.monotonic()-started,uptime=float(Path('/proc/uptime').read_text().split()[0]),"
        assert mark in s
        helper='''            active='\\n\\tactive=1\\n' in state
            phases=[]
            if active and 'fbcon-first' not in snapshot_phases:phases.append('fbcon-first')
            if active and all(pids.values()) and 'desktop-first' not in snapshot_phases:phases.append('desktop-first')
            for phase in phases:
                for repeat in range(2):
                    pre=state_path.read_text()
                    rc=capture(['cat',str(state_path.parent/'kms')],f'kms-{phase}-{repeat}-private.txt')
                    post=state_path.read_text()
                    valid=rc==0 and '\\n\\tactive=1\\n' in pre and '\\n\\tactive=1\\n' in post
                    (out/f'kms-{phase}-{repeat}-state-before-private.txt').write_text(pre)
                    (out/f'kms-{phase}-{repeat}-state-after-private.txt').write_text(post)
                    snapshots.append(dict(phase=phase,repeat=repeat,uptime=float(Path('/proc/uptime').read_text().split()[0]),
                        valid_active_before_and_after=valid,returncode=rc,counts=counts(subprocess.check_output(['dmesg'],text=True))))
                    time.sleep(0.25)
                snapshot_phases.add(phase)
                (out/'snapshot-validation.json').write_text(json.dumps(snapshots,indent=2)+'\\n')
'''
        s=s.replace(mark,helper+mark)
        s=s.replace('reader=None;error=None;rows=[];started=time.monotonic()',
            'reader=None;error=None;rows=[];snapshots=[];snapshot_phases=set();started=time.monotonic()')
    if name=='quiesce-current153.sh':
        start=s.index("if test \"$(grep -c 'active=1' \"$dest/drm-before-blank.txt\"")
        end=s.index('cat /proc/asound/cards > "$dest/soundcards-before-stop.txt"',start)
        s=s[:start]+s[end:]
        mark='python3 /tmp/k155-check-quiesce.py --record'
        block='''test "$(cat /sys/class/vtconsole/vtcon1/name)" = '(M) frame buffer device'
echo 0 > /sys/class/vtconsole/vtcon1/bind
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
timeout -s TERM -k 2 20 sh -c 'echo 4 > /sys/class/graphics/fb0/blank' > "$dest/fbcon-detached-blank.txt" 2>&1
for sample in 1 2 3; do
 sleep 1
 cat /sys/kernel/debug/dri/1/state > "$dest/drm-detached-sample-$sample.txt"
 test "$(grep -c 'active=1' "$dest/drm-detached-sample-$sample.txt" || true)" = 0
done
'''
        assert mark in s;s=s.replace(mark,block+mark)
    dest=ref/name.replace('quiesce-current153','quiesce-current154').replace('k154-startup','k155-startup')
    assert not dest.exists(),dest
    dest.write_text(s)
    if dest.suffix=='.py':ast.parse(s)
    if dest.suffix=='.sh' or name=='k154-startup-trace':subprocess.run(['sh','-n',str(dest)],check=True)
with tarfile.open(out/'observation-tools-private.tar','w') as tar:
    for name in ['collect-preflash.py','quiesce-current154.sh','check-quiesce.py','freeze-for-bootloader.sh',
        'capture-startup.py','k155-startup-trace','display-power.py','capture-wake-recovery.py']:
        tar.add(ref/name,arcname=name)
report=dict(stage=155,kernel_build=154,source_and_image_unchanged=True,new_flash_planned=False,
    snapshots_require_active_crtc_before_and_after=True,snapshot_phases=['fbcon-first','desktop-first'],
    archive_sha256=hashlib.sha256((out/'observation-tools-private.tar').read_bytes()).hexdigest())
(ref/'observation-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
