from pathlib import Path
import runpy,re,hashlib,json,urllib.request
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel124';out=Path('/mnt/e/edk2-samurai-out/kernel124');out.mkdir(exist_ok=True)
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source');k=Path('/home/cy122/pmos-samurai-rootfs122/camera123/kernel')
def block(text,marker):
    pos=text.index(marker);a=text.index('{',pos);i=a+1;depth=1
    while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[a:i]
def records(text):return [(int(a,16),int(b,16),int(c,16),d) for a,b,c,d in re.findall(r'\{\s*(0x[\da-fA-F]+),\s*(0x[\da-fA-F]+),\s*(0x[\da-fA-F]+),\s*(CSIPHY_\w+)\s*\}',text)]
commit='47087509c4289c2580c54f5433e55366b2e00445';name='0089-media-qcom-camss-add-SM8150-C-PHY-support.patch'
p=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616')/name
url=f'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/{commit}/aports/device/testing/linux-oneplus-hotdog-mainline616/{name}'
data=urllib.request.urlopen(url,timeout=30).read();assert data==p.read_bytes()
added='\n'.join(l[1:] for l in data.decode().splitlines() if l.startswith('+') and not l.startswith('+++'))
reference_table=block(added,'lane_regs_sm8150_cphy');reference_records=records(reference_table);assert len(reference_records)==129
inputs=[]
for family in ['camera','camera_8150','camera_7150','ais']:
    p=own/f'drivers/media/platform/msm/{family}/cam_sensor_module/cam_csiphy/include/cam_csiphy_1_1_hwreg.h'
    table=block(p.read_text(),'csiphy_3ph_v1_1_reg');rr=records(table)
    differences=[dict(index=i,native=x,reference=y) for i,(x,y) in enumerate(zip(rr,reference_records)) if x!=y]
    print('VARIANT',family,'tuple_count',len(rr),'mismatch_count',len(differences),'first',differences[:4])
    inputs.append(dict(source_family=family,header_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),tuple_count=len(rr),three_trios_43_tuples_each_exact=rr==reference_records,differences=differences,table_sha256=hashlib.sha256(json.dumps(rr).encode()).hexdigest()))
active=next(x for x in inputs if x['source_family']=='camera_8150')
assert active['tuple_count']==129
assert [(d['native'][0],d['native'][1],d['reference'][1]) for d in active['differences']]==[(0x9b0,0x24,0x23),(0xab0,0x24,0x23),(0xbb0,0x24,0x23)]
active_header=own/'drivers/media/platform/msm/camera_8150/cam_sensor_module/cam_csiphy/include/cam_csiphy_1_1_hwreg.h'
native_table=block(active_header.read_text(),'csiphy_3ph_v1_1_reg');assert '#if' not in native_table
native_records=records(native_table)
make=(own/'drivers/media/platform/msm/Makefile').read_text();assert 'TARGET_PRODUCT:=msmnile' in make and 'obj-$(CONFIG_SPECTRA_CAMERA) += camera_8150/' in make
camera=own/'arch/arm64/boot/dts/19781/sm8150-camera.dtsi';text=camera.read_text()
for label in ['cam_csiphy0','cam_csiphy1','cam_csiphy2','cam_csiphy3']:
    body=block(text,label+':');assert 'mipi-csi-vdd-supply = <&pm8150l_l3>' in body and 'csi-vdd-voltage = <1200000>' in body
mainline=k/'arch/arm64/boot/dts/qcom/sm8150-mtp.dts'
assert mainline.exists();common=mainline.read_text();rail=block(common,'vreg_l3c_1p2:')
assert 'regulator-min-microvolt = <1200000>' in rail and 'regulator-max-microvolt = <1200000>' in rail
parent=common[:common.index('vreg_l3c_1p2:')];assert 'qcom,pm8150l-rpmh-regulators' in parent[-7000:] and 'qcom,pmic-id = "c"' in parent[-7000:]
assert 'vdda-supply = <&vreg_l3c_1p2>' in (k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_text()
hits=[]
for p in (own/'drivers/media/platform/msm/camera_8150').rglob('*.c'):
    t=p.read_text(errors='replace')
    if any(s in t for s in ['mipi-csi-vdd','csi-vdd-voltage']):hits.append(str(p.relative_to(own)))
report=dict(reference_commit=commit,reference_url=url,reference_patch_sha256=hashlib.sha256(data).hexdigest(),native_cphy_header_variants=inputs,active_vendor_source_family='camera_8150',native_cphy_register_tuple_count=129,own_four_csiphys_declared_l3_1200000=True,mainline_l3c_is_pm8150l_ldo3_1200000=True,rail_already_shared_with_dsi=True,source_mapping_not_electrical_measurement=True,native_custom_supply_property_consumers=hits,qos_requires_runtime_revision_read=True,phone_unchanged=True)
(out/'cphy-table-reference-private.h').write_text('static const struct csiphy_lane_regs lane_regs_sm8150_cphy[3][43] = '+reference_table+';\n')
table='static const struct csiphy_lane_regs lane_regs_sm8150_cphy[3][43] = {\n'
for i in range(3):
    table+='\t{\n'+''.join(f'\t\t{{0x{a:04x}, 0x{b:02x}, 0x{c:02x}, {d}}},\n' for a,b,c,d in native_records[i*43:(i+1)*43])+'\t},\n'
table+='};\n'
(out/'cphy-table-native-private.h').write_text(table)
(ref/'native-phy-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
core=own/'drivers/media/platform/msm/camera_8150/cam_sensor_module/cam_csiphy/cam_csiphy_core.c';t=core.read_text();a=t.index('int32_t cam_csiphy_config_dev');print('NATIVE_SETTLE_AND_MASK',t[a:a+5000])
