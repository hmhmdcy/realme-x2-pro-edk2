from pathlib import Path
import hashlib,importlib.util,json,re,shutil,struct,subprocess,sys,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;state=json.loads((HERE/'source-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
build=m.mounted_build();source=build.parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
start=time.monotonic();release=(build/'include/config/kernel.release').read_text().strip()
new=P/'samurai389-private.dtb'
if '--verify-only' not in sys.argv:
 assert not (P/'dt-build-private.log').exists()
 q=subprocess.run(['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1','KERNELRELEASE='+release,'qcom/sm8150-samurai.dtb'],capture_output=True)
 (P/'dt-build-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
 shutil.copyfile(build/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',new)
else:assert new.read_bytes()==(build/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
old=P.parent/'kernel365/samurai365-private.dtb'
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
before=ns['fdt_nodes'](old.read_bytes());nodes=ns['fdt_nodes'](new.read_bytes())
names=['firmware','shared','heap','trace','images'];ranges=[(0,0x500000),(0x7400000,0x9600000),(0x10a00000,0x100000),(0x10b00000,0x100000),(0x20000000,0x8000000)]
added={'/reserved-memory/reservation-icp-'+n for n in names}
assert set(nodes)-set(before)==added and not set(before)-set(nodes)
handles=lambda tree:{int.from_bytes(props['phandle'],'big'):path for path,props in tree.items() if 'phandle' in props}
old_handles=handles(before);new_handles=handles(nodes)
allowed_icp={'status','firmware-name','iommus','memory-region','memory-region-names','phandle'}
references={'clocks','assigned-clocks','assigned-clock-parents','memory-region','remote-endpoint','interconnects','power-domains','interrupt-parent','operating-points-v2','required-opps','phys','io-channels','thermal-sensors','trip','cooling-device','sound-dai','remoteproc','gpio-ranges','interrupts-extended','dmas','qcom,smem-states','slim-ifc-dev','iommu-addresses','iommus','qcom,camss','hwlocks','mboxes','interrupt-map','iommu-map','msi-map','resets'}
references.update({'gpio','gpios','lens-focus','nvmem-cells','qcom,gmu','qcom,bcm-voters','qcom,qmp','qcom,address-setup-supplier','wakeup-parent'})
is_reference=lambda key:key in references or key.endswith(('-supply','-gpios','-gpio')) or re.fullmatch(r'pinctrl-\d+',key)
unknown=[(path,key) for path,props in before.items() for key in props.keys()|nodes[path].keys() if props.get(key)!=nodes[path].get(key) and key!='phandle' and not (path=='/soc@0/icp@ac10000' and key in allowed_icp) and not is_reference(key)]
assert not unknown,sorted(unknown)
renumbered=0;changed={}
for path,props in before.items():
 for key in props.keys()|nodes[path].keys():
  a=props.get(key);b=nodes[path].get(key)
  if a==b:continue
  changed.setdefault(path,[]).append(key)
  if path=='/soc@0/icp@ac10000' and key in allowed_icp:continue
  if key=='phandle':
   assert a is not None and b is not None and old_handles[int.from_bytes(a,'big')]==new_handles[int.from_bytes(b,'big')]==path
   continue
  assert is_reference(key),(path,key)
  assert a is not None and b is not None and len(a)==len(b) and len(a)%4==0,(path,key)
  for i in range(0,len(a),4):
   x=int.from_bytes(a[i:i+4],'big');y=int.from_bytes(b[i:i+4],'big')
   if x==y:continue
   assert x in old_handles and y in new_handles and old_handles[x]==new_handles[y],(path,key,i)
   renumbered+=1
icp=nodes['/soc@0/icp@ac10000'];camera=nodes['/reserved-memory/memory@9ab00000']
assert icp['status']==b'okay\0' and icp['firmware-name']==b'qcom/sm8150/camera-icp.elf\0'
assert camera['reg']==before['/reserved-memory/memory@9ab00000']['reg'] and 'no-map' in camera
assert icp['memory-region-names'].split(b'\0')[:-1]==[b'firmware',b'firmware-iova',b'shared',b'heap',b'trace',b'images']
assert [new_handles[x] for x in struct.unpack('>6I',icp['memory-region'])]==['/reserved-memory/memory@9ab00000']+['/reserved-memory/reservation-icp-'+n for n in names]
specs=[(0x2222,0),(0x2080,0x20),(0x20a0,0x20),(0x2100,0x20),(0x2120,0x20),(0x20c0,0),(0x2140,0)]
words=struct.unpack('>21I',icp['iommus']);assert [(words[i+1],words[i+2]) for i in range(0,21,3)]==specs
assert len({new_handles[words[i]] for i in range(0,21,3)})==1
for name,(address,size) in zip(names,ranges):
 props=nodes['/reserved-memory/reservation-icp-'+name];assert not {'reg','no-map'}&props.keys()
 words=struct.unpack('>5I',props['iommu-addresses']);assert new_handles[words[0]]=='/soc@0/icp@ac10000' and words[1:]==(0,address,0,size)
diagnostics=[l for l in (P/'dt-build-private.log').read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()];assert not diagnostics
report=dict(stage=389,source_commit=state['commit'],seconds=round(time.monotonic()-start,2),dtb_bytes=new.stat().st_size,dtb_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),added_address_only_reservation_nodes=sorted(added),board_icp_enabled_in_candidate=True,seven_sid_specs=specs,firmware_reg_and_no_map_unchanged=True,no_additional_physical_ram_reserved=True,all_other_dt_properties_semantically_preserved=True,renumbered_reference_cells=renumbered,diagnostics=diagnostics,not_deployed=True,passed=True)
(HERE/'dt-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');(P/'dt-semantic-changes-private.json').write_text(json.dumps(changed,indent=2)+'\n');print(json.dumps(report,indent=2))
