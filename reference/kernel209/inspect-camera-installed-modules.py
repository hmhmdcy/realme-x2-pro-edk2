from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes()
result={}
for name in ['imx471','v4l2-cci','qcom-pm8008','qcom-pm8008-regulator','i2c-qcom-cci']:
    p=subprocess.run(['modinfo','-n',name],capture_output=True,text=True,timeout=5)
    item=dict(installed=p.returncode==0)
    if p.returncode==0:
        path=Path(p.stdout.strip());item.update(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    result[name]=item
print(json.dumps(dict(stage=209,read_only_module_inventory=True,modules=result)))
