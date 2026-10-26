from pathlib import Path
import json,os,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes()
out=root/'k209-camera-normal-inspection';out.mkdir(mode=0o700)
dt=Path('/sys/firmware/devicetree/base')
def prop(node,name):
    p=node/name
    if not p.exists():return None
    data=p.read_bytes()
    if name in ['phandle','linux,phandle','regulator-min-microvolt','regulator-max-microvolt']:return int.from_bytes(data,'big')
    return data.rstrip(b'\0').decode(errors='replace').split('\0')
nodes=[]
for file in dt.rglob('compatible'):
    compatible=file.read_bytes().split(b'\0')
    if any(b'cci' in item or b'camss' in item or b'pm8008' in item or b'imx471' in item for item in compatible):
        node=file.parent;nodes.append(dict(path='/'+str(node.relative_to(dt)),compatible=prop(node,'compatible'),status=prop(node,'status'),phandle=prop(node,'phandle')))
rails=[]
for parent in (dt/'soc@0/rsc@18200000').glob('regulators*'):
    for node in parent.iterdir():
        if node.is_dir() and node.name in ['ldo1','smps8']:
            item=dict(path='/'+str(node.relative_to(dt)),parent_compatible=prop(parent,'compatible'),phandle=prop(node,'phandle'),minimum=prop(node,'regulator-min-microvolt'),maximum=prop(node,'regulator-max-microvolt'),runtime=[])
            for reg in Path('/sys/class/regulator').glob('regulator*'):
                if not (reg/'of_node').exists() or (reg/'of_node').resolve()!=node:continue
                values={}
                for name in ['name','state','num_users','microvolts']:
                    try:values[name]=(reg/name).read_text().strip()
                    except OSError as error:values[name]=dict(errno=error.errno)
                item['runtime'].append(values)
            rails.append(item)
modules={name:Path('/sys/module'/Path(name)).exists() for name in ['qcom_camss','i2c_qcom_cci','qcom_pm8008','qcom_pm8008_regulator','imx471','v4l2_cci','samurai_cci_bringup','samurai_front_overlay']}
media={}
for dev in Path('/dev').glob('media*'):
    p=subprocess.run(['media-ctl','-d',str(dev),'-p'],capture_output=True,text=True,timeout=10)
    (out/(dev.name+'-private.txt')).write_text(p.stdout+p.stderr)
    media[dev.name]=dict(exit=p.returncode,imx471_entity_present='imx471' in p.stdout,entities=sum('entity ' in line for line in p.stdout.splitlines()))
report=dict(stage=209,same_current_boot=True,read_only_sysfs_and_media_inspection=True,dt_nodes=nodes,regulator_nodes=rails,modules=modules,media=media,legacy_overlay_firmware_present=Path('/lib/firmware/samurai/k196-front.dtbo').exists(),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
