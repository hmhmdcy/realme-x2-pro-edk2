from pathlib import Path
import json,os
out=Path('/var/lib/samurai/k192-camera-inventory');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
adapters=[]
for p in Path('/sys/bus/i2c/devices').glob('i2c-*'):
 of=p/'of_node'
 if not of.exists():of=p/'device/of_node'
 number=p.name.split('-')[1]
 adapters.append(dict(bus=p.name,name=(p/'name').read_text().strip(),of_path=str(of.resolve()) if of.exists() else None,
  clients=[dict(name=c.name,driver=(c/'driver').resolve().name if (c/'driver').exists() else None) for c in Path('/sys/bus/i2c/devices').glob(number+'-*')]))
rails=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if not (p/'name').exists():continue
 name=(p/'name').read_text().strip()
 if 's8c' not in name.lower():continue
 values={}
 for attr in ['state','microvolts','num_users','status','type']:
  try:values[attr]=(p/attr).read_text().strip()
  except (FileNotFoundError,OSError):pass
 rails.append(dict(name=name,sysfs=p.name,values=values))
gpio=[]
for p in Path('/sys/bus/gpio/devices').glob('gpiochip*'):
 attrs={}
 for name in ['label','base','ngpio']:
  if (p/name).exists():attrs[name]=(p/name).read_text().strip()
 gpio.append(dict(chip=p.name,attrs=attrs,of_path=str((p/'of_node').resolve()) if (p/'of_node').exists() else None))
report=dict(stage=192,adapters=adapters,s8c_regulators=rails,gpiochips=gpio,device_nodes=[p.name for p in Path('/dev').glob('gpiochip*')]+[p.name for p in Path('/dev').glob('i2c-*')])
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
