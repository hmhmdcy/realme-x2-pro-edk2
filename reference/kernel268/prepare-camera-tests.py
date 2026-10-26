"""Keep product libraries standard and select cameras by hardware identity in tests."""
from pathlib import Path
import json

R=Path(__file__).resolve().parent;B=R.parent/'kernel267'
for name in ['native-capture.py','camera-probe.py','run-capture.py']:
    s=(B/name).read_text().replace('stage=267','stage=268').replace('k267-services-current-private','k268-services-current-private')
    s=s.replace('k267-camera-','k268-camera-').replace('k267_camera','k268_camera')
    s=s.replace('k267-client-tools','k268-client-tools').replace('k267-user','k268-user')
    s=s.replace('libcamera=99990.7.2-r15','libcamera=99990.7.2-r19')
    compile(s,name,'exec');(R/name).write_text(s)
print(json.dumps(dict(stage=268,current267_kernel_guard=True,library_r19_required=True,standard_system_paths=True)))
