from pathlib import Path
import json,os
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k194-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
mods={n:Path('/sys/module/'+n).exists() for n in ['qcom_pm8008','qcom_pm8008_regulator','v4l2_cci','imx471','samurai_cci_bringup','samurai_front_identify']}
dt=Path('/sys/firmware/devicetree/base');names=['/soc@0/geniqup@8c0000/i2c@890000','/soc@0/rsc@18200000/regulators-1/smps8']
nodes={n:dict(exists=(dt/n.lstrip('/')).exists(),phandle=int.from_bytes((dt/n.lstrip('/')/'phandle').read_bytes(),'big') if (dt/n.lstrip('/')/'phandle').exists() else None) for n in names}
chips=[]
for p in Path('/sys/bus/gpio/devices').glob('gpiochip*'):
 if (p/'of_node').exists() and str((p/'of_node').resolve()).endswith('/pmic@4/gpio@c000'):
  node=(p/'of_node').resolve();chips.append(dict(node=str(node).split('/base')[-1],phandle=int.from_bytes((node/'phandle').read_bytes(),'big')))
print(json.dumps(dict(modules=mods,nodes=nodes,pm8150l_gpio=chips,adapter_node=str((Path('/sys/bus/i2c/devices/i2c-1/of_node')).resolve()).split('/base')[-1],taint=Path('/proc/sys/kernel/tainted').read_text().strip())))
