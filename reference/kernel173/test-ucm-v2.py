from pathlib import Path
import json, os, re, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k173-ucm-test-v2'); assert not out.exists(); out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k173-source/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
def command(args, data=None, expected=0):
    p = subprocess.run(args,input=data,capture_output=True,timeout=45)
    assert p.returncode == expected,(args,p.returncode,p.stderr.decode())
    return p.stdout.decode()
def pulse(args):
    return command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 ' + args])
def get(n, iface='MIXER'):
    text = command(['amixer','-c','0','cget',"iface="+iface+",name='"+n+"'"])
    return re.search(r': values=(.*)',text)[1].strip()
def set_value(n,v): command(['amixer','-c','0','cset',"name='"+n+"'",str(v)])
def pcm_closed():
    return all(p.read_text().strip() == 'closed' for p in Path('/proc/asound/card0').glob('pcm*/sub*/status'))
def amp(): return {n:Path('/sys/bus/i2c/devices/'+n+'/status').read_text() for n in ['1-0039','1-003a']}
controls = json.loads(Path('/var/lib/samurai/k173-source/validation.json').read_text())['controls']
names = list(controls) + ['AIF1_CAP Mixer SLIM TX0','AIF1_CAP Mixer SLIM TX7']
protected = ['Headphone Jack Switch','Handset Mic Switch','Left Speaker Switch','Right Speaker Switch',
             'HPHL Volume','HPHR Volume','ADC2 Volume','RX HPH Mode']
baseline = {}; rows = []; failures = []; before_log = command(['dmesg']); before_amp = amp()
(out / 'dmesg-before-private.txt').write_text(before_log)
def batch(label,commands,user=False,expected=0):
    commands_file = Path('/run/samurai-ucm173-v2') / ('test-'+label+'.txt')
    commands_file.write_text('\n'.join(commands)+'\n'); commands_file.chmod(0o644)
    args = ['alsaucm','-c','hw:Pro','-b',str(commands_file)]
    env = os.environ.copy(); env['ALSA_CONFIG_UCM2'] = '/run/samurai-ucm173-v2'
    if user:
        args = ['su','-s','/bin/sh','cy122','-c','ALSA_CONFIG_UCM2=/run/samurai-ucm173-v2 alsaucm -c hw:Pro -b '+str(commands_file)]
    p = subprocess.run(args,env=env,capture_output=True,timeout=45)
    (out / (label+'-private.log')).write_bytes(p.stdout+p.stderr)
    if expected == 0:
        assert p.returncode == 0 and not p.stderr,(label,p.returncode,p.stderr.decode())
    else:
        assert p.returncode != 0,(label,p.returncode,p.stderr.decode())
    return p
def check(play,cap):
    assert pcm_closed()
    assert get('QUAT_MI2S_RX Audio Mixer MultiMedia1') == ('on' if play == 'Speaker' else 'off')
    assert get('SLIMBUS_0_RX Audio Mixer MultiMedia1') == ('on' if play == 'Headphones' else 'off')
    assert get('MultiMedia2 Mixer SLIMBUS_0_TX') == 'on'
    for n in [0,1,5,7]: assert get('AIF1_CAP Mixer SLIM TX'+str(n)) == ('on' if n == (5 if cap == 'Mic' else 1) else 'off')
    if cap == 'Headset':
        assert get('AMIC MUX1') == '2' and get('ADC MUX1') == '1' and get('CDC_IF TX1 MUX') == '2'
    if play == 'Headphones':
        assert get('SLIM RX0 MUX') == get('SLIM RX1 MUX') == '1'
        assert get('RX INT1_1 MIX1 INP0') == '5' and get('RX INT2_1 MIX1 INP0') == '6'
        assert get('RX INT1_1 INTERP') == get('RX INT2_1 INTERP') == '1'
    assert {n:get(n) for n in protected} == {n:baseline[n] for n in protected}
    assert amp() == before_amp
    (out / (play.lower()+'-'+cap.lower()+'-mixer-private.json')).write_text(json.dumps({n:get(n) for n in names},indent=2)+'\n')
