from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build()
facts=json.loads((P/'resource-prerequisites-private.json').read_text());assert facts['boot_matches']
camss=facts['camss@acb3000']['phandle'];cc=facts['clock-controller@ad00000']['phandle']
clock_ids=[38,43,45,44,11,12,13,15,14,70,71,72,74,73,75,76,77,74,78]
names=['fast_ahb_src','icp_ahb','icp_src','icp','bps_ahb','bps_areg','bps_axi','bps_src','bps','ipe0_ahb','ipe0_areg','ipe0_axi','ipe_src','ipe0','ipe1_ahb','ipe1_areg','ipe1_axi','ipe1_src','ipe1']
dts='/dts-v1/;\n/plugin/;\n/ { fragment@0 { target-path = "/soc@0"; __overlay__ {\n samurai-icp355-power@ac10000 {\n compatible = "realme,samurai-a5-icp-power-test";\n'
dts+='reg = <0 0xac10000 0 0x8000>, <0 0xac6f000 0 0x3000>, <0 0xac87000 0 0x3000>, <0 0xac91000 0 0x3000>;\nreg-names = "sierra", "bps", "ipe0", "ipe1";\n'
dts+=f'qcom,camss = <{camss}>;\npower-domains = <{cc} 1>, <{cc} 4>, <{cc} 5>;\npower-domain-names = "bps", "ipe0", "ipe1";\n'
dts+='clocks = '+', '.join(f'<{cc} {i}>' for i in clock_ids)+';\nclock-names = '+', '.join('"'+n+'"' for n in names)+';\n}; }; }; };\n'
src=P/'power-test-private.dts';src.write_text(dts);out=P/'power-test-private.dtbo'
q=subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(out),str(src)],capture_output=True);(P/'dtc-private.log').write_bytes(q.stderr);q.check_returncode()
blob=out.read_bytes();header=build/'drivers/media/platform/qcom/camss/camss-icp-a5-power-test-blob.h'
header.write_text('static const unsigned char a5_power_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
(P/'live-overlay-state-private.json').write_text(json.dumps(dict(bytes=len(blob),camss=camss,camcc=cc,clocks=len(clock_ids),generated_header=str(header)),indent=2)+'\n')
print(json.dumps(dict(overlay_bytes=len(blob),clocks=len(clock_ids))))
