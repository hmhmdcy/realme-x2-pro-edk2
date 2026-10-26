from pathlib import Path
import json, os, re, subprocess, tarfile, time, wave

os.umask(0o077)
out = Path('/var/lib/samurai/k173-silent-headset'); assert not out.exists(); out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k173-source/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
def command(args):
    p = subprocess.run(args,capture_output=True,timeout=30)
    assert p.returncode==0,(args,p.stderr.decode()); return p.stdout.decode()
def pulse(args): return command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+args])
def get(n,iface='MIXER'):
    return re.search(r': values=(.*)',command(['amixer','-c','0','cget',"iface="+iface+",name='"+n+"'"]))[1].strip()
def amps(): return {n:Path('/sys/bus/i2c/devices/'+n+'/status').read_text() for n in ['1-0039','1-003a']}
protected = ['HPHL Volume','HPHR Volume','ADC2 Volume','RX HPH Mode','Headphone Jack Switch',
             'Handset Mic Switch','Left Speaker Switch','Right Speaker Switch']
before = command(['dmesg']); (out / 'dmesg-before-private.txt').write_text(before)
gains = {n:get(n) for n in protected}; before_amp = amps(); processes = []
stimulus = out / 'zero-stereo-private.wav'
with wave.open(str(stimulus),'wb') as w:
    w.setparams((2,2,48000,0,'NONE','not compressed')); w.writeframes(bytes(3*48000*4))
try:
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 1')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    assert all(get(n,'CARD')=='off' for n in ['Headphone Jack','Mic Jack'])
    command(['/usr/libexec/samurai-audio-route','headphones','Pro'])
    command(['/usr/libexec/samurai-audio-route','headset','Pro'])
    with (out / 'play-private.log').open('wb') as playlog, (out / 'capture-private.log').open('wb') as caplog:
        rec = subprocess.Popen(['arecord','-q','-D','hw:0,1','-d','3','-r','48000','-c','1','-f','S16_LE',str(out/'capture-private.wav')],stdout=caplog,stderr=caplog)
        processes.append(rec)
        play = subprocess.Popen(['aplay','-q','-D','hw:0,0',str(stimulus)],stdout=playlog,stderr=playlog)
        processes.append(play); time.sleep(.7)
        live = {n:Path('/proc/asound/card0/'+p+'/sub0/status').read_text() for n,p in [('playback','pcm0p'),('capture','pcm1c')]}
        (out / 'pcm-live-private.json').write_text(json.dumps(live,indent=2)+'\n')
        (out / 'dapm-live-private.txt').write_text('\n'.join(str(p)+'\n'+p.read_text() for p in Path('/sys/kernel/debug/asoc').rglob('*')
            if p.is_file() and p.name in ['HPHL','HPHR','HPHL PA','HPHR PA','Mic Jack']))
        assert all('RUNNING' in s for s in live.values()),live
        assert amps() == before_amp
        assert all(p.wait(timeout=8)==0 for p in processes)
    with wave.open(str(out/'capture-private.wav'),'rb') as w:
        capture = dict(frames=w.getnframes(),channels=w.getnchannels(),sample_rate=w.getframerate(),sample_width=w.getsampwidth())
        assert capture == dict(frames=144000,channels=1,sample_rate=48000,sample_width=2)
finally:
    for p in processes:
        if p.poll() is None: p.terminate(); p.wait(timeout=3)
    command(['/usr/libexec/samurai-audio-route','init','Pro'])
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 0')
log = command(['dmesg']); (out / 'dmesg-after-private.txt').write_text(log)
patterns = {'warnings':'WARNING:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out',
            'queue_full':'Message buffer unavailable','resume_failed':'NGD resume failed','oops':'Oops:'}
report = dict(stage=173,kernel_build=172,zero_sample_playback=True,playback_and_capture_running=True,capture_pcm=capture,
              hardware_jacks_absent_and_not_simulated=True,speaker_amps_unchanged_and_off=amps()==before_amp,
              gain_classh_and_jack_pins_unchanged={n:get(n) for n in protected}==gains,
              speaker_and_internal_mic_routes_restored=get('QUAT_MI2S_RX Audio Mixer MultiMedia1')==get('AIF1_CAP Mixer SLIM TX5')=='on',
              headphone_or_headset_sound_and_analog_sampling_not_proven=True,
              same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              fault_delta={n:log.count(p)-before.count(p) for n,p in patterns.items()})
(out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k173-silent-headset-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
assert report['same_boot'] and report['speaker_amps_unchanged_and_off'] and report['gain_classh_and_jack_pins_unchanged']
assert report['taint']==0 and all(v==0 for v in report['fault_delta'].values())
