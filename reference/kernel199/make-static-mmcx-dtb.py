from pathlib import Path
import hashlib,json,struct,subprocess
import libfdt,dtschema
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel199');base=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb';raw=base.read_bytes();assert hashlib.sha256(raw).hexdigest()=='22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3';f=libfdt.Fdt(raw)
def snapshot(tree):
 result={}
 def walk(node,path):
  props={};off=tree.first_property_offset(node,quiet=libfdt.QUIET_NOTFOUND)
  while off>=0:
   p=tree.get_property_by_offset(off);props[p.name]=bytes(p);off=tree.next_property_offset(off,quiet=libfdt.QUIET_NOTFOUND)
  result[path]=props;child=tree.first_subnode(node,quiet=libfdt.QUIET_NOTFOUND)
  while child>=0:walk(child,path.rstrip('/')+'/'+tree.get_name(child));child=tree.next_subnode(child,quiet=libfdt.QUIET_NOTFOUND)
 walk(0,'/');return result
before=snapshot(f);camss='/soc@0/camss@acb3000';camcc='/soc@0/clock-controller@ad00000';old=before[camss]['power-domains'];assert len(old)==24 and before[camss]['power-domain-names']==b'ife0\0ife1\0top\0';specifier=before[camcc]['power-domains'];assert len(specifier)==8;provider,index=struct.unpack('>II',specifier);expected=int(subprocess.check_output(['aarch64-linux-gnu-gcc','-E','-P','-x','c','-I'+str(k/'include'),'-'],input=b'#include <dt-bindings/power/qcom,rpmhpd.h>\nSM8150_MMCX\n').decode().strip());assert index==expected and b'rpmhpd' in bytes(f.getprop(f.node_offset_by_phandle(provider),'compatible'))
f.resize(len(raw)+1024);node=f.path_offset(camss);f.setprop(node,'power-domains',old+specifier);f.setprop(node,'power-domain-names',b'ife0\0ife1\0top\0mmcx\0');f.pack();after=snapshot(f);assert set(before)==set(after);changes=[]
for path in before:
 assert set(before[path])==set(after[path])
 for name,value in before[path].items():
  if value!=after[path][name]:changes.append((path,name))
assert changes==[(camss,'power-domains'),(camss,'power-domain-names')] or sorted(changes)==sorted([(camss,'power-domains'),(camss,'power-domain-names')]);candidate=bytes(f.as_bytearray());p=out/'sm8150-samurai-mmcx-static-private.dtb';assert not p.exists();p.write_bytes(candidate)
validator=dtschema.DTValidator([str(out/'processed-camss-private.json')]);decoded=validator.decode_dtb(candidate)[0]['soc@0']['camss@acb3000'];decoded['$nodename']=['camss@acb3000'];errors=list(validator.iter_errors(decoded,filter=['qcom,sm8150-camss']));assert not errors,[e.message for e in errors];assert base.read_bytes()==raw
r=dict(stage=199,base_canonical_sha256=hashlib.sha256(raw).hexdigest(),candidate_sha256=hashlib.sha256(candidate).hexdigest(),candidate_bytes=len(candidate),source_dts_has_matching_four_domain_contract=True,changed_properties=[dict(node=a,property=b) for a,b in changes],all_other_nodes_properties_and_phandles_identical=True,nodes_checked=len(before),mmcx_index_from_actual_binding=index,strict_camss_node_schema_passed=True,base_dtb_file_unchanged=True,staged_for_boot_validation_only=True,not_flashed_or_booted=True);(ref/'static-dtb-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
