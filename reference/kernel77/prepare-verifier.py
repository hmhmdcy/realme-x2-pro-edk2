"""Reuse the already audited FV parser, with explicit session77 change scope."""
from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent; out=Path('/mnt/e/edk2-samurai-out/kernel77')
base=(ref.parent/'kernel75/verify-firmware.py').read_text()
ns={}
exec(base.split('\ndt_audit=')[0].replace("'/mnt/e/edk2-samurai-out/kernel75'","'/mnt/e/edk2-samurai-out/kernel77'"),ns)
parse=ns['fdt_nodes']
before=parse((out/'firmware-before.dtb').read_bytes()); after=parse((out/'firmware-after.dtb').read_bytes())
bus='/soc@0/geniqup@cc0000/i2c@c94000'
assert bus in before and bus in after
gauge=bus+'/fuel-gauge@55'
assert set(after)-set(before)=={gauge} and not set(before)-set(after)
changes=[]
for path,props in before.items():
    added=set(after[path])-set(props); removed=set(props)-set(after[path])
    assert not removed
    for name in added:
        assert path==bus and name=='clock-frequency'
        changes.append({'path':path,'property':name,'before':None,'after':after[path][name].hex()})
    for name,value in props.items():
        if value!=after[path][name]: changes.append({'path':path,'property':name,'before':value.hex(),'after':after[path][name].hex()})
assert {c['property'] for c in changes}=={'status','clock-frequency'} and len(changes)==2
assert all(c['path']==bus for c in changes)
assert after[bus]['status']==b'okay\0' and after[bus]['clock-frequency']==(100000).to_bytes(4,'big')
assert after[gauge]=={'compatible':b'ti,bq28z610\0','reg':(0x55).to_bytes(4,'big')}
dt={'only_i2c15_status_frequency_and_gauge_added':True,'changed_properties':changes,
    'added_node':gauge,'added_properties':{p:v.hex() for p,v in after[gauge].items()},
    'charger_nodes_absent':not any('mp2650' in p or 'mp2650' in str(v) for p,v in after.items())}
assert dt['charger_nodes_absent']
(out/'dtb-validation.json').write_text(json.dumps(dt,indent=2)+'\n')
script=base.replace('kernel75','kernel77').replace('boot-k75-gpu.img','boot-k77-gauge.img')
script=script.replace("version_before='bd23aaa'","version_before='20a1d60'").replace("version_after='20a1d60'","version_after='136157b'")
script=script.replace('gpu_gmu_status_and_board_zap_path','i2c15_readonly_bq28z610')
(ref/'verify-firmware.py').write_text(script)
subprocess.run(['python3',str(ref/'verify-firmware.py')],check=True,stdout=(out/'firmware-audit.txt').open('w'))
k=Path('/home/cy122/x2pro-linux/linux'); init=Path('/home/cy122/x2pro-linux/initramfs')
source=json.loads((ref/'sources-before.json').read_text())
preserved={}
for name,digest in source.items():
    if name.endswith('sm8150-samurai.dts'):continue
    p=init/('init' if name=='init' else 'usr/sbin/samurai-usb') if name in ('init','samurai-usb') else k/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
    preserved[name]=digest
assert (k/'.config').read_bytes()==(out/'config-before').read_bytes()
assert hashlib.sha256((k/'arch/arm64/boot/Image').read_bytes()).hexdigest()=='f90e6807bad34db3f3c88206ec952b0de78775272e407eb525ea2440ded476bb'
assert hashlib.sha256((out/'logdump-before.img').read_bytes()).hexdigest()=='607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0'
report={'kernel_image_config_and_logdump_unchanged':True,'preserved_sources':preserved,
        'only_boot_update_required':True,'firmware_audit_pass':True,'dtb_audit':dt}
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: gauge-only DTB, firmware/Android FV/FFS checks, unchanged Image/config/logdump and preserved core sources.')
