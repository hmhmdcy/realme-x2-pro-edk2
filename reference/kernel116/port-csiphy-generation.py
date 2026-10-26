from pathlib import Path
import difflib,subprocess,json
k=Path('/home/cy122/pmos-samurai-kernel116/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel116')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel116')
base=k/'drivers/media/platform/qcom/camss'
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/arch/arm64/boot/dts/19781/sm8150-camera.dtsi')
assert 'qcom,csiphy-v1.1' in own.read_text()
names=['camss.h','camss-csiphy-3ph-1-0.c','camss-vfe.c','camss.c'];patch=[]
for name in names:
    p=base/name;before=p.read_text();(out/(name+'.generation-before')).write_text(before)
    t=before
    if name=='camss.h':
        assert t.count('\tCAMSS_845,\n')==1;t=t.replace('\tCAMSS_845,\n','\tCAMSS_845,\n\tCAMSS_8150,\n')
    elif name=='camss-vfe.c':
        assert t.count('\tcase CAMSS_845:\n')==2;t=t.replace('\tcase CAMSS_845:\n','\tcase CAMSS_845:\n\tcase CAMSS_8150:\n')
    elif name=='camss.c':
        start=t.index('static const struct camss_resources sm8150_resources = {')
        end=t.index('static const struct camss_resources sm8250_resources',start)
        b=t[start:end];assert b.count('.version = CAMSS_845,')==1
        t=t[:start]+b.replace('.version = CAMSS_845,','.version = CAMSS_8150,')+t[end:]
    else:
        marker='\tcase CAMSS_845:\n';assert t.count(marker)==2
        t=t.replace(marker,marker+'\tcase CAMSS_8150:\n',1)
        marker='\t\tregs->lane_array_size = ARRAY_SIZE(lane_regs_sdm845);\n\t\tbreak;\n'
        assert t.count(marker)==1
        t=t.replace(marker,marker+'\t/* Own SM8150 DT declares v1.1; use the reference v1.1 lane table. */\n\tcase CAMSS_8150:\n\t\tregs->lane_regs = &lane_regs_sc8280xp[0];\n\t\tregs->lane_array_size = ARRAY_SIZE(lane_regs_sc8280xp);\n\t\tbreak;\n')
    p.write_text(t)
    rel='drivers/media/platform/qcom/camss/'+name
    patch.extend(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(ref/'camss-sm8150-csiphy-generation.patch').write_text(''.join(patch))
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss'],cwd=k,check=True)
report=dict(kernel_candidate=116,own_dt_declares_csiphy_v1_1=True,separate_camss_8150_version=True,
 reference_v1_1_lane_table_selected=True,cphy_not_ported=True,dma_icc_qos_not_ported=True,
 board_camera_nodes_not_enabled=True,not_deployed=True,goal_complete=False)
for folder in [out,ref]: (folder/'camss-generation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
