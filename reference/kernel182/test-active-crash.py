#!/usr/bin/env python3
"""One synthetic remoteproc crash report during an active desktop mic stream."""
from pathlib import Path
import errno
import json
import os
import re
import subprocess
import threading
import time
import wave

os.umask(0o077)
out=Path('/var/lib/samurai/k182-active-crash')
out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#181 ')
assert boot==Path('/var/lib/samurai/k181-final/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
(out/'boot-id-private.txt').write_bytes(boot)
state=Path('/sys/class/remoteproc/remoteproc2/state')
debug=Path('/sys/kernel/debug/remoteproc/remoteproc2')
assert (debug/'name').read_text().strip()=='adsp'
assert state.read_text().strip()=='running'
assert Path('/sys/class/remoteproc/remoteproc2/recovery').read_text().strip()=='enabled'
assert (debug/'coredump').read_text().strip()=='disabled'
def cmd(args):
    p=subprocess.run(args,capture_output=True)
    assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
def pulse(args):
    return cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+args])
def phase(name,**data):
    with (out/'phase-private.json').open('w') as f:
        json.dump(dict(phase=name,**data),f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def read(path):
    try:return Path(path).read_text().strip()
    except FileNotFoundError:return 'absent'
def maps():
    return sorted(p.name for p in Path('/sys/kernel/debug/regmap').iterdir() if p.name.startswith('217:250:'))
def supplies():
    rows={}
    for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
        f=line.split()
        if f and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)',f[0]):rows[f[0]]=int(f[1])
    return rows
