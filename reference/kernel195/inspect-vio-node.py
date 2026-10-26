from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k195-baseline/boot-id-private.txt').read_bytes()
root=Path('/sys/firmware/devicetree/base');p=root/'soc@0/rsc@18200000/regulators-1/ldo1'
reg=[r for r in Path('/sys/class/regulator').glob('regulator.*') if (r/'of_node').exists() and (r/'of_node').resolve()==p]
assert len(reg)==1 and not (p/'phandle').exists() and not any(v.is_dir() for v in p.iterdir())
q=reg[0];values={n:(q/n).read_text().strip() for n in ['state','microvolts','num_users']};assert values==dict(state='disabled',microvolts='1800000',num_users='0')
print(json.dumps(dict(node=str(p).split('/base')[-1],properties=[v.name for v in p.iterdir()],name_property=(p/'name').read_bytes().decode().strip('\0') if (p/'name').exists() else None,compatible_present=(p/'compatible').exists(),phandle_absent=True,regulator=values,max_phandle=max(int.from_bytes(v.read_bytes(),'big') for v in root.rglob('phandle')))))
