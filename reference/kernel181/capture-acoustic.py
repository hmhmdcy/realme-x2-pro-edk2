from pathlib import Path
import hashlib, json, math, os, re, struct, subprocess, sys, tarfile, time, wave

os.umask(0o077)
label=sys.argv[1] if len(sys.argv)>1 else 'dmic0-low48'
peak_dbfs=int(sys.argv[2]) if len(sys.argv)>2 else -48
dmic=sys.argv[3] if len(sys.argv)>3 else 'DMIC0'
assert dmic in ['DMIC0','DMIC1','DMIC2']
mic_pin,dec={'DMIC0':('Handset',5),'DMIC1':('Secondary',7),'DMIC2':('Speaker',5)}[dmic]
assert re.fullmatch('[a-z0-9-]+',label) and peak_dbfs in [-48,-42,-36,-24]
for jack_name in ['Headphone Jack', 'Mic Jack']:
    jack_text = subprocess.check_output(['amixer','-c','0','cget',"iface=CARD,name='" + jack_name + "'"], text=True)
    assert re.search(r': values=(.*)',jack_text)[1].strip() == 'off', jack_name
assert os.uname().version.startswith('#181 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k181-runtime/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/soc@0/remoteproc@17300000/glink-edge/apr/service@4/dais/dai@16/qcom,sd-lines').read_bytes() == b'\0\0\0\1'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=Path('/var/lib/samurai/k181-'+label);out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
def command(args,input=None):
    p=subprocess.run(args,capture_output=True,input=input)
    assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
def pulse(args):
    return command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+args])
def cget(name):
    text=command(['amixer','-c','0','cget',"name='"+name+"'"])
    return re.search(r': values=(.*)',text)[1].strip()
def cset(name,value): command(['amixer','-c','0','cset',"name='"+name+"'",str(value)])
def amp_state():
    states={}
    for name,address in [('left','1-0039'),('right','1-003a')]:
        text=Path('/sys/bus/i2c/devices/'+address+'/status').read_text()
        states[name]={k:v for k,v in re.findall(r'(\w+)=([^\s]+)',text)}
    return states
def snapshot(name):
    data=dict(amps=amp_state(),playback=Path('/proc/asound/card0/pcm0p/sub0/status').read_text(),
              capture=Path('/proc/asound/card0/pcm1c/sub0/status').read_text(),
              ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text())
    for filename in ['pins','pinconf-pins','pinmux-pins']:
        path=Path('/sys/kernel/debug/pinctrl/3100000.pinctrl')/filename
        if path.exists():
            data['i2s_'+filename]='\n'.join(line for line in path.read_text().splitlines() if re.search(r'pin (?:13[789]|140)\b',line))
    (out/(name+'-private.json')).write_text(json.dumps(data,indent=2)+'\n')
    return data
code=[1,1,0,1,0,0,1,1,1,0,1,0,1,0,0]
rate=48000;amplitude=round(32767*10**(peak_dbfs/20));duration=4
names=['Left Speaker Switch','Right Speaker Switch','Headphone Jack Switch',
       'QUAT_MI2S_RX Audio Mixer MultiMedia1','Handset Mic Switch','Secondary Mic Switch','Speaker Mic Switch',
       'DMIC MUX5','ADC MUX5','CDC_IF TX5 MUX','DMIC MUX7','ADC MUX7','CDC_IF TX7 MUX','AIF1_CAP Mixer SLIM TX5','AIF1_CAP Mixer SLIM TX7',
       'MultiMedia2 Mixer SLIMBUS_0_TX']