def wait_for(fn,seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if fn():return
        time.sleep(.1)
    raise RuntimeError('Recovery condition timed out; do not inject again')

before=cmd(['dmesg']);(out/'dmesg-before-private.txt').write_text(before)
start_uptime=float(Path('/proc/uptime').read_text().split()[0])
assert cmd(['sha256sum','/dev/sde32']).split()[0]=='56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55'
cmd(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
cards=json.loads(pulse('pactl -f json list cards'))
assert len(cards)==1 and cards[0]['active_profile']=='HiFi (Mic, Speaker)'
for p in ['pcm0p','pcm1c']:assert read('/proc/asound/card0/'+p+'/sub0/status')=='closed'
amps_before={a:read('/sys/bus/i2c/devices/'+a+'/status') for a in ['1-0039','1-003a']}
assert all('powered=0 muted=1' in value for value in amps_before.values())
initial_supplies=supplies()
assert len(initial_supplies)==5 and all(value==1 for value in initial_supplies.values())
assert maps()==['217:250:0:0','217:250:1:0']
source_before=json.loads(pulse('pactl -f json list sources'))
(out/'sources-before-private.json').write_text(json.dumps(source_before,indent=2)+'\n')
samples=[];errors=[];stopping=threading.Event()
def monitor():
    while not stopping.is_set():
        try:
            samples.append(dict(t=time.monotonic(),adsp=read(state),cards=read('/proc/asound/cards'),
                                maps=maps(),capture=read('/proc/asound/card0/pcm1c/sub0/status')))
        except Exception as e:errors.append(repr(e))
        stopping.wait(.025)
rec=None;watch=None;fds={};submitted=False;result={}
try:
    for name in maps():fds[name]=os.open(str(Path('/sys/kernel/debug/regmap')/name/'name'),os.O_RDONLY)
    raw=out/'active-capture-private.raw'
    with raw.open('wb') as destination,(out/'parecord-private.log').open('wb') as log:
        rec=subprocess.Popen(['su','-s','/bin/sh','cy122','-c',
            'XDG_RUNTIME_DIR=/run/user/10000 parecord --device=alsa_input.platform-sound.HiFi__Mic__source '
            '--raw --format=s16le --rate=48000 --channels=1 --volume=65536'],stdout=destination,stderr=log)
        wait_for(lambda:'RUNNING' in read('/proc/asound/card0/pcm1c/sub0/status'),5)
        assert rec.poll() is None
        (out/'source-outputs-before-private.json').write_text(pulse('pactl -f json list source-outputs'))
        watch=threading.Thread(target=monitor);watch.start()
        assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
        assert state.read_text().strip()=='running'
        phase('before-single-injected-crash-report',capture_running=True,parecord_pid=rec.pid)
        os.sync()
        inject_time=time.monotonic()
        (debug/'crash').write_text('0\n')
        submitted=True
        phase('single-crash-report-submitted',synthetic_type=0)
        # Accept only observed resource removal plus a later rebuilt card.
        wait_for(lambda:any('Realme X2 Pro' not in s['cards'] and not s['maps'] for s in samples),30)
        phase('card-and-regmaps-removal-observed')
        def card_ready():
            if state.read_text().strip()!='running' or 'Realme X2 Pro' not in read('/proc/asound/cards'):return False
            c=json.loads(pulse('pactl -f json list cards'))
            return len(c)==1 and c[0]['active_profile']=='HiFi (Mic, Speaker)'
        wait_for(card_ready,60)
        dead={}
        for name,fd in fds.items():
            try:
                os.pread(fd,64,0)
                raise RuntimeError('Old regmap FD remained valid across recovery')
            except OSError as e:
                assert e.errno in [errno.EIO,errno.ENODEV,errno.ENOENT]
                dead[name]=e.errno
        assert supplies()==initial_supplies
        (out/'source-outputs-after-recovery-private.json').write_text(pulse('pactl -f json list source-outputs'))
        (out/'sources-after-recovery-private.json').write_text(pulse('pactl -f json list sources'))
        phase('automatic-card-recovery-observed',parecord_returncode=rec.poll())
        # Keep the original app alive if it survived; do not replace it silently.
        original_app_alive=rec.poll() is None
        raw_position=raw.stat().st_size/(2*48000)
        if original_app_alive:
            stimulus=Path('/var/lib/samurai/k181-dmic0-ucm181-low24/right-stimulus-private.wav')
            with stimulus.open('rb') as wav,(out/'paplay-private.log').open('wb') as log:
                p=subprocess.run(['su','-s','/bin/sh','cy122','-c',
                    'XDG_RUNTIME_DIR=/run/user/10000 paplay --device=alsa_output.platform-sound.HiFi__Speaker__sink --volume=65536'],
                    stdin=wav,stdout=log,stderr=log,timeout=10)
                assert p.returncode==0
            time.sleep(1)
        result.update(original_parecord_survived=original_app_alive,
                      original_parecord_returncode_before_stop=rec.poll(),
                      postrecovery_tone_raw_position_estimate_seconds=raw_position,
                      postrecovery_tone_played=original_app_alive,
                      old_debugfs_errno=dead,recovery_latency_seconds=time.monotonic()-inject_time)
        rec.send_signal(2) if rec.poll() is None else None
        try:rec.wait(timeout=4)
        except subprocess.TimeoutExpired:rec.terminate();rec.wait(timeout=3)
        result['original_parecord_final_returncode']=rec.returncode
    data=raw.read_bytes()
    assert len(data)%2==0
    with wave.open(str(out/'active-capture-private.wav'),'wb') as wrapped:
        wrapped.setparams((1,2,48000,0,'NONE','not compressed'));wrapped.writeframes(data)
    result['recorded_frames']=len(data)//2
finally:
    if rec and rec.poll() is None:rec.terminate();rec.wait(timeout=4)
    stopping.set()
    if watch:watch.join(timeout=3);assert not watch.is_alive()
    for fd in fds.values():os.close(fd)
    (out/'timeline-private.json').write_text(json.dumps(samples,indent=2)+'\n')
    (out/'monitor-errors-private.json').write_text(json.dumps(errors,indent=2)+'\n')
    (out/'dmesg-after-private.txt').write_text(cmd(['dmesg']))

wait_for(lambda:all(read('/proc/asound/card0/'+p+'/sub0/status')=='closed' for p in ['pcm0p','pcm1c']),12)
after=cmd(['dmesg'])
window='\n'.join(line for line in after.splitlines() if (m:=re.match(r'^\[\s*(\d+\.\d+)\]',line)) and float(m[1])>=start_uptime)
patterns={'warning':'WARNING:','oops':'Oops:','asoc':'ASoC error','dma_prepare':'unable to prepare channel',
          'tx_timeout':'TX timed out','resume':'NGD resume failed','irq_read':'Failed to read IRQ status',
          'irq_config':'Failed to write config','irq_mask':'Failed to sync masks',
          'pdr_listener':'register listener txn wait failed','pdr_missing_state':'register listener response has no state',
          'bringup':'Failed to bring up WCD934X:','underflow':'underflow error','overflow':'overflow error',
          'ngd_interrupt':'Error Interrupt received','transfer_timeout':'failed:-110','qmi_wait':'QMI wait timeout'}
faults={key:window.count(value) for key,value in patterns.items()}
expected={key:window.count(value) for key,value in {'crash_report':'crash detected in adsp:',
          'crash_handler':'handling crash #','recovery':'recovering adsp'}.items()}
report=dict(stage=182,kernel_build=181,synthetic_remoteproc_crash_report_injected_once=submitted,
            actual_dsp_firmware_watchdog_not_injected=True,coredump_disabled_default_unchanged=True,
            recovery_setting_enabled_unchanged=True,capture_pcm_running_at_injection=True,
            card_and_two_regmaps_removal_observed=True,automatic_card_and_pulse_profile_recovery=True,
            no_manual_remoteproc_start_stop_or_driver_rebind=True,same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
            taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=faults,expected_recovery_log_counts=expected,
            monitor_error_count=len(errors),**result)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
phase('completed',fault_counts=faults)
print(json.dumps(report),flush=True)
assert report['same_boot'] and report['taint']==0 and not errors
assert expected['crash_report']==expected['crash_handler']==1 and expected['recovery']>=1
assert not any(faults.values()),faults
