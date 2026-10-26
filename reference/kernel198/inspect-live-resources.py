from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k198-baseline/boot-id-private.txt').read_bytes()
root=Path('/sys/firmware/devicetree/base');paths=dict(tlmm='soc@0/pinctrl@3100000',camcc='soc@0/clock-controller@ad00000',pm8150l_gpio='soc@0/spmi@c440000/pmic@4/gpio@c000',s8c='soc@0/rsc@18200000/regulators-1/smps8')
nodes={n:dict(path='/'+p,phandle=int.from_bytes((root/p/'phandle').read_bytes(),'big')) for n,p in paths.items()}
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines();selected=[l.strip() for l in clocks if 'cam_cc_mclk2_clk ' in l];assert len(selected)==1
r=dict(stage=198,nodes=nodes,mclk2=selected[0],vio_phandle_absent=not (root/'soc@0/rsc@18200000/regulators-1/ldo1/phandle').exists(),cci1_status=(root/'soc@0/cci@ac4b000/status').read_bytes().decode().strip('\0'))
Path('/var/lib/samurai/k198-baseline/resources.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
