"""Offline field-only migration of the current frozen 501 SDP/CDP profile."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/icon-capture-image501-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
delivery=json.loads((OLD/'delivery.json').read_bytes())
assert delivery['files']['launcher.py']['sha256']=='4ae42851fe59748dc259578559846e760cae27c41ab5e7c5df4e586cf800dec5'
for n,row in delivery['files'].items():assert sha((OLD/n).read_bytes())==row['sha256'],n

def migrate(text):
 return (text.replace('Image501','Image502').replace('image501','image502')
  .replace('image502-activation/image502-gauge-live-001','image502-notify-activation/image502-notify-live-001')
  .replace('/var/lib/samurai/image502-gauge-live-001-adopted/','/var/lib/samurai/image502-notify-live-001-adopted/')
  .replace('samurai-image502-postboot-readonly-v1','samurai-image502-notify-postboot-readonly-v1')
  .replace("startswith('#501 ')","startswith('#502 ')")
  .replace('7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9','ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'))

for n in ['worker.py','audit.py','baseline-test-result.json']:(HERE/n).write_bytes((OLD/n).read_bytes())
for n in ['capture-entry.py','transport.py','bind-identity.py']:
 raw=(OLD/n).read_bytes();text=raw.decode()
 (HERE/n).write_bytes(migrate(text).encode())
old_entry=sha((OLD/'capture-entry.py').read_bytes());new_entry=sha((HERE/'capture-entry.py').read_bytes())
launcher=migrate((OLD/'launcher.py').read_text()).replace(old_entry,new_entry)
(HERE/'launcher.py').write_text(launcher)
for n in ['launcher.py','capture-entry.py','transport.py','bind-identity.py']:
 ast.parse((HERE/n).read_bytes())
 patch=''.join(difflib.unified_diff((OLD/n).read_text().splitlines(True),(HERE/n).read_text().splitlines(True),fromfile='501/'+n,tofile='502/'+n))
 (HERE/(n+'.patch')).write_text(patch)
pins={n:{'path':str(OLD/n),'sha256':sha((OLD/n).read_bytes())} for n in ['delivery.json','launcher.py','capture-entry.py','transport.py','bind-identity.py','worker.py','audit.py','baseline-test-result.json','template-test-result.json']}
(HERE/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'derived':True,'runtime_pins_generated':False,'device_network_accessed':False}))