try:
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 1')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    assert pcm_closed() and all(get(n,'CARD') == 'off' for n in ['Headphone Jack','Mic Jack'])
    baseline = {n:get(n) for n in names}
    (out / 'mixer-before-private.json').write_text(json.dumps(baseline,indent=2)+'\n')
    p = batch('user-init',['set _verb HiFi','list _devices','get JackControl/Headphones/HiFi',
                       'get JackControl/Headset/HiFi','get JackHWMute/Headphones/HiFi','get JackHWMute/Headset/HiFi'],user=True)
    assert all(n.encode() in p.stdout for n in ['Speaker','Headphones','Mic','Headset','Headphone Jack','Mic Jack'])
    check('Speaker','Mic')
    for play,cap in [('Speaker','Mic'),('Headphones','Mic'),('Headphones','Headset')]:
        label = play.lower()+'-'+cap.lower()
        p = batch(label,['set _verb HiFi','set _enadev '+play,'set _enadev '+cap,
                         'set _enadev '+play,'set _enadev '+cap,'list _enadevs'])
        check(play,cap)
        rows.append(dict(playback=play,capture=cap,ucm_enable_and_repeat_pass=True,
                         actual_mixer_route_verified=True,physical_jacks_still_absent=True,
                         pcm_not_opened=True,analog_gain_and_classh_and_jack_pins_unchanged=True))
    batch('shared-pcm-ports',['set _verb HiFi','set _enadev Speaker','set _enadev Mic',
                             'set _enadev Headphones','set _enadev Headset','list _enadevs'])
    check('Headphones','Headset')
    batch('speaker-mic-return',['set _verb HiFi','set _enadev Speaker','set _enadev Mic'])
    check('Speaker','Mic')
    batch('inactive',['set _verb HiFi','set _verb Inactive'])
    assert all(get(n) == 'off' for n in ['QUAT_MI2S_RX Audio Mixer MultiMedia1','SLIMBUS_0_RX Audio Mixer MultiMedia1',
                                        'MultiMedia2 Mixer SLIMBUS_0_TX'] + ['AIF1_CAP Mixer SLIM TX'+str(n) for n in [0,1,5,7]])
finally:
    if baseline:
        try:
            command(['/usr/libexec/samurai-audio-route','off','Pro'])
            # Pins and volume were not modified. Restore selectors before BE enables.
            last = ['AIF1_CAP Mixer SLIM TX5','MultiMedia2 Mixer SLIMBUS_0_TX','QUAT_MI2S_RX Audio Mixer MultiMedia1']
            for n in [x for x in names if x not in protected and x not in last]+last:
                set_value(n,baseline[n])
            assert {n:get(n) for n in names} == baseline
        except Exception as error: failures.append('restore: '+str(error))
    for c in ['pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0',
              'pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 0']:
        try: pulse(c)
        except Exception as error: failures.append('pulse: '+str(error))
    assert not failures,failures
log = command(['dmesg']); (out / 'dmesg-after-private.txt').write_text(log)
patterns = {'warnings':'WARNING:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out',
            'queue_full':'Message buffer unavailable','resume_failed':'NGD resume failed','oops':'Oops:'}
report = dict(stage=173,kernel_build=172,same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              user_privilege_exec_pass=True,ucm_version=2,route_cases=rows,shared_pcm_ports_select_one_backend_and_one_tx=True,
              inactive_clears_backends_and_mono_tx_slots=True,mixer_restored=True,
              power_amplifier_state_unchanged=amp() == before_amp,pcm_closed=pcm_closed(),
              fault_delta={n:log.count(p)-before_log.count(p) for n,p in patterns.items()},
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              actual_plug_detection_headphone_sound_headset_capture_not_tested=True)
(out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k173-ucm-test-v2-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
assert report['same_boot'] and report['power_amplifier_state_unchanged'] and report['pcm_closed']
assert report['taint'] == 0 and all(v == 0 for v in report['fault_delta'].values())
