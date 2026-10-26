from pathlib import Path
import runpy,json,re,difflib,subprocess,hashlib
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel123'
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera123/kernel')
report=json.loads((ref/'source-contract-validation.json').read_text())
assert report['smmu_sid_masks_exact'] and report['native_hf_axi_clock_present']
source=Path('/mnt/e/edk2-samurai-out/kernel117/camera-dt-reference/0056-arm64-dts-sm8150-add-the-camera-subsystem.patch')
node='\n'.join(l[1:] for l in source.read_text().splitlines() if l.startswith('+') and not l.startswith('+++'))+'\n'
assert node.count('status = "disabled";')==1
icc='''\t\t\tinterconnects = <&gem_noc MASTER_AMPSS_M0 0 &config_noc SLAVE_CAMERA_CFG 0>,
\t\t\t\t\t<&mmss_noc MASTER_CAMNOC_HF0 0 &mc_virt SLAVE_EBI_CH0 0>,
\t\t\t\t\t<&mmss_noc MASTER_CAMNOC_SF 0 &mc_virt SLAVE_EBI_CH0 0>,
\t\t\t\t\t<&camnoc_virt MASTER_CAMNOC_HF0_UNCOMP 0 &camnoc_virt SLAVE_CAMNOC_UNCOMP 0>;
\t\t\tinterconnect-names = "cam_ahb", "cam_hf_0_mnoc",
\t\t\t\t\t     "cam_sf_0_mnoc", "cam_hf_0_camnoc";

'''
anchor='\t\t\tiommus =';assert node.count(anchor)==1;node=node.replace(anchor,icc+anchor)
changes=[]
name='arch/arm64/boot/dts/qcom/sm8150.dtsi';p=k/name;before=p.read_text()
assert 'camss: camss@' not in before and before.count('\t\tcamcc: clock-controller@ad00000 {')==1
after=before.replace('\t\tcamcc: clock-controller@ad00000 {',node+'\t\tcamcc: clock-controller@ad00000 {');p.write_text(after);changes.append((name,before,after))
name='drivers/media/platform/qcom/camss/camss.c';p=k/name;before=p.read_text();t=before
table='''static const struct resources_icc icc_res_8150[] = {
\t{
\t\t.name = "cam_ahb",
\t\t.icc_bw_tbl.avg = 38400,
\t\t.icc_bw_tbl.peak = 76800,
\t},
\t{
\t\t.name = "cam_hf_0_mnoc",
\t\t.icc_bw_tbl.avg = 2097152,
\t\t.icc_bw_tbl.peak = 2097152,
\t},
\t{
\t\t.name = "cam_sf_0_mnoc",
\t\t.icc_bw_tbl.avg = 0,
\t\t.icc_bw_tbl.peak = 2097152,
\t},
\t{
\t\t.name = "cam_hf_0_camnoc",
\t\t.icc_bw_tbl.avg = 2097152,
\t\t.icc_bw_tbl.peak = 2097152,
\t},
};

'''
anchor='static const struct camss_resources sm8150_resources = {\n\t.version = CAMSS_8150,\n'
assert t.count(anchor)==1;t=t.replace(anchor,table+anchor+'\t.icc_res = icc_res_8150,\n\t.icc_path_num = ARRAY_SIZE(icc_res_8150),\n')
a=t.index('static const struct camss_subdev_resources vfe_res_8150[]');b=t.index('static const struct camss_subdev_resources csiphy_res_8250[]',a)
block=t[a:b];assert block.count('.clock = { "camnoc_axi", "cpas_ahb", "slow_ahb_src",')==2
block=block.replace('.clock = { "camnoc_axi", "cpas_ahb", "slow_ahb_src",','.clock = { "camnoc_axi", "cpas_ahb", "gcc_camera_axi", "slow_ahb_src",')
needle='.clock_rate = { { 0 },\n\t\t\t\t{ 0 },\n\t\t\t\t{ 80000000 },';assert block.count(needle)==2
block=block.replace(needle,'.clock_rate = { { 0 },\n\t\t\t\t{ 0 },\n\t\t\t\t{ 0 },\n\t\t\t\t{ 80000000 },');t=t[:a]+block+t[b:]
needle='\tret = dma_set_mask_and_coherent(dev, 0xffffffff);';assert t.count(needle)==1
t=t.replace(needle,'''\t/*
\t * The native SM8150 IFE IOVA region ends at 0xe0000000.
\t * Keep allocations below that upper bound during bring-up. This mask
\t * does not encode the native 0x07400000 lower reserved boundary.
\t */
\tif (camss->res->version == CAMSS_8150)
\t\tret = dma_set_mask_and_coherent(dev, DMA_BIT_MASK(31));
\telse
\t\tret = dma_set_mask_and_coherent(dev, 0xffffffff);''')
p.write_text(t);changes.append((name,before,t))
names=re.findall(r'"([^\"]+)"',node.split('clock-names = ')[1].split(';')[0]);assert len(names)==31
regs=['csid0','csid1','csiphy0','csiphy1','csiphy2','csiphy3','vfe0','vfe1']
schema='''# SPDX-License-Identifier: (GPL-2.0 OR BSD-2-Clause)
%YAML 1.2
---
$id: http://devicetree.org/schemas/media/qcom,sm8150-camss.yaml#
$schema: http://devicetree.org/meta-schemas/core.yaml#

title: Qualcomm SM8150 CAMSS ISP

maintainers:
  - Robert Foss <robert.foss@linaro.org>

description: |
  SM8150 contains four CSI PHYs and two full image front ends. Board
  supplies and sensor endpoints must be described before enabling CAMSS.
  This local bring-up binding covers the current full-IFE resource subset;
  lite front ends and ICP are not represented.

properties:
  compatible:
    const: qcom,sm8150-camss

'''
for prop,count,items in [('clocks',31,None),('clock-names',None,names),('reg',8,None),('reg-names',None,regs),('interrupts',8,None),('interrupt-names',None,regs),('iommus',8,None),('power-domains',3,None),('power-domain-names',None,['ife0','ife1','top']),('interconnects',4,None),('interconnect-names',None,['cam_ahb','cam_hf_0_mnoc','cam_sf_0_mnoc','cam_hf_0_camnoc'])]:
    schema+=f'  {prop}:\n'
    if count:schema+=f'    minItems: {count}\n    maxItems: {count}\n'
    else:schema+='    items:\n'+''.join(f'      - const: {item}\n' for item in items)
    schema+='\n'
