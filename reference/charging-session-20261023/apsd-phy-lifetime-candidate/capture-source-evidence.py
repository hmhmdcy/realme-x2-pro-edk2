"""Read fixed cached Image-linked source only; no mounted_build or mutation."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
S=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01/source354')
spans={
 'drivers/base/dd.c':[(593,608),(610,632),(732,747),(1315,1360)],
 'drivers/base/devres.c':[(479,549),(552,577)],
 'drivers/base/power/main.c':[(2199,2260)],
 'drivers/base/power/runtime.c':[(374,429),(1216,1265),(1416,1463),(1512,1550),(1617,1635)],
 'include/linux/pm_runtime.h':[(118,137),(537,554),(573,603)],
 'drivers/phy/phy-core.c':[(270,340),(688,735),(803,816)],
 'include/linux/device.h':[(1102,1120)],
 'include/linux/device/devres.h':[(169,182)],
}
out={}
for f,ranges in spans.items():
 data=(S/f).read_bytes();ls=data.decode().splitlines()
 out[f]=dict(sha256=hashlib.sha256(data).hexdigest(),lines=[dict(line=i,text=ls[i-1]) for a,b in ranges for i in range(a,b+1)])
(H/'lifecycle-source-evidence.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(files=len(out),sha256=hashlib.sha256((H/'lifecycle-source-evidence.json').read_bytes()).hexdigest())))
