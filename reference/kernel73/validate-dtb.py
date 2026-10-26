from pathlib import Path
import hashlib, json, struct, runpy

root = Path('/mnt/e/edk2-samurai-out/kernel73')
def fdt_nodes(b):
    assert b[:4] == bytes.fromhex('d00dfeed')
    total, off, strings = struct.unpack_from('>III', b, 4)
    assert total == len(b)
    stack, result = [], {}
    align = lambda n:(n+3)//4*4
    while True:
        token = struct.unpack_from('>I',b,off)[0]
        off += 4
        if token == 1:
            end=b.index(0,off)
            stack.append(b[off:end].decode())
            off=align(end+1)
            result['/'.join(stack) or '/']={}
        elif token == 2:
            stack.pop()
        elif token == 3:
            size,index=struct.unpack_from('>II',b,off)
            off+=8
            end=b.index(0,strings+index)
            name=b[strings+index:end].decode()
            result['/'.join(stack) or '/'][name]=b[off:off+size]
            off=align(off+size)
        elif token == 4:
            pass
        else:
            assert token == 9
            break
    return result

before=fdt_nodes((root/'firmware-before.dtb').read_bytes())
after=fdt_nodes((root/'firmware-after.dtb').read_bytes())
canonical=runpy.run_path(str(Path(__file__).with_name('dtb-canonical.py')))['canonical']
ac,bc=canonical(before),canonical(after)
mdss='/soc@0/display-subsystem@ae00000'
assert mdss in after, [p for p in after if 'display-subsystem' in p]
allowed={mdss:{'status'},mdss+'/dsi@ae94000':{'status','vdda-supply','pinctrl-names','pinctrl-0'},
         mdss+'/dsi@ae94000/ports/port@1/endpoint':{'remote-endpoint','data-lanes','phandle'},
         mdss+'/phy@ae94400':{'status','vdds-supply'},
         '/soc@0/rsc@18200000/regulators-0/ldo14':{'regulator-min-microvolt','regulator-max-microvolt'}}
added=[]
changed=[]
for p,props in ac.items():
    assert p in bc, ('deleted node',p)
    for k in props.keys() | bc[p].keys():
        if props.get(k)!=bc[p].get(k):
            assert k in allowed.get(p,set()), ('unexpected change',p,k)
            changed.append([p,k,props.get(k),bc[p].get(k)])
for p in after.keys()-before.keys():
    assert p.startswith(mdss+'/dsi@ae94000/panel@0') or p in (
        '/soc@0/pinctrl@3100000/display-reset-default-state',
        '/soc@0/pinctrl@3100000/display-power-default-state',
        '/soc@0/pinctrl@3100000/display-te-default-state'), p
    added.append(p)
cells=lambda b:struct.unpack('>'+'I'*(len(b)//4),b)
byph={cells(v['phandle'])[0]:p for p,v in after.items() if 'phandle' in v}
for p,props in before.items():
    for k in ('remote-endpoint','memory-region','power-domains','iommus'):
        if k in props and p not in allowed:
            # Resolve the first reference before and after renumbering phandles.
            oldbyph={cells(v['phandle'])[0]:q for q,v in before.items() if 'phandle' in v}
            assert oldbyph.get(cells(props[k])[0]) == byph.get(cells(after[p][k])[0]), (p,k)
panel=after[mdss+'/dsi@ae94000/panel@0']
assert panel['compatible']==b'samsung,sofef03f-m\0'
for name,pin,flag in [('reset-gpios',6,1),('vci-enable-gpios',25,0),('vddd-enable-gpios',152,0)]:
    ph,gpio,polarity=cells(panel[name])
    assert byph[ph]=='/soc@0/pinctrl@3100000' and (gpio,polarity)==(pin,flag)
report={'only_native_display_changes':True,'added_nodes':sorted(added),'changed_properties':changed,
        'gpio_wiring_checked':True,'core_nodes_preserved':True}
(root/'dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
