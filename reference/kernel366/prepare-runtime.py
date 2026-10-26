"""Use only static-board firmware references in the temporary A5 experiment."""
from pathlib import Path
import importlib.util,json,re,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'postboot-validation.json').read_text())['firmware_reference_matches_live_board']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==json.loads((HERE.parent/'kernel365/source-state.json').read_text())['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
base=(P.parent/'kernel365/samurai365-private.dtb').read_bytes();nodes=ns['fdt_nodes'](base)
phandle=lambda path:int.from_bytes(nodes[path]['phandle'],'big')
paths={'camss':'/soc@0/camss@acb3000','camcc':'/soc@0/clock-controller@ad00000','smmu':'/soc@0/iommu@15000000'}
facts=json.loads((P.parent/'kernel356/live-overlay-state-private.json').read_text());dts=(P.parent/'kernel356/boot-test-private.dts').read_text()
for key,path in paths.items():
 old=facts[key];new=phandle(path)
 # These external references do not participate in local overlay fixups.
 if key=='camss':dts=dts.replace('qcom,camss = <'+str(old)+'>','qcom,camss = <'+str(new)+'>')
 elif key=='smmu':dts=dts.replace('iommus = <'+str(old)+' ','iommus = <'+str(new)+' ')
 else:
  for name in ['clocks','power-domains','resets']:
   pattern=r'('+re.escape(name)+r' = )(.*?);'
   dts=re.sub(pattern,lambda m:m[1]+m[2].replace('<'+str(old)+' ','<'+str(new)+' ')+';',dts,flags=re.S)
 facts[key]=new
memory=phandle(facts['firmware_region_path']);assert nodes['/soc@0/icp@ac10000']['memory-region']==memory.to_bytes(4,'big')
dts=dts.replace('<&camera356>','<'+str(memory)+'>')
dts=re.sub(r' fragment@2 \{ target-path = "[^"]+"; camera356: __overlay__ \{ \}; \};', '',dts)
assert 'camera356' not in dts and 'fragment@2' not in dts
src=P/'boot-test-private.dts';assert not src.exists();src.write_text(dts);out=P/'boot-test-private.dtbo'
q=subprocess.run([str(build/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(out),str(src)],capture_output=True);(P/'dtc-private.log').write_bytes(q.stderr);q.check_returncode()
merged=P/'boot-test-merged-private.dtb'
subprocess.run([str(build/'scripts/dtc/fdtoverlay'),'-i',str(P.parent/'kernel365/samurai365-private.dtb'),'-o',str(merged),str(out)],check=True,capture_output=True)
after=ns['fdt_nodes'](merged.read_bytes())
assert all(after[path]==props for path,props in nodes.items())
assert after['/soc@0/samurai-icp356-boot@ac10000']['memory-region'][:4]==memory.to_bytes(4,'big')
facts.update(bytes=out.stat().st_size,existing_firmware_phandle=memory,static_board_reference_required=True,
    existing_dt_properties_untouched_by_overlay=True,offline_overlay_named_firmware_resolves=True)
(P/'live-overlay-state-private.json').write_text(json.dumps(facts,indent=2)+'\n')
header=build/'drivers/media/platform/qcom/camss/camss-icp-a5-boot-test-blob.h'
header.write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in out.read_bytes())+'\n};\n')
shutil.copyfile(HERE.parent/'kernel364/camss-icp-a5-boot-test.c',HERE/'camss-icp-a5-boot-test.c')
for name in ['build-intree.py','boot-worker.py','launch-boot.py','poll-boot.py']:
 s=(HERE.parent/'kernel364'/name).read_text().replace('stage=364','stage=366').replace('/var/lib/samurai/k364-boot-','/var/lib/samurai/k366-boot-')
 if name=='launch-boot.py':
  s=s.replace("facts=json.loads((P.parent/'kernel355/resource-prerequisites-private.json').read_text());assert facts['boot_matches']", "facts={n:dict(phandle=region[k]) for n,k in [('camss@acb3000','camss'),('clock-controller@ad00000','camcc'),('iommu@15000000','smmu')]}")
  s=s.replace("P.parent/'kernel363/postboot-adoption-private.json'","P/'postboot-adoption-private.json'")
  s=s.replace("['firmware_region_path','firmware_physical','firmware_bytes']","['firmware_region_path','firmware_physical','firmware_bytes','existing_firmware_phandle']")
 if name=='boot-worker.py':
  anchor=" assert (camera/'no-map').exists()"
  s=s.replace(anchor,anchor+"\n assert (camera/'phandle').read_bytes()==meta['existing_firmware_phandle'].to_bytes(4,'big')\n assert (dt/'soc@0/icp@ac10000/memory-region').read_bytes()==(camera/'phandle').read_bytes()")
 (HERE/name).write_text(s);compile(s,name,'exec')
report=dict(stage=366,prepared=True,existing_firmware_phandle=memory,all_existing_dt_properties_untouched=True,static_board_reference_used=True,firmware_cpu_not_started=True)
(HERE/'overlay-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
