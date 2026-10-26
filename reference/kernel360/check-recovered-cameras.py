"""Check installed versions and actual CameraManager enumeration after recovery."""
from pathlib import Path
import json,re,sys
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
packages={}
for item in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 values={line[:1]:line[2:] for line in item.splitlines() if len(line)>2 and line[1]==':'}
 if values.get('P') in ['libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:packages[values['P']]=values.get('V')
q=subprocess.run(['cam','--list'],capture_output=True,text=True,timeout=40)
print(json.dumps(dict(packages=packages,exit_code=q.returncode,stdout=q.stdout,stderr=q.stderr,taint=int(Path('/proc/sys/kernel/tainted').read_text()),camss_runtime_status=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip())))
'''
if '--reuse-observation' in sys.argv:facts=json.loads((host.PRIVATE/'recovered-camera-enumeration-private.json').read_text())
else:
 q=host.ssh('python3 -',input=code.encode(),timeout=50);facts=json.loads(q.stdout);(host.PRIVATE/'recovered-camera-enumeration-private.json').write_bytes(q.stdout)
expected=json.loads((HERE.parent/'kernel342/install-r1-validation.json').read_text())['hardware_cameras']
entries=[line.strip() for line in facts['stdout'].splitlines() if re.match(r'^\s*\d+:',line)]
report=dict(stage=360,installed_packages=facts['packages'],camera_manager_exit_code=facts['exit_code'],camera_entries=entries,
    registered_cameras=len(entries),expected_hardware_cameras=expected,pipewire_nodes_counted=False,frame_capture_tested=False,combined_r28_candidate_installed=False,taint=facts['taint'],camss_runtime_status=facts['camss_runtime_status'],passed=facts['exit_code']==0 and len(entries)==expected and facts['taint']==0)
(HERE/'recovered-camera-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
