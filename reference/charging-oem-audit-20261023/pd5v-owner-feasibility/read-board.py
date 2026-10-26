"""Exact cached native DTB supply sharing/role prerequisites, no device."""
from pathlib import Path
import ast,hashlib,json,struct
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
path=REF/'kernel93/verify-firmware.py';source=path.read_text()
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='fdt_nodes')
env={'struct':struct,'align':lambda n,a:(n+a-1)//a*a}
exec(compile(ast.Module(body=[node],type_ignores=[]),'original-FDT-reader','exec'),env)
dtb=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-dt/samurai-charging-usb-private.dtb')
raw=dtb.read_bytes();assert hashlib.sha256(raw).hexdigest()=='c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503'
nodes=env['fdt_nodes'](raw)
phandles={int.from_bytes(v['phandle'],'big'):p for p,v in nodes.items() if 'phandle' in v}
phy=next(p for p,v in nodes.items() if b'qcom,sm8150-usb-hs-phy\0' in v.get('compatible',b''))
supplies={k:{'phandle':int.from_bytes(v,'big'),'provider':phandles.get(int.from_bytes(v,'big'))} for k,v in nodes[phy].items() if k.endswith('-supply')}
providers={x['provider'] for x in supplies.values() if x['provider']}
consumers=[]
for p,v in nodes.items():
 for name,value in v.items():
  if name.endswith('-supply') and len(value)==4 and phandles.get(int.from_bytes(value,'big')) in providers:
   consumers.append(dict(node=p,supply=name,provider=phandles[int.from_bytes(value,'big')]))
result=dict(dtb_sha256=hashlib.sha256(raw).hexdigest(),usb2_phy=phy,supplies=supplies,
 provider_properties={p:{k:v.hex() for k,v in nodes[p].items()} for p in providers},
 supply_consumers=consumers,typec_nodes={p:{k:v.hex() for k,v in v.items()} for p,v in nodes.items() if p.endswith('/typec@1500')},
 other_pd_tcpc_compatible_nodes={p:{k:v.hex() for k,v in v.items() if k in ('compatible','status','reg')} for p,v in nodes.items() if any(x in v.get('compatible',b'') for x in (b'pdphy',b'tcpci',b'tcpc',b'fusb302',b'usbpd'))},
 pmic_parent={k:v.hex() for k,v in nodes['/soc@0/spmi@c440000/pmic@2'].items() if k in ('compatible','reg','status')},
 device_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'board-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(usb2_phy=phy,supplies=supplies),indent=2))
