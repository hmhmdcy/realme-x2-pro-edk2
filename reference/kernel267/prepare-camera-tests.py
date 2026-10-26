"""Adapt the proven standard-client tests to the current boot and normal services."""
from pathlib import Path
import json

R=Path(__file__).resolve().parent;B=R.parent/'kernel265'
s=(B/'native-capture.py').read_text().replace('k260-work','k267-work').replace('stage=265','stage=267')
s=s.replace('k265-services-current-private','k267-services-current-private')
s=s.replace('k265-camera-','k267-camera-').replace('k265_camera','k267_camera')
s=s.replace('/var/lib/samurai/k265-tools/camera-probe.py','/var/lib/samurai/k267-client-tools/camera-probe.py')
s=s.replace("delay in range(1,19)","delay in [16,17,18]")
compile(s,'native-capture.py','exec');(R/'native-capture.py').write_text(s)
s=(B/'camera-probe.py').read_text().replace('k265-user','k267-user')
needle="devices=[d for d in provider.get_devices() if d.get_display_name()==target];assert len(devices)==1"
assert s.count(needle)==1
s=s.replace(needle,"wanted='ac4b000' if which=='front' else 'ac4a000'\ndevices=[d for d in provider.get_devices() if wanted in str(d.get_properties().get_value('node.name'))];assert len(devices)==1")
compile(s,'camera-probe.py','exec');(R/'camera-probe.py').write_text(s)
s=(B/'run-capture.py').read_text().replace('k265-tools','k267-client-tools').replace('k265-user','k267-user')
s=s.replace('run in range(1,19)','run in [16,17,18]')
compile(s,'run-capture.py','exec');(R/'run-capture.py').write_text(s)
print(json.dumps(dict(stage=267,standard_device_selection_by_cci_identity=True,
 current_guard_and_session_services=True,only_system_production_test_runs_enabled=True)))
