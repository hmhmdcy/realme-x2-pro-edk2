from pathlib import Path

ref = Path(__file__).parent
s = (ref.parent / 'kernel171/collect-final.py').read_text()
s = s.replace('k171-', 'k172-').replace('stage=171','stage=172').replace('kernel_build=168','kernel_build=172')
s = s.replace("startswith('#168 ')","startswith('#172 ')").replace('dmic0-sd1-low48','dmic0-sd1-low24')
s = s.replace('same_boot_as_k171_runtime', 'same_boot_as_k172_runtime').replace('original_k171','original_k172')
s = s.replace('kernel168_retained_boot_and_logdump171_deployed=True','kernel172_boot_and_logdump172_deployed=True')
s = s.replace('no_amp_gain_change_in_k171','no_amp_gain_change_in_k172')
s = s.replace('report = dict(stage=172,', '''jack_status = {}
for n in ['Headphone Jack', 'Mic Jack']:
    text = command(['amixer','-c','0','cget',"iface=CARD,name='" + n + "'"])
    jack_status[n] = re.search(r': values=(.*)',text)[1].strip()
assert all(v == 'off' for v in jack_status.values())
assert log.count('samurai MBHC started: micbias=2700 mV') == log.count('WCD934x headset detection connected') == 1
report = dict(stage=172, jack_status=jack_status, mbhc_bias_mv=2700, jack_bound_once=True,''')
assert not (ref / 'collect-final.py').exists()
(ref / 'collect-final.py').write_text(s)
compile(s,'collect-final.py','exec')
print('K172_FINAL_COLLECTOR_PREPARED',flush=True)
