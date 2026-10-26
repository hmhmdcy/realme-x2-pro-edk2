from pathlib import Path
import json,struct,hashlib
import libfdt,dtschema
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel125/schema-test');k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
raw=(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes();path='/soc@0/camss@acb3000';v=dtschema.DTValidator([str(out/'processed-camss-private.json')])
cells=lambda values:struct.pack('>'+'I'*len(values),*values)
def strict(data):
 node=v.decode_dtb(data)[0]['soc@0']['camss@acb3000'];node['$nodename']=['camss@acb3000'];return list(v.iter_errors(node,filter=['qcom,sm8150-camss']))
def fixture(name,bus,lanes,extra=None,valid=True):
 f=libfdt.Fdt(raw);f.resize(len(raw)+4096);f.setprop(f.path_offset(path),'status',b'okay\0');ports=f.path_offset(path+'/ports')
 f.setprop(ports,'#address-cells',cells([1]));f.setprop(ports,'#size-cells',cells([0]));f.add_subnode(ports,'port@0');port=f.path_offset(path+'/ports/port@0');f.setprop(port,'reg',cells([0]));f.add_subnode(port,'endpoint');ep=f.path_offset(path+'/ports/port@0/endpoint')
 f.setprop(ep,'bus-type',cells([bus]));f.setprop(ep,'data-lanes',cells(lanes))
 for key,value in (extra or {}).items():f.setprop(ep,key,cells(value))
 data=bytes(f.as_bytearray());(out/(name+'.dtb')).write_bytes(data);errors=strict(data);(out/(name+'-strict.txt')).write_text('\n'.join(e.message for e in errors));assert bool(errors)!=valid,(name,[e.message for e in errors][:5]);return dict(name=name,valid=valid,strict_error_count=len(errors))
tests=[]
for n in range(1,4):tests.append(fixture('cphy-valid-'+str(n),1,list(range(n))))
tests.append(fixture('cphy-permuted-abc',1,[2,0],{'line-orders':[0,0]}))
tests.append(fixture('dphy-valid-four-lanes',4,[1,2,3,4],{'clock-lanes':[0]}))
for name,lanes,extra in [('four-trios',[0,1,2,3],None),('invalid-trio',[3],None),('duplicate-trios',[0,0],None),('clock-property',[0],{'clock-lanes':[0]}),('polarity-property',[0],{'lane-polarities':[0,0]}),('line-order-not-abc',[0],{'line-orders':[1]})]:tests.append(fixture('cphy-invalid-'+name,1,lanes,extra,False))
# Resolve the actual rail phandle and compare it with the existing DSI consumer.
f=libfdt.Fdt(raw);n=f.path_offset(path);phy_supply=bytes(f.getprop(n,'vdda-phy-supply'));assert len(phy_supply)==4
rail=f.node_offset_by_phandle(struct.unpack('>I',phy_supply)[0]);assert struct.unpack('>I',f.getprop(rail,'regulator-min-microvolt'))==(1200000,) and struct.unpack('>I',f.getprop(rail,'regulator-max-microvolt'))==(1200000,)
assert f.get_name(rail)=='ldo3'
consumers=[];offset=0;depth=0
while True:
 offset,depth=f.next_node(offset,depth,quiet=libfdt.QUIET_NOTFOUND)
 if offset<0:break
 for key in ['vdda-supply']:
  try:
   if bytes(f.getprop(offset,key))==phy_supply:consumers.append(f.get_path(offset))
  except libfdt.FdtException:pass
assert any('dsi' in name for name in consumers),consumers
report=dict(schema_positive_count=sum(t['valid'] for t in tests),schema_negative_count=sum(not t['valid'] for t in tests),tests=tests,actual_phy_phandle_is_existing_pm8150l_ldo3_1200000=True,actual_dsi_consumer_uses_same_phandle=True,camss_enabled_only_in_private_synthetic_fixtures=True,phone_unchanged=True)
(r/'reference/kernel125/endpoint-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CPHY125_ENDPOINT_SCHEMA_POSITIVE_NEGATIVE_AND_SHARED_RAIL_PASS')