before_log=command(['dmesg']);(out/'dmesg-before-private.txt').write_text(before_log)
(out/'mixer-full-before-private.txt').write_text(command(['amixer','-c','0','contents']))
saved={};results=[]
try:
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 1')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    time.sleep(.5);saved={n:cget(n) for n in names}
    (out/'mixer-before-private.json').write_text(json.dumps(saved,indent=2)+'\n')
    cset('Headphone Jack Switch',0)
    for mic in ['Handset','Secondary','Speaker']: cset(mic+' Mic Switch',int(mic==mic_pin))
    for n in [5,7]:
        cset('AIF1_CAP Mixer SLIM TX'+str(n),0);cset('CDC_IF TX'+str(n)+' MUX','ZERO')
    for name,value in [('DMIC MUX'+str(dec),dmic),('ADC MUX'+str(dec),'DMIC'),('CDC_IF TX'+str(dec)+' MUX','DEC'+str(dec)),
                       ('AIF1_CAP Mixer SLIM TX'+str(dec),1),
                       ('MultiMedia2 Mixer SLIMBUS_0_TX',1),('QUAT_MI2S_RX Audio Mixer MultiMedia1',1)]: cset(name,value)
    for speaker,channel,frequency in [('left',0,997),('right',1,1511)]:
        tone=out/(speaker+'-stimulus-private.wav')
        frames=[]
        for i in range(duration*rate):
            t=i/rate;offset=t-.5;value=0
            if 0<=offset<3:
                slot=int(offset/.2);phase=offset-slot*.2
                fade=min(1,phase/.005,(.2-phase)/.005)
                value=round(amplitude*code[slot]*max(0,fade)*math.sin(2*math.pi*frequency*t))
            frames.append(struct.pack('<hh',value if channel==0 else 0,value if channel==1 else 0))
        with wave.open(str(tone),'wb') as w:
            w.setparams((2,2,rate,0,'NONE','not compressed'));w.writeframes(b''.join(frames))
        for enabled in [True,False]:
            case=speaker+('-on' if enabled else '-off-control')
            for name in ['left','right']:
                cset(name.title()+' Speaker Switch',int((name==speaker)==enabled))
            path=out/(case+'-capture-private.wav')
            capture_start=time.monotonic()
            with (out/(case+'-arecord-private.log')).open('wb') as caplog:
                rec=subprocess.Popen(['arecord','-q','-D','hw:0,1','-d','6','-r','48000','-c','1','-f','S16_LE',str(path)],stdout=caplog,stderr=caplog)
                try:
                    time.sleep(.6);snapshot(case+'-capture-ready')
                    play_start=time.monotonic()
                    with (out/(case+'-aplay-private.log')).open('wb') as playlog:
                        play=subprocess.Popen(['aplay','-q','-D','hw:0,0',str(tone)],stdout=playlog,stderr=playlog)
                        try:
                            time.sleep(.7);live=snapshot(case+'-live')
                            assert 'RUNNING' in live['playback'] and 'RUNNING' in live['capture']
                            assert re.search(r'pin 140 .*function qua_mi2s', live['i2s_pinmux-pins'])
                            amp=live['amps'][speaker]
                            assert amp['failed']=='0' and amp['powered']==str(int(enabled))
                            assert amp['global']==('01' if enabled else '00'),(case,amp)
                            play_rc=play.wait(timeout=8);assert play_rc==0
                        finally:
                            if play.poll() is None: play.terminate();play.wait(timeout=3)
                    rec_rc=rec.wait(timeout=8);assert rec_rc==0
                finally:
                    if rec.poll() is None: rec.terminate();rec.wait(timeout=3)
            snapshot(case+'-closed')
            with wave.open(str(path),'rb') as w: assert w.getnframes()==288000
            results.append(dict(case=case,speaker=speaker,channel=channel,frequency=frequency,
                                target_speaker_enabled=enabled,play_start_after_capture_seconds=play_start-capture_start,
                                capture_frames=288000,capture_input=dmic,play_returncode=play_rc,capture_returncode=rec_rc,
                                target_amp_state_live=amp,stimulus_sha256=hashlib.sha256(tone.read_bytes()).hexdigest()))
finally:
    for name,value in saved.items(): cset(name,value)
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 0')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
    time.sleep(7);snapshot('final')
    log=command(['dmesg']);(out/'dmesg-final-private.txt').write_text(log)
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
report=dict(stage=181,kernel_build=181,tone_peak_dbfs=peak_dbfs,code=code,slot_seconds=.2,leading_silence_seconds=.5,
            sample_rate=rate,cases=results,mixer_restored=all(cget(n)==v for n,v in saved.items()),
            same_boot=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
            fault_delta={n:log.count(p)-before_log.count(p) for n,p in {'warnings':'WARNING:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out','resume_failed':'NGD resume failed'}.items()},
            all_final_amplifiers_off=all(a['global']=='00' and a['powered']=='0' for a in amp_state().values()),
            amp_gain_unchanged=True,acoustic_analysis_pending=True)
(out/'capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k181-'+label+'-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
assert report['mixer_restored'] and report['taint']==0 and all(v==0 for v in report['fault_delta'].values())
