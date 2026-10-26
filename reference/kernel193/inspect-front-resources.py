from pathlib import Path
import json,os
os.umask(0o077);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k193-baseline/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k193-front-resources-r2');out.mkdir(mode=0o700);r={}
root=Path('/sys/firmware/devicetree/base')
for name,path in dict(tlmm='soc@0/pinctrl@3100000',camcc='soc@0/clock-controller@ad00000',vio='soc@0/rsc@18200000/regulators-1/ldo1',nldo='soc@0/rsc@18200000/regulators-1/smps8').items():
 p=root/path;assert p.is_dir(),path;r[name]=dict(path=path,phandle=int.from_bytes((p/'phandle').read_bytes(),'big') if (p/'phandle').is_file() else None,props={n:(p/n).read_bytes().hex() for n in ['regulator-min-microvolt','regulator-max-microvolt','qcom,pmic-id','#clock-cells'] if (p/n).is_file()})
pin={}
for name in ['pinconf-pins','pinmux-pins','pingroups','pinmux-functions']:
 p=Path('/sys/kernel/debug/pinctrl/3100000.pinctrl')/name
 if p.is_file():
  lines=p.read_text().splitlines();(out/(name+'-private.txt')).write_text('\n'.join(lines))
  pin[name]=[s for s in lines if s.startswith(('pin 12 ','pin 15 ','pin 29 ')) or 'cam_mclk' in s]
r['pins']=pin;(out/'summary.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
