from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
log=subprocess.check_output(['dmesg'],text=True);r=dict(module_log=(root/'k200-live-prepare-r1/command-3-private.log').read_text(),kernel_vio_messages=[l for l in log.splitlines() if any(w in l.lower() for w in ['samurai-vio','vio-phandle','vio_lookup','vio lookup','samurai_vio'])],regulators=[])
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if (p/'name').exists() and (p/'name').read_text().strip() in ['ldo1','smps8']:
  node=p/'of_node'
  if not node.exists():node=p/'device/of_node'
  r['regulators'].append(dict(of_path=str(node.resolve()),values={n:(p/n).read_text().strip() for n in ['name','state','microvolts','num_users'] if (p/n).exists()}))
r['vio_phandle_present']=Path('/sys/firmware/devicetree/base/soc@0/rsc@18200000/regulators-1/ldo1/phandle').exists()
print(json.dumps(r))
