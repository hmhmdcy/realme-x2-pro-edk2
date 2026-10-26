"""Prepare existing guarded DT/FV build and verification for the bus-only change."""
from pathlib import Path
import hashlib
import json
import subprocess

ref = Path(__file__).resolve().parent
old = ref.parent/'kernel77'
out = Path('/mnt/e/edk2-samurai-out/kernel79')
(ref/'build-dtb.sh').write_text((old/'build-dtb.sh').read_text().replace('kernel77','kernel79'))
s = (old/'build-firmware.sh').read_text().replace('kernel77','kernel79').replace('k77-gauge','k79-bus')
s = s.replace('136157ba0375d7af92e98896008a8566230c8214','3dd07f48513c3c1b949dd8d911bb0bf7c84f7c96')
(ref/'build-firmware.sh').write_text(s)
s = (old/'verify-firmware.py').read_text().replace('kernel77','kernel79').replace('k77-gauge','k79-bus')
s = s.replace("version_before='20a1d60'", "version_before='136157b'")
s = s.replace("version_after='136157b'", "version_after='3dd07f4'")
s = s.replace('i2c15_readonly_bq28z610','i2c1_adapter_only')
(ref/'verify-firmware.py').write_text(s)
base = s.split('\ndt_audit=')[0]
ns = {}
exec(base, ns)
parse = ns['fdt_nodes']
before = parse((out/'firmware-before.dtb').read_bytes())
after = parse((out/'firmware-after.dtb').read_bytes())
assert before.keys() == after.keys(), 'No new clients or nodes permitted'
changes = []
expected = {('/soc@0/dma-controller@800000','status'),
            ('/soc@0/geniqup@8c0000','status'),
            ('/soc@0/geniqup@8c0000/i2c@884000','status'),
            ('/soc@0/geniqup@8c0000/i2c@884000','clock-frequency')}
for path, props in before.items():
    assert not (props.keys()-after[path].keys())
    for name in props.keys() | after[path].keys():
        a, b = props.get(name), after[path].get(name)
        if a != b:
            assert (path,name) in expected, (path,name)
            assert b == (400000).to_bytes(4,'big') if name == 'clock-frequency' else b == b'okay\0'
            changes.append({'path':path,'property':name,'before':None if a is None else a.hex(),'after':b.hex()})
assert {(c['path'],c['property']) for c in changes} == expected
assert not any('mp2650' in p or 'mp2650' in str(v) for p,v in after.items())
bus = '/soc@0/geniqup@8c0000/i2c@884000'
assert not any(p.startswith(bus+'/') for p in after)
dt = {'only_gpi0_qup0_i2c1_enabled_and_400khz':True,'changed_properties':changes,
      'no_new_nodes_or_clients':True,'mp2650_client_absent':True,
      'gauge_display_gpu_pmic_properties_unchanged':True}
(out/'dtb-validation.json').write_text(json.dumps(dt,indent=2)+'\n')
subprocess.run(['python3',str(ref/'verify-firmware.py')],check=True,stdout=(out/'firmware-audit.txt').open('w'))
k = Path('/home/cy122/x2pro-linux/linux')
init = Path('/home/cy122/x2pro-linux/initramfs')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
preserved = {}
for name,digest in json.loads((ref/'sources-before.json').read_text()).items():
    if name.endswith('sm8150-samurai.dts'): continue
    p = init/('init' if name == 'init' else 'usr/sbin/samurai-usb') if name in ('init','samurai-usb') else k/name
    assert sha(p) == digest, name
    preserved[name] = digest
assert (k/'.config').read_bytes() == (out/'config-before').read_bytes()
assert sha(k/'arch/arm64/boot/Image') == 'f90e6807bad34db3f3c88206ec952b0de78775272e407eb525ea2440ded476bb'
assert sha(out/'logdump-before.img') == '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0'
report = {'only_boot_update_required':True,'kernel_image_config_and_logdump_unchanged':True,
          'preserved_sources':preserved,'dtb_audit':dt,'firmware_audit_pass':True}
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: exact four bus properties only, no charger child; Image/config/logdump and core sources preserved.')
