from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build()
board=json.loads((HERE/'board-memory-validation.json').read_text())
physical=board['exact_board_source_camera_physical'];size=board['exact_board_source_camera_bytes']
region=board['mainline_camera_containing_reserved_ranges']
assert len(region)==1 and region[0]['start']==physical and region[0]['size']==size and region[0]['no_map']
facts=json.loads((P.parent/'kernel355/resource-prerequisites-private.json').read_text());assert facts['boot_matches']
camss=facts['camss@acb3000']['phandle'];cc=facts['clock-controller@ad00000']['phandle'];smmu=facts['iommu@15000000']['phandle']
irq=json.loads((P/'irq-parent-private.json').read_text())['interrupt_parent'];assert irq
clock_ids=[38,43,45,44,11,12,13,15,14,70,71,72,74,73,75,76,77,74,78]
names=['fast_ahb_src','icp_ahb','icp_src','icp','bps_ahb','bps_areg','bps_axi','bps_src','bps','ipe0_ahb','ipe0_areg','ipe0_axi','ipe_src','ipe0','ipe1_ahb','ipe1_areg','ipe1_axi','ipe1_src','ipe1']
dts='''/dts-v1/;
/plugin/;
/ {
 fragment@0 { target-path = "/reserved-memory"; __overlay__ {
  fw356: samurai-icp356-fw-iova { iommu-addresses = <&icp356 0 0 0 0x500000>; };
  sh356: samurai-icp356-shared-iova { iommu-addresses = <&icp356 0 0x07400000 0 0x09600000>; };
  heap356: samurai-icp356-heap-iova { iommu-addresses = <&icp356 0 0x10a00000 0 0x100000>; };
  trace356: samurai-icp356-trace-iova { iommu-addresses = <&icp356 0 0x10b00000 0 0x100000>; };
 }; };
 fragment@1 { target-path = "/soc@0"; __overlay__ {
  icp356: samurai-icp356-boot@ac10000 {
   compatible = "realme,samurai-a5-icp-boot-test";
   #address-cells = <2>; #size-cells = <2>;
   reg = <0 0xac10000 0 0x8000>, <0 0xac6f000 0 0x3000>, <0 0xac87000 0 0x3000>, <0 0xac91000 0 0x3000>;
   reg-names = "sierra", "bps", "ipe0", "ipe1";
'''
dts+=f'   qcom,camss = <{camss}>; iommus = <{smmu} 0x2222 0>;\n'
dts+='   memory-region = <&camera356>, <&fw356>, <&sh356>, <&heap356>, <&trace356>;\n'
dts+='   memory-region-names = "firmware", "firmware-iova", "shared", "heap", "trace";\n'
dts+=f'   power-domains = <{cc} 1>, <{cc} 4>, <{cc} 5>; power-domain-names = "bps", "ipe0", "ipe1";\n'
dts+=f'   resets = <{cc} 9>; reset-names = "icp";\n'
dts+=f'   interrupt-parent = <{irq}>; interrupts = <0 463 1>;\n'
dts+='   clocks = '+', '.join(f'<{cc} {i}>' for i in clock_ids)+';\n   clock-names = '+', '.join('"'+n+'"' for n in names)+';\n  }; }; }; };\n'
dts=dts.removesuffix('};\n')+' fragment@2 { target-path = "'+region[0]['path']+'"; camera356: __overlay__ { }; }; };\n'
src=P/'boot-test-private.dts';src.write_text(dts);out=P/'boot-test-private.dtbo'
q=subprocess.run([str(build/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(out),str(src)],capture_output=True);(P/'dtc-private.log').write_bytes(q.stderr);q.check_returncode()
decoded=subprocess.check_output([str(build/'scripts/dtc/dtc'),'-I','dtb','-O','dts',str(out)],stderr=subprocess.DEVNULL,text=True)
assert '__symbols__' not in decoded and '__fixups__' not in decoded and '__local_fixups__' in decoded
# Resolve the local reference into the existing board reservation offline.
merged=P/'boot-test-merged-private.dtb'
subprocess.run([str(build/'scripts/dtc/fdtoverlay'),'-i',str(build/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'),'-o',str(merged),str(out)],check=True,capture_output=True)
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
nodes=ns['fdt_nodes'](merged.read_bytes())
node=nodes['/soc@0/samurai-icp356-boot@ac10000'];camera=nodes[region[0]['path']]
assert node['memory-region-names'].split(b'\0')[:-1]==[b'firmware',b'firmware-iova',b'shared',b'heap',b'trace']
assert node['memory-region'][:4]==camera['phandle'] and 'no-map' in camera
assert camera['reg']==bytes.fromhex('00000000')+physical.to_bytes(4,'big')+bytes(4)+size.to_bytes(4,'big')
blob=out.read_bytes();header=build/'drivers/media/platform/qcom/camss/camss-icp-a5-boot-test-blob.h'
header.write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
(P/'live-overlay-state-private.json').write_text(json.dumps(dict(bytes=len(blob),camss=camss,camcc=cc,smmu=smmu,interrupt_parent=irq,generated_header=str(header),firmware_region_path=region[0]['path'],firmware_physical=physical,firmware_bytes=size,offline_overlay_named_firmware_resolves=True),indent=2)+'\n')
print(json.dumps(dict(overlay_bytes=len(blob),clocks=len(clock_ids),reserved_alias_regions=4,firmware_physical=hex(physical),named_firmware_resolves=True)))
