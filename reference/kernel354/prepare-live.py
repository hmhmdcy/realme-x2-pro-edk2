from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';directory=source/'drivers/media/platform/qcom/camss'
device=json.loads((P/'runtime-prerequisites-private.json').read_text());assert device['boot_matches'] and device['iommu_cells']==2
phandle=device['phandle']
dts='''/dts-v1/;
/plugin/;
/ {
 fragment@0 {
  target-path = "/reserved-memory";
  __overlay__ {
   a5_fw_iova: samurai-icp354-fw-iova {
    iommu-addresses = <&a5_memory_test 0 0 0 0x500000>;
   };
  };
 };
 fragment@1 {
  target-path = "/soc@0";
  __overlay__ {
   a5_memory_test: samurai-icp354-memory {
    compatible = "realme,samurai-a5-icp-memory-test";
    #address-cells = <2>;
    #size-cells = <2>;
    iommus = <PHANDLE 0x2222 0>;
    memory-region = <&a5_fw_iova>;
    status = "okay";
   };
  };
 };
};
'''.replace('PHANDLE',str(phandle))
(P/'memory-test-private.dts').write_text(dts)
q=subprocess.run([str(build/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(P/'memory-test-private.dtbo'),str(P/'memory-test-private.dts')],capture_output=True)
(P/'dtc-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
decoded=subprocess.check_output([str(build/'scripts/dtc/dtc'),'-I','dtb','-O','dts',str(P/'memory-test-private.dtbo')],stderr=subprocess.DEVNULL,text=True)
assert '__symbols__' not in decoded and '__fixups__' not in decoded and '__local_fixups__' in decoded
raw=(P/'memory-test-private.dtbo').read_bytes();target=build/'drivers/media/platform/qcom/camss';target.mkdir(exist_ok=True)
(target/'camss-icp-a5-memory-test-blob.h').write_text('static const unsigned char a5_memory_test_overlay[] = {\n'+','.join('0x%02x'%b for b in raw)+'\n};\n')
(directory/'camss-icp-a5-memory-test.c').write_text((HERE/'camss-icp-a5-memory-test.c').read_text())
print(json.dumps(dict(dtbo_bytes=len(raw),smmu_phandle=phandle,firmware_sid='0x2222',persistent_dt_changed=False),indent=2))
