import struct
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
