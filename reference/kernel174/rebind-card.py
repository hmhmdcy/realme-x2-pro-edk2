from pathlib import Path
import json, os, subprocess, time

os.umask(0o077)
out=Path('/var/lib/samurai/k174-card-rebind');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k174-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#174 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert 'no soundcards' in Path('/proc/asound/cards').read_text()
log=subprocess.check_output(['dmesg'],text=True);assert log.count('SLIMBUS_0_RX: ASoC error (-22)')==1
(out/'boot-id-private.txt').write_bytes(boot);(out/'dmesg-before-private.txt').write_text(log)
for a in ['1-0039','1-003a']: assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/'+a+'/status').read_text()
assert Path('/sys/class/remoteproc/remoteproc2/state').read_text().strip()=='running'
driver=Path('/sys/bus/platform/drivers/samurai-audio')
assert Path('/sys/bus/platform/devices/sound/driver').resolve()==driver
(driver/'unbind').write_text('sound\n')
assert not Path('/sys/bus/platform/devices/sound/driver').exists()
(driver/'bind').write_text('sound\n')
for attempt in range(20):
    if 'Realme X2 Pro' in Path('/proc/asound/cards').read_text():break
    time.sleep(.5)
assert 'Realme X2 Pro' in Path('/proc/asound/cards').read_text()
time.sleep(2)
after=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-after-private.txt').write_text(after)
assert after.count('Oops:')==after.count('WARNING:')==0
report=dict(stage=174,kernel_build=174,first_boot_soundcard_lost_after_codec_reprobe=True,
 cause='machine jack_component persists across ASoC card unbind; new codec component rejected with -EINVAL',
 explicit_machine_unbind_bind_once=True,soundcard_recovered=True,permanent_jack_lifetime_fix_pending=True,
 stop_irq_change_not_exercised_before_initial_failure=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes())
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
