"""Inspect the existing failed pre-install check, without starting another probe."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k278-negative-support').replace('root.mkdir(mode=0o700);','')
code+=r'''
files={}
for n in ['support-stdout-private.json','support-stderr-private.log','state-private.json']:
 p=root/n;files[n]=dict(exists=p.exists(),text=p.read_text()[-1800:] if p.exists() else None)
print(json.dumps(dict(files=files,current_idle_health=health(),package_versions=subprocess.check_output(['apk','info','-v','libcamera','libcamera-ipa','samurai-camera-config'],text=True))))
'''
q=host.ssh('python3 -',input=code.encode(),check=False,timeout=20);(host.PRIVATE/'negative-state-inspection-private.json').write_bytes(q.stdout+q.stderr);assert q.returncode==0
d=json.loads(q.stdout);print(json.dumps(d,indent=2))
