from pathlib import Path
import json, struct
root=Path(__file__).resolve().parent
align=lambda n,a:(n+a-1)//a*a
def fdt_nodes(b):
    assert b[:4] == bytes.fromhex('d00dfeed')
    total, off, strings = struct.unpack_from('>III', b, 4)
    assert total == len(b)
    stack, result = [], {}
    while True:
        token = struct.unpack_from('>I', b, off)[0]
        off += 4
        if token == 1:
            end=b.index(0, off)
            stack.append(b[off:end].decode())
            off=align(end+1,4)
            path='/'.join(stack) or '/'
            assert path not in result
            result[path]={}
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, nameoff = struct.unpack_from('>II', b, off)
            off += 8
            end=b.index(0,strings+nameoff)
            name=b[strings+nameoff:end].decode()
            path='/'.join(stack) or '/'
            assert name not in result[path]
            result[path][name]=b[off:off+size]
            off=align(off+size,4)
        elif token == 4:
            pass
        elif token == 9:
            assert not stack
            return result
        else:
            raise AssertionError(token)

parse=fdt_nodes
a=parse((root/'samurai-before.dtb').read_bytes())
b=parse((root/'samurai-after.dtb').read_bytes())
def cells(v): return list(struct.unpack('>'+'I'*(len(v)//4),v))
def canonical(nodes):
 refs={cells(v['phandle'])[0]:p for p,v in nodes.items() if 'phandle' in v}
 lists={'clocks':'#clock-cells','assigned-clocks':'#clock-cells',
 'assigned-clock-parents':'#clock-cells','resets':'#reset-cells',
 'dmas':'#dma-cells','phys':'#phy-cells','power-domains':'#power-domain-cells',
 'interconnects':'#interconnect-cells','iommus':'#iommu-cells',
 'interrupts-extended':'#interrupt-cells','thermal-sensors':'#thermal-sensor-cells',
 'io-channels':'#io-channel-cells','cooling-device':'#cooling-cells',
 'qcom,smem-states':'#qcom,smem-state-cells'}
 singles={'interrupt-parent','remote-endpoint','trip','operating-points-v2',
 'required-opps','memory-region','nvmem-cells','qcom,bcm-voters','qcom,gmu',
 'qcom,qmp','wakeup-parent'}
 result={}
 for path,props in nodes.items():
  result[path]={}
  for key,v in props.items():
   if key in ('phandle','linux,phandle'): continue
   typ=lists.get(key)
   if key in ('gpio','gpios') or key.endswith('-gpios') or key.endswith('-gpio'): typ='#gpio-cells'
   if typ or key=='gpio-ranges':
    values=cells(v); decoded=[]; i=0
    while i<len(values):
     if values[i]==0:
      decoded.append(0);i+=1;continue
     provider=refs[values[i]]
     n=3 if key=='gpio-ranges' else cells(nodes[provider][typ])[0]
     assert i+1+n<=len(values),(path,key)
     decoded.append([provider,values[i+1:i+1+n]])
     i+=1+n
    result[path][key]=decoded
   elif key in singles or key.endswith('-supply') or key.startswith('pinctrl-') and key[8:].isdigit():
    result[path][key]=[refs[x] for x in cells(v)]
   else: result[path][key]=v.hex()
 return result
ac,bc=canonical(a),canonical(b)
added=sorted(bc.keys()-ac.keys())
expected=[
 '/regulator-touch-1p8',
 '/soc@0/geniqup@cc0000/i2c@c80000/touchscreen@20',
 '/soc@0/geniqup@cc0000/i2c@c80000/touchscreen@20/rmi4-f12@12',
 '/soc@0/pinctrl@3100000/touch-irq-default-state',
 '/soc@0/pinctrl@3100000/touch-reset-default-state',
 '/soc@0/spmi@c440000/pmic@4/gpio@c000/touch-vio-enable-default-state']
assert added==sorted(expected),(added,expected)
assert not ac.keys()-bc.keys()
changes=[]
for path in sorted(ac):
 for key in sorted(ac[path].keys()|bc[path].keys()):
  if ac[path].get(key)!=bc[path].get(key):
   changes.append(dict(path=path,property=key,before=ac[path].get(key),after=bc[path].get(key)))
allowed={('/soc@0/dma-controller@c00000','status'),
 ('/soc@0/geniqup@cc0000','status'),('/soc@0/geniqup@cc0000/i2c@c80000','status'),
 ('/soc@0/rsc@18200000/regulators-0/ldo17','regulator-min-microvolt'),
 ('/soc@0/rsc@18200000/regulators-0/ldo17','regulator-max-microvolt')}
assert {(c['path'],c['property']) for c in changes}==allowed,changes
for c in changes:
 if c['property']=='status': assert c['before']=='64697361626c656400' and c['after']=='6f6b617900'
 else: assert c['after']==struct.pack('>I',3000000).hex()
touch=bc[expected[1]]
assert touch['interrupts']==struct.pack('>II',122,8).hex()
assert touch['reset-gpios']==[['/soc@0/pinctrl@3100000',[54,1]]]
assert touch['syna,startup-delay-ms']==struct.pack('>I',80).hex()
assert touch['syna,reset-delay-ms']==struct.pack('>I',80).hex()
assert bc['/regulator-touch-1p8']['gpio']==[['/soc@0/spmi@c440000/pmic@4/gpio@c000',[5,0]]]
assert 'enable-active-high' in bc['/regulator-touch-1p8']
report=dict(semantic_dtb_changes=changes,added_nodes=added,phandles_resolved_to_paths=True,
            all_other_properties_unchanged=True,removed_nodes=[])
(root/'dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
