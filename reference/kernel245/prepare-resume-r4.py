"""Test reasserting this modem's original supported diagnostic features."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'native-resume-rf-r3.py').read_text().replace("o=r/'k245-resume-rf-r3'","o=r/'k245-resume-rf-r4'")
old="   d.diagnostic_mode(True);d.gnss_logs(True);run_phase('baseline-off')"
new="   d.negotiate(peer,feature['remote_mask'],feature['width'],'same_boot_original_features_reasserted');end=time.monotonic()+4\n   while time.monotonic()<end:d.poll(min(0.25,end-time.monotonic()))\n   assert d.control_peer==peer and peer not in d.deleted_peers\n   d.diagnostic_mode(True);d.gnss_logs(True);run_phase('baseline-off')"
assert old in s;s=s.replace(old,new).replace('cached_same_boot_resume=True,fresh_feature_handshake=False','cached_same_boot_resume=True,original_features_reasserted=True,fresh_feature_handshake=False')
compile(s,'native-resume-rf-r4.py','exec');(R/'native-resume-rf-r4.py').write_text(s)
t=(R/'launch-resume-r3.py').read_text().replace('native-resume-rf-r3.py','native-resume-rf-r4.py').replace('k245-resume-rf-r3','k245-resume-rf-r4').replace('resume-r3-','resume-r4-');compile(t,'launch-resume-r4.py','exec');(R/'launch-resume-r4.py').write_text(t)
p=(R/'poll-resume-r3.py').read_text().replace('k245-resume-rf-r3','k245-resume-rf-r4');(R/'poll-resume-r4.py').write_text(p)
print('Prepared original supported feature reassertion; no NV/RF setting API.')
