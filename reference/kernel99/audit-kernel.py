from pathlib import Path
import hashlib, json, re, subprocess, struct

out = Path('/mnt/e/edk2-samurai-out/kernel99')
root = Path('/mnt/e/RealmeX2Pro edk2')
namespace = {}
exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0], namespace)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(), namespace)
decode, canonical = namespace['fdt_nodes'], namespace['canonical']
old = canonical(decode((out/'dtb-before').read_bytes()))
new = canonical(decode((out/'dtb-haptics').read_bytes()))
bus = '/soc@0/geniqup@8c0000/i2c@89c000'
node = bus+'/haptics@5a'
pins = '/soc@0/pinctrl@3100000'
added = set(new)-set(old)
assert not set(old)-set(new)
assert added == {node,pins+'/haptics-reset-default-state',pins+'/haptics-irq-default-state'}
changed = {p:sorted(k for k in old[p].keys()|new[p].keys() if old[p].get(k)!=new[p].get(k)) for p in old if old[p]!=new[p]}
assert changed == {bus:['clock-frequency','status']}, changed
assert new[bus]['status'] == b'okay\0'.hex()
assert new[bus]['clock-frequency'] == struct.pack('>I',400000).hex()
assert new[node]['compatible'] == b'realme,samurai-aw8697\0awinic,aw8697\0'.hex()
assert new[node]['reg'] == struct.pack('>I',0x5a).hex()
assert new[node]['reset-gpios'] == [[pins,[116,1]]]
assert new[node]['interrupt-parent'] == [pins]
assert new[node]['interrupts'] == struct.pack('>II',24,2).hex()
assert new[node]['pinctrl-0'] == [pins+'/haptics-reset-default-state',pins+'/haptics-irq-default-state']
assert new[pins+'/haptics-reset-default-state']['pins'] == b'gpio116\0'.hex()
assert new[pins+'/haptics-reset-default-state']['output-low'] == ''
assert new[pins+'/haptics-irq-default-state']['pins'] == b'gpio24\0'.hex()
assert new[pins+'/haptics-irq-default-state']['input-enable'] == ''

def config(path):
    result = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r'(CONFIG_\w+)=(.+)',line)
        if match:
            result[match[1]] = match[2]
        match = re.fullmatch(r'# (CONFIG_\w+) is not set',line)
        if match:
            result[match[1]] = 'n'
    return result
before, after = config(out/'config-before'), config(out/'config-after')
delta = {key:[before.get(key),after.get(key)] for key in before.keys()|after.keys() if before.get(key)!=after.get(key)}
assert delta == {'CONFIG_INPUT_SAMURAI_AW8697':[None,'y'],'CONFIG_INPUT_FF_MEMLESS':['m','y']},delta
assert (out/'cpio-before').read_bytes() == (out/'cpio-after').read_bytes()
assert (root/'linux-port/dts/sm8150-samurai.dts').read_bytes() == (out/'workspace-dts-mirror-before').read_bytes()
source = (root/'reference/kernel99/aw8697-samurai.c').read_bytes()
assert source == Path('/home/cy122/x2pro-linux/linux/drivers/input/misc/aw8697-samurai.c').read_bytes()
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(kernel_audit_pass=True,kernel_build=98,logical_stage=99,
    config_only_changed=delta,cpio_byte_identical=True,init_and_modules_preserved=True,
    dtb_added_nodes=sorted(added),dtb_changed_properties=changed,other_dtb_nodes_semantically_preserved=True,
    workspace_old_dts_mirror_preserved=True,firmware_embedded_dtb_rebuild_required=True,
    driver_source_sha256=hashlib.sha256(source).hexdigest(),
    image_sha256=sha(out/'Image-haptics'),dtb_sha256=sha(out/'dtb-haptics'),cpio_sha256=sha(out/'cpio-after'),
    hardware_tested=False,physical_vibration_confirmed=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
