from pathlib import Path
import re,json,hashlib,runpy,urllib.request
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel123';out=Path('/mnt/e/edk2-samurai-out/kernel123');out.mkdir(exist_ok=True)
runpy.run_path(str(root/'reference/kernel118/ensure-build-volume.py'))
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
k=Path('/home/cy122/pmos-samurai-kernel118/camera121/kernel')
base=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616')
commit='47087509c4289c2580c54f5433e55366b2e00445';verified=[]
for prefix in ['0055','0066','0067','0075','0076']:
    paths=list(base.glob(prefix+'*'));assert len(paths)==1;p=paths[0]
    url=f'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/{commit}/aports/device/testing/linux-oneplus-hotdog-mainline616/{p.name}'
    data=urllib.request.urlopen(url,timeout=30).read();assert data==p.read_bytes()
    verified.append(dict(file=p.name,url=url,sha256=hashlib.sha256(data).hexdigest()))
p=Path('/mnt/e/edk2-samurai-out/kernel117/camera-dt-reference/0056-arm64-dts-sm8150-add-the-camera-subsystem.patch')
url=f'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/{commit}/aports/device/testing/linux-oneplus-hotdog-mainline616/{p.name}'
data=urllib.request.urlopen(url,timeout=30).read();assert data==p.read_bytes();verified.append(dict(file=p.name,url=url,sha256=hashlib.sha256(data).hexdigest()))
exec((root/'reference/kernel120/extract-own-resources.py').read_text().split('records=[]')[0].replace("out=Path('/mnt/e/edk2-samurai-out/kernel120');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')",'unused=None'))
# Reuse only the parser helpers; no older reports are rewritten.
camera=own/'arch/arm64/boot/dts/19781/sm8150-camera.dtsi';text=clean(camera.read_text());resources=[]
for label in ['cam_csid0','cam_csid1','csiphy0','csiphy1','csiphy2','csiphy3','cam_vfe0','cam_vfe1']:
    matches=list(nodes(text,rf'{label}:\s*[^\s{{]+'));assert len(matches)==1,label
    pr=props(matches[0][1]);resources.append(dict(label=label,reg=pr['reg'],interrupts=pr['interrupts']))
print('OWN_RESOURCES',json.dumps(resources))
expected_regs=[0xacb3000,0xacba000,0xac65000,0xac66000,0xac67000,0xac68000,0xacaf000,0xacb6000]
expected_irqs=[464,466,477,478,479,448,465,467]
for i,item in enumerate(resources):
    assert int(re.findall('0x[0-9a-fA-F]+',item['reg'])[0],16)==expected_regs[i]
    assert int(re.findall(r'\d+',item['interrupts'])[1])==expected_irqs[i]
matches=list(nodes(text,r'msm_cam_smmu_ife'));assert len(matches)==1
pr=props(matches[0][1]);sid=[int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+',pr['iommus'])]
assert sid==[0x840,0x620,0x860,0x620,0xa40,0x620,0xa60,0x620,0xc40,0x620,0xc60,0x620,0xe40,0x620,0xe60,0x620]
start=int(re.findall('0x[0-9a-fA-F]+',pr['iova-region-start'])[0],16);length=int(re.findall('0x[0-9a-fA-F]+',pr['iova-region-len'])[0],16)
assert (start,start+length)==(0x7400000,0xe0000000)
cpas=list(nodes(text,r'qcom,cam-cpas@[a-f0-9]+'));assert len(cpas)==1
cp=props(cpas[0][1]);assert 'GCC_CAMERA_HF_AXI_CLK' in cp['clocks']
inter=(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text()
for label in ['gem_noc','config_noc','mmss_noc','mc_virt','camnoc_virt']:assert re.search(rf'{label}:',inter)
header=(k/'include/dt-bindings/interconnect/qcom,sm8150.h').read_text()
for symbol in ['MASTER_AMPSS_M0','SLAVE_CAMERA_CFG','MASTER_CAMNOC_HF0','MASTER_CAMNOC_SF','SLAVE_EBI_CH0','MASTER_CAMNOC_HF0_UNCOMP','SLAVE_CAMNOC_UNCOMP']:assert re.search(rf'#define\s+{symbol}\s+',header)
report=dict(reference_commit=commit,remote_reference_patches_byte_equal=verified,own_camera_source_sha256=hashlib.sha256(camera.read_bytes()).hexdigest(),native_mmio_irq_resources=resources,smmu_sid_masks_exact=True,native_iova_start=start,native_iova_end_exclusive=start+length,conservative_31bit_dma_mask_upper_bound_below_native_end=True,lower_iova_guard_not_proven=True,native_hf_axi_clock_present=True,current_interconnect_providers_and_ids_exist=True,qos_revision_and_cphy_pending=True,phone_unchanged=True)
(ref/'source-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CAMSS_NATIVE_AND_PINNED_SOURCE_CONTRACT_PASS')
