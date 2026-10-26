"""Keep one-use runtime directories and the existing boot/state/restore guards."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'kernel302'
s = (OLD / 'native-controls.py').read_text()
s = s.replace('k302-controls-r', 'k303-(?:joint|ae)-r')
s = s.replace('stage=302', 'stage=303')
s = s.replace("state=dict(stage=303", "kind = 'ae' if '/k303-ae-' in str(root) else 'joint'\nstate=dict(stage=303")
s = s.replace('full_ipa_and_automatic_algorithms_not_implemented=True', "full_iq_not_implemented=True,hardware_ae_requested=(kind=='ae')")
s = s.replace('manual_hardware_ipa_integrated=True', "candidate_hardware_ipa_integrated=True,test_kind=kind")
s = s.replace('len(sensor_commands)==18', "len(sensor_commands)==(18 if kind=='joint' else 0)")
(HERE / 'native-capture.py').write_text(s)
print('Prepared guarded capture worker; no device action')
