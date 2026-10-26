from pathlib import Path
import runpy,json,hashlib,subprocess,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel123';out=Path('/mnt/e/edk2-samurai-out/kernel123')
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera123/kernel')
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss','arch/arm64/boot/dts/qcom/sm8150.dtsi'],cwd=k,check=True,timeout=90)
dt=(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text();cam=(k/'drivers/media/platform/qcom/camss/camss.c').read_text()
a=dt.index('camss: camss@');b=dt.index('camcc: clock-controller@',a);node=dt[a:b]
names=re.findall(r'"([^\"]+)"',node.split('clock-names = ')[1].split(';')[0]);assert len(names)==31
assert 'status = "disabled";' in node and 'icc_res_8150' in cam and 'DMA_BIT_MASK(31)' in cam
a=cam.index('static const struct camss_subdev_resources vfe_res_8150[]');b=cam.index('static const struct camss_subdev_resources csiphy_res_8250[]',a)
assert cam[a:b].count('"gcc_camera_axi"')==2
patch=(ref/'sm8150-camss-path-7.3.patch').read_bytes()
port=dict(candidate=123,camss_node_disabled=True,native_mmio_irq_smmu_matched=True,clock_names=names,icc_paths=4,conservative_dma_bits=31,lower_iova_guard_pending=True,native_hf_bridge_requested_by_both_vfes=True,provisional_local_binding_added=True,enabled_binding_requires_board_supplies=True,native_analog_supply_model_pending=True,qos_not_blindly_ported=True,cphy_still_pending=True,no_sensor_or_pmic_nodes_created=True,phone_unchanged=True,patch_sha256=hashlib.sha256(patch).hexdigest(),source_whitespace_check_pass=True)
(ref/'camss-path-port-validation.json').write_text(json.dumps(port,indent=2)+'\n')
assert 'error:' not in (out/'kernel-full-build.log').read_text().lower()
artifacts=[]
for rel,label in [('arch/arm64/boot/Image','Image'),('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','DTB'),('drivers/media/platform/qcom/camss/qcom-camss.ko','CAMSS')]:
    p=k/rel;data=p.read_bytes();assert data
    (out/(label+'-k123-private')).write_bytes(data)
    artifacts.append(dict(artifact=label,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
identity=subprocess.check_output(['strings',str(k/'vmlinux')],text=True)
lines=[l for l in identity.splitlines() if l.startswith('Linux version 7.')];assert lines and all('#123 SMP' in line for line in lines)
report=dict(candidate=123,full_image_modules_dtb_build_pass=True,module_count=len(list(k.rglob('*.ko'))),artifacts=artifacts,matching_full_rootfs123_not_generated=True,not_deployed=True,goal_complete=False)
assert report['module_count']==770
(ref/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