schema+='''  vdda-phy-supply:
    description: Board PHY supply used by the current CAMSS resource table.

  vdda-pll-supply:
    description: Board PLL supply used by the current CAMSS resource table.

  ports:
    $ref: /schemas/graph.yaml#/properties/ports
    properties:
'''
for i in range(4):
    schema+=f'''      port@{i}:
        $ref: /schemas/graph.yaml#/$defs/port-base
        unevaluatedProperties: false
        properties:
          endpoint:
            $ref: video-interfaces.yaml#
            unevaluatedProperties: false
            properties:
              data-lanes:
                minItems: 1
                maxItems: 4
              bus-type:
                enum: [1, 4]
            required:
              - data-lanes
'''
schema+='''
required:
  - compatible
  - clocks
  - clock-names
  - reg
  - reg-names
  - interrupts
  - interrupt-names
  - iommus
  - power-domains
  - power-domain-names
  - interconnects
  - interconnect-names

allOf:
  - if:
      not:
        properties:
          status:
            const: disabled
        required:
          - status
    then:
      required:
        - vdda-phy-supply
        - vdda-pll-supply

additionalProperties: false
'''
name='Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml';p=k/name;assert not p.exists();p.write_text(schema);changes.append((name,'',schema))
patch=''.join(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name)) for name,a,b in changes)
(ref/'sm8150-camss-path-7.3.patch').write_text(patch)
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss','arch/arm64/boot/dts/qcom/sm8150.dtsi'],cwd=k,check=True)
report=dict(candidate=123,camss_node_disabled=True,native_mmio_irq_smmu_matched=True,clock_names=names,icc_paths=4,conservative_dma_bits=31,lower_iova_guard_pending=True,native_hf_bridge_requested_by_both_vfes=True,provisional_local_binding_added=True,enabled_binding_requires_board_supplies=True,native_analog_supply_model_pending=True,qos_not_blindly_ported=True,cphy_still_pending=True,no_sensor_or_pmic_nodes_created=True,phone_unchanged=True,patch_sha256=hashlib.sha256(patch.encode()).hexdigest())
(ref/'camss-path-port-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
