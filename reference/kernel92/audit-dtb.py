from pathlib import Path
import json, struct
out = Path('/mnt/e/edk2-samurai-out/kernel92')
namespace = {}
exec(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91/verify-firmware.py').read_text().split('\ndt_audit=')[0], namespace)
decode = namespace['fdt_nodes']
before = decode((out/'dtb-before').read_bytes())
after = decode((out/'dtb-connectivity').read_bytes())
before_handles = {v['phandle']:p for p,v in before.items() if 'phandle' in v}
after_handles = {p:v['phandle'] for p,v in after.items() if 'phandle' in v}
references = {'clocks','assigned-clocks','assigned-clock-parents','resets','dmas','phys','interrupt-parent','interrupts-extended','power-domains','interconnects','memory-region','operating-points-v2','nvmem-cells','qcom,qmp','qcom,smem-states','qcom,gmu','qcom,bcm-voters','thermal-sensors','cooling-device','trip','cpu','cpus','cpu-idle-states','next-level-cache','qcom,dsi-phy','qcom,mdp','gpio','gpios','enable-gpio'}
references |= {'iommus','gpio-ranges','wakeup-parent','remote-endpoint','required-opps','io-channels'}
normalized = 0
for path, props in before.items():
    for key, old in list(props.items()):
        new = after[path].get(key)
        if old == new or new is None: continue
        if key in ('phandle','linux,phandle'):
            assert before_handles[old] == path and after_handles[path] == new
            props[key] = new
            normalized += 1
        elif (key in references or key.endswith('-supply') or key.endswith('-gpios') or key.startswith('pinctrl-')) and len(old)==len(new) and len(old)%4==0:
            cells = [old[i:i+4] for i in range(0,len(old),4)]
            converted = [after_handles[before_handles[c]] if c in before_handles and c != new[i*4:i*4+4] else c for i,c in enumerate(cells)]
            # Only accept exact node-reference renumbering; data cells cannot change.
            if b''.join(converted) == new:
                props[key] = new
                normalized += 1
assert not set(before)-set(after)
added = set(after)-set(before)
assert len(added)==4
assert added == {'/soc@0/pinctrl@3100000/samurai-bt-uart-default-state', '/soc@0/pinctrl@3100000/samurai-nfc-irq-default-state', '/soc@0/geniqup@cc0000/serial@c8c000/bluetooth', '/soc@0/geniqup@ac0000/i2c@a84000/nfc@28'}, sorted(added)
changes = {p:sorted(k for k in before[p].keys()|after[p].keys() if before[p].get(k)!=after[p].get(k)) for p in before if before[p]!=after[p]}
allowed = {'/soc@0/dma-controller@a00000':{'status'},'/soc@0/geniqup@ac0000':{'status'},'/soc@0/geniqup@cc0000/serial@c8c000':{'status','pinctrl-names','pinctrl-0'},'/soc@0/geniqup@ac0000/i2c@a84000':{'status','clock-frequency'}}
unexpected = {p:k for p,k in changes.items() if not set(k)<=allowed.get(p,set())}
assert not unexpected,unexpected
nfc = after['/soc@0/geniqup@ac0000/i2c@a84000/nfc@28']
assert struct.unpack('>III',nfc['enable-gpios'])[1:] == (36,0)
assert struct.unpack('>III',nfc['firmware-gpios'])[1:] == (48,0)
assert struct.unpack('>II',nfc['interrupts']) == (47,4)
assert after['/reserved-memory/rmtfs-dynamic'] == before['/reserved-memory/rmtfs-dynamic']
(out/'dtb-validation.json').write_text(json.dumps({'added':sorted(added),'changed':changes,'original_other_nodes_semantically_preserved':True,'phandle_properties_normalized':normalized,'rmtfs_preserved':True,'nfc_ven_gpio':36},indent=2)+'\n')
print('PASS: UART13/NFC9 and wrapper1 only; RMTFS/other DT nodes preserved')
