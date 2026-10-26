from pathlib import Path
import hashlib, json, os, re, shlex, shutil, subprocess, tarfile, time

os.umask(0o077)
out = Path('/var/lib/samurai/k173-deploy'); assert not out.exists(); out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k173-source/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
test = json.loads(Path('/var/lib/samurai/k173-ucm-test-verified/validation.json').read_text())
assert test['mixer_restored'] and test['user_privilege_exec_pass'] and test['conflict_rejected']
assert all(v == 0 for v in test['fault_delta'].values())
(out / 'boot-id-private.txt').write_bytes(boot)
def command(args):
    p = subprocess.run(args,capture_output=True,timeout=30)
    assert p.returncode == 0,(args,p.returncode,p.stderr.decode())
    return p.stdout.decode()
def pulse(args):
    return command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+shlex.join(['pactl']+args)])
def modules():
    return [dict(index=int(p[0]),name=p[1],argument=p[2] if len(p)>2 else '') for p in
            (l.split('\t') for l in pulse(['list','short','modules']).splitlines())]
def reload_audio():
    existing = [r for r in modules() if r['name'] == 'module-udev-detect']
    assert len(existing) <= 1
    if existing: pulse(['unload-module',str(existing[0]['index'])])
    pulse(['load-module','module-udev-detect']+shlex.split(udev['argument']))
    time.sleep(2)
def cget(n,iface='MIXER'):
    return re.search(r': values=(.*)',command(['amixer','-c','0','cget',"iface="+iface+",name='"+n+"'"]))[1].strip()
def idle(): return all(p.read_text().strip() == 'closed' for p in Path('/proc/asound/card0').glob('pcm*/sub*/status'))
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads(Path('/tmp/k173-candidate-files/manifest.json').read_text())['sha256']
baseline = json.loads(Path('/var/lib/samurai/k173-source/validation.json').read_text())
directory = Path('/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro')
for n,digest in baseline['ucm132_before_sha256'].items():
    assert sha(directory / n) == digest
    shutil.copyfile(directory / n,out / (n+'-before-private'))
assert sha(Path('/usr/libexec/samurai-audio-route')) == manifest['samurai-audio-route.py']
assert all(cget(n,'CARD') == 'off' for n in ['Headphone Jack','Mic Jack']) and idle()
protected = ['HPHL Volume','HPHR Volume','ADC2 Volume','RX HPH Mode',
             'Headphone Jack Switch','Handset Mic Switch','Left Speaker Switch','Right Speaker Switch']
gains = {n:cget(n) for n in protected}
before_log = command(['dmesg']); (out / 'dmesg-before-private.txt').write_text(before_log)
before_sinks = json.loads(pulse(['-f','json','list','sinks']))
before_sources = [r for r in json.loads(pulse(['-f','json','list','sources'])) if not r['name'].endswith('.monitor')]
before_cards = json.loads(pulse(['-f','json','list','cards']))
assert len(before_cards) == len(before_sinks) == len(before_sources) == 1
(out / 'pulse-before-private.json').write_text(json.dumps(dict(cards=before_cards,sinks=before_sinks,sources=before_sources),indent=2)+'\n')
udevs = [r for r in modules() if r['name'] == 'module-udev-detect']; assert len(udevs) == 1; udev = udevs[0]
desktop_before = command(['sh','-c','pgrep -x phosh; pgrep -x phoc; pgrep -u 10000 -x pulseaudio'])
(out / 'desktop-pids-before-private.txt').write_text(desktop_before)
changed = False
try:
    for n in ['HiFi.conf','Realme_X2_Pro.conf']:
        source = Path('/tmp/k173-candidate-files') / n; assert sha(source) == manifest[n]
        dest = directory / n; temp = dest.with_name(n+'.k173-new')
        shutil.copyfile(source,temp); temp.chmod(0o644); os.replace(temp,dest)
    changed = True; reload_audio()
    after_sinks = json.loads(pulse(['-f','json','list','sinks']))
    after_sources = [r for r in json.loads(pulse(['-f','json','list','sources'])) if not r['name'].endswith('.monitor')]
    after_cards = json.loads(pulse(['-f','json','list','cards']))
    (out / 'pulse-after-load-private.json').write_text(json.dumps(dict(cards=after_cards,sinks=after_sinks,sources=after_sources),indent=2)+'\n')
    assert len(after_cards) == len(after_sinks) == len(after_sources) == 1
    # Preserve user-session software volumes/mutes across card recreation.
    for old,new,kind in [(before_sinks[0],after_sinks[0],'sink'),(before_sources[0],after_sources[0],'source')]:
        volume = [str(v['value']) for v in old['volume'].values()]
        pulse(['set-'+kind+'-volume',new['name']]+volume)
        pulse(['set-'+kind+'-mute',new['name'],'1' if old['mute'] else '0'])
        pulse(['set-default-'+kind,new['name']])
    assert cget('QUAT_MI2S_RX Audio Mixer MultiMedia1') == cget('MultiMedia2 Mixer SLIMBUS_0_TX') == 'on'
    assert cget('SLIMBUS_0_RX Audio Mixer MultiMedia1') == cget('AIF1_CAP Mixer SLIM TX1') == 'off'
    assert cget('AIF1_CAP Mixer SLIM TX5') == 'on'
    assert {n:cget(n) for n in protected} == gains
    assert all(sha(directory / n) == manifest[n] for n in ['HiFi.conf','Realme_X2_Pro.conf'])
