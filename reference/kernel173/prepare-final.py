from pathlib import Path

ref = Path(__file__).parent
s = (ref.parent / 'kernel172/collect-final.py').read_text()
s = s.replace('k172-', 'k173-').replace('stage=172','stage=173')
s = s.replace('k173-runtime', 'k173-source').replace('k173-preflash', 'k172-preflash')
s = s.replace('dmic0-sd1-low24','dmic0-ucm173-low24')
s = s.replace('same_boot_as_k172_runtime','same_boot_as_k173_source').replace('original_k172','original_k173')
s = s.replace('no_amp_gain_change_in_k172','no_amp_gain_change_in_k173')
marker = 'report = dict(stage=173,'
extra = '''manifest = json.loads(Path('/tmp/k173-candidate-files/manifest.json').read_text())['sha256']
import hashlib
ucm_dir = Path('/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro')
for n in ['HiFi.conf','Realme_X2_Pro.conf']:
    assert hashlib.sha256((ucm_dir / n).read_bytes()).hexdigest() == manifest[n]
assert hashlib.sha256(Path('/usr/libexec/samurai-audio-route').read_bytes()).hexdigest() == manifest['samurai-audio-route.py']
original = json.loads(Path('/var/lib/samurai/k173-source/validation.json').read_text())['controls']
protected = ['HPHL Volume','HPHR Volume','ADC2 Volume','RX HPH Mode',
             'Headphone Jack Switch','Handset Mic Switch','Left Speaker Switch','Right Speaker Switch']
for n in protected:
    current = command(['amixer','-c','0','cget',"name='"+n+"'"])
    assert re.search(r': values=(.*)',current)[1].strip() == original[n]['value']
card_json = json.loads(command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 pactl -f json list cards']))
assert len(card_json) == 1
ports = card_json[0]['ports']
assert ports['[Out] Headphones']['availability'] == ports['[In] Headset']['availability'] == 'not available'
assert card_json[0]['active_profile'] == 'HiFi (Mic, Speaker)'
module_lines = command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 pactl list short modules'])
assert sum('\tmodule-alsa-card\t' in l for l in module_lines.splitlines()) == 1
'''
assert marker in s; s = s.replace(marker,extra+'\nreport = dict(stage=173, installed_ucm173_verified=True, helper_sha256=manifest["samurai-audio-route.py"], analog_gain_classh_mode_and_jack_pins_preserved=True, single_pulse_card_and_alsa_module=True, active_pulse_profile=card_json[0]["active_profile"], headphone_and_headset_ports_unavailable_when_absent=True,')
assert not (ref / 'collect-final.py').exists()
(ref / 'collect-final.py').write_text(s); compile(s,'collect-final.py','exec')
print('K173_FINAL_COLLECTOR_PREPARED',flush=True)
