from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
expected={n:'99990.7.2-r29' for n in ['libcamera','libcamera-gstreamer','libcamera-ipa','libcamera-tools','libcamera-v4l2']}|{n:'0.1.0-r24' for n in ['samurai-camera-config','samurai-camera-stack']}
code=r"""from pathlib import Path
import json
names=NAMES;result={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if fields.get('P') in names:result[fields['P']]=fields['V']
print(json.dumps(result))
""".replace('NAMES',repr(set(expected)))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout);assert d==expected
report=dict(stage=390,only_expected_camera_package_versions_queried=True,packages=d,libcamera_ipe_candidate_not_permanently_installed=True,passed=True)
(HERE/'installed-packages-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=HERE/'current-state-validation.json';s=json.loads(p.read_text());s['camera_package_versions']=d;p.write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(report,indent=2))
