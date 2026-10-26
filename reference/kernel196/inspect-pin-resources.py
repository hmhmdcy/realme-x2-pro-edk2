from pathlib import Path
import json,struct
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k196-baseline/boot-id-private.txt').read_bytes()
p=Path('/sys/firmware/devicetree/base/soc@0/pinctrl@3100000');names=(p/'reg-names').read_bytes().decode().strip('\0').split('\0');cells=struct.unpack('>'+str(len((p/'reg').read_bytes())//4)+'I',(p/'reg').read_bytes());regions=[dict(name=n,address=(cells[4*i]<<32)|cells[4*i+1],size=(cells[4*i+2]<<32)|cells[4*i+3]) for i,n in enumerate(names)]
print(json.dumps(dict(regions=regions,devmem_exists=Path('/dev/mem').exists())))
