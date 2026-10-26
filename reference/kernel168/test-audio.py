from pathlib import Path
import array, hashlib, json, math, os, re, struct, subprocess, sys, tarfile, time, wave

os.umask(0o077)
label=sys.argv[1] if len(sys.argv)>1 else 'first'
assert re.fullmatch('[a-z0-9-]+',label)
assert os.uname().version.startswith('#168 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
before_log=subprocess.check_output(['dmesg'],text=True)
assert 'Version:0x411' in before_log and 'WARNING:' not in before_log
out=Path('/var/lib/samurai/k168-'+label+'-audio');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
def command(args,check=True,input=None):
    p=subprocess.run(args,capture_output=True,input=input)
    if check: assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p
def pulse(args,input=None):
    return command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+args],input=input)
def cget(name):
    text=command(['amixer','-c','0','cget',"name='"+name+"'"]).stdout.decode()
    return re.search(r': values=(.*)',text)[1].strip()
def cset(name,value):
    command(['amixer','-c','0','cset',"name='"+name+"'",str(value)])
def snapshot(name):
    text=[]
    for path in [Path('/proc/asound/card0/pcm0p/sub0/status'),Path('/proc/asound/card0/pcm1c/sub0/status'),
                 Path('/sys/bus/i2c/devices/1-0039/status'),Path('/sys/bus/i2c/devices/1-003a/status')]:
        text.append(str(path)+'\n'+path.read_text())
    power=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power')
    for path in power.glob('runtime_*'):
        try: text.append(str(path)+'\n'+path.read_text())
        except OSError: pass
    data='\n'.join(text);(out/(name+'-private.txt')).write_text(data)
    return data
def run_pcm(name,args,pcm):
    with (out/(name+'-stdout-private.txt')).open('wb') as stdout,(out/(name+'-stderr-private.txt')).open('wb') as stderr:
        proc=subprocess.Popen(args,stdout=stdout,stderr=stderr)
        try:
            time.sleep(.6)
            live=snapshot(name+'-live')
            status=Path('/proc/asound/card0/'+pcm+'/sub0/status').read_text()
            rc=proc.wait(timeout=10)
            assert rc==0,(name,rc)
            assert 'RUNNING' in status,(name,status)
        finally:
            if proc.poll() is None: proc.terminate();proc.wait(timeout=3)
    time.sleep(.3)
    assert Path('/proc/asound/card0/'+pcm+'/sub0/status').read_text().strip()=='closed'
    return live
tone=out/'tone-low-private.wav'
with wave.open(str(tone),'wb') as w:
    w.setparams((2,2,48000,0,'NONE','not compressed'))
    amplitude=round(32767*10**(-48/20))
    w.writeframes(b''.join(struct.pack('<hh',round(amplitude*math.sin(2*math.pi*1000*i/48000)),round(amplitude*math.sin(2*math.pi*800*i/48000))) for i in range(96000)))
names=['Left Speaker Switch','Right Speaker Switch','QUAT_MI2S_RX Audio Mixer MultiMedia1',
       'Handset Mic Switch','Secondary Mic Switch','Speaker Mic Switch',
       'DMIC MUX5','DMIC MUX7','ADC MUX5','ADC MUX7','CDC_IF TX5 MUX','CDC_IF TX7 MUX',
       'AIF1_CAP Mixer SLIM TX5','AIF1_CAP Mixer SLIM TX7','MultiMedia2 Mixer SLIMBUS_0_TX']
saved={};captures=[];plays=[];error=None
snapshot('before')
try:
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 1')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    time.sleep(.5)
    saved={name:cget(name) for name in names}
    (out/'mixer-before-private.json').write_text(json.dumps(saved,indent=2)+'\n')
    for name in names[:3]: cset(name,1)
    for i in range(3):
        live=run_pcm('play-'+str(i),['aplay','-q','-D','hw:0,0',str(tone)],'pcm0p')
        assert live.count('powered=1 muted=0')==2,live
        idle=snapshot('play-'+str(i)+'-closed')
        assert idle.count('powered=0 muted=1')==2,idle
        plays.append(dict(index=i,returncode=0,pcm_live_running=True,both_amplifiers_on_then_off=True))
    for dmic,pin,dec in [('DMIC0','Handset',5),('DMIC1','Secondary',7),('DMIC2','Speaker',5)]:
        for mic in ['Handset','Secondary','Speaker']: cset(mic+' Mic Switch',0)
        for n in [5,7]:
            cset('AIF1_CAP Mixer SLIM TX'+str(n),0)
            cset('CDC_IF TX'+str(n)+' MUX','ZERO')
        cset(pin+' Mic Switch',1)
        cset('DMIC MUX'+str(dec),dmic);cset('ADC MUX'+str(dec),'DMIC')
        cset('CDC_IF TX'+str(dec)+' MUX','DEC'+str(dec))
        cset('AIF1_CAP Mixer SLIM TX'+str(dec),1)
        cset('MultiMedia2 Mixer SLIMBUS_0_TX',1)
        path=out/(dmic+'-private.wav')
        run_pcm(dmic,['arecord','-q','-D','hw:0,1','-d','3','-r','48000','-c','1','-f','S16_LE',str(path)],'pcm1c')
        with wave.open(str(path),'rb') as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
            samples=array.array('h',w.readframes(w.getnframes()))
        tail=samples[24000:]
        captures.append(dict(input=dmic,dec=dec,frames=len(samples),nonzero_after_half_second=sum(x!=0 for x in tail),
                             clipped_after_half_second=sum(abs(x)>=32767 for x in tail),
                             rms_after_half_second=math.sqrt(sum(x*x for x in tail)/len(tail)),returncode=0))
        assert len(samples)==144000 and any(tail),(dmic,len(samples))
finally:
    for name,value in saved.items(): cset(name,value)
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 0')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
    time.sleep(.5)
    snapshot('after-native')
    (out/'dmesg-after-native-private.txt').write_text(subprocess.check_output(['dmesg'],text=True))
# Exercise the desktop route after returning mixer and PulseAudio ownership.
with wave.open(str(tone),'rb') as w: tone_frames=w.readframes(w.getnframes())
assert pulse('paplay --device=alsa_output.platform-sound.HiFi__Speaker__sink --volume=16384 --raw --format=s16le --rate=48000 --channels=2',input=tone_frames).returncode==0
time.sleep(7)
final=snapshot('final');log=subprocess.check_output(['dmesg'],text=True)
(out/'dmesg-final-private.txt').write_text(log)
assert final.count('powered=0 muted=1')==2
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
patterns={'warnings':'WARNING:','prepare':'unable to prepare channel','tx_timeout':'TX timed out',
          'queue_full':'Message buffer unavailable','resume_failure':'NGD resume failed'}
delta={name:log.count(pattern)-before_log.count(pattern) for name,pattern in patterns.items()}
report=dict(stage=168,kernel_build=168,native_playback=plays,digital_microphones=captures,
            desktop_playback_returncode=0,mixer_restored=all(cget(n)==v for n,v in saved.items()),
            final_amplifiers_off=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),new_faults=delta,
            same_boot=True,tone_peak_dbfs=-48,physical_sound_and_pickup_quality_confirmed=False)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k168-'+label+'-audio-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
assert report['mixer_restored'] and report['taint']==0 and all(x==0 for x in delta.values())
