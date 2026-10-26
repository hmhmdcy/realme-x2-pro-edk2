from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,struct
root=Path('/sys/firmware/devicetree/base/soc@0')
out={}
for name in ['camss@acb3000','clock-controller@ad00000','iommu@15000000']:
 p=root/name; d={}
 for prop in ['phandle','compatible','power-domain-names','interconnect-names']:
  f=p/prop
  if f.exists():d[prop]=struct.unpack('>I',f.read_bytes())[0] if prop=='phandle' else f.read_bytes().replace(b'\0',b',').decode()
 out[name]=d
out['boot_matches']=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
out['clocks']=[l.strip() for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines() if any(x in l for x in ['cam_cc_icp','cam_cc_bps','cam_cc_ipe','cam_cc_fast_ahb'])]
out['camss_runtime']={n:(Path('/sys/bus/platform/devices/acb3000.camss/power')/n).read_text().strip() for n in ['runtime_status','runtime_usage'] if (Path('/sys/bus/platform/devices/acb3000.camss/power')/n).exists()}
print(json.dumps(out))
'''
r=host.raw_ssh('python3 -',input=code.encode(),timeout=25)
if r.returncode:raise RuntimeError(r.stderr.decode())
d=json.loads(r.stdout);(host.PRIVATE/'resource-prerequisites-private.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
