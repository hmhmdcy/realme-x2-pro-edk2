"""Reuse the established four-camera test with the new boot and dynamic I2C identity."""
from pathlib import Path
import ast,json

ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel273/regress-four-cameras.py').read_text()
prefix=s[s.index('text='):s.index('exec(compile')]
ns=dict(R=ROOT.parent/'kernel273');exec(compile(prefix,'resolve-tested-four-camera-template','exec'),ns)
text=ns['text']
node=next(n for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
native=ast.literal_eval(node.value).replace('k273','k288').replace('stage=273','stage=288')
start=native.index('def runtime():')
end=native.index('\ndef rails():',start)
native=native[:start]+'''def runtime():
 result={}
 for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
  found=[p for p in Path('/sys/bus/i2c/drivers',driver).glob('*') if p.is_symlink() and re.fullmatch(r'\\d+-[0-9a-f]{4}',p.name)]
  assert len(found)==1,driver
  result[driver]=(found[0]/'power/runtime_status').read_text().strip()
 return result
'''+native[end:]
native=native.replace("root.mkdir(mode=0o700)","assert not root.exists();root.mkdir(mode=0o700)")
native=native.replace("state=dict(state='preflight',terminal=False,pid=os.getpid(),runs=[])","state=dict(stage=288,state='preflight',terminal=False,pid=os.getpid(),runs=[])")
compile(native,'native-four-camera-regression.py','exec')
(ROOT/'native-four-camera-regression.py').write_text(native)
print('Prepared the established 18-leg physical-camera regression for boot288.')
