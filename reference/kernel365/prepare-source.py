"""Describe dormant SM8150 ICP resources and its board-owned firmware RAM."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel365');P.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
git=lambda *args:subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
assert json.loads((HERE.parent/'kernel364/live-reference-diagnosis.json').read_text())['passed']
parent=json.loads((HERE.parent/'kernel364/source-state.json').read_text())['commit'];assert git('rev-parse','HEAD')==parent
diagnostic='drivers/media/platform/qcom/camss/camss-icp-a5-boot-test.c'
assert (source/diagnostic).read_bytes()==(HERE.parent/'kernel364/camss-icp-a5-boot-test.c').read_bytes()
assert git('status','--porcelain')=='M '+diagnostic
subprocess.run(['git','-C',str(source),'add','--',diagnostic],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: diagnose unresolved firmware memory before A5 resources'],check=True,capture_output=True)
diagnostic_commit=git('rev-parse','HEAD')
subprocess.run(['git','-C',str(source),'switch','-c','samurai-icp-board-dt365'],check=True,capture_output=True)
clock_header=(source/'include/dt-bindings/clock/qcom,sm8150-camcc.h').read_text()
ids={int(v):n for n,v in re.findall(r'^#define\s+(CAM_CC_\w+)\s+(\d+)\s*$',clock_header,re.M) if not n.endswith(('_BCR','_GDSC'))}
numbers=[38,43,45,44,11,12,13,15,14,70,71,72,74,73,75,76,77,74,78]
names=['fast_ahb_src','icp_ahb','icp_src','icp','bps_ahb','bps_areg','bps_axi','bps_src','bps','ipe0_ahb','ipe0_areg','ipe0_axi','ipe_src','ipe0','ipe1_ahb','ipe1_areg','ipe1_axi','ipe1_src','ipe1']
assert len(numbers)==len(names)==19
soc_path=source/'arch/arm64/boot/dts/qcom/sm8150.dtsi';soc=soc_path.read_text();assert 'camss_icp:' not in soc
node='''		/* A5 firmware backend; board memory and a driver are needed to enable it. */
		camss_icp: icp@ac10000 {
			compatible = "qcom,sm8150-camss-icp";
			reg = <0 0x0ac10000 0 0x8000>,
			      <0 0x0ac6f000 0 0x3000>,
			      <0 0x0ac87000 0 0x3000>,
			      <0 0x0ac91000 0 0x3000>;
			reg-names = "sierra", "bps", "ipe0", "ipe1";
			interrupts = <GIC_SPI 463 IRQ_TYPE_EDGE_RISING>;
			qcom,camss = <&camss>;
			iommus = <&apps_smmu 0x2222 0>;
'''
node+='\t\t\tclocks = '+',\n\t\t\t\t '.join('<&camcc '+ids[i]+'>' for i in numbers)+';\n'
node+='\t\t\tclock-names = '+',\n\t\t\t\t      '.join('"'+n+'"' for n in names)+';\n'
node+='''			power-domains = <&camcc BPS_GDSC>, <&camcc IPE_0_GDSC>,
					<&camcc IPE_1_GDSC>;
			power-domain-names = "bps", "ipe0", "ipe1";
			resets = <&camcc CAM_CC_ICP_BCR>;
			reset-names = "icp";
			#address-cells = <2>;
			#size-cells = <2>;
			status = "disabled";
		};

'''
soc_path.write_text(soc.replace('\t\tcamss: camss@acb3000 {',node+'\t\tcamss: camss@acb3000 {',1))
board_path=source/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';board=board_path.read_text()
assert 'camera_mem: memory@9ab00000' in board and '&camss_icp {' not in board
board+='''
/* Original 19781 board reservation. The unvalidated ICP backend stays dormant. */
&camss_icp {
	memory-region = <&camera_mem>;
	memory-region-names = "firmware";
};
'''
board_path.write_text(board)
changed=['arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
patch=subprocess.check_output(['git','-C',str(source),'diff','--',*changed]);(HERE/'static-icp-board.patch').write_bytes(patch)
subprocess.run(['git','-C',str(source),'add','--',*changed],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','arm64: dts: qcom: describe dormant SM8150 ICP and Realme firmware memory'],check=True,capture_output=True)
report=dict(stage=365,source=str(source),parent=diagnostic_commit,diagnostic_parent=parent,commit=git('rev-parse','HEAD'),branch='samurai-icp-board-dt365',changed=changed,
    soc_resources_from_verified355=True,board_firmware_reservation_unchanged=True,icp_default_disabled=True,installed=False,
    planned_kernel_image_stage=363,planned_module_release='7.3.0-rc6-rmx1931-samurai-k363+',dt_only_boot_change=True,
    sha256={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in changed})
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
