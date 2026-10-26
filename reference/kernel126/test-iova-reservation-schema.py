from pathlib import Path
import json,struct,hashlib
import libfdt,dtschema
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel126/schema-test');k=Path('/home/cy122/pmos-samurai-build126/kernel');raw=(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes();v=dtschema.DTValidator([str(out/'processed-camss-private.json')]);f=libfdt.Fdt(raw);camss=f.path_offset('/soc@0/camss@acb3000');node=f.path_offset('/reserved-memory/reservation-camss-ife')
cells=lambda data:struct.unpack('>'+'I'*(len(data)//4),data)
regions=cells(f.getprop(node,'iommu-addresses'));cp=f.get_phandle(camss);assert regions==(cp,0,0,0,0x07400000,cp,0,0xe0000000,0,0x20000000)
assert cells(f.getprop(camss,'memory-region'))==(f.get_phandle(node),)
assert bytes(f.getprop(camss,'memory-region-names'))==b'ife-iova\0'
for absent in ['reg','size']:
 try:f.getprop(node,absent)
 except libfdt.FdtException as error:assert error.err==-libfdt.NOTFOUND
 else:raise AssertionError('unexpected physical memory property '+absent)
assert bytes(f.getprop(camss,'status'))==b'okay\0'
def strict(data):
 n=v.decode_dtb(data)[0]['reserved-memory']['reservation-camss-ife'];n['$nodename']=['reservation-camss-ife']
 # This common schema has no standalone selector; validate it explicitly.
 schema_id='http://devicetree.org/schemas/reserved-memory/reserved-memory.yaml'
 assert schema_id in v.schemas
 return list(v._schema_validator(schema_id).iter_errors(n))
assert not strict(raw)
# Strict schema checks actual reservation node in the pinned working schema.
# Exact phandle/range contract and no physical RAM reservation are also checked.
tests=[]
for name,prop,value in [('missing-addresses','iommu-addresses',None),('physical-size-added','size',struct.pack('>Q',0x7400000)),('wrong-phandle','iommu-addresses',struct.pack('>10I',0,0,0,0,0x7400000,0,0,0xe0000000,0,0x20000000))]:
 b=libfdt.Fdt(raw);b.resize(len(raw)+1024);n=b.path_offset('/reserved-memory/reservation-camss-ife')
 if value is None:b.delprop(n,prop)
 else:b.setprop(n,prop,value)
 data=bytes(b.as_bytearray());(out/('iova-'+name+'.dtb')).write_bytes(data);errors=strict(data)
 # Phandle validity is an exact cross-node contract, beyond schema shape.
 if name=='wrong-phandle':
  exact=cells(b.getprop(n,'iommu-addresses'))==regions;assert not exact;detected='exact-cross-node-contract'
 else:assert errors,(name,'schema selector must apply');detected='strict-schema'
 tests.append(dict(name=name,negative_detected=True,validator=detected,strict_errors=len(errors)))
report=dict(actual_dtb_two_exact_native_window_exclusion_ranges=True,low_excluded_end_exclusive=0x07400000,high_excluded_start=0xe0000000,high_end_exclusive=0x100000000,memory_region_phandle_matches=True,no_reg_or_size_no_physical_ram_reservation=True,camss_disabled=False,pinned_schema_version='2026.9',future_main_schema_requires_iommu_ranges_migration=True,strict_actual_reservation_no_errors=True,negative_controls=tests,phone_unchanged=True)
(r/'reference/kernel126/iova-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('IOVA125_ACTUAL_DTB_NATIVE_FULL_WINDOW_AND_STRICT_RESERVATION_SCHEMA_PASS')