except Exception:
    if changed:
        for n in ['HiFi.conf','Realme_X2_Pro.conf']:
            shutil.copyfile(out / (n+'-before-private'),directory / n); (directory / n).chmod(0o644)
        reload_audio()
        (out / 'rollback-completed-private.txt').write_text('Original UCM132 files restored and audio discovery reloaded.\n')
    raise
time.sleep(3)
after_sinks = json.loads(pulse(['-f','json','list','sinks']))
after_sources = [r for r in json.loads(pulse(['-f','json','list','sources'])) if not r['name'].endswith('.monitor')]
after_cards = json.loads(pulse(['-f','json','list','cards']))
(out / 'pulse-final-private.json').write_text(json.dumps(dict(cards=after_cards,sinks=after_sinks,sources=after_sources),indent=2)+'\n')
log = command(['dmesg']); (out / 'dmesg-after-private.txt').write_text(log)
patterns = {'warnings':'WARNING:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out',
            'queue_full':'Message buffer unavailable','resume_failed':'NGD resume failed','oops':'Oops:'}
report = dict(stage=173,kernel_build=172,installed_ucm173=True,ucm_sha256={n:sha(directory/n) for n in ['HiFi.conf','Realme_X2_Pro.conf']},
              helper_sha256=manifest['samurai-audio-route.py'],same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              desktop_and_pulse_pids_unchanged=desktop_before == command(['sh','-c','pgrep -x phosh; pgrep -x phoc; pgrep -u 10000 -x pulseaudio']),
              kernel_and_firmware_not_modified=True,audio_discovery_module_reloaded_with_original_arguments=True,
              sinks=[dict(name=r['name'],active_port=r.get('active_port'),ports=r.get('ports')) for r in after_sinks],
              sources=[dict(name=r['name'],active_port=r.get('active_port'),ports=r.get('ports')) for r in after_sources],
              software_volume_and_mute_preserved=all(old['volume']==new['volume'] and old['mute']==new['mute'] for old,new in
                  [(before_sinks[0],after_sinks[0]),(before_sources[0],after_sources[0])]),
              analog_gain_classh_mode_jack_pins_unchanged=True,fault_delta={n:log.count(p)-before_log.count(p) for n,p in patterns.items()},
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),pcm_closed=idle(),physical_headset_test_pending=True)
(out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k173-deploy-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
assert report['same_boot'] and report['desktop_and_pulse_pids_unchanged'] and report['software_volume_and_mute_preserved']
assert report['taint'] == 0 and all(v == 0 for v in report['fault_delta'].values()) and report['pcm_closed']
