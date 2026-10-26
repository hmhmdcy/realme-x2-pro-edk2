from pathlib import Path
import re
R=Path(__file__).parent
s=(R/'advanced-probe.py').read_text()
needle=" photo=Path('/var/lib/samurai/k264-stills')/({2000000:'front.jpg',2000001:'front-r2.jpg',3000002:'front-profile.jpg'}[int(sys.argv[1])])"
assert s.count(needle)==1;s=s.replace(needle," photo=Path(os.environ['K264_PHOTO_PATH'])")
(R/'system-photo-probe.py').write_text(s)
s=(R/'native-advanced.py').read_text();s=re.sub(r"assert delay in [^\n]+","assert delay in range(6000070,6000075)",s,count=1)
s=s.replace("'/var/lib/samurai/k264-tools/advanced-runner.py'","'/var/lib/samurai/k264-tools/system-runner.py'")
s=s.replace("application='pipewire-probe'", "application='camerabin-system-photo' if delay==6000074 else 'camera-clients'")
s=s.replace("no_shutter_action=delay not in [2000000,2000001,3000002],no_scene_images_saved=delay not in [2000000,2000001,3000002]", "no_shutter_action=delay!=6000074,no_scene_images_saved=delay!=6000074")
needle="assert json.loads((root/'k237-camss-install/state-private.json').read_text())['exit_code']==0"
helper='''
system_services=json.loads((root/'k264-services/summary.json').read_text())['new_processes']
def verify_system_services():
 for item in system_services:
  proc=Path('/proc',str(item['pid']))
  assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
  maps=(proc/'maps').read_text().splitlines()
  assert any(l.split()[-1]=='/usr/lib/libpipewire-0.3.so.0.1609.0' for l in maps)
  assert not any('/var/lib/samurai/k264-' in l and '.so' in l for l in maps)
  if item['name']=='wireplumber':assert any(l.split()[-1]=='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' for l in maps)
verify_system_services()
'''
assert s.count(needle)==1;s=s.replace(needle,needle+helper)
s=s.replace(" report['diagnostic_completed']=completed;", " verify_system_services()\n report['production_service_identities_and_system_maps_verified']=True\n report['diagnostic_completed']=completed;")
(R/'native-system.py').write_text(s)
